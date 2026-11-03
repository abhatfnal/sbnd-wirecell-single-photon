#!/usr/bin/env bash
# Mirror the DV2-MAX x SP59 deliverables into the single-photon repo (files only; NO git add/commit/push).
set -euo pipefail
W=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102
M=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/repos/sbnd-wirecell-single-photon/reconstruction_studies/dv2max_singlephoton59
mkdir -p "$M"/{docs,tables,source,scripts/analysis,config/armO,config/armD,config/compiled}
cp "$W"/docs/DV2MAX_SINGLEPHOTON59_REPORT.md "$W"/docs/INTEGRATION_MAP.md "$W"/docs/config_semantic_diff.txt "$M"/docs/
for t in single_photon_patch_map build_provenance diagnostic_control_original dv2_event_diagnostics \
         event59_original_vs_dv2 cutflow_original_vs_dv2 graph7_dv2_outcome fix2_under_dv2 remaining19_under_dv2 \
         dv2_access_changes; do
    cp "$W/tables/$t.csv" "$M/tables/"
done
cp "$W"/tables/summary.json "$M"/tables/
cp "$W"/source/PATCH.diff "$M"/source/
cp "$W"/scripts/*.sh "$W"/scripts/*.pbs "$W"/scripts/*.py "$W"/scripts/*.cxx "$M"/scripts/
cp "$W"/scripts/analysis/*.py "$M"/scripts/analysis/
cp "$W"/config/armO/pr-operating-point.jsonnet "$M"/config/armO/
cp "$W"/config/armD/pr-operating-point.jsonnet "$M"/config/armD/
cp "$W"/config/compiled/*.leaves.txt "$W"/config/compiled/compiled_md5.txt "$M"/config/compiled/
( cd "$M" && find . -type f | sort | xargs sha256sum ) > "$M/MANIFEST.sha256"
echo "mirrored to $M ($(find "$M" -type f | wc -l) files); not committed"
