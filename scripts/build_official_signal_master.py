#!/usr/bin/env python
"""Build the canonical truth tables of the OFFICIAL Gen2 NC Delta sample (outside Git) and the denominator summaries (small, in Git).

    source env/setup_eaf.sh
    python scripts/build_official_signal_master.py

Inputs (all measured earlier, read-only): $SP_DATA/official_gen2_ncdelta_truth/{events,neutrinos,files}.parquet and the SAM metadata CSVs.
Outputs: $SP_DATA/official_gen2_ncdelta_master/{signal_records,signal_events,units}.parquet + metadata.json
         tables/official_signal/denominators.json and denominators_<region>.csv
No reconstruction efficiency exists yet; nothing here depends on Wire-Cell.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
import pandas as pd
from sbnd_single_photon import signal_master as SM

SPD = Path(os.environ["SP_DATA"]); T = SPD / "official_gen2_ncdelta_truth"; SAM = SPD / "sam"; OUT = SPD / "official_gen2_ncdelta_master"
TAB = REPO / "tables" / "official_signal"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True)
    ev, nu, fl = (pd.read_parquet(T / f"{n}.parquet") for n in ("events", "neutrinos", "files"))
    fm = pd.read_csv(SAM / "official_gen2_ncdelta_flatcaf.meta.csv.gz"); rm = pd.read_csv(SAM / "official_gen2_ncdelta_reco1.meta.csv.gz")
    regions = SM.load_regions()
    n_by_file = fl.set_index("source_file").n_events
    units = SM.build_units(fm, rm, n_by_file)
    rec = SM.build_records(ev, nu, fl, units, fm, filter_box=regions["filter_box"], tpc_box=regions["active_tpc"])
    evt = SM.build_events(rec)
    assert len(evt) == len(ev) == 13773 and len(rec) == 13779 and int(rec.multi_signal_event.sum()) == 12 and rec.groupby(SM.KEY).ngroups == 13773
    rec.to_parquet(OUT / "signal_records.parquet", index=False); evt.to_parquet(OUT / "signal_events.parquet", index=False)
    units.to_parquet(OUT / "units.parquet", index=False)
    summ = {name: SM.denominator_summary(rec, units, box, label=name) for name, box in list(regions.items()) + [("no_region_cut", None)]}
    (TAB / "denominators.json").write_text(json.dumps(summ, indent=1))
    for name, d in summ.items():
        rows = [("N_signal_truth", d["N_signal_truth"])] + [(f"truth_{k}", v) for k, v in d["truth_class"].items()] + \
               [(k, v) for k, v in d["delta"].items()] + [(k, v) for k, v in d["delta_x_class"].items()]
        pd.DataFrame(rows, columns=["quantity", "events"]).to_csv(TAB / f"denominators_{name}.csv", index=False)
    git = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    ins = [T / "events.parquet", T / "neutrinos.parquet", T / "files.parquet", SAM / "official_gen2_ncdelta_flatcaf.meta.csv.gz", SAM / "official_gen2_ncdelta_reco1.meta.csv.gz"]
    meta = dict(schema_version="1.0", created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), git_commit=git,
                sam_definitions=dict(reco1="aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_ncdeltarad_v10_14_02_05_reco1_sbnd",
                                     flat_caf="aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_ncdeltarad_v10_14_02_05_flat_caf_sbnd"),
                input_sha256={p.name: sha(p) for p in ins}, config_sha256={"configs/signal_regions.yaml": sha(REPO / "configs/signal_regions.yaml")},
                rows=dict(signal_records=len(rec), signal_events=len(evt), units=len(units)),
                units_with_flatcaf=int((units.flatcaf_status == "flatcaf_available").sum()), units_without_flatcaf=int((units.flatcaf_status != "flatcaf_available").sum()),
                multi_signal_events=int(rec[rec.multi_signal_event].groupby(SM.KEY).ngroups),
                excluded_cc_delta_radiative_neutrinos=int(((nu.rec_is_delta_rad.astype(bool)) & (nu.isnc == 0)).sum()),
                proton_threshold_mev=SM.PROTON_KE_MEV, key="(reco1_unit, flatcaf, file_index, run, subrun, evt, signal_nu_index)",
                notes="records keep BOTH qualifying neutrinos of the multi-signal events; is_selected_signal is the deterministic event-level choice; truth only, no reconstruction")
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: summ[k]["N_signal_truth"] for k in summ}), json.dumps(meta["rows"]))


if __name__ == "__main__":
    main()
