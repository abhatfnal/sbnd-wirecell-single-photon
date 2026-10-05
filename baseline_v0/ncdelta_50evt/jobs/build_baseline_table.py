#!/usr/bin/env python3
"""
baseline_v0 Phase D: Build ncdelta_wirecell_baseline.csv

Reads per-event WireCell outputs (tracking-pr.root) from:
    ncdelta_50evt/wirecell/evt_NNNN/

and truth quantities from:
    ncdelta_50evt/tables/ncdelta_truth.csv

Produces:
    ncdelta_50evt/tables/ncdelta_wirecell_baseline.csv

Run after all WireCell array jobs complete.
Usage: python3 build_baseline_table.py [--wirecell-dir PATH] [--truth-csv PATH] [--out CSV]

Flag semantics (immutable for baseline_v0):
  cosmic_flag=1, cosmic_filled=0  →  default/unfilled, NOT cosmic rejection
  nue_score=-15                   →  br_filled=0 sentinel, NOT a physical BDT score
  kine_pio_flag                   →  reconstructed 2-shower pi0 hypothesis, NOT pi0 truth
  photon_flag                     →  legacy MicroBooNE photon-tagger response
"""

import argparse
import csv
import glob
import os
import sys

try:
    import uproot
    HAS_UPROOT = True
except ImportError:
    HAS_UPROOT = False
    print("WARNING: uproot not available. Will produce schema-only CSV.", file=sys.stderr)

BASEDIR = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt"

# Columns in the output CSV — see Phase D specification in the project plan
OUTPUT_COLUMNS = [
    # Truth
    "evt_idx", "run", "subrun", "event",
    "true_E_nu_GeV", "true_E_gamma_GeV", "delta_pdg",
    "photon_gap_cm", "vertex_to_boundary_cm", "conv_to_boundary_cm",
    "active_dep_energy_MeV", "containment_class",
    "n_protons", "n_pi0", "n_pipm",
    # Reconstruction existence
    "h5_exists", "sp_count", "edge_count",
    "topology_source", "T_bundle_exists", "T_tagger_exists", "T_kine_exists",
    "nu_candidate_count", "selected_candidate_count",
    # Candidate
    "nu_index", "sel_cluster_id",
    "reco_vx_cm", "reco_vy_cm", "reco_vz_cm",
    "flash_time_us", "flash_pe", "neutrino_type",
    # Inherited taggers (frozen — do not rename)
    "numu_score", "nue_score",
    "cosmic_flag", "cosmic_filled", "cosmict_flag",
    "photon_flag", "shw_sp_filled", "spt_flag",
    "sig_flag", "sig_1_score", "sig_2_score",
    "pio_flag", "pio_1_score", "pio_2_score",
    # Kinematics
    "kine_reco_Enu_MeV", "kine_reco_add_energy",
    "kine_pio_flag", "kine_pio_energy_1", "kine_pio_energy_2", "kine_pio_angle",
    # Shower/cluster structure
    "n_clusters", "n_main_clusters", "n_companions",
    "main_cluster_npoints", "main_cluster_length_cm",
    "n_electron_showers", "largest_shower_energy_MeV",
    "photon_shower_location",  # main | companion | fragmented | not_reconstructed | needs_review
]


def read_tracking_pr(trkpr_path):
    """Extract WireCell tagger branches from tracking-pr.root."""
    row = {col: "" for col in OUTPUT_COLUMNS}
    row["T_tagger_exists"] = 0
    row["T_kine_exists"] = 0
    row["T_bundle_exists"] = 0
    row["nu_candidate_count"] = 0
    row["selected_candidate_count"] = 0

    if not os.path.exists(trkpr_path):
        return row

    if not HAS_UPROOT:
        row["T_tagger_exists"] = "needs_uproot"
        return row

    try:
        with uproot.open(trkpr_path) as f:
            keys = [k.split(";")[0] for k in f.keys()]
            row["T_tagger_exists"] = int("T_tagger" in keys)
            row["T_kine_exists"] = int("T_kine" in keys)
            row["T_bundle_exists"] = int("T_bundle" in keys)

            if "T_tagger" in keys:
                t = f["T_tagger"]
                n = t.num_entries
                row["nu_candidate_count"] = n
                row["selected_candidate_count"] = n  # all candidates for now; selection logic TBD

                if n > 0:
                    # Read first (best) candidate — selection ordering follows tracking-pr convention
                    for branch in ["numu_score", "nue_score", "cosmic_flag", "cosmic_filled",
                                   "cosmict_flag", "photon_flag", "shw_sp_filled", "spt_flag",
                                   "sig_flag", "sig_1_score", "sig_2_score",
                                   "pio_flag", "pio_1_score", "pio_2_score",
                                   "nu_index", "sel_cluster_id", "neutrino_type",
                                   "flash_time", "flash_pe",
                                   "nu_x", "nu_y", "nu_z"]:
                        if branch in t.keys():
                            arr = t[branch].array(library="np")
                            if len(arr) > 0:
                                col_map = {
                                    "flash_time": "flash_time_us",
                                    "nu_x": "reco_vx_cm",
                                    "nu_y": "reco_vy_cm",
                                    "nu_z": "reco_vz_cm",
                                }
                                col = col_map.get(branch, branch)
                                row[col] = arr[0]

            if "T_kine" in keys:
                tk = f["T_kine"]
                if tk.num_entries > 0:
                    for branch in ["kine_reco_Enu", "kine_reco_add_energy",
                                   "kine_pio_flag", "kine_pio_energy_1",
                                   "kine_pio_energy_2", "kine_pio_angle"]:
                        if branch in tk.keys():
                            arr = tk[branch].array(library="np")
                            if len(arr) > 0:
                                col_map = {"kine_reco_Enu": "kine_reco_Enu_MeV"}
                                col = col_map.get(branch, branch)
                                row[col] = arr[0]

    except Exception as e:
        print(f"WARNING: uproot error on {trkpr_path}: {e}", file=sys.stderr)

    return row


def read_h5_sp_count(h5_path):
    """Return (exists, sp_count, edge_count, topology_source) from nugraph.h5."""
    if not os.path.exists(h5_path):
        return 0, 0, 0, ""
    sz = os.path.getsize(h5_path)
    if sz < 100:
        return 0, 0, 0, ""
    # Full h5 parsing would use h5py; return exists=1 and placeholder counts
    return 1, -1, -1, "nugraph.h5"


def main():
    parser = argparse.ArgumentParser(description="Build baseline_v0 NC Delta WireCell table")
    parser.add_argument("--wirecell-dir", default=f"{BASEDIR}/wirecell")
    parser.add_argument("--truth-csv", default=f"{BASEDIR}/tables/ncdelta_truth.csv")
    parser.add_argument("--out", default=f"{BASEDIR}/tables/ncdelta_wirecell_baseline.csv")
    args = parser.parse_args()

    if not os.path.isdir(args.wirecell_dir):
        print(f"FATAL: wirecell dir not found: {args.wirecell_dir}", file=sys.stderr)
        sys.exit(1)

    # Load truth CSV if available
    truth_by_idx = {}
    if os.path.exists(args.truth_csv):
        with open(args.truth_csv) as tf:
            reader = csv.DictReader(tf)
            for r in reader:
                if r.get("evt_idx", "").startswith("#"):
                    continue
                try:
                    idx = int(r["evt_idx"])
                    truth_by_idx[idx] = r
                except (KeyError, ValueError):
                    continue

    # Find per-event directories
    evt_dirs = sorted(glob.glob(os.path.join(args.wirecell_dir, "evt_*")))
    if not evt_dirs:
        print(f"No evt_* directories found in {args.wirecell_dir}", file=sys.stderr)
        print("Run WireCell array jobs first.", file=sys.stderr)
        sys.exit(1)

    rows = []
    for evt_dir in evt_dirs:
        basename = os.path.basename(evt_dir)
        try:
            evt_idx = int(basename.replace("evt_", ""))
        except ValueError:
            continue

        trkpr = os.path.join(evt_dir, "tracking-pr.root")
        h5 = os.path.join(evt_dir, "nugraph.h5")

        row = read_tracking_pr(trkpr)
        row["evt_idx"] = evt_idx

        h5_exists, sp_count, edge_count, topo_src = read_h5_sp_count(h5)
        row["h5_exists"] = h5_exists
        row["sp_count"] = sp_count
        row["edge_count"] = edge_count
        row["topology_source"] = topo_src

        # Merge truth columns
        if evt_idx in truth_by_idx:
            tr = truth_by_idx[evt_idx]
            for col in ["run", "subrun", "event",
                        "true_E_nu_GeV", "true_E_gamma_GeV", "delta_pdg",
                        "photon_gap_cm", "vertex_to_boundary_cm", "conv_to_boundary_cm",
                        "active_dep_energy_MeV", "containment_class",
                        "n_protons", "n_pi0", "n_pipm"]:
                if col in tr:
                    row[col] = tr[col]

        rows.append(row)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written: {args.out}  ({len(rows)} rows)")
    print(f"Events with T_tagger: {sum(1 for r in rows if str(r.get('T_tagger_exists','')) == '1')}")
    print(f"Events with h5:       {sum(1 for r in rows if str(r.get('h5_exists','')) == '1')}")
    print(f"Events photon_flag=1: {sum(1 for r in rows if str(r.get('photon_flag','')) == '1')}")
    nue_sentinel = sum(1 for r in rows if str(r.get('nue_score','')) == '-15.0' or str(r.get('nue_score','')) == '-15')
    print(f"Events nue_score=-15 (sentinel, NOT physical): {nue_sentinel}")


if __name__ == "__main__":
    main()
