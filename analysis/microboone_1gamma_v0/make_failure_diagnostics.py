#!/usr/bin/env python3
"""
make_failure_diagnostics.py — Diagnostic categorization of the 24 shw_sp_filled=0 events.

Uses only frozen baseline_v0 outputs (tracking-pr.root T_tagger, T_kine, T_cluster).
Does NOT use truth information or rerun any reconstruction.

Output: tables/main_vertex_shower_failure_diagnostics.csv

Evidence-based category assignment:
  COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED:
    Type A — dominant EM particle in T_kine has kine_energy_included=3 (companion cluster),
              energy > 50 MeV.
    Type B — kine_pio_energy_1 >> max T_kine EM particle energy, AND kine_pio_flag=1
              (pi0 reco found photon in companion cluster not captured in kine_particle list).
              Calibrated against evt_0000 (confirmed companion cluster; Type B pattern).
  SHOWER_RECONSTRUCTED_ELSEWHERE_UNASSOCIATED:
    Dominant EM particle in T_kine has kine_energy_included=1 (main cluster), energy > 50 MeV,
    but shw_sp_filled=0 (singlephoton_tagger vertex-shower map did not associate the shower).
  SEVERE_IMAGING_UNDERRECO:
    Max reconstructed EM energy across all T_kine particles < 50 MeV AND no companion
    cluster evidence (does not meet threshold for other categories).
  INSUFFICIENT_OUTPUT_TO_DIAGNOSE:
    Contradictory or uninterpretable evidence not resolvable from frozen output alone.
"""

import uproot
import numpy as np
import csv
import os

BASEDIR = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/"
           "ncdelta_50evt/wirecell")
OUTDIR  = os.path.join(os.path.dirname(__file__), "tables")

FAIL_EVTS = [0, 2, 6, 9, 10, 12, 13, 14, 16, 20, 21, 26, 27, 30, 31, 32, 37, 42, 44, 50, 54, 55, 56, 58]

# Threshold for calling a shower "significant" (MeV)
SIGNIFICANT_SHOWER_MeV = 50.0
# Threshold for kine_pio >> T_kine max_em ratio (Type B companion cluster evidence)
PIO_RATIO_MIN = 5.0  # kine_pio_energy_1 must be >= 5× max T_kine EM particle energy

def read_event_diagnostics(evt_idx):
    path = f"{BASEDIR}/evt_{evt_idx:04d}/tracking-pr.root"
    result = {
        "evt_idx": evt_idx,
        "run": "", "subrun": "", "event": "",
        "shw_sp_filled": 0,
        "has_neutrino_candidate": 1,
        "n_companion_clusters": 0,
        "main_cluster_id": -1,
        "n_act_clusters": 0,
        # T_kine EM shower info
        "max_em_energy_mev": float("nan"),
        "max_em_included": -1,
        "max_em_energy_info": -1,
        "max_em_companion_energy_mev": float("nan"),
        "max_em_main_energy_mev": float("nan"),
        # kine_pio
        "kine_pio_flag": -1,
        "kine_pio_energy_1_mev": float("nan"),
        "kine_pio_vtx_dis_cm": float("nan"),
        # T_cluster info
        "n_clusters_total": 0,
        # Diagnostic
        "evidence_type": "",
        "category": "",
        "confidence": "",
        "evidence_note": "",
    }

    with uproot.open(path) as f:
        keys = [k.split(";")[0] for k in f.keys()]

        # T_tagger
        if "T_tagger" in keys:
            t = f["T_tagger"]
            def gf(b):
                return float(t[b].array(library="np")[0]) if b in t.keys() else float("nan")

            result["shw_sp_filled"] = int(gf("shw_sp_filled"))
            result["main_cluster_id"] = int(gf("cluster_id"))

            # act_cluster_id is jagged
            if "act_cluster_id" in t.keys():
                act_arr = t["act_cluster_id"].array(library="np")[0]
                if isinstance(act_arr, np.ndarray):
                    result["n_act_clusters"] = len(act_arr)
                    main_cl = result["main_cluster_id"]
                    result["n_companion_clusters"] = len(act_arr) - (1 if main_cl in act_arr else 0)

        # Trun for RSE
        if "Trun" in keys:
            tr = f["Trun"]
            for rkey in ["run_no", "run", "runNo"]:
                if rkey in tr.keys():
                    result["run"] = int(tr[rkey].array(library="np")[0]); break
            for skey in ["subrun_no", "subrun", "subrunNo"]:
                if skey in tr.keys():
                    result["subrun"] = int(tr[skey].array(library="np")[0]); break
            for ekey in ["event_no", "event", "eventNo"]:
                if ekey in tr.keys():
                    result["event"] = int(tr[ekey].array(library="np")[0]); break

        # T_kine
        if "T_kine" in keys:
            tk = f["T_kine"]
            ptypes  = tk["kine_particle_type"].array(library="np")[0]
            penergy = tk["kine_energy_particle"].array(library="np")[0]
            pinfo   = tk["kine_energy_info"].array(library="np")[0]
            pincl   = tk["kine_energy_included"].array(library="np")[0]

            result["kine_pio_flag"]        = int(tk["kine_pio_flag"].array(library="np")[0])
            result["kine_pio_energy_1_mev"]= float(tk["kine_pio_energy_1"].array(library="np")[0])
            result["kine_pio_vtx_dis_cm"]  = float(tk["kine_pio_vtx_dis"].array(library="np")[0])

            # Collect EM particles (PDG 11)
            em = [(float(pe), int(pi), int(pk))
                  for pt, pe, pi, pk in zip(ptypes, penergy, pinfo, pincl)
                  if int(pt) == 11]

            if em:
                # Sort by energy descending
                em.sort(reverse=True)
                result["max_em_energy_mev"]   = em[0][0]
                result["max_em_energy_info"]  = em[0][1]
                result["max_em_included"]     = em[0][2]

                companion_em = [e for e, i, k in em if k == 3]
                main_em      = [e for e, i, k in em if k == 1]
                result["max_em_companion_energy_mev"] = max(companion_em) if companion_em else 0.0
                result["max_em_main_energy_mev"]      = max(main_em)      if main_em      else 0.0

        # T_cluster
        if "T_cluster" in keys:
            tc = f["T_cluster"]
            result["n_clusters_total"] = len(tc["cluster_id"].array(library="np"))

    return result


def assign_category(r):
    """Assign evidence-based diagnostic category."""
    max_em    = r["max_em_energy_mev"] if not np.isnan(r["max_em_energy_mev"]) else 0.0
    max_comp  = r["max_em_companion_energy_mev"] if not np.isnan(r["max_em_companion_energy_mev"]) else 0.0
    max_main  = r["max_em_main_energy_mev"] if not np.isnan(r["max_em_main_energy_mev"]) else 0.0
    pio_e1    = r["kine_pio_energy_1_mev"] if not np.isnan(r["kine_pio_energy_1_mev"]) else 0.0
    pio_flag  = r["kine_pio_flag"]
    evt       = r["evt_idx"]

    # Type A: dominant EM > 50 MeV in companion cluster
    if max_comp >= SIGNIFICANT_SHOWER_MeV:
        return (
            "A: max_comp_em={:.0f}MeV(incl=3)".format(max_comp),
            "COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED",
            "HIGH",
            "T_kine dominant EM in companion cluster (kine_energy_included=3); "
            "singlephoton_tagger only accesses map_vertex_to_shower[main_vertex]"
        )

    # Type B: kine_pio found photon >> T_kine max EM (companion cluster accessible to pi0 reco but not T_kine list)
    # Calibrated against evt_0000 (confirmed companion cluster, same pattern)
    if (pio_flag == 1 and pio_e1 >= SIGNIFICANT_SHOWER_MeV and max_em > 0
            and pio_e1 / max_em >= PIO_RATIO_MIN):
        return (
            "B: pio_e1={:.0f}MeV >> max_em={:.0f}MeV (ratio={:.1f})".format(
                pio_e1, max_em, pio_e1 / max_em if max_em > 0 else float("inf")),
            "COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED",
            "MEDIUM",
            "kine_pio found {:.0f}MeV photon but T_kine max EM is {:.0f}MeV; "
            "pattern matches evt_0000 (confirmed companion cluster); "
            "pi0 reco likely accessed companion cluster shower".format(pio_e1, max_em)
        )

    # SHOWER_RECONSTRUCTED_ELSEWHERE_UNASSOCIATED:
    # Significant EM in main cluster (included=1) but shw_sp_filled=0
    # "elsewhere" = vertex-shower association pathway of singlephoton_tagger vs NeutrinoKinematics
    if max_main >= SIGNIFICANT_SHOWER_MeV:
        return (
            "main_em={:.0f}MeV(incl=1),shw_sp_filled=0".format(max_main),
            "SHOWER_RECONSTRUCTED_ELSEWHERE_UNASSOCIATED",
            "HIGH",
            "T_kine found {:.0f}MeV EM at main vertex (kine_energy_included=1); "
            "singlephoton_tagger map_vertex_to_shower[main_vertex] did not associate it; "
            "vertex-shower association mismatch between NeutrinoKinematics and singlephoton_tagger".format(max_main)
        )

    # SEVERE_IMAGING_UNDERRECO: some EM found but all small
    return (
        "max_em={:.0f}MeV,pio_e1={:.0f}MeV,pio_flag={}".format(max_em, pio_e1, pio_flag),
        "SEVERE_IMAGING_UNDERRECO",
        "MEDIUM",
        "No significant EM shower found anywhere (max T_kine EM={:.0f}MeV, pio_e1={:.0f}MeV); "
        "photon shower either not reconstructed or severely fragmented below thresholds".format(max_em, pio_e1)
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
print("Reading diagnostics for 24 shw_sp_filled=0 events...")
rows = []
for ei in FAIL_EVTS:
    r = read_event_diagnostics(ei)
    evidence_type, category, confidence, note = assign_category(r)
    r["evidence_type"] = evidence_type
    r["category"]      = category
    r["confidence"]    = confidence
    r["evidence_note"] = note
    rows.append(r)
    print(f"  evt_{ei:04d}: {category} ({confidence})")

# Summary
from collections import Counter
cats = Counter(r["category"] for r in rows)
print("\n=== DIAGNOSTIC SUMMARY ===")
for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {n}")

# Write CSV
out_path = f"{OUTDIR}/main_vertex_shower_failure_diagnostics.csv"
COLS = [
    "evt_idx", "run", "subrun", "event",
    "has_neutrino_candidate", "shw_sp_filled",
    "main_cluster_id", "n_act_clusters", "n_companion_clusters", "n_clusters_total",
    "max_em_energy_mev", "max_em_included", "max_em_energy_info",
    "max_em_companion_energy_mev", "max_em_main_energy_mev",
    "kine_pio_flag", "kine_pio_energy_1_mev", "kine_pio_vtx_dis_cm",
    "evidence_type", "category", "confidence", "evidence_note",
]
with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
print(f"\nWrote: {out_path}")
