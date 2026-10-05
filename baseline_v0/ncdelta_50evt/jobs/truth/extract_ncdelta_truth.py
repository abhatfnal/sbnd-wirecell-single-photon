#!/usr/bin/env python3
"""
Extract per-event truth quantities from NC Delta G4 batch files.
Reads MCTruth (generator) and MCParticle (G4) branches via PyROOT.
Must run inside sbndcode v10_14_02_04 container with env sourced.

Output CSV columns:
  batch, run, subrun, event,
  nu_energy_gev, nu_pdg,
  n_photons, leading_photon_energy_mev,
  n_protons, n_pi0,
  vtx_x, vtx_y, vtx_z,
  conv_gap_cm, conv_x, conv_y, conv_z
"""

import ROOT
import sys
import os

G4DIR = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/g4"
OUTCSV = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/tables/ncdelta_truth.csv"

BATCHES = ["03","04","05","06","07","08","09","10","11","12"]

def get_mctruth_branch_class(tree, batch_num):
    bname = f"simb::MCTruths_generator__NCDeltaBatch{batch_num}."
    br = tree.GetBranch(bname)
    if not br:
        return None, None
    return bname, br.GetClassName()

def extract_photon_conv_gap(tree, event_idx, batch_num):
    """
    Find the leading photon MCParticle and its first e+/e- daughter.
    Returns (conv_gap_cm, conv_x, conv_y, conv_z) or (-1, -999,...) if not found.
    """
    # MCParticle branch from G4 (process name G4, module largeant)
    # try both batch-specific and generic names
    bnames = [
        f"simb::MCParticles_largeant__G4.",
        f"simb::MCParticles_simplemerge__G4.",
    ]
    for bname in bnames:
        br = tree.GetBranch(bname)
        if br:
            break
    else:
        return -1.0, -999.0, -999.0, -999.0

    # Build a map of trackID -> MCParticle using the largeant branch
    tree.GetEntry(event_idx)
    try:
        mcparts_obj = tree.GetLeaf(bname + "obj")
        if not mcparts_obj:
            return -1.0, -999.0, -999.0, -999.0
    except:
        return -1.0, -999.0, -999.0, -999.0

    import math

    # Try to access the vector<MCParticle> directly
    # The branch stores art::Wrapper<std::vector<simb::MCParticle>>
    # After GetEntry, we can access via the branch's object
    # Use a ROOT approach: get the leaf and try to read
    try:
        # Use TTree scan approach: get branch object
        parts_branch = tree.GetBranch(bname)
        class_name = parts_branch.GetClassName()

        # Get the vector from the branch using GetLeaf for the obj sub-branch
        # The art::Wrapper<std::vector<simb::MCParticle>> has a member 'obj'
        # which is std::vector<simb::MCParticle>
        # Try accessing via the sub-branch
        obj_leaf = tree.GetLeaf(bname[:-1] + "/" + bname + "obj")
        if obj_leaf is None:
            return -1.0, -999.0, -999.0, -999.0
    except:
        return -1.0, -999.0, -999.0, -999.0

    return -1.0, -999.0, -999.0, -999.0


def extract_event_truth(tree, event_idx, batch_num):
    """
    Read MCTruth from a G4 batch file event (single process name).
    Returns dict of truth quantities.
    """
    tree.GetEntry(event_idx)
    bname = f"simb::MCTruths_generator__NCDeltaBatch{batch_num}."
    br = tree.GetBranch(bname)
    if not br:
        return None

    class_name = br.GetClassName()
    print(f"  MCTruth branch class: {class_name}", flush=True)

    # The branch stores art::Wrapper<std::vector<simb::MCTruth>>
    # Access via ROOT's auto-loading: branch object is set in tree after GetEntry
    # We can try to get the address via branch->GetAddress()
    obj_ptr = br.GetAddress()
    if not obj_ptr:
        print(f"  WARNING: branch GetAddress() returned NULL", flush=True)
        return None

    # Dereference: the wrapper stores the data product in .obj
    # In art, art::Wrapper<T> has member T obj
    # PyROOT: we need to cast obj_ptr to the right type
    # The class_name should be something like "art::Wrapper<std::vector<simb::MCTruth>>"

    try:
        wrapper = ROOT.gInterpreter.Cast(obj_ptr, class_name)
        if not wrapper:
            print(f"  WARNING: Cast to {class_name} failed", flush=True)
            return None
        mctruth_vec = wrapper.obj  # std::vector<simb::MCTruth>

        if mctruth_vec.size() == 0:
            print(f"  WARNING: MCTruth vector empty", flush=True)
            return None

        mct = mctruth_vec.at(0)

        # Get neutrino
        nu = mct.GetNeutrino()
        nu_pdg = nu.Nu().PdgCode()
        nu_E = nu.Nu().E()  # GeV

        # Get vertex
        nu_vtx = nu.Nu().Position()  # TLorentzVector? or Position() ?
        try:
            vx = nu.Nu().Vx()
            vy = nu.Nu().Vy()
            vz = nu.Nu().Vz()
        except:
            vx, vy, vz = -999.0, -999.0, -999.0

        # Count final state particles
        n_parts = mct.NParticles()
        n_photons = 0
        n_protons = 0
        n_pi0 = 0
        leading_photon_E = 0.0

        for ip in range(n_parts):
            part = mct.GetParticle(ip)
            pdg = part.PdgCode()
            status = part.StatusCode()
            if status != 1:  # only stable final state
                continue
            E_mev = part.E() * 1000.0  # convert GeV -> MeV
            if pdg == 22:
                n_photons += 1
                if E_mev > leading_photon_E:
                    leading_photon_E = E_mev
            elif pdg == 2212:
                n_protons += 1
            elif pdg == 111:
                n_pi0 += 1

        return {
            "nu_energy_gev": round(nu_E, 6),
            "nu_pdg": nu_pdg,
            "n_photons": n_photons,
            "leading_photon_energy_mev": round(leading_photon_E, 3),
            "n_protons": n_protons,
            "n_pi0": n_pi0,
            "vtx_x": round(vx, 2),
            "vtx_y": round(vy, 2),
            "vtx_z": round(vz, 2),
        }
    except Exception as e:
        print(f"  Exception reading MCTruth: {e}", flush=True)
        return None


def main():
    print("=== NC Delta truth extraction ===", flush=True)

    # Load ROOT dictionaries (sbndcode env sources all needed libs)
    ROOT.gSystem.Load("libsimBase")
    ROOT.gSystem.Load("liblarsimSimulationBase")

    rows = []
    header = "batch,run,subrun,event,nu_energy_gev,nu_pdg,n_photons,leading_photon_energy_mev,n_protons,n_pi0,vtx_x,vtx_y,vtx_z,conv_gap_cm,conv_x,conv_y,conv_z"

    for batch in BATCHES:
        g4_file = f"{G4DIR}/batch_{batch}/ncdelta_g4_batch_{batch}.root"
        if not os.path.exists(g4_file):
            print(f"MISSING: {g4_file}", flush=True)
            continue

        print(f"\n--- batch_{batch} ---", flush=True)
        tf = ROOT.TFile.Open(g4_file)
        if not tf or tf.IsZombie():
            print(f"  ERROR: cannot open {g4_file}", flush=True)
            continue

        tree = tf.Get("Events")
        if not tree:
            print(f"  ERROR: Events tree not found", flush=True)
            tf.Close()
            continue

        n_entries = tree.GetEntries()
        print(f"  Entries: {n_entries}", flush=True)

        # Get RSEs from EventAuxiliary
        aux = ROOT.art.EventAuxiliary()
        tree.SetBranchAddress("EventAuxiliary", ROOT.AddressOf(aux))

        for i in range(n_entries):
            tree.GetEntry(i)
            run = aux.run()
            sr = aux.subRun()
            evt = aux.event()
            print(f"  Event {i}: run={run} subRun={sr} event={evt}", flush=True)

            truth = extract_event_truth(tree, i, batch)
            if truth is None:
                print(f"  WARNING: truth extraction failed for batch_{batch} event={evt}", flush=True)
                row = f"{batch},{run},{sr},{evt},-999,-999,-999,-999,-999,-999,-999,-999,-999,-999,-999,-999,-999"
            else:
                # Conversion gap from MCParticle
                conv_gap, cx, cy, cz = -1.0, -999.0, -999.0, -999.0  # placeholder

                row = (f"{batch},{run},{sr},{evt},"
                       f"{truth['nu_energy_gev']},{truth['nu_pdg']},"
                       f"{truth['n_photons']},{truth['leading_photon_energy_mev']},"
                       f"{truth['n_protons']},{truth['n_pi0']},"
                       f"{truth['vtx_x']},{truth['vtx_y']},{truth['vtx_z']},"
                       f"{conv_gap},{cx},{cy},{cz}")
            rows.append(row)

        tf.Close()

    with open(OUTCSV, "w") as fout:
        fout.write(header + "\n")
        for row in rows:
            fout.write(row + "\n")

    print(f"\n=== Written {len(rows)} rows to {OUTCSV} ===", flush=True)


if __name__ == "__main__":
    main()
