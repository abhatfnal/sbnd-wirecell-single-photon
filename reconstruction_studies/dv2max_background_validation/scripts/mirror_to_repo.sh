#!/usr/bin/env bash
# Mirror the DV2-MAX x SP background-validation deliverables into the single-photon repo
# (files only; NO git add/commit/push).  The repo target is the one location outside W this study writes to.
set -euo pipefail
W=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102
M=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/repos/sbnd-wirecell-single-photon/reconstruction_studies/dv2max_background_validation
mkdir -p "$M"/{docs/figures,tables,scripts/analysis,inputs}
cp "$W"/docs/DV2MAX_SINGLEPHOTON_BACKGROUND_VALIDATION.md "$W"/docs/BACKGROUND_INPUT_INVENTORY.md \
   "$W"/docs/config_semantic_diff.txt "$M"/docs/
cp "$W"/docs/figures/*.png "$M"/docs/figures/
for t in background_input_inventory build_provenance control_validation \
         numucc_cutflow ncpi0_cutflow numucc_score_migration ncpi0_score_migration \
         numucc_access_changes ncpi0_access_changes a5_background_comparison fix2_background_comparison \
         newly_selected_backgrounds backgrounds_rejected_by_dv2 signal_background_summary \
         vertex_comparison bdt_input_shift bdt_input_shift_crosssample reproducibility_rerun; do
    cp "$W/tables/$t.csv" "$M/tables/"
done
cp "$W"/tables/summary.json "$W"/tables/numucc_summary.json "$W"/tables/ncpi0_summary.json "$M"/tables/
cp "$W"/inputs/numucc_events.csv "$W"/inputs/ncpi0_events.csv "$W"/inputs/sentinels.csv "$M"/inputs/
cp "$W"/scripts/*.sh "$W"/scripts/*.pbs "$W"/scripts/*.py "$W"/scripts/joblist_*.txt "$M"/scripts/
cp "$W"/scripts/analysis/*.py "$M"/scripts/analysis/
cp "$W"/scratch/infra_pids_limit_201013/README.md "$M"/docs/INFRA_INCIDENT_201013_README.md
( cd "$M" && find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum ) > "$M/MANIFEST.sha256"
echo "mirrored to $M ($(find "$M" -type f | wc -l) files); not committed"
