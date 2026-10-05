#!/usr/bin/env python3
"""
baseline_v0 Phase E: Measure baseline selection response.

Reads ncdelta_50evt/tables/ncdelta_wirecell_baseline.csv
Produces:  ncdelta_50evt/tables/ncdelta_phase_e_summary.csv
           (printed summary to stdout)

Conditional quantities reported:
  1. Fraction producing any WireCell neutrino candidate
  2. Fraction producing T_tagger
  3. Fraction with identifiable reconstructed EM activity
  4. Fraction with photon_flag=1 (legacy MicroBooNE photon-tagger response)
  5. Fraction with shw_sp_filled=1
  6. Fraction with valid nue BDT (nue_score != -15)
  7. Fraction with kine_pio_flag=1 (reconstructed 2-shower pi0 hypothesis)
  8. Fraction where leading photon shower is in companion clusters
  9. Fraction where photon is severely fragmented
 10. Fraction lost primarily to geometric containment

Quantities are studied versus:
  - true photon energy (coarse bins)
  - photon conversion gap
  - active deposited energy
  - boundary distance
  - proton multiplicity

IMPORTANT TERMINOLOGY:
  - photon_flag=1 is the "legacy photon-tagger response" or "MicroBooNE-port photon_flag response"
    NOT the SBND single-photon efficiency
  - nue_score=-15 is a sentinel (br_filled=0), NOT a physical BDT score
  - kine_pio_flag is a reconstructed 2-shower hypothesis, NOT pi0 truth
"""

import csv
import os
import sys
from collections import defaultdict

BASEDIR = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt"
TABLE_IN = f"{BASEDIR}/tables/ncdelta_wirecell_baseline.csv"
TABLE_OUT = f"{BASEDIR}/tables/ncdelta_phase_e_summary.csv"


def safe_float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def safe_int(v, default=None):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def frac(n, d, label=""):
    if d == 0:
        return f"0/0 (N/A)"
    pct = 100.0 * n / d
    return f"{n}/{d} ({pct:.1f}%)"


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    if not os.path.exists(TABLE_IN):
        print(f"FATAL: baseline table not found: {TABLE_IN}", file=sys.stderr)
        print("Run build_baseline_table.py first.", file=sys.stderr)
        sys.exit(1)

    rows = []
    with open(TABLE_IN) as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("evt_idx", "").startswith("#"):
                continue
            rows.append(r)

    N = len(rows)
    if N == 0:
        print("No rows in baseline table.", file=sys.stderr)
        sys.exit(1)

    print(f"\nbaseline_v0 Phase E — NC Delta Radiative selection response")
    print(f"Total events: {N}")
    print(f"Baseline: WCT 251ff143, larwirecell 9295e2a3, sbndcode v10_14_02_04")
    print(f"Source: {TABLE_IN}")

    # ---- Conditional fraction counters ----
    n_has_candidate = sum(1 for r in rows if safe_int(r.get("nu_candidate_count"), 0) > 0)
    n_has_tagger = sum(1 for r in rows if str(r.get("T_tagger_exists")) == "1")
    n_has_em = sum(1 for r in rows if safe_int(r.get("sp_count"), 0) > 20)  # >20 SP as proxy for EM
    n_photon_flag = sum(1 for r in rows if str(r.get("photon_flag")) == "1")
    n_shw_filled = sum(1 for r in rows if str(r.get("shw_sp_filled")) == "1")
    n_valid_nue = sum(1 for r in rows
                      if safe_float(r.get("nue_score")) is not None
                      and safe_float(r.get("nue_score"), -15.0) != -15.0)
    n_pio_flag = sum(1 for r in rows if str(r.get("kine_pio_flag")) == "1")
    n_companion = sum(1 for r in rows if r.get("photon_shower_location") == "companion")
    n_fragmented = sum(1 for r in rows if r.get("photon_shower_location") == "fragmented")
    n_geom_loss = sum(1 for r in rows if r.get("containment_class") in ["outside_av", "boundary_corner"])

    print_section("Conditional stage fractions (Phases E.1–E.10)")
    print(f" 1. Any WireCell neutrino candidate:           {frac(n_has_candidate, N)}")
    print(f" 2. T_tagger present:                          {frac(n_has_tagger, N)}")
    print(f" 3. Identifiable EM activity (SP>20):          {frac(n_has_em, N)}")
    print(f" 4. photon_flag=1 (legacy tagger response):    {frac(n_photon_flag, N)}")
    print(f" 5. shw_sp_filled=1:                           {frac(n_shw_filled, N)}")
    print(f" 6. Valid nue BDT (nue_score != -15 sentinel): {frac(n_valid_nue, N)}")
    print(f" 7. kine_pio_flag=1 (reco 2-shower hypothesis):{frac(n_pio_flag, N)}")
    print(f" 8. Leading photon shower in companion cluster: {frac(n_companion, N)}")
    print(f" 9. Photon shower severely fragmented:         {frac(n_fragmented, N)}")
    print(f"10. Lost to geometric containment:             {frac(n_geom_loss, N)}")

    # ---- Breakdown by containment class ----
    print_section("Breakdown by containment class")
    by_class = defaultdict(list)
    for r in rows:
        cc = r.get("containment_class") or "unknown"
        by_class[cc].append(r)
    for cc, grp in sorted(by_class.items()):
        n_pf = sum(1 for r in grp if str(r.get("photon_flag")) == "1")
        n_cand = sum(1 for r in grp if safe_int(r.get("nu_candidate_count"), 0) > 0)
        print(f"  {cc:25s}: N={len(grp):3d}  candidate={frac(n_cand, len(grp))}  photon_flag={frac(n_pf, len(grp))}")

    # ---- Coarse energy bins ----
    print_section("photon_flag response vs true photon energy (coarse bins)")
    bins = [(0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.8), (0.8, 99.)]
    labels = ["<100 MeV", "100-300 MeV", "300-500 MeV", "500-800 MeV", ">800 MeV"]
    for (lo, hi), label in zip(bins, labels):
        grp = [r for r in rows if lo <= (safe_float(r.get("true_E_gamma_GeV"), -1) or -1) < hi]
        if not grp:
            continue
        n_pf = sum(1 for r in grp if str(r.get("photon_flag")) == "1")
        n_cand = sum(1 for r in grp if safe_int(r.get("nu_candidate_count"), 0) > 0)
        print(f"  E_gamma {label:12s}: N={len(grp):3d}  candidate={frac(n_cand, len(grp))}  photon_flag={frac(n_pf, len(grp))}")

    # ---- Conversion gap bins ----
    print_section("photon_flag response vs conversion gap (coarse bins)")
    gap_bins = [(0, 5), (5, 15), (15, 30), (30, 99.)]
    gap_labels = ["<5 cm", "5-15 cm", "15-30 cm", ">30 cm"]
    for (lo, hi), label in zip(gap_bins, gap_labels):
        grp = [r for r in rows if lo <= (safe_float(r.get("photon_gap_cm"), -1) or -1) < hi]
        if not grp:
            continue
        n_pf = sum(1 for r in grp if str(r.get("photon_flag")) == "1")
        n_cand = sum(1 for r in grp if safe_int(r.get("nu_candidate_count"), 0) > 0)
        print(f"  gap {label:10s}: N={len(grp):3d}  candidate={frac(n_cand, len(grp))}  photon_flag={frac(n_pf, len(grp))}")

    print_section("Terminology reminder (immutable for baseline_v0)")
    print("  photon_flag=1  = legacy MicroBooNE photon-tagger response")
    print("                   NOT the SBND single-photon efficiency")
    print("  nue_score=-15  = br_filled=0 sentinel, NOT a physical BDT score")
    print("  kine_pio_flag  = reconstructed 2-shower pi0 hypothesis, NOT pi0 truth")
    print("  cosmic_flag=1 + cosmic_filled=0  = default unfilled, NOT cosmic rejection")

    # ---- Write summary CSV ----
    summary_rows = []
    metrics = [
        ("any_wct_candidate", n_has_candidate, N),
        ("T_tagger_present", n_has_tagger, N),
        ("identifiable_em_sp20", n_has_em, N),
        ("photon_flag_1_legacy_tagger", n_photon_flag, N),
        ("shw_sp_filled_1", n_shw_filled, N),
        ("valid_nue_bdt_not_sentinel", n_valid_nue, N),
        ("kine_pio_flag_1_reco_hypothesis", n_pio_flag, N),
        ("photon_in_companion_cluster", n_companion, N),
        ("photon_severely_fragmented", n_fragmented, N),
        ("lost_to_geometric_containment", n_geom_loss, N),
    ]
    for label, num, den in metrics:
        summary_rows.append({
            "metric": label,
            "numerator": num,
            "denominator": den,
            "fraction": round(num / den, 4) if den > 0 else None,
            "percent": round(100.0 * num / den, 1) if den > 0 else None,
        })

    os.makedirs(os.path.dirname(TABLE_OUT), exist_ok=True)
    with open(TABLE_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "numerator", "denominator", "fraction", "percent"])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\nSummary CSV written: {TABLE_OUT}")


if __name__ == "__main__":
    main()
