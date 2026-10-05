#!/bin/bash
# Submit 10 NC Delta gen batches for baseline_v0 Phase A.
#
# Usage: bash submit_gen_batches.sh [--dry-run]
#   --dry-run: print qsub commands but do not submit
#
# Each batch: 1000 NCRES attempts, unique firstRun, ~6 expected accepted events.
# Total: 10,000 attempts, ~60 expected accepted events.
#
# After all batches complete:
#   1. Check $BASEDIR/ncdelta_50evt/logs/container_gen_batch_NN.log for PASS
#   2. Run jobs/gen/merge_accepted.sh to combine outputs
#   3. Proceed to Phase B (truth extraction) and Phase C (reconstruction)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASEDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0
LOGDIR="$BASEDIR/ncdelta_50evt/logs"
PBS_SCRIPT="$SCRIPT_DIR/pbs_ncdelta_gen_batch.pbs"

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
    echo "[DRY RUN] No jobs will be submitted"
fi

[ -f "$PBS_SCRIPT" ] || { echo "FATAL: PBS script not found: $PBS_SCRIPT"; exit 1; }
mkdir -p "$LOGDIR"

echo "=== Submitting NC Delta gen batches for baseline_v0 Phase A ==="
echo "PBS script: $PBS_SCRIPT"
echo "Log directory: $LOGDIR"
echo ""

JOB_IDS=()

for NN in 01 02 03 04 05 06 07 08 09 10; do
    CMD="qsub \
        -v BATCH_ID=${NN} \
        -e ${LOGDIR}/gen_batch_${NN}.err \
        -o ${LOGDIR}/gen_batch_${NN}.out \
        -N ncdelta_gen_b${NN} \
        ${PBS_SCRIPT}"

    if [ $DRY_RUN -eq 1 ]; then
        echo "[DRY RUN] $CMD"
    else
        JOBID=$(eval $CMD)
        JOB_IDS+=("$JOBID")
        echo "Batch $NN submitted: $JOBID"
        # Stagger by 2 seconds to avoid scheduler race
        sleep 2
    fi
done

if [ $DRY_RUN -eq 0 ] && [ ${#JOB_IDS[@]} -gt 0 ]; then
    echo ""
    echo "=== Submitted job IDs ==="
    for jid in "${JOB_IDS[@]}"; do echo "  $jid"; done

    # Append job IDs to provenance
    PROV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/docs/BASELINE_PROVENANCE.md
    if [ -f "$PROV" ]; then
        echo "" >> "$PROV"
        echo "## Gen batch submission ($(date -u +%Y-%m-%dT%H:%M:%SZ))" >> "$PROV"
        echo "" >> "$PROV"
        IDX=1
        for jid in "${JOB_IDS[@]}"; do
            echo "- gen batch $(printf '%02d' $IDX): $jid" >> "$PROV"
            IDX=$((IDX+1))
        done
        echo "Job IDs appended to BASELINE_PROVENANCE.md"
    fi

    echo ""
    echo "Monitor with: qstat -u abhat | grep ncdelta_gen"
    echo "Logs: $LOGDIR/"
fi
