#!/usr/bin/env python3
"""
extract_rse.py
Run inside sbndcode v10_14_02_04 container.
Reads art::EventAuxiliary from reco1_out.root using ROOT SetBranchAddress.
Outputs RSE list to stdout as CSV: entry_index,run,subrun,event
"""
import sys
import ROOT
ROOT.gROOT.SetBatch(True)

INFILE = sys.argv[1]

# The sbndcode env sources art libraries; art::EventAuxiliary should be available
f = ROOT.TFile.Open(INFILE)
if not f or f.IsZombie():
    print(f"ERROR: cannot open {INFILE}", file=sys.stderr)
    sys.exit(1)

t = f.Get("Events")
n = t.GetEntries()
print(f"# Events: {n}", file=sys.stderr)

# Approach 1: SetBranchAddress with art::EventAuxiliary C++ object
try:
    aux = ROOT.art.EventAuxiliary()
    t.SetBranchAddress("EventAuxiliary", ROOT.AddressOf(aux))
    print("entry_index,run,subrun,event")
    for i in range(n):
        t.GetEntry(i)
        r = aux.run()
        sr = aux.subRun()
        ev = aux.event()
        print(f"{i},{r},{sr},{ev}")
    sys.exit(0)
except Exception as e:
    print(f"Approach 1 failed: {e}", file=sys.stderr)

# Approach 2: access branch directly
try:
    t.GetEntry(0)
    # Try attribute access after GetEntry
    aux_obj = getattr(t, "EventAuxiliary", None)
    if aux_obj is not None:
        print("entry_index,run,subrun,event")
        for i in range(n):
            t.GetEntry(i)
            aux_obj = t.EventAuxiliary
            r = int(aux_obj.run())
            sr = int(aux_obj.subRun())
            ev = int(aux_obj.event())
            print(f"{i},{r},{sr},{ev}")
        sys.exit(0)
except Exception as e:
    print(f"Approach 2 failed: {e}", file=sys.stderr)

# Approach 3: use TTreeReader
try:
    reader = ROOT.TTreeReader("Events", f)
    run_rv = ROOT.TTreeReaderValue("UInt_t")(reader, "EventAuxiliary.id_.subRun_.run_.run_")
    sr_rv  = ROOT.TTreeReaderValue("UInt_t")(reader, "EventAuxiliary.id_.subRun_.subRun_")
    ev_rv  = ROOT.TTreeReaderValue("ULong64_t")(reader, "EventAuxiliary.id_.event_")
    print("entry_index,run,subrun,event")
    i = 0
    while reader.Next():
        print(f"{i},{run_rv.Get()[0]},{sr_rv.Get()[0]},{ev_rv.Get()[0]}")
        i += 1
    sys.exit(0)
except Exception as e:
    print(f"Approach 3 failed: {e}", file=sys.stderr)

print("ERROR: All RSE extraction approaches failed", file=sys.stderr)
sys.exit(1)
