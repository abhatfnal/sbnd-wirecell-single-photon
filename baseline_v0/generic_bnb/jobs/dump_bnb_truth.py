#!/usr/bin/env python3
"""
dump_bnb_truth.py
Run inside sbndcode v10_14_02_04 container.
Reads simb::MCTruth and simb::GTruth from reco1_out.root using ROOT with LArSoft dicts.
Outputs: bnb_truth_categories.csv

Usage: python3 dump_bnb_truth.py <input.root> <output.csv>
"""
import sys
import csv
import ROOT

ROOT.gROOT.SetBatch(True)

INFILE = sys.argv[1]
OUTCSV = sys.argv[2]

# In sbndcode container, dictionaries are loaded via setup
# Load explicitly in case not auto-loaded
for lib in ["libnusimdata_SimulationBase.so", "libsimulationbase.so"]:
    ROOT.gSystem.Load(lib)

f = ROOT.TFile.Open(INFILE)
if not f or f.IsZombie():
    print(f"ERROR: cannot open {INFILE}")
    sys.exit(1)

t = f.Get("Events")
if not t:
    print("ERROR: no Events tree")
    sys.exit(1)

n_events = t.GetEntries()
print(f"Events: {n_events}")

# Disable all branches first, then enable only what we need
t.SetBranchStatus("*", 0)
t.SetBranchStatus("EventAuxiliary*", 1)
t.SetBranchStatus("simb::MCTruths_generator__GenieGen*", 1)
t.SetBranchStatus("simb::GTruths_generator__GenieGen*", 1)

rows = []

for i in range(n_events):
    t.GetEntry(i)

    # Get EventAuxiliary for RSE - access via leaf
    run_leaf = t.GetLeaf("EventAuxiliary.id_.subRun_.run_.run_")
    subrun_leaf = t.GetLeaf("EventAuxiliary.id_.subRun_.subRun_")
    event_leaf = t.GetLeaf("EventAuxiliary.id_.event_")

    run = int(run_leaf.GetValue()) if run_leaf else -1
    subrun = int(subrun_leaf.GetValue()) if subrun_leaf else -1
    event = int(event_leaf.GetValue()) if event_leaf else -1

    # Try to get MCTruth
    mctruths = None
    try:
        mctruths = getattr(t, "simb::MCTruths_generator__GenieGen.obj")
    except Exception:
        pass

    if mctruths is None or len(mctruths) == 0:
        rows.append({
            "run": run, "subrun": subrun, "event": event,
            "nu_pdg": -999, "ccnc": -999, "mode": -999,
            "interaction_type": -999, "nu_energy_gev": -999,
            "category": "NO_MCTRUTH", "corsika_only": 0,
        })
        continue

    truth = mctruths[0]
    nu = truth.GetNeutrino()
    nu_pdg = nu.Nu().PdgCode()
    ccnc = nu.CCNC()  # 0=CC, 1=NC
    mode = nu.Mode()  # genie scattering type: 1=QE,3=DIS,4=RES,5=COH,10=MEC
    itype = nu.InteractionType()  # NUANCE-style
    nu_E = nu.Nu().E()

    # Assign category
    if nu_pdg in (14, -14):
        flavor = "numu"
    elif nu_pdg in (12, -12):
        flavor = "nue"
    elif nu_pdg in (16, -16):
        flavor = "nutau"
    else:
        flavor = f"pdg{nu_pdg}"

    if ccnc == 0:
        cat = f"{flavor}_CC"
    else:
        # NC -- try to distinguish pi0 from final-state particles
        # This requires looking at final state; start with generic NC
        cat = f"{flavor}_NC"

    rows.append({
        "run": run, "subrun": subrun, "event": event,
        "nu_pdg": nu_pdg, "ccnc": ccnc, "mode": mode,
        "interaction_type": itype, "nu_energy_gev": round(nu_E, 4),
        "category": cat, "corsika_only": 0,
    })

# Write CSV
fieldnames = ["run", "subrun", "event", "nu_pdg", "ccnc", "mode",
              "interaction_type", "nu_energy_gev", "category", "corsika_only"]
with open(OUTCSV, "w", newline="") as out:
    w = csv.DictWriter(out, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"Written {len(rows)} rows to {OUTCSV}")

# Summary
from collections import Counter
cats = Counter(r["category"] for r in rows)
print("Category counts:")
for cat, n in sorted(cats.items()):
    print(f"  {cat}: {n}")
