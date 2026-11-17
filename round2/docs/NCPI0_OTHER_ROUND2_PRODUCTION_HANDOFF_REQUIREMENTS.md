# Round-2 production handoff: what Haiwang receives for each single-photon model

Date: 2026-11-17. Status: **contract only. No final model exists.** After the thesis audit
(`YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`), ncpi0 is ready for development training. For other, the EXT sample
exists (`fg1-beamoff-train`) but is statistically limited and needs reprocessing. Neither is ready for final training. SP numu is proposed to join Round 2 under the same contract
(`SP_BDT_ROUND2_FREEZE_ORDER.md` §5; spec `single_photon_numu_training_spec` v0.1.0). A model is handed over only when every field below is filled.

**Update, 2026-11-17 evening.** Haiwang's Round-2 refresh is running (`HAIWANG_ROUND2_ACTIVE_PRODUCTION_TRACKER.md`):
- WCLocal2026Nov16, WCT 0.38.0 `c935e30d`, Snehadri's DV2-MAX `aurora_space` bundle `51588842…`;
- the Aurora training NC Δ and BNB are complete; the FermiGrid evaluation side is in its final reruns.

Fields 11 and 16 below now have concrete candidates. The exporter of fields 14–15 exists, with a Python-side
equivalence on the development fixtures (`SP_BDT_EXPORT_EQUIVALENCE_STATUS.md`). Owners: SP numu / other / ncpi0 are
Avinay's. The upstream νμ / νe models are Xuyang's and Matteo's, and they are different models from SP numu / SP nue.

**Naming.** The inherited MicroBooNE files keep their names and their place (`single_photon_<x>_bdt_final.xml`). SBND
models get versioned names and their own directory, so the two can never be swapped by accident:
`sbnd/weights/single_photon/single_photon_<x>_bdt_sbnd_round2_v<k>.{xml,json,features.json,sha256}`.
`v<k>` increases on any change of training spec, inputs or training sample.

| # | field | single_photon_ncpi0 | single_photon_other |
|---:|---|---|---|
| 1 | versioned model filename | `single_photon_ncpi0_bdt_sbnd_round2_v1.xml` (+ `.json`, `.features.json`) | `single_photon_other_bdt_sbnd_round2_v1.xml` (+ `.json`, `.features.json`) |
| 2 | SHA256 | of all three files, in `<name>.sha256`. To be filled at freeze | same |
| 3 | classifier name | `single_photon_ncpi0` (NC π⁰ background rejection) | `single_photon_other` ("other" background rejection) |
| 4 | training code commit | commit of `round2/` in `abhatfnal/sbnd-wirecell-single-photon`, clean tree, recorded by the trainer | same |
| 5 | training spec version | `single_photon_ncpi0_training_spec` ≥ v1.0.0 with status `READY_FOR_FINAL_TRAINING` (today v0.2.0 `READY_FOR_DEVELOPMENT_TRAINING`) | `single_photon_other_training_spec` ≥ v1.0.0 (today v0.2.3 `READY_ONLY_AFTER_ADDITIONAL_TRAINING_SAMPLE`) |
| 6 | ordered feature list | 45 names, `round2/config/features/single_photon_ncpi0_inputs_v0.json` (sha256 `5882391f…`), or its successor if inputs change | 146 names, `…_other_inputs_v0.json` (sha256 `0c3d3083…`) |
| 7 | score direction | higher = more single-photon-like; keep `score > threshold` | same |
| 8 | operating threshold | in **log10-odds**. Chosen jointly, only after the upstream models and the SP model set are frozen and the refresh is complete, on a **training/validation** partition only. Never tuned on official Round-2 samples. Placed between distinct validation scores; rows within 1e-4 of the cut listed. Legacy control cut −0.05 (reference only) | same; legacy 0.2 |
| 9 | default / missing semantics | inputs float32; scored only when `shw_sp_filled == 1` and every input is finite, otherwise sentinel −20 (MicroBooNE's initial value; proposal to confirm); `kine_pio_flag` policy as in the spec; `reco` inputs read as stored | same; `reco_nuvtxY` ← `T_kine.kine_nu_y_corr` |
| 10 | upstream-model dependencies | the 15 νe level-1 TMVA models (`uboone/weights/{br3_3,…,tro_5}_BDT.weights.xml`, shipped; stored and fixed). **Not** `nue_score` | `numu_tagger1/2.weights.xml`, `cos_tagger_10.weights.xml` (shipped, unless Xuyang/Matteo change them) and **Xuyang/Matteo's frozen νμ final model** (file + sha256), recomputed offline on the refreshed training CAFs |
| 11 | vertex / reconstruction version | toolkit commit + DL vertex checkpoint sha256 of the Aurora training refresh; must equal Round-2 production. **Candidate (running):** WCT 0.38.0 `c935e30d`, wire-cell-data `99c6497f`, DV2-MAX `aurora_space` bundle `51588842…`. Tree `recTreeWireCell` = `dv2_split_move` (default) or `recTreeWireCell_dv2snap` = `dv2_snap`: to be confirmed | same |
| 12 | training sample manifest | refresh lists from `tools/make_refresh_list.py` + `round2/manifests/wcl1116_aurora_v0/manifest_*.{json,tsv.gz}` (path, size, mtime, list sha256); official samples absent (firewall log) | same, plus the odd-run beam-off half of `wcl1116-fg-beamoff` as a named, approved exception |
| 13 | validation summary | Aurora test fold, per sample: AUC, efficiency / rejection at the threshold, per truth category, overtraining (train / validation / test), score distributions, feature importance. No official-sample numbers | same, plus per background category (cosmic-matched, out-of-volume) |
| 14 | deployment format | TMVA BDT XML, `BoostType=Grad`, no transformations, variables in feature-list order, written by `sp_retrain/export_tmva.py` in the inherited `xgboost2TMVA` layout; native JSON, `.features.json` and `.sha256` beside it | same |
| 15 | scorer-equivalence test result | `tools/export_equivalence_check.py`. The XML forest sum must equal the native leaves summed in double exactly. Native XGBoost margin (float32 sum) vs XML: within `1e-5·max(1,|m|)`, with **zero decision flips** at the chosen threshold. Python ↔ toolkit bit-identical (**C++ side still to run**); order and missing-value guards. Dev fixtures: pass (`SP_BDT_EXPORT_EQUIVALENCE_STATUS.md`) | same |
| 16 | expected Wire-Cell config key / path | route A: `single_photon_ncpi0_xml = 'sbnd/weights/single_photon/single_photon_ncpi0_bdt_sbnd_round2_v1.xml'`, resolved by `wc.resolve`. Route B: offline score table keyed `(file_id, run, subrun, event, cand)` | `single_photon_other_xml = …_other_bdt_sbnd_round2_v1.xml` |
| 17 | legacy control model path | `uboone/weights/single_photon_ncpi0_bdt_final.xml`, sha256 `983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3`. **Not in wire-cell-data today**; add it from the reference bundle if a legacy score is wanted in production | `uboone/weights/single_photon_other_bdt_final.xml`, sha256 `8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16`, same remark |
| 18 | date / frozen status | to be filled at freeze; today **not frozen: FINAL TRAINING WAITS FOR REFRESH** (training lists, vertex-tree confirmation) | **not frozen: WAITS FOR REFRESH + FROZEN UPSTREAM NUMU + TRAINING BEAM-OFF** (odd-run half of `wcl1116-fg-beamoff` on the training side) |

## Checklist before Haiwang launches Round-2

1. **Upstream frozen.** Both training specs are `READY_FOR_FINAL_TRAINING`. The recovered target is recorded with its
   source, and the specs reviewed.
2. **Trained in the Round-2 domain.** Training ran on the training refresh (today's candidate: WCLocal2026Nov16-Aurora),
   not on aurora-r2. The refresh provenance
   (toolkit commit, DL vertex sha256, νμ / νe weight sha256) equals the Round-2 production configuration.
3. **Firewall log.** It shows only Aurora training samples (`wcl1116-aurora-*`). The beam-off odd-run half is used only
   through an approved exception written into the spec. No `wcl1116-fg-*` evaluation output is touched.
4. **Export and equivalence.** The exporter output and its equivalence-test report are attached, with zero decision flips.
5. **Deployment route.** Route A or B is chosen.
   - Route A: the new scorer is built with the XML and its sha256 compiled into the config. `single_photon_*_score`
     branches are added to `T_tagger`, the merge schema is rebuilt, and the new schema md5 is recorded.
   - Route B: the offline scorer version and its input mapping are frozen.
6. **Model order.**
   - SP other uses the **frozen νμ final model**.
   - SP numu, which is inherited, also reads `numu_score`. Decide whether it is retrained or its domain shift is accepted.
7. **Legacy controls.** The legacy XMLs are kept under their original names, for a legacy score beside the new one.
8. **Feeds the EAF handoff.** Everything above goes into `EAF_ROUND2_EVALUATION_HANDOFF.md`, so the EAF evaluation knows
   exactly which models produced the Round-2 scores.
