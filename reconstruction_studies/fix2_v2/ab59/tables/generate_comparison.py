#!/usr/bin/env python3
"""
generate_comparison.py — Parts F, G, J of the 59-event Fix2-v2 A/B study.

For each of 59 NC Delta events, reads baseline and Fix2-v2 patched tracking-pr.root,
extracts the key tagger branches, reads fix2_v2/fix2_diag log lines, and
classifies each event.

Outputs:
    fix2_ab59_event_comparison.csv   (Part F)
    fix2_ab59_summary.txt            (Part G)
"""

import uproot, re, os, csv, glob, sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon"
BASEDIR  = f"{BASE}/baseline_v0/ncdelta_50evt/wirecell"
PATCHDIR = f"{BASE}/development/fix2_vertex_shower_onehop_20261005/ab59/wirecell"
LOGDIR   = f"{BASE}/development/fix2_vertex_shower_onehop_20261005/ab59/logs"
OUTDIR   = os.path.dirname(__file__)

N_EVENTS = 59

# Known expected behaviour for Part J
EXPECTED = {
    14: {"fix2_activates": True,  "shw_filled_change": (0,1), "energy_mev": 121.6},
    20: {"fix2_activates": True,  "shw_filled_change": (0,1), "energy_mev": 153.8},
    58: {"fix2_activates": False, "shw_filled_change": (0,0)},   # different-cluster, no recovery
     5: {"fix2_activates": False, "shw_filled_change": (1,1)},   # control
     1: {"fix2_activates": False, "shw_filled_change": (1,1)},   # control
    15: {"fix2_activates": False, "shw_filled_change": (1,1)},   # control
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def read_tagger(root_path):
    """Return dict of tagger values, or None if T_tagger absent/empty."""
    if not os.path.isfile(root_path):
        return None
    try:
        f = uproot.open(root_path)
        if "T_tagger" not in f:
            return None
        t = f["T_tagger"]
        if t.num_entries == 0:
            return None
        arr = t.arrays(library="np")
        def g(k, default=0.0):
            v = arr.get(k)
            return float(v[0]) if v is not None and len(v) > 0 else default
        return {
            "has_tagger": 1,
            "run":    int(g("run_no",    -1)),
            "subrun": int(g("subrun_no", -1)),
            "event":  int(g("event_no",  -1)),
            "shw_sp_filled":          g("shw_sp_filled"),
            "shw_sp_n_20mev_showers": g("shw_sp_n_20mev_showers"),
            "shw_sp_n_20br1_showers": g("shw_sp_n_20br1_showers"),
            "shw_sp_energy":          g("shw_sp_energy"),
            "photon_flag":            g("photon_flag"),
            "br_filled":              g("br_filled"),
        }
    except Exception as e:
        print(f"  WARNING: uproot error {root_path}: {e}", file=sys.stderr)
        return None

def read_fix2_log(evt_idx):
    """Return dict from fix2_v2 and fix2_diag log lines in the lar log."""
    tag = f"evt_{evt_idx:04d}"
    logf = os.path.join(LOGDIR, f"lar_ab59_{tag}.log")
    result = {
        "fallback_activated": 0,
        "direct_has_usable":  -1,   # -1 = not found in log
        "n_direct_showers":   -1,
        "n_neighbor_showers_added": 0,
        "bfs_hops":          "",
        "diag_vtx_type":     "",
        "diag_same_cl":      "",
        "diag_shw_energy":   "",
    }
    if not os.path.isfile(logf):
        return result
    with open(logf, errors="replace") as fh:
        for line in fh:
            # fix2_v2: main_vtx_deg=N map_size=M all_showers=K n_direct=D
            m = re.search(r"fix2_v2: main_vtx_deg=\d+ map_size=\d+ all_showers=\d+ n_direct=(\d+)", line)
            if m:
                result["n_direct_showers"] = int(m.group(1))

            # fix2_v2: direct_has_usable=true/false
            m = re.search(r"fix2_v2: direct_has_usable=(\w+)", line)
            if m:
                result["direct_has_usable"] = 1 if m.group(1) == "true" else 0

            # fix2_v2: fallback n_edges=N n_neighbor_new=M total_candidates=K
            m = re.search(r"fix2_v2: fallback n_edges=\d+ n_neighbor_new=(\d+)", line)
            if m:
                result["fallback_activated"] = 1
                result["n_neighbor_showers_added"] = int(m.group(1))

            # fix2_diag: MAXE_SHW E=NMeV pdg=P vtx_type=V ... same_cl=B
            m = re.search(r"fix2_diag: MAXE_SHW E=([\d.]+)MeV.*vtx_type=(\d+).*same_cl=(\w+)", line)
            if m:
                result["diag_shw_energy"] = m.group(1)
                result["diag_vtx_type"]   = m.group(2)
                result["diag_same_cl"]    = m.group(3)

            # fix2_diag: BFS_FOUND hops=N or BFS_NO_PATH
            m = re.search(r"fix2_diag: BFS_FOUND hops=(\d+)", line)
            if m:
                result["bfs_hops"] = m.group(1)
            if re.search(r"fix2_diag: BFS_NO_PATH", line):
                result["bfs_hops"] = "NO_PATH"
    return result

def classify_event(bsl, pat, log):
    """Assign one of the Part F event classes."""
    if bsl is None and pat is None:
        return "NO_NEUTRINO_CANDIDATE"
    if bsl is None or pat is None:
        return "OTHER"   # one missing

    b_filled = bsl.get("shw_sp_filled", 0)
    p_filled = pat.get("shw_sp_filled", 0)
    fb = log.get("fallback_activated", 0)
    du = log.get("direct_has_usable", -1)

    if not fb:
        if b_filled == p_filled:
            return "UNCHANGED_DIRECT_SUCCESS"
        else:
            return "UNEXPECTED_CHANGE_WITHOUT_FALLBACK"
    else:
        if p_filled == 1 and b_filled == 0:
            return "RECOVERED_BY_FIX2"
        elif p_filled == 0 and b_filled == 0:
            return "FALLBACK_ACTIVATED_NO_RECOVERY"
        elif b_filled == 1 and p_filled == 1:
            b_e = bsl.get("shw_sp_energy", 0)
            p_e = pat.get("shw_sp_energy", 0)
            if abs(b_e - p_e) > 1.0:
                return "FALLBACK_ACTIVATED_DIFFERENT_SHOWER"
            else:
                return "UNEXPECTED_CHANGE_WITHOUT_FALLBACK"
        else:
            return "OTHER"

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
rows = []
missing_patched = []

for idx in range(N_EVENTS):
    tag = f"evt_{idx:04d}"
    b_root = os.path.join(BASEDIR,  tag, "tracking-pr.root")
    p_root = os.path.join(PATCHDIR, tag, "tracking-pr.root")

    bsl = read_tagger(b_root)
    pat = read_tagger(p_root)
    log = read_fix2_log(idx)

    if pat is None:
        missing_patched.append(idx)

    cls = classify_event(bsl, pat, log)

    # expected_change_class
    exp = EXPECTED.get(idx, {})
    exp_cls = ""
    if exp:
        if exp.get("fix2_activates"):
            exp_cls = "SHOULD_RECOVER"
        elif "shw_filled_change" in exp:
            b_exp, p_exp = exp["shw_filled_change"]
            if b_exp == p_exp:
                exp_cls = "SHOULD_BE_UNCHANGED"
        if idx == 58:
            exp_cls = "SHOULD_REMAIN_UNRECOVERED"

    def bv(d, k, default="NA"):
        if d is None: return default
        v = d.get(k, default)
        return f"{v:.3f}" if isinstance(v, float) else str(v)

    selected_shower_changed = ""
    if bsl and pat and bsl["has_tagger"] and pat["has_tagger"]:
        b_e = bsl.get("shw_sp_energy", 0)
        p_e = pat.get("shw_sp_energy", 0)
        selected_shower_changed = "1" if abs(b_e - p_e) > 1.0 else "0"

    row = {
        "evt_idx":      idx,
        "run":          bv(bsl, "run"),
        "subrun":       bv(bsl, "subrun"),
        "event":        bv(bsl, "event"),
        "baseline_has_tagger":            bv(bsl, "has_tagger", "0"),
        "patched_has_tagger":             bv(pat, "has_tagger", "0"),
        "baseline_shw_sp_filled":         bv(bsl, "shw_sp_filled"),
        "patched_shw_sp_filled":          bv(pat, "shw_sp_filled"),
        "baseline_shw_sp_n_20mev_showers":bv(bsl, "shw_sp_n_20mev_showers"),
        "patched_shw_sp_n_20mev_showers": bv(pat, "shw_sp_n_20mev_showers"),
        "baseline_shw_sp_n_20br1_showers":bv(bsl, "shw_sp_n_20br1_showers"),
        "patched_shw_sp_n_20br1_showers": bv(pat, "shw_sp_n_20br1_showers"),
        "baseline_shw_sp_energy":         bv(bsl, "shw_sp_energy"),
        "patched_shw_sp_energy":          bv(pat, "shw_sp_energy"),
        "baseline_photon_flag":            bv(bsl, "photon_flag"),
        "patched_photon_flag":             bv(pat, "photon_flag"),
        "baseline_br_filled":              bv(bsl, "br_filled"),
        "patched_br_filled":               bv(pat, "br_filled"),
        "fallback_activated":              str(log["fallback_activated"]),
        "n_direct_showers":                str(log["n_direct_showers"]),
        "direct_has_usable":               str(log["direct_has_usable"]),
        "n_neighbor_showers_added":        str(log["n_neighbor_showers_added"]),
        "selected_shower_changed":         selected_shower_changed,
        "bfs_hops":                        log["bfs_hops"],
        "diag_vtx_type":                   log["diag_vtx_type"],
        "diag_same_cl":                    log["diag_same_cl"],
        "diag_shw_energy_mev":             log["diag_shw_energy"],
        "event_class":                     cls,
        "expected_change_class":           exp_cls,
        "notes": "",
    }

    # Add notes for known events
    if idx == 14:
        row["notes"] = "signal evt: 1-hop track, same cluster, vtx_type=1"
    elif idx == 20:
        row["notes"] = "signal evt: 1-hop track, diff cluster graph-connected, vtx_type=2"
    elif idx == 58:
        row["notes"] = "companion-cluster: BFS_NO_PATH, vtx_type=3, shw_cl=45 main_cl=2"
    elif idx == 54:
        row["notes"] = "11 candidates found, downstream tagger fail"
    elif idx in (1, 5, 15):
        row["notes"] = "known-good control: direct_has_usable=true expected"

    rows.append(row)

# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------
outfile = os.path.join(OUTDIR, "fix2_ab59_event_comparison.csv")
fieldnames = list(rows[0].keys())
with open(outfile, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
print(f"Written: {outfile}")

# ---------------------------------------------------------------------------
# Part G summary
# ---------------------------------------------------------------------------
n_total = len(rows)
n_no_nu  = sum(1 for r in rows if r["event_class"] == "NO_NEUTRINO_CANDIDATE")
n_recovered = sum(1 for r in rows if r["event_class"] == "RECOVERED_BY_FIX2")
n_fb_no_rec = sum(1 for r in rows if r["event_class"] == "FALLBACK_ACTIVATED_NO_RECOVERY")
n_fb_diff   = sum(1 for r in rows if r["event_class"] == "FALLBACK_ACTIVATED_DIFFERENT_SHOWER")
n_unchanged = sum(1 for r in rows if r["event_class"] == "UNCHANGED_DIRECT_SUCCESS")
n_unexp     = sum(1 for r in rows if r["event_class"] == "UNEXPECTED_CHANGE_WITHOUT_FALLBACK")
n_other     = sum(1 for r in rows if r["event_class"] == "OTHER")
n_fallback  = sum(1 for r in rows if r["fallback_activated"] == "1")

n_gain_filled = sum(1 for r in rows
                    if r["baseline_shw_sp_filled"] == "0.000"
                    and r["patched_shw_sp_filled"] == "1.000")
n_lose_filled = sum(1 for r in rows
                    if r["baseline_shw_sp_filled"] == "1.000"
                    and r["patched_shw_sp_filled"] == "0.000")
n_changed_shower = sum(1 for r in rows if r["selected_shower_changed"] == "1")
n_changed_n20  = sum(1 for r in rows
                     if r["baseline_shw_sp_n_20mev_showers"] != r["patched_shw_sp_n_20mev_showers"]
                     and r["baseline_shw_sp_n_20mev_showers"] not in ("NA","")
                     and r["patched_shw_sp_n_20mev_showers"] not in ("NA",""))
n_changed_n20br1 = sum(1 for r in rows
                       if r["baseline_shw_sp_n_20br1_showers"] != r["patched_shw_sp_n_20br1_showers"]
                       and r["baseline_shw_sp_n_20br1_showers"] not in ("NA","")
                       and r["patched_shw_sp_n_20br1_showers"] not in ("NA",""))
n_changed_pflag = sum(1 for r in rows
                      if r["baseline_photon_flag"] != r["patched_photon_flag"]
                      and r["baseline_photon_flag"] not in ("NA","")
                      and r["patched_photon_flag"] not in ("NA",""))

summary_lines = [
    "=== Fix2-v2 59-Event A/B Study — Part G Summary ===",
    f"Total events:                     {n_total}",
    f"Missing patched output:           {len(missing_patched)} {missing_patched}",
    "",
    "--- Fallback activation ---",
    f"1. Events where fallback activates: {n_fallback}/{n_total}",
    "",
    "--- shw_sp_filled changes ---",
    f"2. Events gaining shw_sp_filled=1:  {n_gain_filled}  (RECOVERED_BY_FIX2)",
    f"3. Events losing  shw_sp_filled=1:  {n_lose_filled}  (KEY SAFETY CRITERION)",
    "",
    "--- Already-working events ---",
    f"4. Events changing selected shower (when both filled=1): {n_changed_shower}",
    "",
    "--- Feature changes ---",
    f"5. Events changing shw_sp_n_20mev_showers: {n_changed_n20}",
    f"6. Events changing shw_sp_n_20br1_showers: {n_changed_n20br1}",
    f"7. Events changing photon_flag:             {n_changed_pflag}",
    "",
    "--- Safety criterion ---",
    f"8. Unexpected changes (direct_has_usable=true but result changed): {n_unexp}",
    f"   {'PASS' if n_unexp == 0 else 'FAIL — investigate before proceeding'}",
    "",
    "--- Event class counts ---",
    f"   UNCHANGED_DIRECT_SUCCESS:           {n_unchanged}",
    f"   RECOVERED_BY_FIX2:                  {n_recovered}",
    f"   FALLBACK_ACTIVATED_NO_RECOVERY:     {n_fb_no_rec}",
    f"   FALLBACK_ACTIVATED_DIFFERENT_SHOWER:{n_fb_diff}",
    f"   UNEXPECTED_CHANGE_WITHOUT_FALLBACK: {n_unexp}",
    f"   NO_NEUTRINO_CANDIDATE:              {n_no_nu}",
    f"   OTHER:                              {n_other}",
]

summary_path = os.path.join(OUTDIR, "fix2_ab59_summary.txt")
with open(summary_path, "w") as f:
    f.write("\n".join(summary_lines) + "\n")
print(f"Written: {summary_path}")

print("\n".join(summary_lines))
