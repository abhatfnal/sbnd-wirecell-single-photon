#!/usr/bin/env python
"""Attach the per-interaction systematic-weight blocks (rec.mc.nu.wgt.univ, 22,485 universes) to the SELECTED events of the frozen final selection, both productions.

    source env/setup_eaf.sh && export BEARER_TOKEN_FILE=... && python scripts/ncdelta_syst_extract.py owners|extract|audit  [--workers 24]

owners : write the event-level owner tables (signal and background, with the unresolved reasons) -- no CAF access.
extract: read the owner interaction's block for every resolved selected event, with the per-file recTree <-> recTreeWireCell identity proof.
audit  : every interaction's block from a random sample of files (tails, zeros, exactly-one fractions) -- no selection involved.
No weight is applied to any result here; imp_weight is read but never multiplied.
"""
import argparse, json, multiprocessing as mp
from ncdelta_syst_common import *
from sbnd_single_photon import samples as S, syst_weights as SW

OUT = SPD / "ncdelta_purity_datamc" / "syst"; OUT.mkdir(parents=True, exist_ok=True)
TABS = REPO / "tables" / "ncdelta_purity_datamc"


def urls(prod, sample):
    if prod == "old_fg1":
        return S.manifest_urls(S.load_samples()[sample])
    return [r["url"] for r in S.read_manifest(REPO / "manifests" / "wcl1116" / f"{sample}.tsv.gz")]


def do_owners():
    cfg = load_cfg(); sigN, nat_in = natural_signal_in_region()
    for prod in PRODUCTIONS:
        s, _ = signal_owners(prod, cfg); s.to_parquet(OUT / f"owners_S_{prod}.parquet", index=False)
        b, *_ = background_owners(prod, cfg, sigN, nat_in); b.to_parquet(OUT / f"owners_B_{prod}.parquet", index=False)
        print(prod, "S events", len(s), "B events", len(b))


def jobs_for(prod):
    js = []
    s = pd.read_parquet(OUT / f"owners_S_{prod}.parquet"); s = s[s.n20br1 & s.file_index.notna()]
    u = urls(prod, "official_gen2_ncdelta")
    for fi, g in s.groupby("file_index"):
        rows = [dict(run=int(r.run), subrun=int(r.subrun), evt=int(r.evt), ev=int(r.ev), k=int(r.owner_k), ex=float(r.vtx_x), ey=float(r.vtx_y), ez=float(r.vtx_z), epdg=int(r.nu_pdg)) for r in g.itertuples()]
        js.append(("S", int(fi), u[int(fi)], rows))
    b = pd.read_parquet(OUT / f"owners_B_{prod}.parquet"); b = b[b.n20br1 & ~b.removed_in_region_natural_signal & b.resolved]
    light = pd.read_parquet(LIGHT[prod]); u = urls(prod, "bnb_cv")
    # expected vertex = Wire-Cell truth-neutrino vertex of the matched interaction (independent of the CAF position used to build the link)
    sel = b[KEY + ["owner_k"]].rename(columns={"owner_k": "mnu_k"}).merge(light[["file_index", "ev", "mnu_k", "mnu_x", "mnu_y", "mnu_z", "mnu_pdg"]].drop_duplicates(["file_index", "ev", "mnu_k"]), on=["file_index", "ev", "mnu_k"], how="left")
    assert sel.mnu_x.notna().all()
    b = b.merge(sel, on=KEY, how="left", validate="one_to_one")
    for fi, g in b.groupby("file_index"):
        rows = [dict(run=int(r.run), subrun=int(r.subrun), evt=int(r.evt), ev=int(r.ev), k=int(r.owner_k), ex=float(r.mnu_x), ey=float(r.mnu_y), ez=float(r.mnu_z), epdg=int(r.mnu_pdg)) for r in g.itertuples()]
        js.append(("B", int(fi), u[int(fi)], rows))
    return js


def do_extract(workers):
    for prod in PRODUCTIONS:
        js = jobs_for(prod); print(prod, "files", len(js), "events", sum(len(j[3]) for j in js), flush=True)
        with mp.get_context("spawn").Pool(workers) as p:
            res = list(p.imap_unordered(SW.owner_blocks_worker, js, chunksize=4))
        bad = [r for r in res if not r["ok"]]; print(" file errors:", len(bad), [b["err"] for b in bad[:2]], flush=True)
        assert len(bad) == 0, "extraction errors: nothing is saved"
        for tag in ("S", "B"):
            rr = [r for r in res if r["tag"] == tag and r["ok"]]
            proof = pd.DataFrame([dict(file_index=r["file_index"], **r["proof"]) for r in rr]); proof.to_parquet(OUT / f"proof_{tag}_{prod}.parquet", index=False)
            ev = [dict({k: v for k, v in o.items() if k != "W"}, file_index=r["file_index"]) for r in rr for o in r["ev"]]
            W = np.stack([o["W"] if o["W"] is not None else np.full(22485, np.nan, np.float32) for r in rr for o in r["ev"]]).astype(np.float32)
            meta = pd.DataFrame(ev); meta.to_parquet(OUT / f"blocks_meta_{tag}_{prod}.parquet", index=False); np.save(OUT / f"blocks_{tag}_{prod}.npy", W)
            print(" ", tag, "events", len(meta), "W", W.shape, flush=True)


def do_audit(workers, n_files=150, seed=7):
    rng = np.random.default_rng(seed); out = {}
    for tag, sample in (("B", "bnb_cv"), ("S", "official_gen2_ncdelta")):
        u = urls("nov16", sample); idx = rng.choice(len(u), n_files, replace=False)
        with mp.get_context("spawn").Pool(workers) as p:
            res = list(p.imap_unordered(SW.sample_blocks_worker, [(tag, int(i), u[int(i)], 40) for i in idx]))
        ok = [r for r in res if r["ok"]]; print(tag, "files ok", len(ok), "of", len(res), flush=True)
        np.save(OUT / f"audit_sample_{tag}.npy", np.concatenate([r["W"] for r in ok])); np.save(OUT / f"audit_sample_{tag}_pdg.npy", np.concatenate([r["pdg"] for r in ok]))
        np.save(OUT / f"audit_sample_{tag}_iscc.npy", np.concatenate([r["iscc"] for r in ok]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["owners", "extract", "audit"]); ap.add_argument("--workers", type=int, default=24); a = ap.parse_args()
    {"owners": do_owners, "extract": lambda: do_extract(a.workers), "audit": lambda: do_audit(a.workers)}[a.stage]()
