#!/usr/bin/env python
"""Build a versioned upstream-score OVERLAY for one registered sample/production from a candidate-input table prepared by the CAF reader.  BLOCKED by design: scoring any registered
(official / evaluation) sample requires a filled `evaluation_guard` in configs/upstream_release.yaml (named approver + date + frozen model bundle hash + selection manifest hash) or a designated
non-evaluation fixture; the guard is checked FIRST, before any file is read.  The released defaults are used unchanged; no model, vertex mode or threshold is chosen here.

    python scripts/upstream_overlay_build.py --sample SAMPLE --production nov16 --inputs DIR --releases <clone>/releases --out overlay.parquet [--simulation]

DIR holds the tables of the PINNED release's own builder (tables/build_tables.py --objs, run with `--file-id-from dirname`): cands_<TAG>.parquet and objs_<model>_<TAG>.parquet (18 level-1 tables),
identity (file_id, run, subrun, event, cand). They are scored under that identity and translated 1:1 to the EAF identity (file_index, ev, run, subrun, evt, nu_index) through our events table and manifest;
reconstruction quantities present in both (kine_reco_Enu, shw_sp_energy) are carried as id_* checks for join_overlay.  Simulation samples are corrected on COPIES (1.071, simulation only) for the nu_mu classifier; data and the nu_e classifier see raw inputs.
"""
import argparse, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sbnd_single_photon import upstream_scores as US


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", required=True); ap.add_argument("--production", required=True); ap.add_argument("--inputs", required=True); ap.add_argument("--releases", required=True)
    ap.add_argument("--tag", required=True); ap.add_argument("--events", required=True); ap.add_argument("--manifest-urls", required=True, help="text file, one URL per line, in manifest (file_index) order"); ap.add_argument("--out", required=True); ap.add_argument("--simulation", action="store_true"); a = ap.parse_args(); cfg = US.load_config()
    auth = US.require_authorization(a.sample, cfg)                                                      # FIRST: nothing is read before this passes
    if not cfg["applicability"].get(a.production, {}).get("applicable"): raise SystemExit(f"production {a.production!r}: the released models are not applicable ({cfg['applicability'].get(a.production)})")
    rep = US.verify_release(a.releases, cfg)
    if not rep["ok"]: raise SystemExit("release verification failed: " + str([c for c in rep["checks"] if not c["ok"]]))
    d = Path(a.inputs); key = US.UPSTREAM_KEY; cands = pd.read_parquet(d / f"cands_{a.tag}.parquet")
    nue_objs = {m: pd.read_parquet(d / f"objs_{m}_{a.tag}.parquet") for m in US._manifest(Path(a.releases), cfg, "nue")["level1"]["models"]}
    numu_objs = {m: pd.read_parquet(d / f"objs_{m}_{a.tag}.parquet") for m in US._manifest(Path(a.releases), cfg, "numu")["level1"]["models"]}
    nue = US.score_nue(a.releases, cfg, cands, nue_objs, key)                                           # raw inputs, always
    c, o1, corr = (US.apply_numu_sim_correction(cands, numu_objs["numu_1"], numu_objs["numu_2"], cfg, True, key) if a.simulation else (cands, numu_objs["numu_1"], None))
    numu = US.score_numu(a.releases, cfg, c, dict(numu_objs, numu_1=o1), key, a.simulation)
    ov = US.make_overlay(nue, numu, key, US.provenance_record(cfg, a.sample, a.production, a.simulation, len(cands), auth, dict(correction_report=corr)))
    ov = US.carry_identity_checks(ov, cands, key, {"kine_reco_Enu": "kine_reco_Enu", "shw_sp_energy": "shw_sp_energy"}); prov = ov.attrs["provenance"]
    urls = [l.strip() for l in open(a.manifest_urls) if l.strip()]; ov = US.translate_identity(ov, pd.read_parquet(a.events), US.file_map_from_manifest(urls, "dirname")); ov.attrs["provenance"] = prov
    print("wrote", US.write_overlay(ov, a.out))


if __name__ == "__main__":
    main()
