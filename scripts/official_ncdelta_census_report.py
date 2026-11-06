#!/usr/bin/env python
"""Truth-only census report of the official Gen2 EX_ncdeltarad flatCAFs (from official_ncdelta_truth_scan.py products + SAM metadata CSVs).
No Wire-Cell, no efficiency. Writes small summaries to tables/official_ncdelta/ and a plot to plots/official_ncdelta/."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon.truth_signal import FILTER_BOX  # noqa: E402
from sbnd_single_photon.truth import ActiveVolume  # noqa: E402
SPD = Path(os.environ["SP_DATA"]); R = SPD / "official_gen2_ncdelta_truth"; SAM = SPD / "sam"
T = REPO / "tables" / "official_ncdelta"; P = REPO / "plots" / "official_ncdelta"; T.mkdir(parents=True, exist_ok=True); P.mkdir(parents=True, exist_ok=True)

f = pd.read_parquet(R / "files.parquet"); e = pd.read_parquet(R / "events.parquet"); n = pd.read_parquet(R / "neutrinos.parquet")
fm = pd.read_csv(SAM / "official_gen2_ncdelta_flatcaf.meta.csv.gz"); rm = pd.read_csv(SAM / "official_gen2_ncdelta_reco1.meta.csv.gz")
out = {}
# ---------------- file level
fi = f.merge(fm[["name", "events", "pot", "parents"]].rename(columns={"name": "source_file", "events": "sam_events", "pot": "sam_pot"}), on="source_file", how="left")
rmi = rm.drop(columns=["parents"]).rename(columns={"name": "parents", "gen": "r1_gen", "pot": "r1_pot", "events": "r1_events"})[["parents", "r1_gen", "r1_pot", "r1_events"]]
fi = fi.merge(rmi, on="parents", how="left")
out["files"] = dict(n_files=len(f), readable=len(f), zero_event_files=int((f.n_events == 0).sum()), stored_events=int(f.n_events.sum()),
    sum_TotalPOT=float(f.TotalPOT.sum()), sum_TotalGenEvents=float(f.TotalGenEvents.sum()), sum_TotalEvents=float(f.TotalEvents.sum()),
    files_missing_TotalPOT_hist=int(f.TotalPOT.isna().sum()), files_missing_TotalGenEvents_hist=int(f.TotalGenEvents.isna().sum()),
    has_genie_record_all=bool(f.has_genie_record.all()), size_total_GB=float(f["size"].sum() / 1e9))
out["files"]["TotalGenEvents_value_counts"] = {str(k): int(v) for k, v in f.TotalGenEvents.value_counts(dropna=False).head(8).items()}
out["files"]["TotalEvents_equals_n_events"] = int((f.TotalEvents == f.n_events).sum())
out["files"]["TotalEvents_value_counts"] = {str(k): int(v) for k, v in f.TotalEvents.value_counts(dropna=False).head(6).items()}
out["files"]["sam_events_equals_n_events"] = int((fi.sam_events == fi.n_events).sum())
out["files"]["TotalPOT_equals_SAM_mc_pot"] = int(np.isclose(fi.TotalPOT, fi.sam_pot, rtol=1e-5).sum())
out["files"]["TotalPOT_zero_event_files_nonzero"] = int(((f.n_events == 0) & (f.TotalPOT > 0)).sum())
# ---------------- SAM accounting (reco1 = filter-stage-adjacent units; flatCAF = what is readable here)
orph = rm[~rm.name.isin(fm.parents)]
out["sam_accounting"] = dict(reco1_files=len(rm), reco1_events=int(rm.events.sum()), reco1_zero_event_files=int((rm.events == 0).sum()),
    reco1_generated_event_count_per_file_unique=sorted(rm.gen.unique().tolist()), reco1_sum_generated_events=float(rm.gen.sum()), reco1_sum_mc_pot=float(rm.pot.sum()),
    flatcaf_files=len(fm), flatcaf_events=int(fm.events.sum()), flatcaf_sum_mc_pot=float(fm.pot.sum()),
    reco1_without_flatcaf_child=len(orph), events_in_them=int(orph.events.sum()), pot_in_them=float(orph.pot.sum()), generated_in_them=float(orph.gen.sum()),
    zero_event_reco1_without_child=int((orph.events == 0).sum()),
    filter_pass_fraction_reco1=float(rm.events.sum() / rm.gen.sum()),
    flatcaf_units_generated_events=float(rm[rm.name.isin(fm.parents)].gen.sum()), flatcaf_units_pot=float(rm[rm.name.isin(fm.parents)].pot.sum()),
    pot_per_generated_event=float(rm.pot.sum() / rm.gen.sum()))
# ---------------- event level
key = ["run", "subrun", "evt"]
out["events"] = dict(n_events=len(e), duplicate_run_subrun_evt=int(e.duplicated(key).sum()), duplicate_file_run_subrun_evt=int(e.duplicated(["file_index"] + key).sum()),
    n_nu_distribution={str(k): int(v) for k, v in e.n_nu.value_counts().sort_index().items()},
    events_with_gt1_nu=int((e.n_nu > 1).sum()))
rec_flag = e.is_ncdelta_radiative
out["signal_identification"] = dict(
    events_record_delta_radiative=int((rec_flag == 1).sum()), events_record_not_delta_radiative=int((rec_flag == 0).sum()), events_unknown=int((rec_flag == -1).sum()),
    proxy_fires=int(e.is_ncdelta_rad_proxy.sum()), proxy_agrees_with_record_all=bool(e.proxy_agrees_with_record.all()), proxy_agrees_n=int(e.proxy_agrees_with_record.sum()),
    n_signal_nu_candidates_dist={str(k): int(v) for k, v in e.n_signal_nu_candidates.value_counts().sort_index().items()},
    delta_pdg_counts={str(k): int(v) for k, v in e[rec_flag == 1].delta_pdg.value_counts().items()},
    decay_nucleon_pdg_counts={str(k): int(v) for k, v in e[rec_flag == 1].decay_nucleon_pdg.value_counts().items()},
    delta_charge_counts={str(k): int(v) for k, v in e[rec_flag == 1].delta_charge.value_counts().items()},
    nucleon_status_at_decay={str(k): int(v) for k, v in e[rec_flag == 1].nucleon_status_at_decay.value_counts().items()})
s = e[rec_flag == 1].copy()
ns = len(s); out["signal_identification"]["n_signal_events"] = ns
sn = n.merge(e[["file_index", "ev", "signal_nu_index"]], on=["file_index"], how="left") if False else None
# signal-neutrino level (the neutrino chosen by the record): re-derive from the neutrino table
n["k"] = n.groupby(["file_index", "ev"]).cumcount()
sig = n.merge(e[["file_index", "ev", "signal_nu_index", "is_ncdelta_radiative"]], on=["file_index", "ev"])
sig = sig[(sig.k == sig.signal_nu_index) & (sig.is_ncdelta_radiative == 1)]
frac = lambda m: float(m.mean()) if len(m) else None
out["signal_neutrino"] = dict(n=len(sig), isnc_fraction=frac(sig.isnc == 1), iscc_fraction=frac(sig.iscc == 1), resonant_fraction=frac(sig.genie_mode == 1),
    genie_mode_counts={str(k): int(v) for k, v in sig.genie_mode.value_counts().items()}, resnum_counts={str(k): int(v) for k, v in sig.resnum.value_counts().items()},
    resnum0_fraction=frac(sig.resnum == 0), nu_pdg_counts={str(k): int(v) for k, v in sig.pdg.value_counts().items()},
    int_type_counts={str(k): int(v) for k, v in sig.rec_int_type.value_counts().items()}, at_least_one_primary_photon=frac(sig.n_photons >= 1),
    photon_multiplicity={str(k): int(v) for k, v in sig.n_photons.value_counts().sort_index().items()},
    photon_gt20_fraction_any=frac(sig.n_photons_gt20 >= 1), hardest_primary_photon_mev_q=np.nanpercentile(sig.max_photon_mev, [5, 25, 50, 75, 95]).round(1).tolist(),
    record_photon_mev_q=np.nanpercentile(sig.rec_photon_e_gev * 1000, [5, 25, 50, 75, 95]).round(1).tolist(),
    via_in_nucleus_photon_fraction=frac(sig.rec_via_photon.astype(bool)), nu_energy_gev_q=np.nanpercentile(sig.E, [5, 25, 50, 75, 95]).round(3).tolist())
vx, vy, vz = sig.position_x, sig.position_y, sig.position_z
inbox = FILTER_BOX.contains(vx, vy, vz); intpc = ActiveVolume().contains(vx, vy, vz)
out["signal_neutrino"].update(vertex_in_filter_box=frac(inbox), vertex_in_active_tpc_box=frac(intpc), vertex_in_filter_box_n=int(inbox.sum()),
    vertex_in_active_tpc_n=int(intpc.sum()), vertex_q=dict(x=np.percentile(vx, [5, 50, 95]).round(1).tolist(), y=np.percentile(vy, [5, 50, 95]).round(1).tolist(), z=np.percentile(vz, [5, 50, 95]).round(1).tolist()))
pcat = np.minimum(sig.n_p35, 2)
out["signal_neutrino"]["truth_protons_35MeV"] = {"0p": int((pcat == 0).sum()), "1p": int((pcat == 1).sum()), ">=2p": int((pcat == 2).sum())}
out["signal_neutrino"]["n_p35_hist"] = np.bincount(np.clip(sig.n_p35.values, 0, 8), minlength=9).tolist()
out["signal_neutrino"]["primary_pi0_ge1"] = frac(sig.n_pi0 >= 1); out["signal_neutrino"]["primary_pi_charged_ge1"] = frac(sig.n_pic >= 1)
by = {}
for dname, g in sig.groupby("rec_delta_pdg"):
    pc = np.minimum(g.n_p35, 2); by[str(int(dname))] = dict(n=len(g), p0=int((pc == 0).sum()), p1=int((pc == 1).sum()), p2=int((pc == 2).sum()), nucleon={str(k): int(v) for k, v in g.rec_nucleon_pdg.value_counts().items()})
out["signal_neutrino"]["truth_protons_by_delta"] = by
# all stored neutrinos, and the non-signal ones (what else is in a stored event)
oth = n.merge(e[["file_index", "ev", "signal_nu_index", "is_ncdelta_radiative"]], on=["file_index", "ev"]); oth = oth[~((oth.k == oth.signal_nu_index) & (oth.is_ncdelta_radiative == 1))]
out["other_neutrinos_in_events"] = dict(n=len(oth), nc_fraction=frac(oth.isnc == 1), cc_fraction=frac(oth.iscc == 1),
    in_active_tpc_box=frac(ActiveVolume().contains(oth.position_x, oth.position_y, oth.position_z)), in_filter_box=frac(FILTER_BOX.contains(oth.position_x, oth.position_y, oth.position_z)),
    record_delta_radiative_nc=int(((oth.rec_is_delta_rad == 1) & (oth.isnc == 1)).sum()))
out["all_neutrinos"] = dict(n=len(n), isnc_fraction=frac(n.isnc == 1))
# events without a record-defined signal neutrino (surprises)
bad = e[rec_flag != 1]; out["surprises"] = dict(events_without_signal_by_record=len(bad), examples=bad[["file_index", "ev", "run", "subrun", "evt", "n_nu"]].head(10).to_dict("records"),
    events_two_or_more_signal_nu=int((e.n_signal_nu_candidates >= 2).sum()),
    signal_nc_not_resnum0=int((sig.resnum != 0).sum()), signal_not_resonant=int((sig.genie_mode != 1).sum()),
    signal_without_primary_photon=int((sig.n_photons == 0).sum()), signal_nu_outside_filter_box=int((~inbox).sum()))
# field behaviour vs BNB CV
chk = {}
for c in f.columns:
    if c.startswith("chk_") and c.endswith("_min"): chk[c[4:-4]] = dict(min=float(f[c].min()), max=float(f[c.replace("_min", "_max")].max()), nonzero=int(f[c.replace("_min", "_nz")].sum()), sentinel=int(f[c.replace("_min", "_sent")].sum()), n=int(f[c.replace("_min", "_n")].sum()))
out["field_behaviour"] = chk
(T / "official_ncdelta_census.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
# small csv for the signal neutrino table by delta type / proton cat
pd.DataFrame([dict(delta_pdg=k, **{x: v for x, v in d.items() if x != "nucleon"}) for k, d in by.items()]).to_csv(T / "truth_protons_by_delta.csv", index=False)
# ---------------- plot
fig, ax = plt.subplots(2, 3, figsize=(15, 8)); ax = ax.ravel()
ax[0].hist(sig.rec_photon_e_gev * 1000, bins=np.linspace(0, 1500, 61), color="#0072B2"); ax[0].axvline(20, color="k", ls="--"); ax[0].set_xlabel("radiative photon energy from GENIE record [MeV]")
ax[1].hist(sig.E, bins=np.linspace(0, 4, 41), color="#009E73"); ax[1].set_xlabel("true E_nu [GeV]")
w = np.bincount(np.clip(sig.n_p35.values, 0, 6), minlength=7); ax[2].bar(range(7), w, color="#D55E00"); ax[2].set_xlabel("post-FSI primary protons, KE>35 MeV (6 = 6+)")
ax[3].hist2d(sig.position_z, sig.position_x, bins=[np.linspace(-20, 520, 55), np.linspace(-220, 220, 45)], cmap="viridis"); ax[3].set_xlabel("true vertex z [cm]"); ax[3].set_ylabel("x [cm]")
ax[4].hist2d(sig.position_z, sig.position_y, bins=[np.linspace(-20, 520, 55), np.linspace(-220, 220, 45)], cmap="viridis"); ax[4].set_xlabel("true vertex z [cm]"); ax[4].set_ylabel("y [cm]")
dc = sig.groupby([sig.rec_delta_pdg.astype(int), np.minimum(sig.n_p35, 2)]).size().unstack(fill_value=0); dc.plot.bar(ax=ax[5], rot=0, color=["#999999", "#E69F00", "#56B4E9"]); ax[5].set_xlabel("Delta pdg (2114 = Delta0 -> n gamma, 2214 = Delta+ -> p gamma)"); ax[5].legend(["0p", "1p", ">=2p"])
fig.suptitle(f"Official Gen2 EX_ncdeltarad flatCAF truth census (N={ns} filter-passing events with record-verified Delta->N gamma; NO efficiency; no FV)", fontsize=10, color="firebrick")
fig.tight_layout(); fig.savefig(P / "official_ncdelta_truth_census.png", dpi=80)
print(json.dumps({k: out[k] for k in ("files", "sam_accounting")}, indent=1, default=str)[:3500])
