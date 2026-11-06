#!/usr/bin/env python
"""Audit of the first-pass BNB truth taxonomy (precedence, multi-active, dirt, box sensitivity). Event level, valid events and all.

    python scripts/truth_taxonomy_audit.py bnb_cv   -> tables/baseline/<sample>_truth_taxonomy_audit.json (+ csv)
The 'active volume' box is the PROVISIONAL taxonomy box in truth.py, NOT an analysis fiducial volume.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import scanio as X, truth as T  # noqa: E402

s = sys.argv[1] if len(sys.argv) > 1 else "bnb_cv"
t = X.load_scan(os.environ["SP_DATA"] + "/baseline_scan", s)
code = t["ev_t_code"]; valid = t["ev_valid"]; n = len(code)
av = T.ActiveVolume()
res = dict(sample=s, n_events=int(n), n_valid=int(valid.sum()))
res["category_all_events"] = {nm: int((code == k).sum()) for k, nm in enumerate(T.CATEGORIES)}
res["category_valid_events"] = {nm: int(((code == k) & valid).sum()) for k, nm in enumerate(T.CATEGORIES)}
res["n_nu_per_event"] = {int(k): int(v) for k, v in zip(*np.unique(t["ev_t_n_nu"], return_counts=True))}
res["n_active_nu_per_event"] = {int(k): int(v) for k, v in zip(*np.unique(t["ev_t_n_act"], return_counts=True))}
# single-active events: interaction table, and effect of pi0-vs-flavour precedence
single = t["ev_t_n_act"] == 1
df = pd.DataFrame(dict(pdg=t["ev_t_a_pdg"][single], cc=t["ev_t_a_cc"][single], nc=t["ev_t_a_nc"][single], pi0=t["ev_t_a_pi0"][single], code=code[single], valid=valid[single]))
tab = df.groupby(["pdg", "cc", "nc", "pi0"]).size().rename("n_events").reset_index()
tab["category"] = [T.CATEGORIES[int(c)] for c in df.groupby(["pdg", "cc", "nc", "pi0"]).code.first().values]
tab.to_csv(REPO / "tables" / "baseline" / f"{s}_truth_single_active_interactions.csv", index=False)
cat = lambda k: T.CATEGORIES[k]
res["single_active_with_pi0"] = dict(NC_PI0=int(((code == T.CODE["NC_PI0"])).sum()), CC_PI0=int((code == T.CODE["CC_PI0"]).sum()),
    note="under 'flavour-first' precedence the CC_PI0 events would be NUMU_CC/NUE_CC/OTHER_CC and NC_PI0 would be OTHER_NC")
cc_pi0 = df[(df.cc) & df.pi0]
res["CC_PI0_by_flavour_if_flavour_first"] = {str(int(k)): int(v) for k, v in cc_pi0.pdg.value_counts().items()}
res["single_active_neither_cc_nor_nc"] = int((~df.cc & ~df.nc).sum()); res["single_active_both_cc_and_nc"] = int((df.cc & df.nc).sum())
res["OTHER_category_events"] = int((code == T.CODE["OTHER"]).sum())
oth = df[df.code == T.CODE["OTHER"]]
res["OTHER_pdgs"] = {str(int(k)): int(v) for k, v in oth.pdg.value_counts().items()}
res["single_active_pdg_not_in_12_14"] = {str(int(k)): int(v) for k, v in df[~df.pdg.isin([12, 14])].pdg.value_counts().items()}
# box sensitivity of single-active events: distance of the active vertex to the nearest box face
x, y, z = t["ev_t_a_x"][single], t["ev_t_a_y"][single], t["ev_t_a_z"][single]
d = np.minimum.reduce([x - av.x[0], av.x[1] - x, y - av.y[0], av.y[1] - y, z - av.z[0], av.z[1] - z])
res["single_active_vertex_within_cm_of_box_face"] = {str(c): float((d < c).mean()) for c in (2, 5, 10, 20)}
res["note"] = "Neutrinos just outside the box are classified as dirt; DIRT_NO_ACTIVE / MULTI_ACTIVE depend on the box edge. Provisional box, NOT an FV."
Path(REPO / "tables" / "baseline" / f"{s}_truth_taxonomy_audit.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
