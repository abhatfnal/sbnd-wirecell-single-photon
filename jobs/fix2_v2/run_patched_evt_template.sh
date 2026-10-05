#!/usr/bin/env bash
# Template — parameterized by EVT_IDX and EVT_TAG
# Called by individual run_patched_evtNNNN.pbs scripts
# Usage: EVT_IDX=14 EVT_TAG=evt_0014 bash run_patched_evt_template.sh
set -euo pipefail

DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005
CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
INTDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08
CFGDIR=$INTDIR/reco-bundle-id-fix-validation-20260916/config-final
SNAPSHOT=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data
INFILE=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root

OUTDIR="$DEV/patched/$EVT_TAG"
LOGFILE="$DEV/logs/lar_fix2_patched_$EVT_TAG.log"
mkdir -p "$OUTDIR"

source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true

export LD_LIBRARY_PATH="$DEV/build:$CAND/build/lwc-install-clean/lib:$CAND/install/wct-clean/lib:${LD_LIBRARY_PATH:-}"
export CET_PLUGIN_PATH="$CAND/build/lwc-install-clean/lib:$CAND/install/wct-clean/lib:${CET_PLUGIN_PATH:-}"
export WIRECELL_PATH="${SNAPSHOT}:${CFGDIR}:${CAND}/config/sce-override:${CAND}/wct/cfg"
export FHICL_FILE_PATH="$CAND/config:$CFGDIR:${FHICL_FILE_PATH:-}"

echo "[PATCHED $EVT_TAG] LD_LIBRARY_PATH[0]: $(echo $LD_LIBRARY_PATH | tr ':' '\n' | head -1)"
echo "Library: $(IFS=':' read -ra DIRS <<< "$LD_LIBRARY_PATH"; for d in "${DIRS[@]}"; do [ -f "$d/libWireCellClus.so" ] && { ls -lh "$d/libWireCellClus.so"; break; }; done)"

cd "$OUTDIR"
set +e
lar --nskip "$EVT_IDX" -n 1 \
    -c wcls-img-clus-matching-xin-prod.fcl \
    -s "$INFILE" \
    --no-output \
    > "$LOGFILE" 2>&1
LAR_EXIT=$?
set -e
echo "lar exit: $LAR_EXIT"

echo "Output files in patched/$EVT_TAG:"
ls -lh "$OUTDIR/" 2>/dev/null

if [ -f "$OUTDIR/tracking-pr.root" ]; then
    python3 - <<PYEOF
import sys
try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    f = ROOT.TFile('$OUTDIR/tracking-pr.root')
    t = f.Get('T_tagger')
    if not t or t.GetEntries() == 0:
        print('T_tagger: empty or missing')
        sys.exit(0)
    t.GetEntry(0)
    filled = getattr(t, 'shw_sp_filled', -1)
    n20 = getattr(t, 'shw_sp_n_20mev_showers', -1)
    energy = getattr(t, 'shw_sp_energy', -1)
    n20br1 = getattr(t, 'shw_sp_n_20br1_showers', -1)
    print(f'RESULT $EVT_TAG: shw_sp_filled={filled} shw_sp_n_20mev_showers={n20} shw_sp_energy={energy:.1f}MeV shw_sp_n_20br1_showers={n20br1}')
except Exception as e:
    print(f'ROOT_CHECK_ERROR: {e}')
PYEOF
else
    echo "tracking-pr.root: NOT FOUND in $OUTDIR"
fi

[ $LAR_EXIT -ne 0 ] && {
    echo "[WARN] lar non-zero; tail of log:"
    tail -10 "$LOGFILE"
}
echo "PATCHED_RUN_DONE_$EVT_TAG"
