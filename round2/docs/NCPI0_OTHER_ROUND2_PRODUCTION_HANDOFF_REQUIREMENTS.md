# Round-2 production handoff: what Haiwang receives for each single-photon model

Date: 2026-11-17. Status: **contract only. No final model exists.** After the thesis audit
(`YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`), ncpi0 is ready for development training and other needs an
in-time-cosmic sample. Neither is ready for final training. SP numu is proposed to join Round 2 under the same contract
(`SP_BDT_ROUND2_FREEZE_ORDER.md` §4; spec `single_photon_numu_training_spec` v0.1.0). A model is handed over only when every field below is filled.

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
| 5 | training spec version | `single_photon_ncpi0_training_spec` ≥ v1.0.0 with status `READY_FOR_FINAL_TRAINING` (today v0.2.0 `READY_FOR_DEVELOPMENT_TRAINING`) | `single_photon_other_training_spec` ≥ v1.0.0 (today v0.2.0 `READY_ONLY_AFTER_ADDITIONAL_TRAINING_SAMPLE`) |
| 6 | ordered feature list | 45 names, `round2/config/features/single_photon_ncpi0_inputs_v0.json` (sha256 `5882391f…`), or its successor if inputs change | 146 names, `…_other_inputs_v0.json` (sha256 `0c3d3083…`) |
| 7 | score direction | higher = more single-photon-like; keep `score > threshold` | same |
| 8 | operating threshold | in **log10-odds**, chosen on the Aurora validation fold only. Never tuned on official samples. Legacy control cut −0.05 | same; legacy 0.2 |
| 9 | default / missing semantics | inputs float32; scored only when `shw_sp_filled == 1` and every input is finite, otherwise sentinel −20 (MicroBooNE's initial value; proposal to confirm); `kine_pio_flag` policy as in the spec; `reco` inputs read as stored | same; `reco_nuvtxY` ← `T_kine.kine_nu_y_corr` |
| 10 | upstream-model dependencies | the 15 νe level-1 TMVA models (`uboone/weights/{br3_3,…,tro_5}_BDT.weights.xml`, shipped) | `numu_tagger1/2.weights.xml`, `cos_tagger_10.weights.xml` (shipped) and **Xuyang's frozen νμ final model** (file + sha256) |
| 11 | vertex / reconstruction version | toolkit commit + DL vertex checkpoint sha256 of the Aurora training refresh; must equal Round-2 production | same |
| 12 | training sample manifest | refresh lists + `round2/manifests/<refresh>/manifest_*.{json,tsv.gz}` (path, size, mtime, list sha256); official samples absent (firewall log) | same |
| 13 | validation summary | Aurora test fold, per sample: AUC, efficiency / rejection at the threshold, per truth category, overtraining (train / validation / test), score distributions, feature importance. No official-sample numbers | same, plus per background category (cosmic-matched, out-of-volume) |
| 14 | deployment format | TMVA BDT XML, `BoostType=Grad`, `NTransformations=0`, variables in feature-list order, via the validated exporter; native JSON beside it | same |
| 15 | scorer-equivalence test result | `SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md` §4: training ↔ XML within 1e-5 with **zero decision flips**; Python ↔ toolkit bit-identical; order and missing-value guards | same |
| 16 | expected Wire-Cell config key / path | route A: `single_photon_ncpi0_xml = 'sbnd/weights/single_photon/single_photon_ncpi0_bdt_sbnd_round2_v1.xml'`, resolved by `wc.resolve`. Route B: offline score table keyed `(file_id, run, subrun, event, cand)` | `single_photon_other_xml = …_other_bdt_sbnd_round2_v1.xml` |
| 17 | legacy control model path | `uboone/weights/single_photon_ncpi0_bdt_final.xml`, sha256 `983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3`. **Not in wire-cell-data today**; add it from the reference bundle if a legacy score is wanted in production | `uboone/weights/single_photon_other_bdt_final.xml`, sha256 `8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16`, same remark |
| 18 | date / frozen status | to be filled at freeze; today **not frozen (development only; EAF XML check and Round-2 freezes pending)** | **not frozen (in-time-cosmic sample missing; `numu_score` input pending Xuyang)** |

## Checklist before Haiwang launches Round-2

1. **Upstream frozen.** Both training specs are `READY_FOR_FINAL_TRAINING`. The recovered target is recorded with its
   source, and the specs reviewed.
2. **Trained in the Round-2 domain.** Training ran on the training refresh, not on aurora-r2. The refresh provenance
   (toolkit commit, DL vertex sha256, νμ / νe weight sha256) equals the Round-2 production configuration.
3. **Firewall log.** It shows only Aurora development samples. The fg1 beam-off train half is not used unless an
   approved exception was written into the spec.
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
