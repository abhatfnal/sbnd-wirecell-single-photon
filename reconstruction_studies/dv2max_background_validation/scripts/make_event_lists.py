#!/usr/bin/python3
"""Build the fixed background event lists (truth only; no reconstruction information is used).

numucc_events.csv : the first N_NUMUCC 'numucc_clean' events of the Stage-A 10k census, in selection_index order
ncpi0_events.csv  : ALL 'ncpi0_clean' events, in selection_index order
evt_idx = row number in the list (= the evt_NNNN run directory); --nskip = entry in source_file.
Topology (diagnostic) from GENIE (status-1 particles) + G4 'largeant' MCParticles of the active interaction:
  numucc: muon E, G4 track length (sum of trajectory steps), muon end in active LAr, pi0/pi+-/proton counts
  ncpi0 : leading pi0 E, its two decay photons (E, conversion distance = photon track end - pi0 start), asymmetry
"""
import csv, json, math, os, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partlist_decoder as P   # noqa: E402
import uproot                  # noqa: E402

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102"
N_NUMUCC = 400
BOXES = json.load(open(P.ACTIVE_JSON))["placements"]


def dist_to_boundary(x, y, z):
    best = None
    for b in BOXES:
        lo, hi = b["min_cm"], b["max_cm"]
        if all(lo[i] <= v <= hi[i] for i, v in enumerate((x, y, z))):
            d = min(min(v - lo[i], hi[i] - v) for i, v in enumerate((x, y, z)))
            best = d if best is None else max(best, d)
    return best


def g4(job):
    cls, r, ir = job
    f = uproot.open(r["source_file"])
    rows = P.decode_mcparticles(P.raw(f, "simb::MCParticles_largeant__GenieGen.", int(r["entry"])),
                                want=lambda st, tid, pdg, mo: pdg in (111, 22, 13, -13))
    v = (float(r["vtx_x"]), float(r["vtx_y"]), float(r["vtx_z"]))
    at_v = [q for q in rows if q["start"] and math.dist(q["start"][:3], v) < 0.5]
    o = {}
    if cls == "numucc":
        mu = sorted([q for q in at_v if abs(q["pdg"]) == 13], key=lambda q: -q["p4"][3])
        o["g4_muon_found"] = int(bool(mu))
        if mu:
            m = mu[0]
            o["g4_muon_E_GeV"] = round(m["p4"][3], 4)
            o["g4_muon_straight_len_cm"] = round(math.dist(m["start"][:3], m["end"][:3]), 1)
            o["g4_muon_end_in_active"] = int(bool(P.active_tpc(*m["end"][:3], BOXES)))
    pi0 = sorted([q for q in at_v if q["pdg"] == 111], key=lambda q: -q["p4"][3])
    o["g4_n_pi0_at_vertex"] = len(pi0)
    if pi0:
        q = pi0[0]
        ph = sorted([g for g in rows if g["pdg"] == 22 and g["mother"] == q["trackid"]], key=lambda g: -g["p4"][3])
        o["g4_pi0_E_GeV"] = round(q["p4"][3], 4)
        o["g4_pi0_n_photons"] = len(ph)
        for k, g in enumerate(ph[:2]):
            o[f"g4_gamma{k + 1}_E_GeV"] = round(g["p4"][3], 4)
            o[f"g4_gamma{k + 1}_conv_cm"] = round(math.dist(q["start"][:3], g["end"][:3]), 1)
            o[f"g4_gamma{k + 1}_end_in_active"] = int(bool(P.active_tpc(*g["end"][:3], BOXES)))
        if len(ph) >= 2:
            e1, e2 = ph[0]["p4"][3], ph[1]["p4"][3]
            o["g4_gamma_asym"] = round((e1 - e2) / (e1 + e2), 3)
    return r["selection_index"], o


def main():
    E = list(csv.DictReader(open(f"{W}/inputs/stageA10k_truth_events.csv")))
    I = list(csv.DictReader(open(f"{W}/inputs/stageA10k_truth_interactions.csv")))
    act = {}
    for r in I:
        if r["in_active_lar"] == "1":
            act.setdefault(r["selection_index"], []).append(r)
    lists = {"numucc": [r for r in E if r["numucc_clean"] == "1"][:N_NUMUCC],
             "ncpi0": [r for r in E if r["ncpi0_clean"] == "1"]}
    jobs = [(cls, r, act[r["selection_index"]][0]) for cls, L in lists.items() for r in L]
    with Pool(16) as pool:
        G = dict(pool.map(g4, jobs, chunksize=2))
    for cls, L in lists.items():
        out = []
        for i, r in enumerate(L):
            a = act[r["selection_index"]][0]
            row = dict(evt_idx=i, run=r["run"], subrun=r["subrun"], event=r["event"], rse=r["rse"],
                       selection_index=r["selection_index"], source_file=r["source_file"], entry=r["entry"],
                       truth_class=cls, n_interactions=r["n_interactions"], n_active_interactions=r["n_active_interactions"],
                       nu_pdg=a["nu_pdg"], ccnc=a["ccnc"], mode=a["mode"], nu_E_GeV=a["nu_E_GeV"],
                       lepton_pdg=a["lepton_pdg"], lepton_E_GeV=a["lepton_E_GeV"],
                       vtx_x=a["vtx_x"], vtx_y=a["vtx_y"], vtx_z=a["vtx_z"],
                       vtx_dist_to_active_boundary_cm=round(dist_to_boundary(float(a["vtx_x"]), float(a["vtx_y"]), float(a["vtx_z"])), 1),
                       n_pi0=a["n_pi0"], pi0_E_GeV=a["pi0_E_GeV"], n_pipm=a["n_pipm"], n_proton=a["n_proton"],
                       n_proton_ke35=a["n_proton_ke35"], proton_KE_GeV=a["proton_KE_GeV"], n_gamma_fs=a["n_gamma"])
            row.update(G[r["selection_index"]])
            out.append(row)
        cols = []
        for row in out:
            for k in row:
                if k not in cols:
                    cols.append(k)
        with open(f"{W}/inputs/{cls}_events.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, restval=""); w.writeheader(); w.writerows(out)
        print(cls, len(out))


if __name__ == "__main__":
    main()
