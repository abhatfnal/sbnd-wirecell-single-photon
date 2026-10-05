#!/bin/bash
# Submit PBS array for WireCell reconstruction of all accepted NC Delta events.
#
# Run this AFTER reco1 completes.
# Determines the number of events in ncdelta_reco1.root and submits a PBS array.
#
# Usage: bash submit_wirecell_array.sh [--dry-run]

set -euo pipefail

BASEDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt
RECO1="$BASEDIR/reco1/ncdelta_reco1.root"
LOGDIR="$BASEDIR/logs"
PBS_SCRIPT="$(cd "$(dirname "$0")" && pwd)/pbs_ncdelta_wirecell_array.pbs"

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
    echo "[DRY RUN]"
fi

[ -f "$RECO1" ] || { echo "FATAL: $RECO1 not found. Run reco1 first."; exit 1; }
[ -f "$PBS_SCRIPT" ] || { echo "FATAL: $PBS_SCRIPT not found."; exit 1; }

# Count events using an sbndcode-aware ROOT command
# We need the container for this
CONTAINER=/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif
LARSOFT_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs
SBND_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/sbnd-v10_14_02_04_delta.squashfs

module use /soft/modulefiles
module load spack-pe-base
module load apptainer

echo "=== Counting events in $RECO1 ==="

N_EVENTS=$(apptainer exec --fakeroot \
    --bind /lus/eagle \
    --bind /lus/grand \
    --overlay "$LARSOFT_SQ":ro \
    --overlay "$SBND_SQ":ro \
    "$CONTAINER" \
    bash -lc "
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
root -b -q -l 'TFile f(\"$RECO1\"); TTree* t = (TTree*)f.Get(\"Events\"); cout << t->GetEntries() << endl; f.Close();' 2>/dev/null | tail -1
" 2>/dev/null)

if ! [[ "$N_EVENTS" =~ ^[0-9]+$ ]] || [ "$N_EVENTS" -eq 0 ]; then
    echo "FATAL: Could not determine event count from $RECO1 (got: '$N_EVENTS')"
    echo "Check that the file is valid and that the Events TTree exists."
    exit 1
fi

echo "Found $N_EVENTS events"
LAST_IDX=$((N_EVENTS - 1))

echo ""
echo "Will submit PBS array: -J 0-${LAST_IDX}"
echo "PBS script: $PBS_SCRIPT"
echo "Log directory: $LOGDIR"
mkdir -p "$LOGDIR"

CMD="qsub \
    -J 0-${LAST_IDX} \
    -e ${LOGDIR}/wct_evt^array_index^.err \
    -o ${LOGDIR}/wct_evt^array_index^.out \
    ${PBS_SCRIPT}"

if [ $DRY_RUN -eq 1 ]; then
    echo "[DRY RUN] $CMD"
    exit 0
fi

JOBID=$(eval $CMD)
echo "Submitted: $JOBID"

# Append to provenance
PROV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/docs/BASELINE_PROVENANCE.md
if [ -f "$PROV" ]; then
    echo "" >> "$PROV"
    echo "## WireCell array submission ($(date -u +%Y-%m-%dT%H:%M:%SZ))" >> "$PROV"
    echo "- wirecell array (0-${LAST_IDX}): $JOBID" >> "$PROV"
    echo "Job ID appended to BASELINE_PROVENANCE.md"
fi

echo ""
echo "Monitor with: qstat -u abhat | grep ncdelta_wct"
echo "Logs: $LOGDIR/wct_evt*.{err,out}"
