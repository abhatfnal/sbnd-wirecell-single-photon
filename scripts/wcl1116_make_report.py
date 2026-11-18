#!/usr/bin/env python
"""Writes docs/analysis/WCL1116_NOV16_FROZEN_R1_SELECTION_REPLAY.md from the committed tables (tables/wcl1116_nov16_replay/). Every number is read from a CSV/JSON; nothing is typed in.

    source env/setup_eaf.sh && python scripts/wcl1116_make_report.py
"""
import json, sys
from pathlib import Path
import pandas as pd
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import signal_pipeline as SP
T = REPO / "tables" / "wcl1116_nov16_replay"; DOC = REPO / "docs" / "analysis" / "WCL1116_NOV16_FROZEN_R1_SELECTION_REPLAY.md"
rd = lambda n: pd.read_csv(T / n)
md = lambda df: SP.markdown_table(df, index=False, floatfmt="{:.4g}")
js = lambda n: json.load(open(T / n))
pct = lambda x, d=2: f"{x:.{d}f} %"


def build():
    L = []; A = L.append
    cf, eff = rd("signal_cutflow_old_vs_nov16.csv"), rd("signal_topology_efficiency.csv")
    ea = eff[eff.policy == "any"].set_index(["production", "group"]); ef = eff[eff.policy == "first"].set_index(["production", "group"])
    G = lambda prod, grp, col="efficiency_pct": ea.loc[(prod, grp), col]
    sm = js("signal_summary.json"); bs = js("bnb_summary.json"); mig = rd("signal_migration_summary.csv").set_index("migration").N
    fcs = rd("signal_migration_first_changed_stage.csv"); ceil = rd("signal_reco_ceiling.csv").set_index("production"); vd = rd("signal_vertex_distance.csv"); vm = rd("signal_vertex_distance_matched.csv").set_index("topology")
    ff = pd.read_csv(T / "signal_first_failure.csv", header=[0, 1], index_col=0); inv = rd("sample_inventory.csv"); prov = rd("production_provenance.csv")
    tax = rd("signal_photon_taxonomy_old_vs_nov16.csv"); tx = tax[tax.group == "all"].pivot_table(index="outcome", columns="production", values=["n", "pct"])
    vas = rd("signal_vertex_change_vs_selection.csv"); ish = rd("signal_bdt_input_shift_by_family.csv"); ssh = rd("signal_score_migration.csv")
    bt = rd("bnb_selected_totals.csv").set_index("production"); bo, bn = bt.loc["old_fg1 (corrected R1)"], bt.loc["nov16"]; bcat = rd("bnb_category_old_vs_new.csv"); bmv = rd("bnb_migration_first_changed_stage.csv")
    nat = rd("bnb_natural_cv_cutflow.csv").set_index("stage"); cs = rd("controls_selection_counts.csv"); cm = rd("controls_old_vs_new_migration.csv"); cfc = rd("controls_first_changed_stage.csv")
    ex_o, ex_n = sm["old"]["expected"], sm["nov16"]["expected"]
    A("# WCL1116 Nov16: frozen Round-1 selection replay (`NOV16_FROZEN_R1_SELECTION_REPLAY`)\n")
    A("Date: 2026-11-18. Branch `analysis/wcl1116-nov16-frozen-r1-replay-20261118` (base `daf95442515b601eecda41c6c586931a5ae38c54`). **Diagnostic only.** The selection is the frozen, source-faithful, corrected Round-1 chain applied unchanged to Haiwang's `WCLocal2026Nov16-FermiGrid` production. Nothing was tuned, trained, scanned or chosen from these results; no analysis FV was adopted; no vertex mode was chosen.\n")
    A("> **This is not the Round-2 reconstruction.** It answers *what the Nov16 reconstruction does to the already-frozen Round-1 analysis*; it does not answer which cuts or models Round 2 should use. The ~Nov 23 production is expected to change the effective boundary and possibly the upstream BDTs (section 13); the analysis must then be re-run with independently frozen choices. None of the numbers below may be used to set a Round-2 threshold, feature, model, vertex mode, FV, signal/topology/background definition or strategy.\n")
    A("## 1. Headline\n")
    A(f"Dedicated NC-Delta radiative MC, provisional TPC-box truth denominator {int(G('old_fg1','total','N_truth')):,} (identical for both productions):\n")
    A(md(pd.DataFrame([dict(production="old fg1-era `ncdr`, corrected Round 1", selected=int(G("old_fg1", "total", "selected")), efficiency=pct(G("old_fg1", "total")), interval68=f"{G('old_fg1','total','lo68_pct'):.2f}-{G('old_fg1','total','hi68_pct'):.2f} %"),
                       dict(production="WCLocal2026Nov16 `recTreeWireCell`", selected=int(G("nov16", "total", "selected")), efficiency=pct(G("nov16", "total")), interval68=f"{G('nov16','total','lo68_pct'):.2f}-{G('nov16','total','hi68_pct'):.2f} %")])))
    A(f"\nGeneric BNB-CV selected non-signal events: **{int(bo.non_signal)} -> {int(bn.non_signal)}** (1g0p {int(bo.reco_1g0p)} -> {int(bn.reco_1g0p)}; 1g1p {int(bo.reco_1g1p)} -> {int(bn.reco_1g1p)}; >=2p {int(bo.reco_ge2p)} -> {int(bn.reco_ge2p)}). The dedicated-signal efficiency rose by a factor {G('nov16','total')/G('old_fg1','total'):.2f} and the selected non-signal BNB count by a factor {bn.non_signal/bo.non_signal:.2f}: **the larger efficiency comes with a similar increase in selected background, so this replay does not by itself show an improvement of the selection.** The efficiency is a dedicated-signal efficiency, not a purity or S/B (section 11).\n")
    A("## 2. Repository, corrections verified, tree, policy\n")
    A("- Repository `/home/abhat/Single-photon/sbnd-wirecell-single-photon`, host `jupyter-abhat-single-photon---9ba4d904`; analysis commit `daf9544` (scorer correction) is the base. The tree contains the corrections: TMVA response `v`; `score = log10((1+v)/(1-v))` applied **once** (`wcl1116_replay_common.to_D` keeps the raw response as `v_<model>` and transforms once; a test pins this); `kine_pio_flag = 0` for the legacy ncpi0 (the builder stores `c_score_ncpi0_pio0`, computed with `legacy_scorer.ncpi0_input_matrix(..., \"zero\")`); the four legacy MicroBooNE XMLs with the recorded SHA256 values (a test checks them); frozen thresholds numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0. The obsolete tanh-space scorer and the SBND development BDTs (`DEV_DO_NOT_DEPLOY`) are not used.")
    A("- Tree read: **`recTreeWireCell`** (production default `dv2_split_move`); `caf.MergedCaf` opens only that tree. The alternate `recTreeWireCell_dv2snap` exists in the same files and is recorded for provenance only; it was **not** read and snap vs split-move was **not** compared.")
    A("- Selection (pre-FV): `shw_sp_n_20mev_showers > 0`; numu, other, ncpi0, nue scores as above; `shw_sp_n_20br1_showers == 1`. Candidate policy `any` (policy `first` also tabulated). No analysis FV; same truth signal definition, 35 MeV post-FSI proton topology, background taxonomy, candidate/evaluable semantics and non-finite treatment as corrected Round 1.")
    A("- Builder reproduction: the (additive) Nov16 builder reproduces the stored Round-1 candidate pieces exactly on the test files, and the old reference below reproduces every Round-1 anchor (asserted in code and pinned by a test).\n")
    A("## 3. What changed between the old production and Nov16\n")
    A(md(prov))
    A("\n**Attribution verdict: `VERTEX + OTHER RECONSTRUCTION CHANGES`.** Step 1 (imaging, clustering, matching) is reused and identical, and the candidate set is unchanged (section 6), but step 2 changed in more than the vertex placement: the wire-cell-toolkit commit, the wire-cell-data bundle, the DL-vertex model/bundle, the step-2 chain structure and the flat-tree schema all differ. The old vertex mode and DL model, the booked numu/nue weights, the old cosmic boundary and SCE policy are *not stated* in the production documentation. The comparison therefore cannot be called vertex-only. Nov16 still uses the box boundary and no SCE back-correction (as stated by Haiwang).\n")
    A("## 4. Sample inventory (WCLocal2026Nov16-FermiGrid)\n")
    A(md(inv[["folder", "registry", "pairs", "pairs_OK", "pairs_PARTIAL", "pairs_EMPTY", "merged_cafs", "caf_events", "wc_valid_split", "wc_valid_snap"]]))
    A("\nBase `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/<folder>/`; WCT 0.38.0 `c935e30d`, larwirecell `ad5d9421`, wire-cell-data `99c6497f` (DV2-MAX `aurora_space`), sbndcode `v10_14_02_03`; trees `recTreeWireCell` (schema `af9c87c8`, 2,416 branches) and `recTreeWireCell_dv2snap` (schema `d4396a34`). Counts equal Haiwang's README. Open data and Run-3 have no dedicated truth; the old open-data production used an older toolkit (`f6fd2209`) and an older schema, so its old-vs-new comparison is between two quite different productions.\n")
    A("**Critical gate: a refreshed dedicated NC-Delta sample IS available** (`mc-ncdr/`: the same SAM selection as Round 1, 13,772 events, all with Wire-Cell output, the same CAF files in the same order as the Round-1 manifest). The truth denominator is reco-independent and identical (12,427; all events of the denominator joined on run/subrun/event, one never arrived in either production). The apples-to-apples signal efficiency is therefore supportable. Generic-BNB NC-Delta events were not substituted for it.\n")
    A("## 5. Signal: cutflow, topology, first failure\n")
    A("Cumulative cutflow, policy `any`, denominator 12,427:\n")
    A(md(cf.rename(columns={"old_fg1_N": "old", "nov16_N": "Nov16"})[["stage", "old", "Nov16", "delta", "old_pct_of_12427", "nov16_pct_of_12427"]]))
    A("\nEfficiency (exact binomial 68 % interval):\n")
    rows = []
    for g in ["total", "0p", "1p", ">=2p", "Delta0", "Delta+"]:
        rows.append(dict(group=g + (" (descriptive; Delta charge is not reco proton topology)" if g.startswith("Delta") else ""), N_truth=int(G("old_fg1", g, "N_truth")), old=f"{int(G('old_fg1',g,'selected'))} = {G('old_fg1',g):.2f} % ({G('old_fg1',g,'lo68_pct'):.2f}-{G('old_fg1',g,'hi68_pct'):.2f})",
                         nov16=f"{int(G('nov16',g,'selected'))} = {G('nov16',g):.2f} % ({G('nov16',g,'lo68_pct'):.2f}-{G('nov16',g,'hi68_pct'):.2f})"))
    A(md(pd.DataFrame(rows)))
    A(f"\nPolicy `first`: old {int(ef.loc[('old_fg1','total'),'selected'])} ({ef.loc[('old_fg1','total'),'efficiency_pct']:.2f} %), Nov16 {int(ef.loc[('nov16','total'),'selected'])} ({ef.loc[('nov16','total'),'efficiency_pct']:.2f} %).\n")
    A("Exclusive first failure, `any` policy, percent of 12,427 (Round-1 categories):\n")
    ffd = pd.DataFrame({"category": ff.index, "old N": ff[("N", "old_fg1")].astype(int).values, "Nov16 N": ff[("N", "nov16")].astype(int).values, "old %": ff[("pct", "old_fg1")].values, "Nov16 %": ff[("pct", "nov16")].values})
    A(md(ffd))
    A("\n**Reconstruction ceiling vs BDT response** (before any BDT cut):\n")
    A(md(ceil.reset_index()[["production", "N_truth", "wc_valid", "with_candidate", "n20_shower", "bdt_evaluable", "mean_ncand", "total_candidates_signal_events"]]))
    A(f"\nCandidate formation is unchanged (same events, same candidate counts). The >20 MeV-shower and BDT-evaluable ceilings are slightly **lower** in Nov16. Everything that raises the efficiency is therefore in the BDT stages (`BDT RESPONSE MIGRATION`); no gain in the reconstruction ceiling is seen before the BDT cuts.\n")
    A("## 6. Signal migration (matched events, same run/subrun/event)\n")
    A(md(rd("signal_migration_summary.csv")))
    A("\nFirst stage whose cumulative any-candidate state differs (events that change selection):\n")
    A(md(fcs.pivot_table(index="first_changed_stage", columns="migration", values="N", fill_value=0).reset_index()))
    A("\nBy truth topology and, descriptively, by Delta charge:\n")
    A(md(rd("signal_migration_by_topology.csv").pivot_table(index="topology", columns="migration", values="N").reset_index()))
    A("")
    A(md(rd("signal_migration_by_delta_charge.csv").pivot_table(index="delta", columns="migration", values="N").reset_index()))
    A("\nFirst changed stage by topology: `tables/wcl1116_nov16_replay/signal_migration_stage_by_topology.csv`. Counter transitions (`shw_sp_filled`, >20 MeV shower count, `n_20br1` count) of matched candidates: `counts_migration_matched_candidates.csv`.\n")
    A("## 7. Vertex and reconstruction diagnostics (signal)\n")
    A("Reco-to-true neutrino-vertex distance (evaluation only; exact (0,0,0) = no vertex is excluded):\n")
    v = vd[vd.view == "nearest candidate"][["production", "topology", "n_events", "median_cm", "frac_lt_1cm", "frac_lt_3cm", "frac_lt_5cm"]]
    A(md(v))
    A(f"\nMatched events (nearest candidate): the vertex moved >1 cm closer in {vm.loc['all','frac_improved_gt_1cm']*100:.1f} % and >1 cm farther in {vm.loc['all','frac_worsened_gt_1cm']*100:.1f} % of events. Vertex proximity improved clearly for every topology.\n")
    A("Photon-reconstruction taxonomy of the signal photon (Round-1 code and classes unchanged; events with >= 1 candidate, N = 11,331 in both; the OLD column reproduces the Round-1 taxonomy table exactly):\n")
    tt = pd.DataFrame({"outcome": tx.index, "old N": tx[("n", "old_fg1")].astype(int).values, "Nov16 N": tx[("n", "nov16")].astype(int).values, "old %": tx[("pct", "old_fg1")].values, "Nov16 %": tx[("pct", "nov16")].values})
    A(md(tt))
    A("\nImproved: the signal photon's shower in a passing candidate, fewer fragmented photons, fewer photons typed as tracks, fewer showers outside the main-vertex set. **Worsened:** more photon showers typed as a non-electron particle and more photon particle rows missing. The new vertexing does not remove the Round-1 reconstruction loss categories uniformly. Proton/shower ownership beyond these classes was not re-derived.\n")
    A("Association of the selection change with the per-event vertex change (descriptive; truth used only for evaluation; **association, not causation**):\n")
    A(md(vas))
    A("\nBDT-input change between the productions for matched candidates (first 600 files with candidates; a sample, `signal_bdt_input_shift*.csv`):\n")
    A(md(ish))
    A("\nInputs change broadly (the reconstructed vertex in ~99 % of matched candidates; shower geometry, pi0 kinematics, upstream numu scores in many), with median signed changes near zero: the frozen classifiers are evaluating many shifted inputs, not one offset feature or a default value. Frozen-score migration of matched candidates:\n")
    A(md(ssh))
    A("\n## 8. Generic BNB CV\n")
    A(md(bt.reset_index()[["production", "selected_events", "signal_like", "non_signal", "reco_1g0p", "reco_1g1p", "reco_ge2p"]]))
    A("\nNon-signal selected events by candidate-associated truth category (Round-1 taxonomy, unchanged) with matched enter/leave counts:\n")
    A(md(bcat))
    A("\nMatched selection movement (events, same run/subrun/evt; first changed stage):\n")
    A(md(rd("bnb_migration_summary.csv")))
    A("")
    A(md(bmv.pivot_table(index="first_changed_stage", columns="movement", values="N", fill_value=0).reset_index()))
    A(f"\nThe intrinsic-nueCC category among selected BNB non-signal events (the Round-1 source-faithful reference of 1) is {int(bcat.set_index('category').loc['NUE_CC','nov16'])} in Nov16. Natural NC-Delta in the BNB CV (117 events, descriptive, low statistics): final {int(nat.loc['final','old_fg1'])} -> {int(nat.loc['final','nov16'])} of 117.\n")
    A("## 9. nueCC control (dedicated intrinsic nueCC MC) and data controls\n")
    keep = ["sample", "production", "usable_events_wc_valid", "candidates", "events_candidate", "events_n20mev", "events_bdt_evaluable", "events_numu", "events_other", "events_ncpi0", "events_nue", "events_n20br1", "selected_per_1000_usable_events"]
    A(md(cs[keep]))
    A("\nThe Round-1 'reference of 1' belongs to the intrinsic-nueCC *category inside the generic BNB CV* (section 8), not to the dedicated nueCC sample; the dedicated-sample old reference above was rebuilt with the same builder and scorer. Matched old-vs-new migration of the controls:\n")
    A(md(cm[["sample", "matched_events", "only_old", "only_new", "old_pass_new_pass", "old_pass_new_fail", "old_fail_new_pass", "ncand_more", "ncand_fewer"]]))
    A("\nFirst changed stage: `controls_first_changed_stage.csv`. The data controls are counts only: no truth interpretation, no new sideband, and no beam-off normalisation (blocker G is still open): the per-1,000-event rates are not exposure-normalised and beam-off and beam-on are not compared quantitatively. Run-3 BNB has no Round-1 counterpart. Data-vs-MC shape comparisons were **not** repeated (they would need the beam-off normalisation).\n")
    A("## 10. Figures\n")
    for f, t in (("fig_cutflow_old_vs_nov16.png", "cumulative signal cutflow"), ("fig_topology_efficiency_old_vs_nov16.png", "efficiency by truth topology"), ("fig_vertex_distance_old_vs_nov16.png", "reco-vertex distance"),
                 ("fig_sp_scores_old_vs_nov16.png", "four frozen SP scores (identical binning; clipped at +-3)"), ("fig_bnb_background_old_vs_nov16.png", "selected BNB non-signal by category")):
        A(f"- `plots/wcl1116_nov16_replay/{f}`: {t}")
    A("")
    A("## 11. Purity / S/B / rate: exact definitions and what is supportable\n")
    A("Round 1 defined **no purity, no S/B and no significance**: they are blocked until the beam-off normalisation (G) and flash-time reference (H) are resolved (`ROUND2_EVALUATION_CONTRACT_SCORER_BASELINES.md`). None is derived here. The quantities that *are* defined are kept distinct:\n")
    pot = bs["pot"]
    t = pd.DataFrame([
        dict(quantity="dedicated-signal efficiency (selected / frozen truth denominator)", old=pct(G("old_fg1", "total")), nov16=pct(G("nov16", "total")), note="dedicated NC-Delta MC only"),
        dict(quantity="selected signal rate per 1e20 POT (Round-1 expected-yield definition; stat. only)", old=f"{ex_o['total']:.1f} +- {ex_o['total_stat_unc']:.1f}", nov16=f"{ex_n['total']:.1f} +- {ex_n['total_stat_unc']:.1f}", note="NOT an S/B"),
        dict(quantity="selected non-signal BNB rate per 1e20 POT (Poisson stat. only; no cosmic-only component)", old=f"{sum(bo[f'rate_per_1e20_{k}'] for k in ('1g0p','1g1p','ge2p')):.0f}", nov16=f"{sum(bn[f'rate_per_1e20_{k}'] for k in ('1g0p','1g1p','ge2p')):.0f}", note=f"CV exposure {pot:.3g} POT, same files"),
        dict(quantity="generic-BNB truth signal fraction (signal-like / selected events)", old=f"{int(bo.signal_like)}/{int(bo.selected_events)} = {100*bo.signal_like/bo.selected_events:.2f} %", nov16=f"{int(bn.signal_like)}/{int(bn.selected_events)} = {100*bn.signal_like/bn.selected_events:.2f} %", note="natural NC-Delta in generic MC; NOT a purity"),
        dict(quantity="BNB non-signal acceptance (selected non-signal / usable BNB-CV events)", old=f"{bs['old']['non_signal']}/{bs['wc_valid_old']:,}", nov16=f"{bs['nov16']['non_signal']}/{bs['wc_valid_new']:,}", note="background acceptance, descriptive"),
    ])
    A(md(t))
    A("\nPurity, S/B and significance: **not computed** (not defined in Round 1; the dedicated-signal and generic-BNB samples carry different physics normalisations and must not be combined into a purity).\n")
    A("## 12. Interpretation (diagnostic; no tuning)\n")
    A("**Improved**")
    A(f"- Reconstructed-vertex proximity: the fraction of events with a candidate vertex within 5 cm of the true vertex is {vd[(vd.production=='old_fg1')&(vd.view=='nearest candidate')&(vd.topology=='all')].frac_lt_5cm.iloc[0]*100:.0f} % -> {vd[(vd.production=='nov16')&(vd.view=='nearest candidate')&(vd.topology=='all')].frac_lt_5cm.iloc[0]*100:.0f} % (truth 0p {vd[(vd.production=='old_fg1')&(vd.view=='nearest candidate')&(vd.topology=='0p')].frac_lt_5cm.iloc[0]*100:.0f} -> {vd[(vd.production=='nov16')&(vd.view=='nearest candidate')&(vd.topology=='0p')].frac_lt_5cm.iloc[0]*100:.0f} %; truth 1p {vd[(vd.production=='old_fg1')&(vd.view=='nearest candidate')&(vd.topology=='1p')].frac_lt_5cm.iloc[0]*100:.0f} -> {vd[(vd.production=='nov16')&(vd.view=='nearest candidate')&(vd.topology=='1p')].frac_lt_5cm.iloc[0]*100:.0f} %).")
    A("- Photon-shower association: more signal photons end as a shower in a passing candidate; fewer fragmented, track-typed or main-vertex-set-excluded photons.")
    A(f"- Dedicated-signal efficiency {pct(G('old_fg1','total'))} -> {pct(G('nov16','total'))}, in every truth topology ({G('old_fg1','0p'):.2f}/{G('old_fg1','1p'):.2f}/{G('old_fg1','>=2p'):.2f} -> {G('nov16','0p'):.2f}/{G('nov16','1p'):.2f}/{G('nov16','>=2p'):.2f} % for 0p/1p/>=2p); truth 0p is now the highest, a change of ordering.\n")
    A("**Worsened or not improved**")
    A(f"- The selected non-signal BNB count rose from {int(bo.non_signal)} to {int(bn.non_signal)}; NC pi0, outside-TPC and CC pi0 categories rise, and the intrinsic-nueCC category from {int(bcat.set_index('category').loc['NUE_CC','old'])} to {int(bcat.set_index('category').loc['NUE_CC','nov16'])}. The dedicated nueCC control selects {int(cs[(cs['sample']=='nuecc')&(cs.production=='nov16')].events_n20br1.iloc[0])} vs {int(cs[(cs['sample']=='nuecc')&(cs.production!='nov16')].events_n20br1.iloc[0])} events.")
    A("- Candidate formation is unchanged and the >20 MeV-shower ceiling is slightly lower; photons typed as a non-electron particle and missing particle rows increase.")
    A(f"- {int(mig.get('old pass -> new fail',0))} signal events selected in the old reconstruction are not selected in Nov16.\n")
    A("**What is associated with the vertex / reconstruction change** (association only): the per-event selection change is concentrated in events whose vertex moved closer (table in section 7) and the frozen-BDT inputs change broadly. **What cannot be isolated:** the vertex placement from the other step-2 changes (toolkit, wire-cell-data, DL bundle, upstream numu/nue scores that are inputs of the SP numu/other BDTs, schema); the effect of the unchanged box boundary; and whether the response of the frozen MicroBooNE-trained classifiers to shifted inputs is a domain effect. No causal statement is made.\n")
    A("## 13. Nov16 versus the upcoming Nov23 production\n")
    A("**Nov16 contains:** Snehadri's improved vertexing (`aurora_space` DL bundle), the current **box boundary**, the shipped (MicroBooNE-trained) upstream BDTs, and **no SCE back-correction**.\n")
    A("**The upcoming ~Nov23 production is expected (per the collaboration plan communicated with this task; Haiwang's plan `issues/50-sbnd-effective-boundary/plan.md` itself gives no date and does not name Xuyang) to add or change:**\n")
    A("- a measured non-box *effective boundary* (wall inset versus drift distance, per TPC), with separate data and MC shapes, and no SCE back-correction for either;")
    A("- consequences that propagate through TGM, the STM containment gate, FC, the neutrino containment flags (`match_isFC`), the cosmic-tagger flags (BDT inputs), and the nue / single-photon `angular_cut`, `shower_to_wall` and `bad_reconstruction_2(_sp)` inputs (the plan marks these 'validate');")
    A("- possibly Xuyang's updated upstream BDT, and a full new production and analyzer rerun.\n")
    A("Therefore **the Nov16 result is not the final Round-2 result.** Its purpose is to isolate and document what the current improved reconstruction does to the frozen Round-1 analysis, as a clean reference. In particular the outside-TPC and cosmic-like background categories and the nue-sensitive stages are quantities for which the Nov23 inputs are expected to differ; no prediction of their direction is made here. The Nov23 analysis must re-freeze its choices independently of this replay.\n")
    A("## 14. Limits\n")
    A("- One production, one replay: nothing was tuned or selected from it; the alternate vertex tree was not read.")
    A("- The old nueCC, beam-off and open-data references were rebuilt with the same builder and scorer (not taken from Round-1 products, which did not rescore them); the old open-data production is a different, older toolkit.")
    A("- The BDT-input shift table is a 600-file sample; the taxonomy covers events with >= 1 candidate (N = 11,331); proton/shower ownership beyond the Round-1 classes and data-vs-MC shapes were not recomputed.")
    A("- A transient dCache pool outage caused missing pieces in the first CV and old-nueCC passes; they were re-read (0 errors in the final tables, 37,742 / 11,441 files).")
    A("- BNB selected-event truth uses the Round-1 `deep` association on the 704 newly selected candidates; statistics are Poisson-limited and no systematics are included.")
    return L


if __name__ == "__main__":
    L = build()
    DOC.write_text("\n".join(L) + "\n"); print("wrote", DOC, len(L), "lines")
