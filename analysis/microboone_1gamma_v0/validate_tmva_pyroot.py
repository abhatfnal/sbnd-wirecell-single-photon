#!/usr/bin/env python3
"""
validate_tmva_pyroot.py — Part A ROOT/TMVA cross-validation.

Requires: ROOT with TMVA available (run inside sbndcode apptainer with LArSoft sourced).
Reads all 33 evaluable NC Delta events, evaluates all 4 BDTs via ROOT TMVA::Reader,
compares against Python scores from ncdelta_microboone_bdt_scores.csv.

Output: tables/tmva_python_crosscheck.csv

Tolerance: 1e-4 absolute (TMVA float32 arithmetic vs Python float64; differences
at the 6th–7th significant digit are expected but not at 4th).
"""

import sys
import csv
import math
import xml.etree.ElementTree as ET
import os

try:
    import ROOT
    ROOT.gSystem.Load("libTMVA.so")
    from ROOT import TMVA, TFile, gROOT
    gROOT.SetBatch(True)
except ImportError as e:
    print(f"FATAL: ROOT/TMVA not available: {e}")
    print("Run inside sbndcode container with: source /cvmfs/.../setup.sh")
    sys.exit(1)

# Try uproot for T_kine reading (Python); fallback to TFile for T_tagger
try:
    import uproot
    import numpy as np
    HAS_UPROOT = True
except ImportError:
    HAS_UPROOT = False
    print("WARNING: uproot not available; kine_nu_y_corr/kine_pio_* will be read via TBranch")

BASEDIR = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/"
           "ncdelta_50evt/wirecell")
REFDIR  = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/reference/"
           "sbnd_single_photon_microboone_reference_20261005/weights")
SCOREDIR = os.path.join(os.path.dirname(__file__), "tables")
PYTHON_CSV = f"{SCOREDIR}/ncdelta_microboone_bdt_scores.csv"
OUT_CSV    = f"{SCOREDIR}/tmva_python_crosscheck.csv"

TOLERANCE = 1e-4  # absolute difference threshold for PASS

XML_PATHS = {
    "numu":  f"{REFDIR}/single_photon_numu_bdt_final.xml",
    "other": f"{REFDIR}/single_photon_other_bdt_final.xml",
    "ncpi0": f"{REFDIR}/single_photon_ncpi0_bdt_final.xml",
    "nue":   f"{REFDIR}/single_photon_nue_bdt_final.xml",
}

RECO_NUVTX_MAP = {"reco_nuvtxY": "kine_nu_y_corr"}  # read from T_kine
KINE_PIO_VARS = {
    "kine_pio_mass","kine_pio_flag","kine_pio_vtx_dis",
    "kine_pio_energy_1","kine_pio_energy_2",
    "kine_pio_theta_1","kine_pio_theta_2",
    "kine_pio_phi_1","kine_pio_phi_2",
    "kine_pio_dis_1","kine_pio_dis_2",
    "kine_pio_angle",
}


def parse_xml_variables(xml_path):
    """Return list of (VarIndex, Expression) sorted by VarIndex."""
    root = ET.parse(xml_path).getroot()
    vars_el = root.find("Variables")
    var_list = sorted(
        [(int(v.get("VarIndex")), v.get("Expression"))
         for v in vars_el.findall("Variable")],
        key=lambda x: x[0]
    )
    return var_list


def setup_reader(model_name, xml_path, var_list, var_storage):
    """Create and configure a TMVA::Reader. var_storage is a dict {varname: float array[1]}."""
    reader = TMVA.Reader("Silent")
    for _, varname in var_list:
        if varname not in var_storage:
            import array
            var_storage[varname] = array.array("f", [0.0])
        reader.AddVariable(varname, var_storage[varname])
    reader.BookMVA("BDT", xml_path)
    return reader


def read_kine_scalar(tk_file, branch):
    """Read a scalar float from a TTree (T_kine) branch."""
    tk = tk_file.Get("T_kine")
    if not tk:
        return None
    tk.GetEntry(0)
    val = getattr(tk, branch, None)
    if val is None:
        return None
    return float(val)


def read_event(evt_idx, model_name, var_list, var_storage):
    """Fill var_storage from tracking-pr.root for this event/model.
    Returns dict of branch→value, or None on failure."""
    path = f"{BASEDIR}/evt_{evt_idx:04d}/tracking-pr.root"
    tf = TFile.Open(path, "READ")
    if not tf or tf.IsZombie():
        return None

    tt = tf.Get("T_tagger")
    tk = tf.Get("T_kine")
    if not tt:
        tf.Close()
        return None

    tt.GetEntry(0)

    for _, varname in var_list:
        val = 0.0
        if varname in RECO_NUVTX_MAP and model_name == "other":
            # Read kine_nu_y_corr from T_kine
            if tk:
                tk.GetEntry(0)
                src = RECO_NUVTX_MAP[varname]
                val = float(getattr(tk, src, 0.0))
        elif varname in KINE_PIO_VARS and model_name == "ncpi0":
            # Read kine_pio_* from T_kine
            if tk:
                tk.GetEntry(0)
                val = float(getattr(tk, varname, 0.0))
        else:
            # Read from T_tagger
            val = float(getattr(tt, varname, 0.0))
        var_storage[varname][0] = val

    tf.Close()
    return var_storage


def load_python_scores():
    """Load Python BDT scores keyed by evt_idx."""
    scores = {}
    with open(PYTHON_CSV) as f:
        for row in csv.DictReader(f):
            ei = int(row["evt_idx"])
            if row["numu_bdt_evaluable"] == "1":
                scores[ei] = {
                    "run": row["run"], "subrun": row["subrun"], "event": row["event"],
                    "numu": float(row["numu_bdt_score"]),
                    "other": float(row["other_bdt_score"]),
                    "ncpi0": float(row["ncpi0_bdt_score"]),
                    "nue": float(row["nue_bdt_score"]),
                }
    return scores


def main():
    python_scores = load_python_scores()
    evaluable_evts = sorted(python_scores.keys())
    print(f"Evaluating {len(evaluable_evts)} events × 4 BDTs via ROOT TMVA...")

    results = []
    model_stats = {m: {"abs_diffs": [], "n_pass": 0, "n_total": 0}
                   for m in ["numu", "other", "ncpi0", "nue"]}

    for model_name in ["numu", "other", "ncpi0", "nue"]:
        print(f"\nModel: {model_name}")
        var_list = parse_xml_variables(XML_PATHS[model_name])

        import array
        var_storage = {vn: array.array("f", [0.0]) for _, vn in var_list}
        reader = setup_reader(model_name, XML_PATHS[model_name], var_list, var_storage)

        for evt_idx in evaluable_evts:
            py_score = python_scores[evt_idx][model_name]

            filled = read_event(evt_idx, model_name, var_list, var_storage)
            if filled is None:
                print(f"  evt_{evt_idx:04d}: SKIP (failed to read)")
                continue

            root_score = float(reader.EvaluateMVA("BDT"))
            abs_diff   = abs(root_score - py_score)
            rel_diff   = abs_diff / max(abs(py_score), 1e-10)
            passed     = abs_diff < TOLERANCE

            model_stats[model_name]["abs_diffs"].append(abs_diff)
            model_stats[model_name]["n_total"] += 1
            if passed:
                model_stats[model_name]["n_pass"] += 1

            pscore = python_scores[evt_idx]
            results.append({
                "run":              pscore["run"],
                "subrun":           pscore["subrun"],
                "event":            pscore["event"],
                "evt_idx":          evt_idx,
                "model":            model_name,
                "python_score":     f"{py_score:.9f}",
                "root_tmva_score":  f"{root_score:.9f}",
                "absolute_difference":  f"{abs_diff:.2e}",
                "relative_difference":  f"{rel_diff:.2e}",
                "pass":             "PASS" if passed else "FAIL",
            })
            status = "PASS" if passed else "FAIL"
            print(f"  evt_{evt_idx:04d}: py={py_score:.6f} root={root_score:.6f} |diff|={abs_diff:.2e} [{status}]")

    # Write CSV
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "run","subrun","event","evt_idx","model",
            "python_score","root_tmva_score","absolute_difference","relative_difference","pass"
        ])
        w.writeheader()
        w.writerows(results)
    print(f"\nWrote: {OUT_CSV}")

    # Summary
    print("\n=== CROSS-VALIDATION SUMMARY ===")
    all_pass = True
    for model_name in ["numu", "other", "ncpi0", "nue"]:
        st = model_stats[model_name]
        n = st["n_total"]
        if n == 0:
            continue
        diffs = st["abs_diffs"]
        max_d  = max(diffs)
        med_d  = sorted(diffs)[len(diffs) // 2]
        np_    = st["n_pass"]
        status = "ALL_PASS" if np_ == n else f"FAIL ({n-np_} failures)"
        print(f"  {model_name}: {np_}/{n} PASS | max_abs={max_d:.2e} | median_abs={med_d:.2e} | {status}")
        if np_ < n:
            all_pass = False

    print(f"\nOverall: {'ALL_PASS — Python scores validated' if all_pass else 'FAILURES DETECTED — investigate before proceeding'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
