#!/bin/bash
# Check status of all 10 NC Delta gen batches and fill gen_batch_summary.csv.
#
# Run this after the batches complete (or partially, to check progress).
# Usage: bash check_gen_batches.sh
#
# Reads per-batch provenance.txt and lar log files.
# Updates: ncdelta_50evt/tables/gen_batch_summary.csv

BASEDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt
LOGDIR="$BASEDIR/logs"
TABLE="$BASEDIR/tables/gen_batch_summary.csv"

PBS_JOBS=(
    192796.sophia-pbs-01.lab.alcf.anl.gov
    192797.sophia-pbs-01.lab.alcf.anl.gov
    192798.sophia-pbs-01.lab.alcf.anl.gov
    192799.sophia-pbs-01.lab.alcf.anl.gov
    192800.sophia-pbs-01.lab.alcf.anl.gov
    192801.sophia-pbs-01.lab.alcf.anl.gov
    192802.sophia-pbs-01.lab.alcf.anl.gov
    192803.sophia-pbs-01.lab.alcf.anl.gov
    192804.sophia-pbs-01.lab.alcf.anl.gov
    192805.sophia-pbs-01.lab.alcf.anl.gov
)

BATCH_IDS=(01 02 03 04 05 06 07 08 09 10)

echo "batch,pbs_job,attempted_ncres,accepted_ncdelta,lar_exit,output_root_exists,file_size_bytes,first_run,first_art_event,last_art_event,filter_acceptance_pct,rng_independence,pass_fail" > "$TABLE"

TOTAL_ATTEMPTED=0
TOTAL_ACCEPTED=0
ALL_PASS=1

for i in "${!BATCH_IDS[@]}"; do
    NN="${BATCH_IDS[$i]}"
    JOBID="${PBS_JOBS[$i]}"
    BATCH_NUM=$(echo "$NN" | sed 's/^0*//')
    [ -z "$BATCH_NUM" ] && BATCH_NUM=0
    FIRST_RUN=$(( BATCH_NUM * 10 ))

    OUTDIR="$BASEDIR/gen/batch_${NN}"
    PROV="$OUTDIR/provenance.txt"
    OUTROOT="$OUTDIR/ncdelta_gen_batch_${NN}.root"
    LARLOG="$LOGDIR/lar_gen_batch_${NN}.log"
    CONTAINER_LOG="$LOGDIR/container_gen_batch_${NN}.log"

    # Output root exists?
    ROOT_EXISTS=0
    FILE_SIZE=0
    if [ -f "$OUTROOT" ]; then
        FILE_SIZE=$(stat -c%s "$OUTROOT" 2>/dev/null || echo 0)
        [ "$FILE_SIZE" -gt 1000 ] && ROOT_EXISTS=1
    fi

    # Attempted/accepted from provenance
    ATTEMPTED="not_run"
    ACCEPTED="not_run"
    if [ -f "$PROV" ]; then
        ATTEMPTED=$(grep "ncres_attempted:" "$PROV" | awk '{print $2}' | head -1 || echo "unknown")
        ACCEPTED=$(grep "accepted_events:" "$PROV" | awk '{print $2}' | head -1 || echo "unknown")
    fi

    # lar exit from container log
    LAR_EXIT="not_run"
    if [ -f "$CONTAINER_LOG" ]; then
        if grep -q "NCDELTA_GEN_BATCH_${NN}_PASS" "$CONTAINER_LOG" 2>/dev/null; then
            LAR_EXIT=0
        elif grep -q "NCDELTA_GEN_BATCH_${NN}_FAIL" "$CONTAINER_LOG" 2>/dev/null; then
            LAR_EXIT=1
        else
            LAR_EXIT="running_or_incomplete"
        fi
    fi

    # ART event range from lar log
    FIRST_EVT="unknown"
    LAST_EVT="unknown"
    if [ -f "$LARLOG" ]; then
        FIRST_EVT=$(grep -m1 "Begin processing" "$LARLOG" | grep -oP 'event \K[0-9]+' | head -1 || echo "unknown")
        LAST_EVT=$(grep "Begin processing" "$LARLOG" | grep -oP 'event \K[0-9]+' | tail -1 || echo "unknown")
    fi

    # Filter acceptance percent
    ACCEPTANCE="unknown"
    if [[ "$ATTEMPTED" =~ ^[0-9]+$ ]] && [[ "$ACCEPTED" =~ ^[0-9]+$ ]] && [ "$ATTEMPTED" -gt 0 ]; then
        ACCEPTANCE=$(echo "scale=2; $ACCEPTED * 100 / $ATTEMPTED" | bc 2>/dev/null || echo "unknown")
    fi

    # RNG independence (PENDING until manually checked)
    RNG_CHECK="PENDING"

    # Overall PASS/FAIL
    PASS_FAIL="PENDING"
    if [ "$ROOT_EXISTS" -eq 1 ] && [ "$LAR_EXIT" = "0" ]; then
        PASS_FAIL="PASS"
    elif [ "$LAR_EXIT" = "not_run" ]; then
        PASS_FAIL="NOT_RUN"
        ALL_PASS=0
    elif [ "$LAR_EXIT" = "running_or_incomplete" ]; then
        PASS_FAIL="RUNNING"
    elif [ "$ROOT_EXISTS" -eq 0 ]; then
        PASS_FAIL="FAIL_NO_OUTPUT"
        ALL_PASS=0
    fi

    echo "  Batch $NN: attempted=$ATTEMPTED accepted=$ACCEPTED lar_exit=$LAR_EXIT root_exists=$ROOT_EXISTS PASS_FAIL=$PASS_FAIL"

    echo "$NN,$JOBID,$ATTEMPTED,$ACCEPTED,$LAR_EXIT,$ROOT_EXISTS,$FILE_SIZE,$FIRST_RUN,$FIRST_EVT,$LAST_EVT,$ACCEPTANCE,$RNG_CHECK,$PASS_FAIL" >> "$TABLE"

    if [[ "$ACCEPTED" =~ ^[0-9]+$ ]]; then
        TOTAL_ACCEPTED=$((TOTAL_ACCEPTED + ACCEPTED))
    fi
    if [[ "$ATTEMPTED" =~ ^[0-9]+$ ]]; then
        TOTAL_ATTEMPTED=$((TOTAL_ATTEMPTED + ATTEMPTED))
    fi
done

echo ""
echo "=== Generation summary ==="
echo "Total attempted (from provenance): $TOTAL_ATTEMPTED"
echo "Total accepted (from provenance):  $TOTAL_ACCEPTED"
if [ "$TOTAL_ATTEMPTED" -gt 0 ]; then
    OVERALL_ACCEPT=$(echo "scale=2; $TOTAL_ACCEPTED * 100 / $TOTAL_ATTEMPTED" | bc 2>/dev/null || echo "?")
    echo "Overall acceptance: ${OVERALL_ACCEPT}%"
fi
echo ""
echo "Table: $TABLE"
echo ""

if [ "$TOTAL_ACCEPTED" -ge 50 ]; then
    echo "TARGET MET: $TOTAL_ACCEPTED >= 50 accepted events."
    echo "Next: inspect independence check, then run merge_accepted.sh"
elif [ "$TOTAL_ATTEMPTED" -gt 0 ]; then
    NEEDED=$(( (50 - TOTAL_ACCEPTED) ))
    # At 0.6% acceptance, batches needed = ceil(needed / 6)
    EXTRA_BATCHES=$(( (NEEDED + 5) / 6 ))
    echo "TARGET NOT MET: $TOTAL_ACCEPTED < 50 accepted events."
    echo "Estimated additional 1000-event batches needed: $EXTRA_BATCHES"
    echo "Do NOT regenerate completed batches. Submit top-up batches only."
else
    echo "Status: batches still running or not yet started."
fi
