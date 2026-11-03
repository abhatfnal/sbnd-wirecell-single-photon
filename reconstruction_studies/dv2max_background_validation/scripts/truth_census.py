#!/usr/bin/python3
"""Generator-truth census of the Stage-A 10k BNB+CORSIKA reco1 sample (login node, read-only inputs).

usage: truth_census.py <stageA10k_events.csv> <out_interactions.csv> <out_events.csv> [nproc]

Per generator interaction (simb::MCTruth 'generator', n >= 1 per event):
  nu pdg / CC-NC / mode (MCTruth.fMCNeutrino), cross-checked against GTruth (fProbePDG, fGint) and MCFlux (fntype);
  vertex = fNu trajectory start (world cm), active-LAr test = SBND volTPCActive boxes (sbnd_v02_06 GDML json);
  final-state content from the GENIE particle list: status == 1 particles (GENIE kIStStableFinalState).
Truth predicates (generator truth only; nothing reconstructed):
  NUMUCC interaction : |nu pdg| == 14, CC, vertex in active LAr, decoders agree
  NCPI0  interaction : NC, >= 1 status-1 pi0 (pdg 111), vertex in active LAr, decoders agree
  event class        : >= 1 qualifying interaction; 'clean' = exactly one interaction in active LAr in the event
"""
import csv, json, math, os, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partlist_decoder as P   # noqa: E402
import uproot                  # noqa: E402

BOXES = json.load(open(P.ACTIVE_JSON))["placements"]
MP = 0.938272


def ke(q):
    p4 = q["p4"]
    if p4 is None:
        return None
    m = math.sqrt(max(p4[3] ** 2 - p4[0] ** 2 - p4[1] ** 2 - p4[2] ** 2, 0.0))
    return p4[3] - m


def per_file(job):
    path, rows = job
    out = []
    f = uproot.open(path)
    for r in rows:
        e = int(r["entry_or_nskip"])
        mts = P.decode_mctruth_full(P.raw(f, "simb::MCTruths_generator__GenieGen.", e))
        gts = P.decode_gtruth(P.raw(f, "simb::GTruths_generator__GenieGen.", e))
        fls = P.decode_flat(P.raw(f, "simb::MCFluxs_generator__GenieGen.", e), f, "simb::MCFlux")
        assert len(mts) == len(gts) == len(fls)
        for k, (mt, gt, fl) in enumerate(zip(mts, gts, fls)):
            ntype = int(fl["fntype"])
            agree = (mt["nu_pdg"] == gt["fProbePDG"] == ntype) and ((gt["fGint"] == 2) == (mt["ccnc"] == 0)) and \
                    ((gt["fGint"] == 3) == (mt["ccnc"] == 1))
            vx = mt["nu_start"]
            tpc = P.active_tpc(vx[0], vx[1], vx[2], BOXES) if vx else ""
            parts = mt["particles"]
            fs = [q for q in parts if q["status"] == 1]
            nu = [q for q in parts if q["status"] == 0 and q["pdg"] == mt["nu_pdg"]]
            lep = [q for q in fs if q["pdg"] == mt["lepton_pdg"]]
            pi0 = sorted([q["p4"][3] for q in fs if q["pdg"] == 111], reverse=True)
            pipm = [ke(q) for q in fs if abs(q["pdg"]) == 211]
            prot = sorted([ke(q) for q in fs if q["pdg"] == 2212], reverse=True)
            gam = sorted([q["p4"][3] for q in fs if q["pdg"] == 22], reverse=True)
            nucc = int(abs(mt["nu_pdg"]) == 14 and mt["ccnc"] == 0 and bool(tpc) and agree)
            ncpi0 = int(mt["ccnc"] == 1 and len(pi0) >= 1 and bool(tpc) and agree)
            lp = lep[0]["p4"] if lep else None
            out.append(dict(
                selection_index=r["selection_index"], rse=f'{r["run"]}:{r["subrun"]}:{r["event"]}',
                run=r["run"], subrun=r["subrun"], event=r["event"], source_file=path, entry=e,
                n_interactions=len(mts), interaction=k, nu_pdg=mt["nu_pdg"],
                ccnc=("CC" if mt["ccnc"] == 0 else "NC" if mt["ccnc"] == 1 else mt["ccnc"]),
                mode=f'{mt["mode"]}:{P.MODE.get(mt["mode"], "?")}', interaction_type=mt["interaction_type"],
                nu_E_GeV=round(nu[0]["p4"][3], 5) if nu and nu[0]["p4"] else None,
                lepton_pdg=mt["lepton_pdg"], lepton_E_GeV=round(lp[3], 5) if lp else None,
                lepton_cos_z=round(lp[2] / math.sqrt(lp[0] ** 2 + lp[1] ** 2 + lp[2] ** 2), 4) if lp and any(lp[:3]) else None,
                vtx_x=round(vx[0], 4), vtx_y=round(vx[1], 4), vtx_z=round(vx[2], 4), vtx_t_ns=round(vx[3], 3),
                active_tpc=tpc or "none", in_active_lar=int(bool(tpc)),
                n_fs=len(fs), n_pi0=len(pi0), pi0_E_GeV=";".join(f"{x:.4f}" for x in pi0),
                n_pipm=len(pipm), pipm_KE_GeV=";".join(f"{x:.4f}" for x in pipm),
                n_proton=len(prot), proton_KE_GeV=";".join(f"{x:.4f}" for x in prot),
                n_proton_ke35=sum(1 for x in prot if x > 0.035),
                n_gamma=len(gam), gamma_E_GeV=";".join(f"{x:.4f}" for x in gam),
                gtruth_gint=gt["fGint"], gtruth_probe=gt["fProbePDG"], gtruth_numpi0_excl=gt["fNumPi0"],
                mcflux_ntype=ntype, decoders_agree=int(agree),
                int_numucc_active=nucc, int_ncpi0_active=ncpi0))
    return out


def main():
    ev_csv, out_int, out_ev = sys.argv[1], sys.argv[2], sys.argv[3]
    nproc = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    by_file = {}
    for r in csv.DictReader(open(ev_csv)):
        by_file.setdefault(r["source_file"], []).append(r)
    jobs = list(by_file.items())
    rows = []
    with Pool(nproc) as pool:
        for i, o in enumerate(pool.imap(per_file, jobs, chunksize=4)):
            rows.extend(o)
            if i % 200 == 0:
                print(f"{i}/{len(jobs)} files", flush=True)
    with open(out_int, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    ev = {}
    for r in rows:
        ev.setdefault(r["selection_index"], []).append(r)
    erows = []
    for si, its in sorted(ev.items(), key=lambda kv: int(kv[0])):
        act = [x for x in its if x["in_active_lar"]]
        nq = [x for x in its if x["int_numucc_active"]]
        pq = [x for x in its if x["int_ncpi0_active"]]
        a0 = act[0] if len(act) == 1 else None
        erows.append(dict(
            selection_index=si, rse=its[0]["rse"], run=its[0]["run"], subrun=its[0]["subrun"], event=its[0]["event"],
            source_file=its[0]["source_file"], entry=its[0]["entry"], n_interactions=len(its), n_active_interactions=len(act),
            all_decoders_agree=int(all(x["decoders_agree"] for x in its)),
            event_numucc=int(bool(nq)), event_ncpi0=int(bool(pq)), clean_single_active=int(len(act) == 1),
            numucc_clean=int(bool(nq) and len(act) == 1), ncpi0_clean=int(bool(pq) and len(act) == 1),
            active_interaction=(a0["interaction"] if a0 else ""),
            active_nu_pdg=(a0["nu_pdg"] if a0 else ""), active_ccnc=(a0["ccnc"] if a0 else ""),
            active_mode=(a0["mode"] if a0 else ""), active_nu_E_GeV=(a0["nu_E_GeV"] if a0 else ""),
            vtx_x=(a0["vtx_x"] if a0 else ""), vtx_y=(a0["vtx_y"] if a0 else ""), vtx_z=(a0["vtx_z"] if a0 else "")))
    with open(out_ev, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(erows[0].keys())); w.writeheader(); w.writerows(erows)
    print("events", len(erows), "interactions", len(rows),
          "numucc", sum(r["event_numucc"] for r in erows), "numucc_clean", sum(r["numucc_clean"] for r in erows),
          "ncpi0", sum(r["event_ncpi0"] for r in erows), "ncpi0_clean", sum(r["ncpi0_clean"] for r in erows),
          "n_active hist", {k: sum(1 for r in erows if r["n_active_interactions"] == k) for k in range(5)})


if __name__ == "__main__":
    main()
