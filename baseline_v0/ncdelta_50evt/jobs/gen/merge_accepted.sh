#!/bin/bash
# Merge all accepted NC Delta gen outputs into a single artROOT file.
#
# Run this AFTER all 10 gen batches have completed successfully.
# Checks each batch for expected output before merging.
#
# Usage: bash merge_accepted.sh [--dry-run]
#
# Output: ncdelta_50evt/gen/ncdelta_gen_merged.root

set -euo pipefail

BASEDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0
GENDIR="$BASEDIR/ncdelta_50evt/gen"
LOGDIR="$BASEDIR/ncdelta_50evt/logs"

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
    echo "[DRY RUN]"
fi

MERGED="$GENDIR/ncdelta_gen_merged.root"

echo "=== Merge NC Delta gen batches ==="
echo "Scanning batch outputs..."

INPUTS=()
TOTAL_ACCEPTED=0

for NN in 01 02 03 04 05 06 07 08 09 10 11 12; do
    BATCHFILE="$GENDIR/batch_${NN}/ncdelta_gen_batch_${NN}.root"
    PROV="$GENDIR/batch_${NN}/provenance.txt"

    if [ ! -f "$BATCHFILE" ]; then
        echo "  MISSING: batch $NN — $BATCHFILE"
        continue
    fi

    FSIZ=$(stat -c%s "$BATCHFILE" 2>/dev/null || echo 0)
    if [ "$FSIZ" -lt 1000 ]; then
        echo "  EMPTY: batch $NN — $BATCHFILE ($FSIZ bytes)"
        continue
    fi

    # Extract accepted count from provenance
    ACC="unknown"
    if [ -f "$PROV" ]; then
        ACC=$(grep "accepted_events:" "$PROV" | awk '{print $2}' | tail -1 || echo "unknown")
    fi
    echo "  OK: batch $NN — $BATCHFILE ($FSIZ bytes, accepted=$ACC)"
    INPUTS+=("$BATCHFILE")
    if [[ "$ACC" =~ ^[0-9]+$ ]]; then
        TOTAL_ACCEPTED=$((TOTAL_ACCEPTED + ACC))
    fi
done

echo ""
echo "Found ${#INPUTS[@]} / 12 batch files"
echo "Total accepted events (from provenance): $TOTAL_ACCEPTED"

if [ ${#INPUTS[@]} -eq 0 ]; then
    echo "FATAL: No batch outputs found. Run gen batches first."
    exit 1
fi

if [ $DRY_RUN -eq 1 ]; then
    echo "[DRY RUN] Would merge: ${INPUTS[*]}"
    echo "[DRY RUN] Output: $MERGED"
    exit 0
fi

# Use hadd for artROOT merging (standard LArSoft approach)
# Must be run inside the sbndcode container/environment
echo ""
echo "Merging with hadd..."
echo "Output: $MERGED"

CONTAINER=/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif
LARSOFT_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs
SBND_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/sbnd-v10_14_02_04_delta.squashfs

module use /soft/modulefiles
module load spack-pe-base
module load apptainer

INPUTS_STR="${INPUTS[*]}"

apptainer exec --fakeroot \
    --bind /lus/eagle \
    --bind /lus/grand \
    --overlay "$LARSOFT_SQ":ro \
    --overlay "$SBND_SQ":ro \
    "$CONTAINER" \
    bash -lc "
set -euo pipefail
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
hadd -f '$MERGED' $INPUTS_STR
echo 'hadd complete'
ls -lh '$MERGED'
" 2>&1 | tee "$LOGDIR/merge_accepted.log"

if [ -f "$MERGED" ] && [ "$(stat -c%s "$MERGED" 2>/dev/null || echo 0)" -gt 1000 ]; then
    echo ""
    echo "MERGE COMPLETE: $MERGED"
    echo "Total accepted events from provenance: $TOTAL_ACCEPTED"
    echo ""
    echo "Next steps:"
    echo "  1. Submit G4: qsub jobs/g4/pbs_ncdelta_g4.pbs"
    echo "  2. Run Phase B truth extraction on merged file"
else
    echo "MERGE FAILED: output missing or empty"
    exit 1
fi
