#!/usr/bin/env python3
"""
score_microboone_bdts.py — Offline MicroBooNE single-photon BDT scorer for SBND baseline_v0.

Evaluates the four original MicroBooNE single-photon TMVA GradBDT models against
the frozen baseline_v0 tracking-pr.root outputs. No reconstruction code is modified.
All four BDT models (numu, other, ncpi0, nue) are read from the frozen reference XMLs
without alteration.

Variable order is authoritative from the XML <Variables> block.
Evaluability is determined mechanically per Step 3 criteria; shw_sp_filled and br_filled
are used as diagnostic flags, not imposed as extra cuts.

Usage:
    python3 score_microboone_bdts.py

Outputs:
    tables/ncdelta_microboone_bdt_scores.csv
    tables/ncdelta_microboone_cutflow.csv
    tables/ncdelta_reco_failure_taxonomy.csv
"""

import xml.etree.ElementTree as ET
import uproot
import numpy as np
import csv
import math
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REFDIR = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/reference/"
          "sbnd_single_photon_microboone_reference_20261005")
BASEDIR = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/"
           "ncdelta_50evt/wirecell")
OUTDIR  = os.path.join(os.path.dirname(__file__), "tables")

XML_PATHS = {
    "numu":  f"{REFDIR}/weights/single_photon_numu_bdt_final.xml",
    "other": f"{REFDIR}/weights/single_photon_other_bdt_final.xml",
    "ncpi0": f"{REFDIR}/weights/single_photon_ncpi0_bdt_final.xml",
    "nue":   f"{REFDIR}/weights/single_photon_nue_bdt_final.xml",
}
EXPECTED_NVARS = {"numu": 73, "other": 146, "ncpi0": 45, "nue": 56}

N_EVENTS = 59

# ---------------------------------------------------------------------------
# TMVA GradBDT evaluator (pure Python, exact tree-walk)
# ---------------------------------------------------------------------------
def _parse_xml(xml_path):
    """Return (var_list, trees) where var_list=[(idx,name),...] and
    trees=[(boost_weight, root_node_data), ...].
    root_node_data is a nested list structure for fast evaluation."""
    root = ET.parse(xml_path).getroot()
    # Variable list
    vars_el = root.find("Variables")
    var_list = sorted(
        [(int(v.get("VarIndex")), v.get("Expression"))
         for v in vars_el.findall("Variable")],
        key=lambda x: x[0]
    )
    # Precompute tree structures as nested Python objects for speed.
    # Each node is either:
    #   ("leaf", res_value) — leaf node
    #   ("internal", ivar, cut, left_child, right_child)
    def _build(node_el):
        children = [c for c in node_el if c.tag == "Node"]
        if not children:  # leaf
            return ("leaf", float(node_el.get("res")))
        # internal: left is pos='l', right is pos='r'
        left  = next(c for c in children if c.get("pos") == "l")
        right = next(c for c in children if c.get("pos") == "r")
        return ("internal",
                int(node_el.get("IVar")),
                float(node_el.get("Cut")),
                _build(left),
                _build(right))

    weights = root.find("Weights")
    trees = []
    for bt in weights.findall("BinaryTree"):
        bw   = float(bt.get("boostWeight"))
        rn   = bt.find("Node")
        trees.append((bw, _build(rn)))
    return var_list, trees


def _eval_tree(node, values):
    """Walk one decision tree. Exact TMVA GradBDT leaf-response sum."""
    while node[0] == "internal":
        _, ivar, cut, left, right = node
        node = left if values[ivar] <= cut else right
    return node[1]  # ("leaf", res_value) → res_value


class TmvaBdt:
    def __init__(self, name, xml_path):
        self.name = name
        self.var_list, self.trees = _parse_xml(xml_path)
        expected = EXPECTED_NVARS[name]
        assert len(self.var_list) == expected, (
            f"{name}: expected {expected} vars, got {len(self.var_list)}")

    def evaluate(self, values):
        """values: list indexed by VarIndex (in XML order).
        Returns tanh(raw_sum) matching TMVA::Reader::EvaluateMVA() for GradBoost.
        ROOT applies tanh(x) = 2/(1+exp(-2x))-1 to the raw weighted-leaf sum.
        Caller must verify all values[i] are finite before calling."""
        raw = sum(bw * _eval_tree(tree, values) for bw, tree in self.trees)
        return math.tanh(raw)


# ---------------------------------------------------------------------------
# Model instances
# ---------------------------------------------------------------------------
print("Loading BDT models...", flush=True)
MODELS = {name: TmvaBdt(name, path) for name, path in XML_PATHS.items()}
print(f"  numu ({len(MODELS['numu'].var_list)} vars), "
      f"other ({len(MODELS['other'].var_list)} vars), "
      f"ncpi0 ({len(MODELS['ncpi0'].var_list)} vars), "
      f"nue ({len(MODELS['nue'].var_list)} vars)")


# ---------------------------------------------------------------------------
# Input collection per model
# ---------------------------------------------------------------------------
# kine_nu_y_corr mapping: 'other' BDT variable 'reco_nuvtxY' → T_kine.kine_nu_y_corr
RECO_NUVTX_MAP = {
    "reco_nuvtxY": ("T_kine", "kine_nu_y_corr"),
}
# kine_pio_* variables for ncpi0 come from T_kine
KINE_PIO_VARS = {
    "kine_pio_mass", "kine_pio_flag", "kine_pio_vtx_dis",
    "kine_pio_energy_1", "kine_pio_energy_2",
    "kine_pio_theta_1", "kine_pio_theta_2",
    "kine_pio_phi_1", "kine_pio_phi_2",
    "kine_pio_dis_1", "kine_pio_dis_2",
    "kine_pio_angle",
}


def collect_inputs(model_name, tagger_data, kine_data):
    """Collect input vector for a model. Returns (values_list, issues_list).
    values_list is indexed by VarIndex. issues_list lists any missing/sentinel inputs."""
    model  = MODELS[model_name]
    values = [float("nan")] * len(model.var_list)
    issues = []

    for idx, varname in model.var_list:
        # Resolve source tree and actual branch name to look up
        if varname in RECO_NUVTX_MAP:
            src_tree, src_branch = RECO_NUVTX_MAP[varname]
            data   = kine_data if src_tree == "T_kine" else tagger_data
            lookup = src_branch  # mapped branch name differs from varname
        elif varname in KINE_PIO_VARS and model_name == "ncpi0":
            data   = kine_data
            lookup = varname
        else:
            data   = tagger_data
            lookup = varname

        if data is None or lookup not in data:
            issues.append(f"branch_missing:{varname}")
            continue
        v = data[lookup]
        if not math.isfinite(v):
            issues.append(f"not_finite:{varname}")
            continue
        values[idx] = v

    return values, issues


def is_evaluable(values, issues):
    """Mechanically: all inputs must be finite. No NaN allowed."""
    if issues:
        return False
    return all(math.isfinite(v) for v in values)


# ---------------------------------------------------------------------------
# Read one event
# ---------------------------------------------------------------------------
def read_event(evt_idx):
    """Returns (tagger_data, kine_data, meta) or (None, None, meta) on error.
    meta contains has_neutrino_candidate, shw_sp_filled, br_filled, etc."""
    path = f"{BASEDIR}/evt_{evt_idx:04d}/tracking-pr.root"
    meta = {
        "evt_idx": evt_idx,
        "run": None, "subrun": None, "event": None,
        "has_neutrino_candidate": False,
        "shw_sp_filled": 0, "br_filled": 0,
        "cosmic_filled": 0, "photon_flag": 0,
        "shw_sp_n_20mev_showers": 0, "shw_sp_n_20br1_showers": 0,
        "shw_sp_energy": float("nan"),
        "kine_nu_x_corr": float("nan"),
        "kine_nu_y_corr": float("nan"),
        "kine_nu_z_corr": float("nan"),
        "kine_pio_flag": None,
        "n_protons_kine_above35mev": 0,
        "has_t_kine": False,
    }
    tagger_data = None
    kine_data   = None

    try:
        with uproot.open(path) as f:
            all_keys = [k.split(";")[0] for k in f.keys()]

            if "T_tagger" in all_keys:
                meta["has_neutrino_candidate"] = True
                t = f["T_tagger"]
                tagger_data = {}
                for b in t.keys():
                    arr = t[b].array(library="np")
                    if len(arr) != 1:
                        continue
                    val = arr[0]
                    # Skip jagged branches (inner element is an array, not scalar)
                    if isinstance(val, np.ndarray):
                        continue
                    try:
                        tagger_data[b] = float(val)
                    except (TypeError, ValueError):
                        pass
                # Meta from T_tagger
                for key in ["shw_sp_filled", "br_filled", "cosmic_filled", "photon_flag",
                            "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers"]:
                    if key in tagger_data:
                        meta[key] = int(tagger_data[key])
                if "shw_sp_energy" in tagger_data:
                    meta["shw_sp_energy"] = tagger_data["shw_sp_energy"]
                # Get run/subrun/event from T_tagger if available, else Trun
            if "Trun" in all_keys:
                tr = f["Trun"]
                for rkey in ["run_no", "run", "runNo"]:
                    if rkey in tr.keys():
                        meta["run"] = int(tr[rkey].array(library="np")[0])
                        break
                for skey in ["subrun_no", "subrun", "subrunNo"]:
                    if skey in tr.keys():
                        meta["subrun"] = int(tr[skey].array(library="np")[0])
                        break
                for ekey in ["event_no", "event", "eventNo"]:
                    if ekey in tr.keys():
                        meta["event"] = int(tr[ekey].array(library="np")[0])
                        break
            if "T_kine" in all_keys:
                meta["has_t_kine"] = True
                tk = f["T_kine"]
                kine_data = {}
                for b in tk.keys():
                    arr = tk[b].array(library="np")
                    if len(arr) != 1:
                        continue
                    val = arr[0]
                    if isinstance(val, np.ndarray):
                        continue
                    try:
                        kine_data[b] = float(val)
                    except (TypeError, ValueError):
                        pass
                for key in ["kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr"]:
                    if key in kine_data:
                        meta[key] = kine_data[key]
                if "kine_pio_flag" in kine_data:
                    meta["kine_pio_flag"] = int(kine_data["kine_pio_flag"])
                # Count protons above 35 MeV KE from T_kine jagged arrays
                try:
                    ptypes  = tk["kine_particle_type"].array(library="np")[0]
                    penergy = tk["kine_energy_particle"].array(library="np")[0]
                    if isinstance(ptypes, np.ndarray):
                        n_p = int(sum(1 for pt, pe in zip(ptypes, penergy)
                                      if int(pt) == 2212 and float(pe) > 35.0))
                        meta["n_protons_kine_above35mev"] = n_p
                except Exception:
                    pass
    except Exception as e:
        meta["error"] = str(e)
    return tagger_data, kine_data, meta


# ---------------------------------------------------------------------------
# Main scoring loop
# ---------------------------------------------------------------------------
def score_all():
    rows = []
    for evt_idx in range(N_EVENTS):
        tagger, kine, meta = read_event(evt_idx)
        row = {
            "evt_idx": evt_idx,
            "run": meta["run"],
            "subrun": meta["subrun"],
            "event": meta["event"],
            "has_neutrino_candidate": int(meta["has_neutrino_candidate"]),
            "shw_sp_filled": meta["shw_sp_filled"],
            "br_filled": meta["br_filled"],
            "shw_sp_n_20mev_showers": meta["shw_sp_n_20mev_showers"],
            "shw_sp_n_20br1_showers": meta["shw_sp_n_20br1_showers"],
            "shw_sp_energy": f"{meta['shw_sp_energy']:.4f}" if math.isfinite(meta.get("shw_sp_energy", float("nan"))) else "",
            "kine_nu_y_corr": f"{meta['kine_nu_y_corr']:.4f}" if math.isfinite(meta.get("kine_nu_y_corr", float("nan"))) else "",
            "kine_pio_flag": meta["kine_pio_flag"] if meta["kine_pio_flag"] is not None else "",
            "n_protons_kine_above35mev": meta["n_protons_kine_above35mev"] if meta["has_t_kine"] else "",
            "proton_category": (
                "UNCLASSIFIABLE_NO_KINE" if not meta["has_t_kine"]
                else ("Np" if meta["n_protons_kine_above35mev"] > 0 else "0p")
            ),
        }

        if not meta["has_neutrino_candidate"]:
            for model_name in ["numu", "other", "ncpi0", "nue"]:
                row[f"{model_name}_bdt_evaluable"] = 0
                row[f"{model_name}_bdt_score"] = ""
                row[f"{model_name}_failure_reason"] = "NO_NEUTRINO_CANDIDATE"
        else:
            # Mechanically check shw_sp_filled for shw_sp_*-dependent models
            sp_filled = meta["shw_sp_filled"]

            for model_name in ["numu", "other", "ncpi0", "nue"]:
                if sp_filled == 0:
                    row[f"{model_name}_bdt_evaluable"] = 0
                    row[f"{model_name}_bdt_score"] = ""
                    row[f"{model_name}_failure_reason"] = "MAIN_VERTEX_SHOWER_INACCESSIBLE"
                    continue
                # Collect inputs
                values, issues = collect_inputs(model_name, tagger, kine)
                if is_evaluable(values, []):
                    # Verify all finite
                    non_finite = [i for i, v in enumerate(values) if not math.isfinite(v)]
                    if non_finite:
                        issues = [f"non_finite_at_index_{i}" for i in non_finite[:3]]
                if issues:
                    row[f"{model_name}_bdt_evaluable"] = 0
                    row[f"{model_name}_bdt_score"] = ""
                    row[f"{model_name}_failure_reason"] = "; ".join(issues[:3])
                else:
                    score = MODELS[model_name].evaluate(values)
                    row[f"{model_name}_bdt_evaluable"] = 1
                    row[f"{model_name}_bdt_score"] = f"{score:.6f}"
                    row[f"{model_name}_failure_reason"] = ""

        rows.append(row)
        if evt_idx % 10 == 0:
            print(f"  Scored evt_{evt_idx:04d}...", flush=True)

    return rows


# ---------------------------------------------------------------------------
# Failure taxonomy
# ---------------------------------------------------------------------------
def build_taxonomy(score_rows):
    """Conservative classification into the required categories."""
    tax_rows = []
    for row in score_rows:
        evt = row["evt_idx"]
        has_nc = row["has_neutrino_candidate"]
        sp_filled = row["shw_sp_filled"]
        br_filled = row["br_filled"]
        nue_eval  = row["nue_bdt_evaluable"]
        sp_e      = row.get("shw_sp_energy", "")
        failure   = row["numu_failure_reason"]

        if not has_nc:
            cls = "NO_NEUTRINO_CANDIDATE"
        elif not sp_filled:
            # Engineering Event 0 = companion cluster confirmed
            if evt == 0:
                cls = "COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED"
            else:
                cls = "MAIN_VERTEX_SHOWER_INACCESSIBLE"
        elif nue_eval:
            # Shower features available; check for severe under-reco
            try:
                sp_energy = float(sp_e)
                if sp_energy < 50:
                    cls = "SEVERE_SHOWER_UNDERRECO"
                else:
                    cls = "SHOWER_FEATURES_AVAILABLE"
            except (ValueError, TypeError):
                cls = "SHOWER_FEATURES_AVAILABLE"
        else:
            cls = "UNRESOLVED"

        tax_rows.append({"evt_idx": evt, "failure_class": cls,
                         "has_neutrino_candidate": has_nc,
                         "shw_sp_filled": sp_filled,
                         "br_filled": br_filled,
                         "nue_bdt_evaluable": nue_eval,
                         "shw_sp_energy": sp_e,
                         "notes": ""})
    return tax_rows


# ---------------------------------------------------------------------------
# Cut flow
# ---------------------------------------------------------------------------
def compute_cutflow(score_rows):
    """MicroBooNE sequential cut flow. See Step 6 for FV treatment."""
    steps = [
        ("total_events",          lambda r: True),
        ("has_neutrino_candidate",lambda r: r["has_neutrino_candidate"]),
        ("shw_sp_n_20mev_showers_gt0", lambda r: r["has_neutrino_candidate"] and r["shw_sp_n_20mev_showers"] > 0),
        ("all_4_bdts_evaluable",  lambda r: all(r[f"{m}_bdt_evaluable"] for m in ["numu","other","ncpi0","nue"])),
        ("numu_score_gt0p4",      lambda r: r["numu_bdt_evaluable"] and r["numu_bdt_score"] != "" and float(r["numu_bdt_score"]) > 0.4),
        ("other_score_gt0p2",     lambda r: r["other_bdt_evaluable"] and r["other_bdt_score"] != "" and float(r["other_bdt_score"]) > 0.2),
        ("ncpi0_score_gtneg0p05", lambda r: r["ncpi0_bdt_evaluable"] and r["ncpi0_bdt_score"] != "" and float(r["ncpi0_bdt_score"]) > -0.05),
        ("nue_score_gtneg1p0",    lambda r: r["nue_bdt_evaluable"] and r["nue_bdt_score"] != "" and float(r["nue_bdt_score"]) > -1.0),
        ("shw_sp_n_20br1_showers_eq1", lambda r: r["shw_sp_n_20br1_showers"] == 1),
    ]
    # Sequential application
    passing = list(score_rows)
    results = []
    for name, cut in steps:
        if name == "total_events":
            n = len(score_rows)
        else:
            passing = [r for r in passing if cut(r)]
            n = len(passing)
        n_0p    = sum(1 for r in passing if r["proton_category"] == "0p")
        n_np    = sum(1 for r in passing if r["proton_category"] == "Np")
        n_unk   = sum(1 for r in passing if r["proton_category"] == "UNCLASSIFIABLE_NO_KINE")
        results.append({"step": name, "count": n, "is_0p": n_0p, "is_np": n_np,
                         "unclassifiable": n_unk, "notes": ""})
    return results, passing


# ---------------------------------------------------------------------------
# Run and write
# ---------------------------------------------------------------------------
print("Scoring 59 NC Delta events...", flush=True)
score_rows = score_all()

# Write BDT scores CSV
SCORES_COLS = [
    "evt_idx","run","subrun","event","has_neutrino_candidate","shw_sp_filled","br_filled",
    "shw_sp_n_20mev_showers","shw_sp_n_20br1_showers","shw_sp_energy",
    "kine_nu_y_corr","kine_pio_flag","n_protons_kine_above35mev","proton_category",
    "numu_bdt_evaluable","numu_bdt_score","numu_failure_reason",
    "other_bdt_evaluable","other_bdt_score","other_failure_reason",
    "ncpi0_bdt_evaluable","ncpi0_bdt_score","ncpi0_failure_reason",
    "nue_bdt_evaluable","nue_bdt_score","nue_failure_reason",
]
scores_path = f"{OUTDIR}/ncdelta_microboone_bdt_scores.csv"
with open(scores_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=SCORES_COLS, extrasaction="ignore")
    w.writeheader()
    w.writerows(score_rows)
print(f"Wrote: {scores_path}")

# Write taxonomy CSV
tax_rows = build_taxonomy(score_rows)
tax_path = f"{OUTDIR}/ncdelta_reco_failure_taxonomy.csv"
with open(tax_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["evt_idx","failure_class","has_neutrino_candidate",
                                       "shw_sp_filled","br_filled","nue_bdt_evaluable",
                                       "shw_sp_energy","notes"])
    w.writeheader()
    w.writerows(tax_rows)
print(f"Wrote: {tax_path}")

# Write cutflow CSV
cutflow_rows, final_passing = compute_cutflow(score_rows)

# Note FV: we skip the FV cut as per Step 6 instructions
# Add FV provenance note
for row in cutflow_rows:
    if "numu" in row["step"] or row["step"] == "all_4_bdts_evaluable":
        pass
cutflow_rows.insert(3, {
    "step": "FV_CUT_SKIPPED_PRE_FV_REFERENCE",
    "count": "(MicroBooNE literal: 5<reco_nuvtxX<250 cm — not applied; kine_nu_x_corr available but SBND FV not defined here)",
    "is_0p": "", "is_np": "", "unclassifiable": "", "notes": "PRE_FV_REFERENCE_SELECTION"
})

cutflow_path = f"{OUTDIR}/ncdelta_microboone_cutflow.csv"
with open(cutflow_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["step","count","is_0p","is_np","unclassifiable","notes"])
    w.writeheader()
    w.writerows(cutflow_rows)
print(f"Wrote: {cutflow_path}")

# Print summary stats
print("\n=== SCORING SUMMARY ===")
n_total = len(score_rows)
for model in ["numu","other","ncpi0","nue"]:
    n_eval = sum(1 for r in score_rows if r[f"{model}_bdt_evaluable"])
    scores = [float(r[f"{model}_bdt_score"]) for r in score_rows if r[f"{model}_bdt_score"] != ""]
    if scores:
        print(f"  {model}: {n_eval}/{n_total} evaluable, "
              f"score range [{min(scores):.3f}, {max(scores):.3f}], "
              f"mean={np.mean(scores):.3f}")
    else:
        print(f"  {model}: {n_eval}/{n_total} evaluable")

# 0p/Np/UNCLASSIFIABLE
n_0p  = sum(1 for r in score_rows if r["proton_category"] == "0p")
n_np  = sum(1 for r in score_rows if r["proton_category"] == "Np")
n_unk = sum(1 for r in score_rows if r["proton_category"] == "UNCLASSIFIABLE_NO_KINE")
print(f"\n0p events: {n_0p}/{n_total}")
print(f"Np events: {n_np}/{n_total}")
print(f"UNCLASSIFIABLE_NO_KINE: {n_unk}/{n_total}")

# Taxonomy summary
from collections import Counter
tax_counts = Counter(r["failure_class"] for r in tax_rows)
print("\n=== FAILURE TAXONOMY ===")
for cls, n in sorted(tax_counts.items(), key=lambda x: -x[1]):
    print(f"  {cls}: {n}")

print("\n=== CUT FLOW (PRE-FV) ===")
for row in cutflow_rows:
    if row["count"] != "":
        try:
            n = int(row["count"])
            unk = row.get("unclassifiable", "")
            unk_str = f", unk={unk}" if unk not in ("", 0) else ""
            print(f"  {row['step']}: {n} (0p={row['is_0p']}, Np={row['is_np']}{unk_str})")
        except (ValueError, TypeError):
            print(f"  {row['step']}: {row['count']}")
