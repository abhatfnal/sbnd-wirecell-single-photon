#!/usr/bin/env bash
# Submission wrapper for the 59-event Fix2-v2 A/B study.
# Usage: bash submit_ab59.sh
set -euo pipefail

DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005
PBS_SCRIPT=$DEV/ab59/jobs/run_ab59_array.pbs

echo "=== Fix2 A/B Study Submission ==="
echo "PBS script: $PBS_SCRIPT"
echo "Library:    $DEV/build/libWireCellClus.so"
echo "MD5:        $(md5sum "$DEV/build/libWireCellClus.so" | awk '{print $1}')"
echo "Date:       $(date)"
echo ""

# Verify library exists and is the expected size
LIB="$DEV/build/libWireCellClus.so"
if [ ! -f "$LIB" ]; then
    echo "ERROR: patched library not found at $LIB"
    exit 1
fi
LIB_SIZE_MB=$(du -m "$LIB" | awk '{print $1}')
echo "Library size: ${LIB_SIZE_MB} MB"
if [ "$LIB_SIZE_MB" -lt 300 ]; then
    echo "ERROR: library too small (< 300 MB) — possible incomplete build"
    exit 1
fi

# Verify input file exists
INFILE=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root
if [ ! -f "$INFILE" ]; then
    echo "ERROR: input file not found: $INFILE"
    exit 1
fi
echo "Input file: $INFILE ($(ls -lh "$INFILE" | awk '{print $5}'))"

# Ensure output directories exist
mkdir -p "$DEV/ab59/logs" "$DEV/ab59/wirecell"

echo ""
echo "Submitting PBS array job (indices 0-58, 59 total)..."
JOB_ID=$(qsub "$PBS_SCRIPT")
echo "Submitted: $JOB_ID"
echo ""
echo "Monitor with:"
echo "  qstat -J ${JOB_ID%%.*}"
echo "  ls $DEV/ab59/wirecell/ | wc -l   # patched output dirs"
echo ""
echo "PBS script: $PBS_SCRIPT"
echo "Log dir:    $DEV/ab59/logs/"
echo "Output dir: $DEV/ab59/wirecell/"
echo "AB59_SUBMITTED $JOB_ID"
