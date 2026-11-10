"""Event-level tables of the photon-shower / vertex reconstruction audit (pandas only; I/O free). Builds, from the raw scan tables, the signal-photon association, the exclusive shower-stage outcome of every
candidate-stage event and the reco vertex geometry. Nothing here touches a baseline decision: the baseline flags are inputs, never outputs."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import shower_audit as SA

K = ["file_index", "ev"]


def photon_association(raw: dict) -> pd.DataFrame:
    """One row per event: photon charge in candidates / outside, the dominant (candidate, T_kine row) holding the largest share of the in-candidate photon charge, its fraction, its T_kine row
    attributes and its PF state. The dominant object is keyed by the overlap row's own ``kine_index`` (the T_kine row index inside the candidate; -1 = a piece without a particle row), not by
    ``particle_id``: a few pool-2 showers share a start-segment id (`particle_id` duplicates), the row index is unique. Shallowest PF node is used if several map to one row."""
    cand, kine, pf, po, truth = raw["cand"].copy(), raw["kine"], raw["pf"].copy(), raw["pho_ov"].copy(), raw["truth"]
    cand["nu_index"] = cand.nu_index.astype(int); pf["nu_index"] = pf.nu_index.astype(int); po["nu_index"] = po.nu_index.astype(int); po["kine_index"] = po.kine_index.astype(int)
    q_tot = po.groupby(K).q.sum().rename("q_total").reset_index()
    inc = po[po.nu_index >= 0]
    q_in = inc.groupby(K).q.sum().rename("q_in_cands").reset_index()
    cp = inc.groupby(K + ["nu_index", "kine_index"]).q.sum().rename("q_part").reset_index().sort_values(K + ["q_part", "nu_index", "kine_index"], ascending=[True, True, False, True, True])
    dom = cp.drop_duplicates(K, keep="first").rename(columns={"nu_index": "dom_nu", "kine_index": "dom_row"})
    ev = truth.merge(q_tot, on=K, how="left").merge(q_in, on=K, how="left").merge(dom, on=K, how="left")
    ev[["q_total", "q_in_cands", "q_part"]] = ev[["q_total", "q_in_cands", "q_part"]].fillna(0.0)
    ev["dominant_fraction"] = np.where(ev.q_in_cands > 0, ev.q_part / ev.q_in_cands.replace(0, np.nan), 0.0)
    ncw = inc.groupby(K).nu_index.nunique().rename("n_cand_with_photon").reset_index()
    ev = ev.merge(ncw, on=K, how="left"); ev["n_cand_with_photon"] = ev.n_cand_with_photon.fillna(0).astype(int)
    cmap = cand[K + ["cand_pos", "nu_index"]].rename(columns={"nu_index": "dom_nu"})
    ev = ev.merge(cmap, on=K + ["dom_nu"], how="left")
    kk = kine[K + ["cand_pos", "row", "kine_particle_id", "kine_particle_type", "kine_energy_particle", "kine_particle_is_shower", "kine_particle_pool", "kine_energy_included"]].rename(columns={"row": "dom_row"})
    ev = ev.merge(kk, on=K + ["cand_pos", "dom_row"], how="left")
    ev["has_kine_row"] = ev.kine_particle_id.notna()
    pfn = pf[pf.kine_index >= 0].rename(columns={"kine_index": "dom_row", "nu_index": "dom_nu", "start_x": "pf_start_x", "start_y": "pf_start_y", "start_z": "pf_start_z"})[K + ["dom_nu", "dom_row", "node_id", "parent_id", "depth", "pf_start_x", "pf_start_y", "pf_start_z"]]
    pfn = pfn.sort_values(K + ["dom_nu", "dom_row", "depth"]).drop_duplicates(K + ["dom_nu", "dom_row"], keep="first")
    par = pf[K + ["nu_index", "node_id", "parent_id", "is_pseudo", "pdg"]].rename(columns={"nu_index": "dom_nu", "node_id": "parent_id", "parent_id": "gp_id", "is_pseudo": "par_pseudo", "pdg": "par_pdg"})
    par = par.drop_duplicates(K + ["dom_nu", "parent_id"], keep="first")
    ev = ev.merge(pfn, on=K + ["dom_nu", "dom_row"], how="left").merge(par, on=K + ["dom_nu", "parent_id"], how="left")
    ev["pf_state"] = [SA.pf_attachment_state(bool(pd.notna(n)), int(d) if pd.notna(d) else 0, bool(p == 1), int(g) if pd.notna(g) else 0) for n, d, p, g in zip(ev.node_id, ev.depth, ev.par_pseudo, ev.gp_id)]
    ev.loc[~ev.has_kine_row, "pf_state"] = "no_kine_row"
    assert not ev.duplicated(K).any(), "photon association is not one row per event"
    return ev
