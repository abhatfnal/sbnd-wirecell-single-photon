"""Canonical truth table of the OFFICIAL Gen2 NC Delta -> N gamma sample, and its efficiency denominators (pure, tested; no ROOT).

Truth sources (already measured, outside Git): ``$SP_DATA/official_gen2_ncdelta_truth/{events,neutrinos,files}.parquet`` (flatCAF census with the
exact GENIE-record ancestry) and SAM metadata of the generation units (``$SP_DATA/sam/official_gen2_ncdelta_{flatcaf,reco1}.meta.csv.gz``).

Three tables (docs/analysis/OFFICIAL_SIGNAL_MASTER_TABLE.md):
  records  one row per QUALIFYING signal neutrino (NC, GENIE-record Delta-radiative). The 6 events with two qualifying neutrinos keep BOTH rows;
           ``is_selected_signal`` marks the one the deterministic event-level rule adopted (``truth_signal`` rule, SIGNAL_TRUTH_AND_DENOMINATOR.md s5).
  events   one row per stored signal event (the selected record plus event bookkeeping)
  units    one row per generation (reco1) unit with SAM POT, generated-event count and flatCAF availability

DENOMINATOR RULE (event level, region V a parameter):  an event counts ONCE in N_signal_truth(V) if >= 1 qualifying neutrino has its vertex in V;
its truth class is that of the in-V qualifying neutrino (lowest index if several, flagged).  N_signal_truth, POT and generated throws are three
different quantities; the throws are never the efficiency denominator.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .truth import ActiveVolume

KEY = ["file_index", "ev"]
CAT_LABEL = {0: "0p", 1: "1p", 2: "ge2p"}
DELTA_LABEL = {2114: "Delta0", 2214: "Delta+"}
PROTON_KE_MEV = 35.0                    # PROVISIONAL, as everywhere in this analysis


def parent_reco1_name(flatcaf_meta: pd.DataFrame) -> pd.Series:
    """flatCAF filename -> its (single) SAM parent, the reco1 generation unit."""
    p = flatcaf_meta.set_index("name").parents
    if p.str.contains(",").any() or p.isna().any():
        raise ValueError("a flatCAF has none or several SAM parents: the unit mapping is not one-to-one")
    return p


def build_units(flat_meta: pd.DataFrame, reco1_meta: pd.DataFrame, n_events_by_flatcaf: pd.Series | None = None) -> pd.DataFrame:
    """One row per generation unit (reco1 file). POT / generated events are the SAM ``mc.pot`` / ``mc.generated_event_count`` of the unit."""
    par = parent_reco1_name(flat_meta)
    u = reco1_meta.rename(columns={"name": "reco1_unit", "pot": "unit_pot", "gen": "unit_gen_events", "events": "reco1_events"})[
        ["reco1_unit", "unit_pot", "unit_gen_events", "reco1_events"]].copy()
    if u.reco1_unit.duplicated().any():
        raise ValueError("duplicate reco1 unit names in SAM metadata")
    child = pd.DataFrame({"flatcaf": par.index, "reco1_unit": par.values})
    if child.reco1_unit.duplicated().any():
        raise ValueError("two flatCAFs share one reco1 parent")
    u = u.merge(child, on="reco1_unit", how="left")
    u["flatcaf_status"] = np.where(u.flatcaf.notna(), "flatcaf_available", "no_flatcaf_child")
    if n_events_by_flatcaf is not None:
        u["n_signal_events"] = u.flatcaf.map(n_events_by_flatcaf).fillna(0).astype(int)
    if (~child.reco1_unit.isin(u.reco1_unit)).any():
        raise ValueError("a flatCAF names a parent absent from the reco1 definition")
    return u


def qualifying_neutrinos(nu: pd.DataFrame) -> pd.DataFrame:
    """Qualifying signal neutrinos: NC AND a GENIE-record Delta radiative decay (the filter's own process test). A CC neutrino with a Delta-radiative
    photon does NOT qualify (3 in the official sample); ``k`` is the ``rec.mc.nu`` index = position within the event."""
    nu = nu.copy()
    nu["k"] = nu.groupby(KEY).cumcount()
    return nu[nu.rec_is_delta_rad.astype(bool) & (nu.isnc == 1)]


def build_records(events: pd.DataFrame, nu: pd.DataFrame, files: pd.DataFrame, units: pd.DataFrame, flat_meta: pd.DataFrame, *,
                  filter_box: ActiveVolume, tpc_box: ActiveVolume) -> pd.DataFrame:
    q = qualifying_neutrinos(nu)
    if len(q) == 0:
        raise ValueError("no qualifying signal neutrino")
    r = q.rename(columns={"k": "signal_nu_index", "pdg": "nu_pdg", "E": "nu_energy_gev", "position_x": "vtx_x", "position_y": "vtx_y",
                          "position_z": "vtx_z", "rec_delta_pdg": "delta_pdg", "rec_nucleon_pdg": "decay_nucleon_pdg", "n_p35": "n_true_protons",
                          "n_p_all": "n_true_protons_all_ke", "n_pi0": "n_primary_pi0", "n_pic": "n_primary_pi_charged", "n_n": "n_primary_neutrons"})
    r["photon_energy_mev"] = r.rec_photon_e_gev * 1000.0
    r["n_signal_nu"] = r.groupby(KEY).signal_nu_index.transform("size")
    r["multi_signal_event"] = r.n_signal_nu > 1
    r["delta_charge"] = r.delta_pdg.map({2114: 0, 2214: 1})
    r["truth_cat"] = np.clip(r.n_true_protons.values, 0, 2).astype(np.int8)
    r["in_filter_box"] = filter_box.contains(r.vtx_x, r.vtx_y, r.vtx_z).values
    r["in_active_tpc"] = tpc_box.contains(r.vtx_x, r.vtx_y, r.vtx_z).values
    ev = events[KEY + ["run", "subrun", "evt", "signal_nu_index"]].rename(columns={"signal_nu_index": "selected_nu_index"})
    r = r.merge(ev, on=KEY, how="left", validate="many_to_one")
    if r.selected_nu_index.isna().any():
        raise ValueError("a qualifying neutrino belongs to an event absent from the events table")
    r["is_selected_signal"] = r.signal_nu_index == r.selected_nu_index
    if (r.groupby(KEY).is_selected_signal.sum() != 1).any():
        raise ValueError("an event does not have exactly one selected signal record")
    f = files.set_index("file_index").source_file
    r["flatcaf"] = r.file_index.map(f)
    r = r.merge(units.dropna(subset=["flatcaf"])[["flatcaf", "reco1_unit", "unit_pot", "unit_gen_events", "flatcaf_status"]], on="flatcaf", how="left", validate="many_to_one")
    if r.reco1_unit.isna().any():
        raise ValueError("a flatCAF of the truth census has no generation unit in SAM")
    cols = ["reco1_unit", "flatcaf", "file_index", "ev", "run", "subrun", "evt", "signal_nu_index", "is_selected_signal", "n_signal_nu",
            "multi_signal_event", "delta_pdg", "delta_charge", "decay_nucleon_pdg", "nu_pdg", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z",
            "in_filter_box", "in_active_tpc", "photon_energy_mev", "n_true_protons", "n_true_protons_all_ke", "truth_cat", "n_primary_pi0",
            "n_primary_pi_charged", "n_primary_neutrons", "genie_mode", "resnum", "unit_pot", "unit_gen_events", "flatcaf_status"]
    return r[cols].sort_values(KEY + ["signal_nu_index"]).reset_index(drop=True)


def build_events(records: pd.DataFrame) -> pd.DataFrame:
    """One row per stored signal event: the selected record + ``n_signal_in_filter_box`` / ``n_signal_in_active_tpc`` (multi-signal diagnostics)."""
    g = records.groupby(KEY)
    ev = records[records.is_selected_signal].copy().set_index(KEY)
    ev["n_signal_in_filter_box"] = g.in_filter_box.sum()
    ev["n_signal_in_active_tpc"] = g.in_active_tpc.sum()
    return ev.reset_index()


def region_records(records: pd.DataFrame, box: ActiveVolume | None) -> pd.DataFrame:
    """Event-level signal records of region V: one per event with >= 1 qualifying neutrino in V (lowest index if several, ``n_in_region`` flags it).
    ``box=None`` means no region cut. A qualifying neutrino outside V is never the signal interaction of the event."""
    r = records
    if box is not None:
        r = r[box.contains(r.vtx_x, r.vtx_y, r.vtx_z).values]
    r = r.sort_values(KEY + ["signal_nu_index"])
    n = r.groupby(KEY).signal_nu_index.transform("size")
    out = r.groupby(KEY, sort=False).head(1).copy()
    out["n_in_region"] = n.loc[out.index].values
    return out.reset_index(drop=True)


def denominator_summary(records: pd.DataFrame, units: pd.DataFrame, box: ActiveVolume | None, *, label: str,
                        unit_subset: set | None = None) -> dict:
    """N_signal_truth(V; S) and its class splits, with POT(S) and generated throws(S) kept SEPARATE.

    S = units with a flatCAF (or ``unit_subset`` of reco1 unit names: e.g. the units that have a merged CAF). Same S in numerator and POT."""
    s_units = units[units.flatcaf_status == "flatcaf_available"]
    if unit_subset is not None:
        s_units = s_units[s_units.reco1_unit.isin(unit_subset)]
        records = records[records.reco1_unit.isin(unit_subset)]
    rr = region_records(records, box)
    d = dict(region=label, box=None if box is None else dict(x=list(box.x), y=list(box.y), z=list(box.z)),
             N_signal_truth=int(len(rr)), n_events_with_several_in_region=int((rr.n_in_region > 1).sum()),
             POT_signal_sample=float(s_units.unit_pot.sum()), generated_throws=int(s_units.unit_gen_events.sum()), n_units=int(len(s_units)),
             truth_class={CAT_LABEL[c]: int((rr.truth_cat == c).sum()) for c in (0, 1, 2)},
             delta={DELTA_LABEL[p]: int((rr.delta_pdg == p).sum()) for p in (2114, 2214)})
    d["delta_x_class"] = {f"{DELTA_LABEL[p]}_{CAT_LABEL[c]}": int(((rr.delta_pdg == p) & (rr.truth_cat == c)).sum()) for p in (2114, 2214) for c in (0, 1, 2)}
    d["R_signal_per_POT"] = d["N_signal_truth"] / d["POT_signal_sample"] if d["POT_signal_sample"] > 0 else float("nan")
    d["R_signal_per_1e20_POT"] = d["R_signal_per_POT"] * 1e20
    d["NOTE"] = "generated_throws is exposure/filter bookkeeping, NOT the efficiency denominator"
    assert sum(d["truth_class"].values()) == d["N_signal_truth"] and sum(d["delta"].values()) == d["N_signal_truth"]
    return d


def load_regions(path=None) -> dict:
    """``configs/signal_regions.yaml`` -> {name: ActiveVolume}. Unknown regions raise (no silent default)."""
    import yaml
    from pathlib import Path
    p = Path(path) if path else Path(__file__).resolve().parents[2] / "configs" / "signal_regions.yaml"
    raw = yaml.safe_load(open(p))
    return {k: ActiveVolume(x=tuple(v["x"]), y=tuple(v["y"]), z=tuple(v["z"])) for k, v in raw["regions"].items()}
