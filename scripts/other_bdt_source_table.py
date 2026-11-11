#!/usr/bin/env python
"""Source table of the 146 inputs of the frozen ``single_photon_other_bdt_final.xml``: CAF branch, declaration (type, DEFAULT/fill value) and filling code in the fg1 production source.

    python scripts/other_bdt_source_table.py --wct-src <dir with NeutrinoTaggerInfo.h and the NeutrinoTagger*.cxx / TaggerCheckNeutrino.cxx / NeutrinoKinematics.cxx at 4b6853d4>
Writes tables/other_bdt_audit/input_source_table.csv. Nothing is inferred: a field the source does not document says so. Source: github.com/HaiwangYu/wire-cell-toolkit branch sbnd-wc-flatcaf, commit 4b6853d4
(the commit declared by the producer for the official Gen2 NC-Delta production; the merged CAFs record Trun.wct_version sbnd-dlvtx-35-pre-master-merge-2026-09-02-424-g78f81c64 and Trun.bdt_weights_dir uboone/weights).
"""
from __future__ import annotations
import argparse, os, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
import pandas as pd
from sbnd_single_photon import bdt as B

CXX = ["NeutrinoTaggerSinglePhoton.cxx", "NeutrinoTaggerCosmic.cxx", "NeutrinoTaggerNuMu.cxx", "NeutrinoTaggerNuE.cxx", "NeutrinoTaggerSSM.cxx", "TaggerCheckNeutrino.cxx", "NeutrinoKinematics.cxx"]


def group_of(n: str) -> str:
    if n.startswith("cosmict_") or n.startswith("cosmic_"):
        return "cosmic tagger (flags/scores of the cosmic-muon taggers)"
    if n.startswith("numu_"):
        return "numuCC tagger (flags/scores)"
    if n == "reco_nuvtxY":
        return "vertex position"
    if re.match(r"shw_sp_vec_dQ_dx_|shw_sp_(max_dQ_dx_sample|n_below|n_lowest|n_highest|lowest_dQ|highest_dQ|medium_dQ|min_dQ|vec_mean_dedx|vec_median_dedx)", n):
        return "shower calorimetry (dQ/dx along the shower)"
    if re.match(r"shw_sp_(proton_|num_protons|num_muons|num_mip_tracks|n_good_tracks|br2_num_valid_tracks)", n):
        return "track / proton activity at the vertex"
    if re.match(r"shw_sp_(br\d|lem_|hol_)", n):
        return "shower-quality sub-taggers (br2/br4/lem/hol)"
    if re.match(r"shw_sp_(n_good_showers|n_br\d_showers|n_20br1_showers)", n):
        return "shower multiplicity"
    if re.match(r"shw_sp_(shw_vtx_dis|max_shw_dis|min_dis|stem_length|length_|n_vertex|n_other_vertex|n_stem_size|E_indirect|flag_all_above)", n):
        return "shower / vertex geometry"
    return "single-photon shower identification (other)"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--wct-src", required=True); ap.add_argument("--model", default="other", choices=["other", "numu", "ncpi0", "nue"], help="Phase 12: the same table for the other frozen models (default: other, unchanged output)")
    ap.add_argument("--outdir", default=None); a = ap.parse_args(); src = Path(a.wct_src)
    info = (src / "NeutrinoTaggerInfo.h").read_text().splitlines()
    cxx = {f: (src / f).read_text().splitlines() for f in CXX}
    m = B.TmvaBdt(a.model, B.DEFAULT_WEIGHT_DIR / f"single_photon_{a.model}_bdt_final.xml"); rows = []
    for idx, n in m.var_list:
        branch = B.input_branch(a.model, n); base = branch.split(".")[-1]
        decl = next(((i + 1, l.strip()) for i, l in enumerate(info) if re.search(rf"\b(float|int|double|bool)\s+{re.escape(base)}\s*(\{{[^}}]*\}})?\s*;", l)), None)
        typ = dflt = comment = ""
        if decl:
            mm = re.search(rf"\b(float|int|double|bool)\s+{re.escape(base)}\s*(?:\{{([^}}]*)\}})?\s*;\s*(//.*)?", decl[1]); typ, dflt, comment = mm.group(1), (mm.group(2) or ""), (mm.group(3) or "").lstrip("/ ").strip()
        fills = []
        for f, lines in cxx.items():
            for i, l in enumerate(lines):
                if re.search(rf"\b(ti|tagger_info|info|tinfo)\.{re.escape(base)}\s*=[^=]", l) or re.search(rf"\b{re.escape(base)}\s*=[^=].*;", l) and f != "NeutrinoKinematics.cxx" and re.search(rf"\.{re.escape(base)}\b", l):
                    fills.append((f, i + 1, l.strip()[:150]))
        first = fills[0] if fills else ("", "", "")
        rows.append(dict(var_index=idx, bdt_variable=n, caf_branch=branch, group=group_of(n), declared_type=typ, declared_default=dflt, header_line=decl[0] if decl else "", header_comment=comment or "(none in source)",
                         n_fill_sites=len(fills), first_fill_file=first[0], first_fill_line=first[1], first_fill_code=first[2], scope="candidate (one value per neutrino-candidate bundle; wc.T_tagger)" if base != "kine_nu_y_corr" else "candidate (wc.T_kine)"))
    t = pd.DataFrame(rows); out = Path(a.outdir) if a.outdir else REPO / "tables" / "other_bdt_audit"; out.mkdir(parents=True, exist_ok=True); t.to_csv(out / ("input_source_table.csv" if a.model == "other" else f"input_source_table_{a.model}.csv"), index=False)
    print(len(t), "inputs;", int((t.header_line == "").sum()), "without header declaration;", int((t.n_fill_sites == 0).sum()), "without a fill site found;", int((t.header_comment != "(none in source)").sum()), "with a header comment")
    print(t.group.value_counts().to_string())


if __name__ == "__main__":
    main()
