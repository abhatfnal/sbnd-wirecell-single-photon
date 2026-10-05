#!/usr/bin/env bash
# Per-event shell script for the 59-event Fix2-v2 A/B study.
# Called by run_ab59_array.pbs with EVT_IDX set to the PBS array index (0-58).
set -euo pipefail

EVT_IDX="${EVT_IDX:?EVT_IDX must be set}"
EVT_TAG="$(printf 'evt_%04d' "$EVT_IDX")"

DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005
CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
INTDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08
CFGDIR=$INTDIR/reco-bundle-id-fix-validation-20260916/config-final
SNAPSHOT=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data
INFILE=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root

OUTDIR="$DEV/ab59/wirecell/$EVT_TAG"
LOGFILE="$DEV/ab59/logs/lar_ab59_$EVT_TAG.log"
mkdir -p "$OUTDIR"

source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true

export LD_LIBRARY_PATH="$DEV/build:$CAND/build/lwc-install-clean/lib:$CAND/install/wct-clean/lib:${LD_LIBRARY_PATH:-}"
export CET_PLUGIN_PATH="$CAND/build/lwc-install-clean/lib:$CAND/install/wct-clean/lib:${CET_PLUGIN_PATH:-}"
export WIRECELL_PATH="${SNAPSHOT}:${CFGDIR}:${CAND}/config/sce-override:${CAND}/wct/cfg"
export FHICL_FILE_PATH="$CAND/config:$CFGDIR:${FHICL_FILE_PATH:-}"

echo "[AB59 $EVT_TAG] Start: $(date)"
echo "[AB59 $EVT_TAG] Library: $(IFS=':' read -ra DIRS <<< "$LD_LIBRARY_PATH"; for d in "${DIRS[@]}"; do [ -f "$d/libWireCellClus.so" ] && { ls -lh "$d/libWireCellClus.so"; break; }; done)"

cd "$OUTDIR"
set +e
lar --nskip "$EVT_IDX" -n 1 \
    -c wcls-img-clus-matching-xin-prod.fcl \
    -s "$INFILE" \
    --no-output \
    > "$LOGFILE" 2>&1
LAR_EXIT=$?
set -e
echo "[AB59 $EVT_TAG] lar exit: $LAR_EXIT"

# Validate output
if [ -f "$OUTDIR/tracking-pr.root" ]; then
    python3 - <<PYEOF
import sys, os
try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    f = ROOT.TFile('$OUTDIR/tracking-pr.root')
    t = f.Get('T_tagger')
    has_tagger = (t is not None and t.GetEntries() > 0)
    if not has_tagger:
        print('AB59_RESULT $EVT_TAG: has_tagger=0 shw_sp_filled=NA')
        sys.exit(0)
    t.GetEntry(0)
    filled  = getattr(t, 'shw_sp_filled', -1)
    n20     = getattr(t, 'shw_sp_n_20mev_showers', -1)
    n20br1  = getattr(t, 'shw_sp_n_20br1_showers', -1)
    energy  = getattr(t, 'shw_sp_energy', -1.0)
    pflag   = getattr(t, 'photon_flag', -1)
    brfill  = getattr(t, 'br_filled', -1)
    run     = getattr(t, 'run_no', -1)
    sub     = getattr(t, 'subrun_no', -1)
    evt     = getattr(t, 'event_no', -1)
    print(f'AB59_RESULT $EVT_TAG: has_tagger=1 run={run} sub={sub} evt={evt} '
          f'shw_sp_filled={filled} shw_sp_n_20mev={n20} shw_sp_energy={energy:.1f} '
          f'shw_sp_n_20br1={n20br1} photon_flag={pflag} br_filled={brfill}')
except Exception as e:
    print(f'ROOT_CHECK_ERROR $EVT_TAG: {e}')
    sys.exit(1)
PYEOF
else
    echo "AB59_RESULT $EVT_TAG: tracking-pr.root NOT FOUND (lar_exit=$LAR_EXIT)"
fi

# Print fix2_diag lines for Part J validation
echo "=== fix2_diag lines for $EVT_TAG ==="
grep "fix2_diag:" "$LOGFILE" 2>/dev/null || echo "(none)"
echo "=== fix2_onehop lines for $EVT_TAG ==="
grep "fix2_onehop:" "$LOGFILE" 2>/dev/null || echo "(none)"

[ $LAR_EXIT -ne 0 ] && {
    echo "[WARN] lar non-zero for $EVT_TAG; tail of log:"
    tail -20 "$LOGFILE"
}
echo "AB59_JOB_DONE_$EVT_TAG"
