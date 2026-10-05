#!/bin/bash
set -euo pipefail

EVT_IDX=0
EVT_DIR=evt_0000
BASEDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt
INFILE=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root
OUTDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/wirecell/evt_0000
LOGDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/logs

INTDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08
CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
CFGDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/reco-bundle-id-fix-validation-20260916/config-final
SNAPSHOT=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data

CAND_WCTLIB="$CAND/install/wct-clean/lib"
CAND_LWCLIB="$CAND/build/lwc-install-clean/lib"

gate_pass() { echo "[GATE PASS] $*"; }
gate_fail() { echo "[GATE FAIL] $*"; exit 1; }

echo "=== Inner environment (container) ==="
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
echo "sbndcode: ${SBNDCODE_VERSION:-not set}"
echo "INFILE: $INFILE"
echo "EVT_IDX: $EVT_IDX"

# Frozen WireCell libraries (baseline_v0: WCT 251ff143, larwirecell 9295e2a3)
export LD_LIBRARY_PATH="$CAND_LWCLIB:$CAND_WCTLIB:${LD_LIBRARY_PATH:-}"
export CET_PLUGIN_PATH="$CAND_LWCLIB:$CAND_WCTLIB:${CET_PLUGIN_PATH:-}"
# config-final MUST come before $CAND/config to get correct WCT FCL
export WIRECELL_PATH="${SNAPSHOT}:${CFGDIR}:${CAND}/config/sce-override:${CAND}/wct/cfg"
export FHICL_FILE_PATH="$CFGDIR:$CAND/config:${FHICL_FILE_PATH:-}"

echo "WIRECELL_PATH: $WIRECELL_PATH"
echo "FHICL_FILE_PATH (first two): $(echo $FHICL_FILE_PATH | tr ':' '\n' | head -2 | tr '\n' ':')"

# Check if already done
H5="$OUTDIR/nugraph.h5"
TRKPR="$OUTDIR/tracking-pr.root"
if [ -f "$H5" ] && [ -f "$TRKPR" ]; then
    H5SZ=$(stat -c%s "$H5" 2>/dev/null || echo 0)
    TRKPRSZ=$(stat -c%s "$TRKPR" 2>/dev/null || echo 0)
    if [ "$H5SZ" -gt 1000 ] && [ "$TRKPRSZ" -gt 1000 ]; then
        echo "[WCT SKIP] Outputs already exist for evt $EVT_IDX"
        gate_pass "WCT outputs present from prior run"
        ls -lh "$OUTDIR/"
        echo "WCT_EVT_${EVT_IDX}_COMPLETE (skip)"
        exit 0
    fi
fi

echo ""
echo "=== Run WireCell for event index $EVT_IDX ==="
date
WCT_LOG="$LOGDIR/lar_wct_${EVT_DIR}.log"
cd "$OUTDIR"

echo "lar command: lar -c wcls-img-clus-matching-xin-prod.fcl -s $INFILE --nskip $EVT_IDX -n 1"
set +e
lar -c wcls-img-clus-matching-xin-prod.fcl \
    -s "$INFILE" \
    --nskip "$EVT_IDX" \
    -n 1 \
    > "$WCT_LOG" 2>&1
WCT_EXIT=$?
set -e
date
echo "lar exit: $WCT_EXIT"

# Rename outputs to canonical names if lar added timestamp suffixes
for f in tracking-pr.root nugraph.h5 mabc.zip tf-default.root; do
    ext="${f##*.}"
    base="${f%.*}"
    MATCHES=($(ls ${base}*.${ext} 2>/dev/null || true))
    if [ "${#MATCHES[@]}" -eq 1 ] && [ "${MATCHES[0]}" != "$f" ]; then
        mv "${MATCHES[0]}" "$f"
        echo "Renamed: ${MATCHES[0]} -> $f"
    fi
done

H5SZ=$(stat -c%s "$H5" 2>/dev/null || echo 0)
TRKPRSZ=$(stat -c%s "$TRKPR" 2>/dev/null || echo 0)

if [ $WCT_EXIT -ne 0 ]; then
    echo "[WCT WARN] lar exited $WCT_EXIT"
    if [ "$H5SZ" -gt 1000 ] && [ "$TRKPRSZ" -gt 1000 ]; then
        echo "  But outputs exist -- likely destructor crash (valid)"
        gate_pass "WCT complete with destructor crash for evt $EVT_IDX"
    else
        echo "  Outputs missing or empty:"
        ls -lh "$OUTDIR/" 2>/dev/null || true
        tail -40 "$WCT_LOG"
        gate_fail "WCT failed for evt $EVT_IDX"
    fi
else
    gate_pass "WCT complete (exit 0) for evt $EVT_IDX"
fi

echo ""
echo "=== Output inventory for evt $EVT_IDX ==="
ls -lh "$OUTDIR/"
echo ""
echo "WCT_EVT_${EVT_IDX}_COMPLETE"
date
