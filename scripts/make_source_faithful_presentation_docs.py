#!/usr/bin/env python
"""Renders the corrected presentation handoff documents from ONE slide specification (so the outline and the handoff cannot disagree). No analysis, no PPTX.

    python scripts/make_source_faithful_presentation_docs.py
Writes docs/presentation/NCDELTA_SOURCE_FAITHFUL_ROUND1_PRESENTATION_OUTLINE.md and docs/presentation/NCDELTA_SOURCE_FAITHFUL_PRESENTATION_HANDOFF.md.
All numbers in the text are checked against NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.json by tests/test_source_faithful_presentation_package.py.
"""
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; DOC = REPO / "docs" / "presentation"
A = "presentation_assets/ncdelta_source_faithful/"

# ---------------------------------------------------------------------------------------------------------------- main slides
MAIN = [
 dict(n=1, title="NC Δ → Nγ in SBND: a first look with the frozen, source-faithful Wire-Cell chain",
      purpose="Open immediately after the inclusive single-photon talk and say what is different here.",
      headline="An exclusive look at the NC-Delta radiative channel with the inherited single-photon chain, before any SBND-specific retraining.",
      numbers=[], asset="none (title slide)",
      notes="Nate has just shown the inclusive single-photon picture and several reconstruction issues that appear there. I'm going to zoom in on one specific process, NC-Delta to N gamma, where we have a large dedicated official signal sample. That lets us quantify how photon reconstruction, vertexing and the inherited BDTs behave separately in the exclusive 1gamma0p and 1gamma1p channels.",
      caveats="This is a characterisation, not a result: no optimisation, no retraining, no approved fiducial volume, no purity, no S/B.",
      notsay="Do not call it a measurement or a result; do not quote the inclusive efficiency next to ours."),
 dict(n=2, title="Exclusive NC-Δ channels: truth proton topology is not the Delta charge",
      purpose="Fix the vocabulary once so that no later slide is misread.",
      headline="The same 12,427 signal events can be split by Delta charge or by truth proton topology; these are different splits, and reco 1γ0p / 1γ1p are neither.",
      numbers=["12,427 official Gen2 signal events in the provisional TPC box", "truth 0p / 1p / ≥2p = 5,863 / 5,557 / 1,007 (post-FSI protons above 35 MeV)", "Delta0 → nγ / Delta+ → pγ = 6,846 / 5,581"],
      asset="table built from the numbers above (no figure); optionally a two-row diagram: Delta charge (top) and truth proton topology (bottom) as independent splits",
      notes="Delta zero decays to a neutron and a photon, Delta plus to a proton and a photon. But the label 0p, 1p, 2p-plus counts post-FSI protons above 35 MeV in the final state, so a Delta-zero event can still have truth protons from rescattering or secondary interactions, and a Delta-plus decay proton can be lost. The reconstructed 1γ0p and 1γ1p channels are a third thing: they count reconstructed proton objects.",
      caveats="35 MeV is a characterisation convention. Delta charge, proton origin and topology are entangled.",
      notsay="Do not equate Delta0 with 0p or Delta+ with 1p. Do not call truth 0p/1p the Delta decay nucleon."),
 dict(n=3, title="Scope: the inherited MicroBooNE chain on the official sample, as MicroBooNE defines it",
      purpose="State exactly what was run and what was not done.",
      headline="Unmodified production fg1 Wire-Cell reconstruction plus the frozen MicroBooNE-derived single-photon BDT chain, with the MicroBooNE score convention.",
      numbers=["chain: candidate → > 20 MeV shower → numu > 0.4 → other > 0.2 → ncpi0 > -0.05 → nue > -1.0 → n_20br1 = 1", "score = log10((1+v)/(1-v)), v = TMVA response; kine_pio_flag = 0 for the ncpi0 BDT", "candidate policy: any; truth proton threshold 35 MeV; truth region: provisional TPC box (12,427 events)"],
      asset="schematic of the chain (boxes with the five cuts), built from the numbers above",
      notes="Everything here is inherited and frozen: the reconstruction, the four BDTs and their thresholds. Nothing was tuned or retrained. The cuts are applied on the MicroBooNE log-odds score. The truth region and the proton threshold are conventions for characterisation, not approved analysis definitions. Nate's inclusive study uses the same or related Wire-Cell single-photon machinery with a different physics denominator and final selection, so the efficiencies are not comparable.",
      caveats="No approved fiducial volume; analysis-definition decisions on FV, proton threshold, included == 3 rows and candidate policy are open. Source-faithfulness was established by reading the MicroBooNE source and by internal reproduction checks, not by comparison with stored MicroBooNE scores (none are available).",
      notsay="Do not say the scorer was validated against MicroBooNE production scores. Do not compare with Nate's 4.51 %."),
 dict(n=4, title="The frozen baseline selects 6.7 % of official NC-Δ signal",
      purpose="Give the headline and the topology dependence.",
      headline="833 of 12,427 official signal events are selected: 6.70 % (68 % interval 6.48–6.94 %).",
      numbers=["833 / 12,427 = 6.70 % (68 % interval 6.48–6.94 %)", "truth 0p 6.36 %, truth 1p 7.49 %, truth ≥2p 4.37 % — ≥2p now has the lowest efficiency", "policy first: 795 = 6.40 %"],
      asset=A + "02_cutflow.png",
      notes="With the chain applied as MicroBooNE defines it, 6.7 percent of the official signal survives. By truth proton topology the efficiencies are 6.4, 7.5 and 4.4 percent for 0p, 1p and 2-plus; the 2-plus class is now the lowest. The natural NC-Delta population in the BNB CV is statistically compatible, with low statistics.",
      caveats="Provisional truth box, no analysis fiducial volume. Delta0/Delta+ efficiencies (5.76 / 7.87 %) are backup only because charge, topology and proton origin are entangled.",
      notsay="Do not show or quote 9.28 %, 1,153 or the old topology efficiencies as current. Do not call this the analysis efficiency."),
 dict(n=5, title="Most of the loss occurs in photon reconstruction and the inherited BDT stages",
      purpose="Show where the signal goes, stage by stage.",
      headline="About a third of the signal is lost before any BDT sees it; the inherited BDT stages account for most of the rest, and nue is now a real stage.",
      numbers=["cumulative: 12,427 → 12,426 (wc.valid) → 11,331 (candidate) → 8,080 (> 20 MeV shower) → 8,034 (BDT evaluable) → 4,943 (numu) → 2,717 (other) → 1,305 (ncpi0) → 893 (nue) → 833 (n_20br1 = final)",
               "exclusive first failure (of 12,427): candidate 8.8 %, shower 26.2 %, numu 24.9 %, other 17.9 %, ncpi0 11.3 %, nue 3.3 %, n_20br1 0.5 %", "numu failures = 26.7 % of the total loss (3,094 of 11,594)"],
      asset=A + "03_loss_budget.png (first-failure bars); " + A + "02_cutflow.png if both views are wanted",
      notes="The first failure is the first stage at which an event fails. Roughly 9 percent have no candidate and 26 percent have no usable photon shower of more than 20 MeV, so more than a third is lost before the BDTs. The numu stage fails 25 percent of the events, other 18, ncpi0 11, and the nue stage 3 percent. Most of these are reconstruction-state effects rather than a photon-energy threshold.",
      caveats="Exclusive first failure and cumulative survival differ by a documented 3-event bookkeeping difference at numu (+3) and ncpi0 (−3).",
      notsay="Do not say nue removes nothing. Do not use the old 26.9 %/29.8 % shares or the old first-failure numbers."),
 dict(n=6, title="The photon is often mis-typed, fragmented, or owned by a hadron-typed object",
      purpose="Show the reconstruction failure modes that precede the BDTs.",
      headline="Photon-reconstruction failures occur before the BDTs and are unchanged by the scorer correction.",
      numbers=["27.6 % of signal photons have a track-typed dominant object", "median ~3 pieces for a fragmented photon", "567 events with a good electron shower outside the main-vertex shower set (17.4 % of the shower-stage failures)", "29.6 % of the shower-stage failures are typed muon / pion / proton; 1.2 % are genuinely below 20 MeV"],
      asset=A + "04_photon_taxonomy.png", notes="Among the events that fail the shower stage, the photon is frequently reconstructed as a track, split into several pieces, or attached to a hadron-typed object. Only about one percent are genuinely below 20 MeV. These are reconstruction problems, and they sit upstream of every BDT.",
      caveats="Fractions are of the 11,331 candidate-stage events; association, not causation.", notsay="Do not claim a cause for the fragmentation; do not call these BDT failures."),
 dict(n=7, title="The inherited BDTs respond strongly to reconstruction state",
      purpose="Show that numu, other and ncpi0 follow the reconstructed object state.",
      headline="numu survival depends strongly on reconstructed shower compactness; other and ncpi0 follow vertex and pair-formation state.",
      numbers=["numu survival: total shower length < 20 cm 28.3 % vs ≥ 20 cm 72.8 %", "numu survival: < 5 segments 24.0 % vs ≥ 5 segments 72.3 %", "other survival given numu: truth 0p 46.8 % vs truth 1p 62.7 %", "ncpi0 survival given other: 48.0 %"],
      asset=A + "05_numu_compactness.png (corrected). Optional: " + A + "05b_other_vertex_class_survival.png (drawn with the as-run other cut: qualitative use only, quote no bar values)",
      notes="The numu BDT strongly separates compact, few-segment photon objects from extended ones: 28 percent of compact objects survive against 73 percent of extended ones. This is an association with reconstruction state. The fake-pi0 interpretation of ncpi0 and the multiplicity interpretation of n_20br1 remain valid qualitatively.",
      caveats="Association, not causation. Object-class splits and the attribution percentages were not recomputed and are not shown. No claim about training-domain mismatch.",
      notsay="Do not say the BDTs are wrong or mismatched; do not quote the old 29 % vs 74 %."),
 dict(n=8, title="The truth-0p vertex follows the photon; a reconstructed proton anchors the interaction",
      purpose="Explain why other follows vertex anchoring.",
      headline="Where a reconstructed proton exists the vertex sits on the interaction; where there is none it is displaced along the photon.",
      numbers=["median |V_reco − V_true|: truth 1p 0.87 cm vs truth 0p 11.30 cm (objects with a stored row: 818 of 833 selected events)", "other survival given numu: truth 0p 46.8 % vs truth 1p 62.7 %"],
      asset=A + "06_vertex_provenance.png", notes="For truth-1p events the vertex is within a centimetre of truth; for truth-0p events it is typically displaced by about eleven centimetres, along the photon. The other BDT survival follows this vertex anchoring. This motivates the updated deep-learning vertexing that Snehadri is developing.",
      caveats="Association, not causation; the reason the vertexing places the vertex along the photon in 0p events is still open. The vertex medians use the objects that still have a stored row.",
      notsay="Do not claim causality between vertex placement and the BDT response."),
 dict(n=9, title="The source-faithful nue stage is an efficiency-versus-background trade-off",
      purpose="Explain the biggest change from the corrected scorer.",
      headline="The source-faithful nue rejection costs substantial NC-Delta efficiency and removes essentially all of the previously selected intrinsic-nue CC background.",
      numbers=["signal: 1,305 events reach nue, 893 pass; 412 removed (survival 68.4 %; truth 0p 72.0 %, 1p 67.5 %, ≥2p 51.7 %)", "intrinsic nue-CC BNB-CV events selected: 175 (as-run, historical) → 1 (corrected); 174 of the 175 leave", "312 of the as-run selected signal events leave through nue"],
      asset=A + "12_nue_tradeoff.png",
      notes="The nue stage removes 412 signal events at its cumulative stage. But the same stage removes 174 of the 175 intrinsic-nue CC events that the earlier as-run chain selected, leaving one. So the nue BDT is a strong efficiency-versus-background trade-off, and an especially important target for SBND-specific retraining, which Xuyang is doing.",
      caveats="This is a trade-off to be evaluated, not a verdict on the BDT. Background counts are BNB-CV statistical, with no cosmic-only component. A retrained nue BDT must be checked on both signal efficiency and intrinsic-nue background.",
      notsay="Do not call nue 'bad' or 'overly aggressive'; do not say it removes no signal; do not predict what retraining will do."),
 dict(n=10, title="Reco 1γ0p and 1γ1p are not truth labels: proton reconstruction drives the migration",
      purpose="Show truth → reco topology migration and its reasons.",
      headline="The matching reco topology is selected for 91.7 % / 80.8 % / 63.6 % of truth 0p / 1p / ≥2p selected events; the rest migrate through proton inefficiency, mis-typing and merging.",
      numbers=["truth 0p → reco 0p / 1p / ≥2p: 342 / 30 / 1; truth 1p: 61 / 336 / 19; truth ≥2p: 5 / 11 / 28", "diagonal fractions 91.7 % / 80.8 % / 63.6 %; reco totals 1g0p 408, 1g1p 377, ≥2p 48", "proton typing efficiency above 35 MeV 46 %, at 200–300 MeV 67 %, above 500 MeV 22 %", "17 % of protons above 35 MeV have a row typed muon / pion / electron-shower; 65 % of merged truth-1p protons merge into the signal photon", "matched candidate (pre-BDT): truth 1p → reco 0p 883, truth 0p → reco 1p 468 / 319 by reason"],
      asset=A + "08_migration_matrix.png (left) and " + A + "07_proton_reco_vs_ke.png (right); optional " + A + "07b_migration_reasons.png (use its matched-candidate counts only)",
      notes="A reconstructed 1γ0p is not a truth 0p. Truth 1p events become reco 0p when the proton is mis-typed, merged into another object or has no row; truth 0p events become reco 1p when the photon is typed as a proton or a neutron-induced secondary proton is reconstructed. The 35 MeV threshold is not the dominant reason.",
      caveats="35 MeV truth convention; proton typing numbers are pre-BDT and unchanged; the old '→ final' counts of the migration-reason figure are as-run and must not be quoted.",
      notsay="Do not call reco 1γ0p/1γ1p truth; do not say the threshold dominates; do not use the old 425 / 471 / 39 diagonal."),
 dict(n=11, title="Once the right objects are reconstructed, the Delta observables work",
      purpose="Show that the Delta mass is usable for correctly reconstructed pairs.",
      headline="For selected, truth-matched Delta+ decay pairs the reconstructed mass is unbiased with a ~34 MeV half-width.",
      numbers=["N = 251 truth-matched decay pairs", "median(M_reco − M_true_decay) = −0.1 MeV; 68 % interval [−44.5, +23.4] MeV (half-width 34.0 MeV, RMS 62.8 MeV)"],
      asset=A + "09_delta_mass_residual.png",
      notes="When the photon and the decay proton are both correctly reconstructed and matched, the reconstructed Delta mass is centred on the truth within a fraction of an MeV with a 68 percent interval of about minus 44 to plus 23 MeV. This is a statement about correctly matched pairs, not about all selected events.",
      caveats="Restricted to selected objects with a stored row (events selected only under the corrected scorer have none); decay pairs are truth-defined; the photon-energy response number of the previous package was not recomputed and is not shown.",
      notsay="Do not show the old +2.8 MeV / [−44, +34] MeV headline for this selected subset."),
 dict(n=12, title="The surviving background is dominated by NC π0, outside-TPC and CC π0",
      purpose="Show the corrected background composition and the signal and background rates, without an S/B.",
      headline="282 selected non-signal BNB-CV events (150 / 93 / 39 in reco 1γ0p / 1γ1p / ≥2p); intrinsic nue-CC is now 1 event.",
      numbers=["282 = 150 / 93 / 39 (reco 1g0p / 1g1p / ≥2p); rates 552 / 342 / 143 per 1e20 POT (statistical only)", "categories: NC π0 116 (41.1 %), outside-TPC ν 62 (22.0 %), CC π0 60 (21.3 %), numu CC 14, other NC 13, cosmic/unmatched 13, ambiguous 3, nue CC 1",
               "1g0p: NC π0 56 (37 %), outside-TPC 53 (35 %), CC π0 20 (13 %); 1g1p: NC π0 46 (49 %), CC π0 24 (26 %), outside-TPC 9 (10 %)", "signal rate 29.3 per 1e20 POT in the provisional TPC box (14.4 / 13.3 / 1.7 for 1g0p / 1g1p / ≥2p)"],
      asset=A + "10_backgrounds.png and " + A + "11_rates.png",
      notes="After the source-faithful nue rejection the surviving beam-neutrino background is mostly NC pi-zero, neutrino interactions outside the TPC box, and CC pi-zero. The signal rate and the background rate are shown side by side but their ratio is not an S over B: the volumes are not common and there is no beam-off normalisation.",
      caveats="No cosmic-only component, no nue CC special-sample rate, statistical errors only; signal is restricted to the provisional TPC box while the background covers the whole generated volume.",
      notsay="Do not call the ratio an S/B, purity or significance; do not use 635 = 310/230/95 or 'nue CC 37 % of 1g1p'."),
 dict(n=13, title="Summary",
      purpose="Close the physics content.",
      headline="The corrected first look gives 6.70 %; losses start in photon reconstruction; the inherited BDTs follow reconstruction state; nue is a real efficiency/background trade-off.",
      numbers=["833 / 12,427 = 6.70 %", "truth 0p / 1p / ≥2p 6.36 / 7.49 / 4.37 %", "282 non-signal BNB-CV events; signal rate 29.3 per 1e20 POT; not an S/B"],
      asset="text slide (4–5 bullets)", notes="Take-homes: the efficiency is 6.7 percent; the photon is often mis-typed, fragmented or mis-attached before any BDT; numu follows shower compactness and other follows vertex anchoring; the source-faithful nue stage trades 412 signal events for removing nearly all intrinsic-nue background; reco topologies are not truth labels; the Delta observables are usable when the right objects are found.",
      caveats="Everything is a characterisation on a provisional denominator.", notsay="Do not state a purity, S/B or an optimised working point."),
 dict(n=14, title="Next: SBND-specific retraining and Round-2 evaluation",
      purpose="State the actual plan without claiming unfinished work.",
      headline="Round 2 retrains and re-evaluates against the source-faithful Round-1 baseline of 6.70 %.",
      numbers=["Round-2 sequence: (1) freeze updated DL vertexing; (2) freeze Xuyang's upstream numu / nue configuration; (3) training-only Aurora refresh; (4) train and freeze the SP models; (5) Haiwang regenerates the official Round-2 CAFs; (6) independent EAF evaluation against R1-source-faithful", "Snehadri: updated DL vertexing is being established / will be frozen for Round 2", "SP ncpi0: original target definition recovered from the Yandel thesis; ready for development training if the frozen-XML compatibility check passes (the structural check agrees with the thesis); the final model waits for the Round-2 training refresh", "SP other: original target definition recovered; needs an additional training cosmic / off-beam component that is not currently in the Aurora training samples; the final model waits for Xuyang's frozen numu chain and the Round-2 training refresh", "nothing is trained yet", "firewall: Aurora = training / development; official FermiGrid fg1 = evaluation", "compare against R1-source-faithful = 6.70 % (never the historical as-run 9.28 %)"],
      asset="text slide (plan diagram optional)",
      notes="The corrected Round-1 result is the reference. The Round-2 order is: freeze the updated deep-learning vertexing, freeze Xuyang's upstream numu and nue configuration, refresh the training sample on Aurora, train and freeze the single-photon models, have Haiwang regenerate the official Round-2 CAFs, and then evaluate independently on EAF against the source-faithful Round-1 baseline. For the ncpi0 and other BDTs the original target definitions have been recovered from Erin Yandel's thesis; nothing has been trained. Training uses Aurora; the official FermiGrid fg1 samples are for evaluation only.",
      caveats="Do not imply that the ncpi0 / other training has begun or finished, or that the DL vertexing is already frozen. The ncpi0 / other target definitions were recovered from Erin Yandel's thesis; other additionally needs a cosmic / off-beam training component that is not yet available. Blockers G (beam-off normalisation), H (flash-time reference) and J (same-event SPINE output) remain.",
      notsay="Do not claim any Round-2 result, or that retraining will recover the nue-CC rejection or the efficiency."),
]

BACKUP = [
 ("B1", "Legacy scorer correction", "Historical as-run 1,153 / 12,427 = 9.28 %; source-faithful 833 / 12,427 = 6.70 %. Decomposition: old 1,153; score convention only 831 (6.69 %); kine_pio_flag only 1,161; full 833. score = log10((1+v)/(1-v)), v = TMVA response; cuts at the frozen numbers (response-space equivalents 0.4305 / 0.2263 / −0.0575 / −0.8182). The change is almost entirely the score convention; the kine_pio_flag override is small. The as-run nue cut (> −1.0 on v) was vacuous.", A + "backup/B01_scorer_correction.png", "Mention only on request or if the audience saw the earlier numbers."),
 ("B2", "Complete cutflow", "Cumulative and first-failure table for all stages (numbers file, slide 5).", A + "backup/B02_cutflow_loss_budget_combined.png", "Include the +3 / −3 bookkeeping note."),
 ("B3", "Corrected differential efficiency", "Efficiency rises with photon energy (1.8 % in the 50–100 MeV bin to 9.0 % at 400–500 MeV) and is lower for backward photons (2.8 % backward-most vs 8.4 % forward-most cos θ); 3.4 % in the last 50 cm in z; interior diagnostic box 8.4 % vs 5.1 % outside (not a proposed FV).", A + "backup/B03a_eff_vs_photon_energy.png, B03b_eff_vs_photon_angle.png, B03c_vertex_z.png", "Descriptive; energy and angle are correlated."),
 ("B4", "Natural NC-Delta in the BNB CV", "8 / 117 = 6.8 % vs the dedicated sample's 6.70 %, p = 0.85; the natural population remains statistically compatible; statistics are limited.", A + "14_natural_cv.png (+ backup/B04_natural_cv_crosscheck_differential.png)", "Not a validation of every detail of the dedicated sample."),
 ("B5", "Photon taxonomy detail", "Taxonomy vs photon energy and photon type vs energy (before the BDTs; unchanged).", A + "backup/B08_photon_taxonomy_vs_energy.png, B09_photon_type_vs_energy.png", "Association, not causation."),
 ("B6", "numu compactness and attribution", "SHAP families are a property of the frozen XML (unchanged); quote only the corrected survival numbers (28.3 / 72.8 %; 24.0 / 72.3 %).", A + "backup/B10_numu_shap_families.png", "Do not quote survival numbers printed in the figure caption of the older package."),
 ("B7", "ncpi0 and n_20br1", "Qualitative: the ncpi0 stage rejects events where a shower pair is formed for a single photon (fake-pair/fragmentation); n_20br1 follows photon multiplicity/fragmentation. Corrected stage numbers: ncpi0 survival 48.0 % given other; n_20br1 first failure 0.5 %.", "text slide (no figure; the older pair-origin percentages are NOT recomputed)", "Do not show the old 94.2 % / 88.0 %."),
 ("B8", "Shower attachment (567 events)", "Parent of the 567 shower-not-in-main-vertex-set events: true signal proton 62 %, mis-typed photon piece 15 %, pi0 pair 6 % (before the BDTs; unchanged).", A + "backup/B11_shower_attachment_parents.png", "Ownership, not vertexing."),
 ("B9", "Proton PID failure modes", "182 of 362 protons above 500 MeV mistyped; mistyped protons 55–66 cm vs 122 cm; low-KE protons merge into the signal photon (65 %).", A + "backup/B12_proton_pid_high_ke.png, B13_proton_low_ke_merge.png", "Pre-BDT; unchanged."),
 ("B10", "Proton origin and Delta charge", "Corrected efficiencies only: Delta0 5.76 %, Delta+ 7.87 % (entangled with topology and proton origin). The decay-vs-FSI percentage-point differences of the older package were not recomputed and must not be shown.", "none (table)", "State the entanglement."),
 ("B11", "Detailed background composition", "Counts by channel and category from the corrected composition table (numbers file, slide 12).", A + "10_backgrounds.png", "No cosmic-only component."),
 ("B12", "Analysis-definition caveats", "Fiducial volume, 35 vs 50 MeV proton threshold, included == 3 rows and candidate policy remain OPEN decisions; decision-support numbers of the older package start from the superseded 9.28 % and were not recomputed — show no numbers.", "none (text)", "No option is preferred for its efficiency."),
 ("B13", "SPINE harmonisation", "Truth-side NC-Delta definition harmonised on the same events; frozen Wire-Cell efficiency on the harmonised denominators: 685 / 8,668 = 7.90 % (harmonised 0p50 7.18 %, Np50 8.79 %). A denominator-definition effect only; no same-event SPINE reconstruction output exists yet.", "none (table)", "Not a Wire-Cell-vs-SPINE comparison."),
 ("B14", "Common issues with the inclusive single-photon study", "Shared conclusions: photon fragmentation, vertex placement, BDT retraining, flash association as an inclusive-study issue to test, and the new vertexing as a shared development direction. Same/related Wire-Cell machinery, different denominator and final selection.", "none (text)", "Do not compare efficiencies; do not show a numerical 'consistency check'."),
 ("B15", "Roadmap and blockers", "Done / largely done / open decisions D, E, F; blocked G (beam-off normalisation), H (flash-time reference), J (same-event SPINE output).", "table from the baseline document section 17", ""),
 ("B16", "Sample provenance and conversion definition", "fg1 chain pin, official Gen2 sample 13,773 events (12,427 in the TPC box); true conversion distance = Geant4 end point of the primary photon (11,512 events), the reco gap is a different quantity (Spearman 0.975 for detached showers).", A + "backup/B06_official_sample_census.png, B07_conversion_distance.png", "Truth / geometry only; unchanged."),
]

QA = [
 ("Why did the efficiency change from the earlier as-run 9.28 % to 6.70 %?", "The first-look scorer applied the frozen cuts to the bare TMVA response v, while MicroBooNE applies them to log10((1+v)/(1-v)). On v the nue cut (> −1.0) was vacuous and the numu/other cuts were looser. With the real convention the selected count is 833, not 1,153. The kine_pio_flag override changes it by only +8 events."),
 ("Was the physics analysis wrong?", "A scorer implementation error was found by a source audit and corrected. The reconstruction, truth and mechanism studies that do not depend on the BDT decision are unchanged, and the mechanism conclusions (photon fragmentation/mis-typing, numu vs compactness, other vs vertex anchoring, proton migration) survive with corrected numbers. The efficiency, topology ordering, nue stage and background composition did change."),
 ("What exactly was wrong with the scorer?", "Two things: (1) the score is log10((1+v)/(1-v)) with v the TMVA response, and the first look cut on v; (2) MicroBooNE forces kine_pio_flag = 0 in the single-photon ncpi0 BDT input, and the first look fed the real value. The first dominates; the second is small."),
 ("Why does nue now remove so much signal?", "Because it is now a real cut: 412 of the 1,305 events reaching it are removed (68.4 % survive; 51.7 % for ≥2p). It is the stage that removes 174 of the 175 intrinsic-nue CC events the as-run chain selected, so it is a trade-off, not simply an inefficiency."),
 ("Does nue retraining risk bringing the intrinsic-nue background back?", "It can, in principle: a retrained nue BDT has to be judged on both signal efficiency and intrinsic-nue background on the evaluation sample. The Round-2 contract compares both against the source-faithful baseline; we do not predict the outcome."),
 ("Why retrain the BDTs rather than simply loosen the thresholds?", "A threshold scan needs a defined denominator and a normalised background, which are still open (decisions D/E/F and blockers G/H). The reconstruction problems (fragmentation, vertex placement) change the inputs that the BDTs see; retraining on SBND simulation is a separate development step, with the original ncpi0/other target definitions recovered from the Yandel thesis (ncpi0 ready for development training if the frozen-XML check passes; other still needs a cosmic / off-beam training component); nothing is trained yet. We make no claim yet that the inherited BDTs are mismatched; the Round-2 evaluation will test that."),
 ("Why are the 0p and 1p efficiencies different?", "6.36 % vs 7.49 %: descriptively, other survival given numu is 46.8 % for truth 0p and 62.7 % for truth 1p, which is associated with vertex anchoring by a reconstructed proton. This is association, not causation."),
 ("Why can Delta0 have truth protons?", "Truth topology counts post-FSI protons above 35 MeV; rescattering and secondary interactions can produce them in Delta0 events, and a Delta+ decay proton can be lost. Delta charge and truth topology are different splits."),
 ("How do fragmentation and vertexing affect the BDTs?", "numu survival is 28.3 % for compact photon objects vs 72.8 % for extended ones, and other survival follows vertex anchoring (46.8 % vs 62.7 %). Both are associations with reconstruction state, which is why the vertex and reconstruction updates come first."),
 ("What will change in Round 2?", "New reconstruction/models: Xuyang's SBND nue and numu retraining, Snehadri's updated DL vertexing (being established, to be frozen for Round 2), Avinay's SP ncpi0/other retraining (target definitions recovered, nothing trained yet), and Haiwang regenerating the CAFs once everything is frozen. Evaluation is against the source-faithful Round-1 baseline (6.70 %)."),
 ("Which samples are used for training and which for evaluation?", "Aurora samples are for training/development; the official FermiGrid fg1 samples, including the official Gen2 NC-Delta sample, are for evaluation only."),
 ("Why no purity or S/B yet?", "The signal is restricted to the provisional TPC box while the background covers the whole generated volume, there is no beam-off normalisation (G) and no flash-time reference (H), and the cosmic-only component is absent."),
 ("How does this compare with Nate's inclusive study?", "It uses the same or related Wire-Cell single-photon machinery but a different physics denominator and final selection, so the efficiencies are not comparable. The shared conclusions are photon fragmentation, vertex placement, BDT retraining, flash association as an issue to test, and new vertexing."),
 ("Is the SPINE comparison available yet?", "No. The truth-side definition is harmonised (Wire-Cell efficiency on the harmonised denominator is 7.90 %), but there is no same-event SPINE reconstruction output yet, so no Wire-Cell-versus-SPINE comparison can be shown."),
 ("Was the corrected scorer validated against stored MicroBooNE scores?", "No such stored scores or live TMVA exist on EAF. It was established by reading the MicroBooNE source and by internal checks (hand-computed algebra; exact reproduction of the as-run scores from stored inputs; exact reproduction of every as-run product with the as-run mode). Exact reproduction of production scores is not claimed."),
]

DONT = ["do not use 9.28 % (or 1,153) as the current efficiency; it is HISTORICAL AS-RUN and appears only on the scorer-correction backup slide",
        "do not use 635 (= 310 / 230 / 95) as the current selected BNB background; the current value is 282 = 150 / 93 / 39",
        "do not call 29.3 per 1e20 POT divided by any background rate an S/B, a purity or a significance",
        "do not equate Delta0 with 0p or Delta+ with 1p",
        "do not call truth 0p/1p the Delta decay nucleon",
        "do not claim BDT retraining is complete (nothing is retrained in Round 1; Avinay's ncpi0/other retraining has not started)",
        "do not claim causality from vertex/proton correlations; say 'associated with'",
        "do not compare Nate's 4.51 % directly with 6.70 %, and do not show a numerical NC-Delta consistency check against his study",
        "do not invent corrected values for anything marked REVIEW / DO NOT USE or DROP FROM PRESENTATION in the numbers file",
        "do not claim the source-faithful scorer was validated against stored MicroBooNE scores; it was established by source reading plus internal reproduction checks",
        "do not describe nue as 'removing nothing' or as simply 'bad'; it is an efficiency/background trade-off",
        "do not show the old 425 / 471 / 39 matrix, the old +2.8 MeV Delta-mass headline, 13 / 117, 40.6 per 1e20 or 'nue CC 17 % / 37 %' as current"]


def slide_block(s, full=True):
    L = [f"### Slide {s['n']}: {s['title']}", "", f"- **Purpose:** {s['purpose']}", f"- **Headline statement:** {s['headline']}"]
    if s["numbers"]:
        L.append("- **Exact numbers to show:**"); L += [f"  - {x}" for x in s["numbers"]]
    else:
        L.append("- **Exact numbers to show:** none")
    L.append(f"- **Recommended graphic:** {s['asset']}")
    L.append(f"- **Speaker notes (30–60 s):** {s['notes']}")
    L.append(f"- **Caveat to keep visible:** {s['caveats']}")
    L.append(f"- **What NOT to say:** {s['notsay']}")
    return "\n".join(L) + "\n"


BANNER = ("> **Authoritative corrected package.** Baseline: source-faithful Round-1, 833 / 12,427 = 6.70 % (branch `analysis/ncdelta-source-faithful-legacy-scorer-20261117`, commit `daf95442515b601eecda41c6c586931a5ae38c54`). "
          "The earlier package (`NCDELTA_BASELINE_PRESENTATION_OUTLINE.md`, 9.28 %) is HISTORICAL AS-RUN.\n")

# ---------------------------------------------------------------------------------------------------------------- outline
out = ["# NC-Delta → Nγ first look: corrected presentation outline (source-faithful Round-1)", "", BANNER,
       "Slide-by-slide handoff for the presentation-building session. 14 main slides (about 14 minutes) plus backup. Numbers: `NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.md/.json`; assets: `NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_ASSETS.csv` and `presentation_assets/ncdelta_source_faithful/`. "
       "Differences from the earlier outline: the headline is 6.70 %; the first-failure story gains a real nue stage (own slide, slide 9); the migration matrix, backgrounds, Delta mass, rates and natural-CV numbers are corrected; the final slide carries the Round-2 plan; the earlier optional slides (differential efficiency, natural CV, SPINE) are backup.", "", "## Main slides", ""]
out += [slide_block(s) for s in MAIN]
out += ["## Backup slides", "", "| id | title | content | asset | note |", "|---|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in BACKUP]
out += ["", "## Short version (8 slides, if time is cut)", "", "Keep 1, 2, 4, 5, 7 (numu line only), 9, 12, 14; fold 3 into 1, 6 into 5, 8 into 7, 10 and 11 into backup, 13 into 14.", ""]
(DOC / "NCDELTA_SOURCE_FAITHFUL_ROUND1_PRESENTATION_OUTLINE.md").write_text("\n".join(out))

# ---------------------------------------------------------------------------------------------------------------- handoff
H = ["# Handoff for the presentation Claude: NC-Delta → Nγ first look (corrected, source-faithful Round-1)", "", BANNER,
     "This document is self-contained: you do not need the analysis repository. It tells you what the talk is, what every term means, which numbers are current, which are forbidden, and what to put on each slide. "
     "Numbers are quoted exactly as they appear in the machine-readable file `NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.json`; figures are in `presentation_assets/ncdelta_source_faithful/` (see `NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_ASSETS.csv`).", "",
     "## 1. Purpose of the talk", "",
     "Avinay presents a first-look characterisation of the exclusive NC-Delta radiative channel (Δ → Nγ, one photon with zero or one reconstructed proton) in SBND. It runs the unmodified production Wire-Cell reconstruction and the frozen MicroBooNE-derived single-photon BDT chain on the official Gen2 dedicated NC-Delta signal sample, and asks where the signal is lost, why, and what that means for SBND-specific retraining. The talk is given right after Nate's inclusive single-photon talk. It is a characterisation, not a result.", "",
     "## 2. Critical terminology", "",
     "- **Delta0 → n γ** and **Delta+ → p γ**: the Delta charge state and the nucleon from the decay.",
     "- **truth 0p / 1p / ≥2p**: the number of POST-FSI final-state protons above 35 MeV in the truth record (a convention). It is not the decay nucleon.",
     "- Therefore **Delta charge ≠ truth proton topology**: a Delta0 event can have truth protons (rescattering, secondary interactions) and a Delta+ event can have none above threshold.",
     "- **reco 1γ0p / 1γ1p / ≥2p**: counts of reconstructed proton objects in the selected event. They are **not truth labels**; events migrate between truth and reco topology.",
     "- **v and score**: v is the TMVA BDT response; the cut variable is score = log10((1+v)/(1−v)).",
     "- **first failure (exclusive)** versus **cumulative survival**: the first stage an event fails versus events surviving all stages up to a given stage.",
     "- **as-run / historical**: the earlier implementation that cut on the bare response; superseded. **source-faithful**: the MicroBooNE convention; current.", "",
     "## 3. Analysis scope", "",
     "- Inherited, frozen MicroBooNE single-photon chain, applied with the MicroBooNE score convention (source-faithful): candidate → > 20 MeV shower → numu > 0.4 → other > 0.2 → ncpi0 > −0.05 → nue > −1.0 → n_20br1 = 1; kine_pio_flag = 0 in the ncpi0 input.",
     "- Official Gen2 dedicated NC-Delta sample (fg1-compatible Wire-Cell production); provisional truth TPC box of 12,427 events (|x|, |y| < 200 cm, 0 < z < 500 cm); candidate policy `any`; 35 MeV truth-proton convention.",
     "- No approved fiducial volume; no optimisation or retraining in Round 1; no final purity, S/B or significance.", "",
     "## 4. Corrected headline", "",
     "**833 / 12,427 = 6.70 %** (68 % interval 6.48–6.94 %); truth 0p 6.36 %, 1p 7.49 %, ≥2p 4.37 % (≥2p now lowest). The earlier **9.28 % (1,153 / 12,427)** came from applying the cuts to the bare TMVA response; it is HISTORICAL AS-RUN, superseded, and may appear only on the scorer-correction backup slide, labelled as such. The change is almost entirely the score convention (score-convention-only gives 831; kine_pio_flag-only gives 1,161; full source-faithful gives 833).", "",
     "## 5. Main slides", ""]
H += [slide_block(s) for s in MAIN]
H += ["## 6. Backup slides", ""]
for a, b, c, d, e in BACKUP:
    H += [f"### {a}: {b}", "", f"{c}", "", f"- Graphic: {d}", f"- Note: {e}" if e else "- Note: -", ""]
H += ["## 7. Questions Avinay should be ready for", ""]
for q, a in QA:
    H += [f"**Q: {q}**", "", f"A: {a}", ""]
H += ["## 8. Transition from Nate", "",
      "\"Nate has just shown the inclusive single-photon picture and several reconstruction issues that appear there. I'm going to zoom in on one specific process, NC-Delta to N gamma, where we have a large dedicated official signal sample. That lets us quantify how photon reconstruction, vertexing and the inherited BDTs behave separately in the exclusive 1gamma0p and 1gamma1p channels.\"", "",
      "Scope note to say or put on slide 3: same/related Wire-Cell single-photon reconstruction machinery, different physics denominator and final selection; the efficiencies are not comparable. Shared conclusions to name: photon fragmentation, vertex placement, BDT retraining, flash association as an inclusive-study issue to test, and new vertexing as a shared development direction.", "",
      "## 9. Round-2 plan", "",
      "- Central Round-2 sequence: (1) freeze the updated DL vertexing; (2) freeze Xuyang's upstream numu / nue configuration; (3) training-only Aurora refresh; (4) train and freeze the SP models; (5) Haiwang regenerates the official Round-2 CAFs; (6) independent EAF evaluation against R1-source-faithful.",
      "- Who: **Snehadri** – updated DL vertexing is being established / will be frozen for Round 2; **Xuyang** – SBND retraining of the upstream nue and numu BDTs; **Avinay** – SP ncpi0 and other models; **Haiwang** – regenerate the Round-2 CAFs once reconstruction and models are frozen.",
      "- SP ncpi0: the original target definition was recovered from Erin Yandel's 2024 thesis; it is ready for development training if the frozen-XML compatibility check passes (the structural check agrees with the thesis); the final model must still wait for the Round-2 training refresh. SP other: the original target definition was recovered; it needs an additional training cosmic / off-beam component that is not currently available in the Aurora training samples; the final model must also wait for Xuyang's frozen numu chain and the Round-2 training refresh. **Neither BDT has been trained.**",
      "- Firewall: **Aurora = training/development; official FermiGrid/fg1 = evaluation.** The official Gen2 NC-Delta sample is never a training input.",
      "- Evaluation: Round 2 is compared with **R1-source-faithful = 6.70 %**, not the historical 9.28 %. Three reference points are always kept apart: R1-as-run (diagnostic only), R1-source-faithful (the baseline), Round 2 (the thing under test).", "",
      "## 10. Things the presentation Claude must NOT do", ""] + [f"- {x}" for x in DONT]
H += ["", "## 11. Status vocabulary in the numbers file", "",
      "AUTHORITATIVE CORRECTED = use. RECONSTRUCTION-ONLY UNCHANGED = use (defined before or independent of the BDT selection). HISTORICAL AS-RUN = only on the scorer-correction backup slide, labelled. REVIEW / DO NOT USE = never show. The second table of the numbers file classifies every number flagged REVIEW in the earlier package (SAFE UNCHANGED, CORRECTED VALUE EXISTS, NEEDS RECOMPUTE, DROP FROM PRESENTATION); show only the first two.", ""]
(DOC / "NCDELTA_SOURCE_FAITHFUL_PRESENTATION_HANDOFF.md").write_text("\n".join(H))
print("outline/handoff written")
