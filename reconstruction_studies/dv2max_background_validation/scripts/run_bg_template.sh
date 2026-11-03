#!/usr/bin/env bash
# DV2-MAX x SP background validation (2026-11-02): one lar process per (arm, runset, event).
#   ARM O = vertex_method=original, ARM D = vertex_method=dv2_split_move  -- EXACT signal-study stack:
#     libraries, Python site, DV2 bundle and wct-int cfg are used READ-ONLY from the signal work area SIGW;
#     configs = byte-identical copies in W/configs (md5-checked against SIGW at run time);
#     same container, sbndcode env, LD_LIBRARY_PATH edit, LD_PRELOAD, PYTHONPATH, DV2_STRICT=1, prod fcl, -n 1.
#   ARM F = the frozen Fix2-v2 stack (CAND build + frozen libWireCellClus.so 9cff76d0 + config-final), exactly as
#     fix2_vertex_shower_onehop_20261005/ab59/jobs/run_ab59_template.sh -- control reference for ARM O only.
# Only the input differs from the signal study: INFILE/--nskip come from W/inputs/${RUNSET}_events.csv.
# Usage: ARM=O|D|F RUNSET=numucc|ncpi0 EVT_IDX=N bash run_bg_template.sh
set -euo pipefail
ARM="${ARM:?}"; RUNSET="${RUNSET:?}"; EVT_IDX="${EVT_IDX:?}"
case "$ARM" in O) VM=original;; D) VM=dv2_split_move;; F) VM=frozen_fix2v2;; *) echo "GUARD_FAIL ARM=$ARM"; exit 5;; esac
case "$RUNSET" in numucc|ncpi0) ;; *) echo "GUARD_FAIL RUNSET=$RUNSET"; exit 5;; esac
EVT_TAG="$(printf 'evt_%04d' "$EVT_IDX")"
PFX="BG$ARM"

W=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102
SIGW=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102
SNAPSHOT=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data
LIST="$W/inputs/${RUNSET}_events.csv"
LINE=$(awk -F, -v i="$EVT_IDX" 'NR>1 && $1==i {print; exit}' "$LIST")
[ -n "$LINE" ] || { echo "GUARD_FAIL no evt_idx $EVT_IDX in $LIST"; exit 5; }
RSE=$(echo "$LINE" | cut -d, -f5); INFILE=$(echo "$LINE" | cut -d, -f7); NSKIP=$(echo "$LINE" | cut -d, -f8)
[ -f "$INFILE" ] || { echo "GUARD_FAIL input missing $INFILE"; exit 5; }

OUTDIR="$W/runs/$RUNSET/arm$ARM/wirecell/$EVT_TAG"
LOGDIR="$W/logs/$RUNSET/arm$ARM"
LOGFILE="$LOGDIR/lar_$EVT_TAG.log"
case "$OUTDIR" in "$W"/runs/*/arm?/wirecell/evt_*) ;; *) echo "GUARD_FAIL outdir $OUTDIR"; exit 5;; esac
if [ -e "$OUTDIR" ] && [ -n "$(ls -A "$OUTDIR" 2>/dev/null)" ]; then
    echo "GUARD_FAIL $OUTDIR not empty; refusing to overwrite"; exit 5
fi
mkdir -p "$OUTDIR" "$LOGDIR"

source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
ORIG_PYTHONPATH="${PYTHONPATH:-}"

if [ "$ARM" = F ]; then
    DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005
    CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
    CFGDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/reco-bundle-id-fix-validation-20260916/config-final
    EXPECTED_MD5=9cff76d0d81a4b6c45a88908e78e73e4
    export LD_LIBRARY_PATH="$DEV/build:$CAND/build/lwc-install-clean/lib:$CAND/install/wct-clean/lib:${LD_LIBRARY_PATH:-}"
    export CET_PLUGIN_PATH="$CAND/build/lwc-install-clean/lib:$CAND/install/wct-clean/lib:${CET_PLUGIN_PATH:-}"
    export WIRECELL_PATH="${SNAPSHOT}:${CFGDIR}:${CAND}/config/sce-override:${CAND}/wct/cfg"
    export FHICL_FILE_PATH="$CAND/config:$CFGDIR:${FHICL_FILE_PATH:-}"
else
    WCT=$SIGW/build/install/wct
    LWC=$SIGW/build/lwc-install
    SITE=$SIGW/build/pyenv/site39
    EXPECTED_MD5=$(cat "$SIGW/build/validation/libWireCellClus.so.md5")
    [ "$EXPECTED_MD5" = 927a1834af1e44dfef3467dcc6e53976 ] || { echo "GUARD_FAIL signal md5 file changed"; exit 3; }
    export LD_LIBRARY_PATH="$WCT/lib:$LWC/lib:$PYTHON_LIB:${LD_LIBRARY_PATH:-}"
    # identical to the signal study: drop larsoft libtorch (it shadows the torch wheel's RUNPATH $ORIGIN)
    export LD_LIBRARY_PATH="$(echo "${LD_LIBRARY_PATH:-}" | tr ':' '\n' | grep -v '/scisoft/larsoft/libtorch/' | grep -v '^$' | tr '\n' ':' | sed 's/:$//')"
    export CET_PLUGIN_PATH="$LWC/lib:$WCT/lib:${CET_PLUGIN_PATH:-}"
    export WIRECELL_PATH="$SNAPSHOT:$W/configs/arm$ARM:$W/configs/common:$W/configs/sce-override:$SIGW/source/wct-int/cfg"
    export FHICL_FILE_PATH="$W/configs/common:${FHICL_FILE_PATH:-}"
    # configs must be byte-identical to the signal study
    ( cd "$W/configs" && md5sum -c --quiet signal_config_md5.txt ) || { echo "GUARD_FAIL configs differ from signal study"; exit 4; }
    ( cd "$SIGW/config" && md5sum -c --quiet "$W/configs/signal_config_md5.txt" ) || { echo "GUARD_FAIL SIGW configs changed"; exit 4; }
fi

LIB=""
IFS=':' read -ra DIRS <<< "$LD_LIBRARY_PATH"
for d in "${DIRS[@]}"; do [ -f "$d/libWireCellClus.so" ] && { LIB="$d/libWireCellClus.so"; break; }; done
LIBMD5=$(md5sum "$LIB" | cut -d' ' -f1)
echo "[$PFX $RUNSET $EVT_TAG] Library: $LIB md5=$LIBMD5"
[ "$LIBMD5" = "$EXPECTED_MD5" ] || { echo "GUARD_FAIL library md5 $LIBMD5 != $EXPECTED_MD5"; exit 3; }
if [ "$ARM" != F ]; then
    MAINJ=""; OPJ=""
    IFS=':' read -ra WP <<< "$WIRECELL_PATH"
    for d in "${WP[@]}"; do [ -z "$MAINJ" ] && [ -f "$d/wcls-img-clus-matching-xin.jsonnet" ] && MAINJ="$d/wcls-img-clus-matching-xin.jsonnet"; done
    for d in "${WP[@]}"; do [ -z "$OPJ" ] && [ -f "$d/pr-operating-point.jsonnet" ] && OPJ="$d/pr-operating-point.jsonnet"; done
    echo "[$PFX $RUNSET $EVT_TAG] Main jsonnet: $MAINJ  Operating point: $OPJ"
    [ "$MAINJ" = "$W/configs/common/wcls-img-clus-matching-xin.jsonnet" ] || { echo "GUARD_FAIL main jsonnet $MAINJ"; exit 4; }
    [ "$OPJ" = "$W/configs/arm$ARM/pr-operating-point.jsonnet" ] || { echo "GUARD_FAIL op point $OPJ"; exit 4; }
    grep -q "^    vertex_method='$VM',$" "$OPJ" || { echo "GUARD_FAIL vertex_method $VM not in $OPJ"; exit 4; }
    if grep -v "^ *//" "$OPJ" | grep -q "main_vertex_swap_apply"; then echo "GUARD_FAIL swap_apply set"; exit 4; fi
    echo "[$PFX $RUNSET $EVT_TAG] libtorch dirs left on LD_LIBRARY_PATH: $(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -c libtorch)"
fi
echo "[$PFX $RUNSET $EVT_TAG] vertex_method=$VM input=$INFILE nskip=$NSKIP rse=$RSE Start: $(date) host=$(hostname)"
T0=$(date +%s)
cd "$OUTDIR"
set +e
if [ "$ARM" = F ]; then
    lar --nskip "$NSKIP" -n 1 -c wcls-img-clus-matching-xin-prod.fcl -s "$INFILE" --no-output > "$LOGFILE" 2>&1
else
    env LD_PRELOAD="$PYTHON_LIB/libpython3.9.so.1.0" \
        PYTHONPATH="$SITE:$WCT/python:$ORIG_PYTHONPATH" \
        DV2_STRICT=1 DV2_HOOK_LOG="$OUTDIR/dv2_hook.jsonl" \
        lar --nskip "$NSKIP" -n 1 \
            -c wcls-img-clus-matching-xin-prod.fcl \
            -s "$INFILE" \
            --no-output \
            > "$LOGFILE" 2>&1
fi
LAR_EXIT=$?
set -e
echo "[$PFX $RUNSET $EVT_TAG] lar exit: $LAR_EXIT  runtime_sec=$(( $(date +%s) - T0 ))"
grep -m1 "Begin processing the 1st record" "$LOGFILE" | sed "s/^/[$PFX $RUNSET $EVT_TAG] /" || true
echo "=== vertex / DV2 lines for $RUNSET $EVT_TAG ==="
grep -h "vertex_method dv2\|DL vertex failed\|no DV2-MAX prediction\|Traceback" "$LOGFILE" 2>/dev/null | cut -c1-300 || echo "(none)"
echo "DV2_HOOK_LINES=$(cat "$OUTDIR/dv2_hook.jsonl" 2>/dev/null | wc -l)"
[ $LAR_EXIT -ne 0 ] && { echo "[WARN] lar non-zero for $RUNSET $EVT_TAG"; tail -20 "$LOGFILE"; }
echo "${PFX}_JOB_DONE_${RUNSET}_$EVT_TAG"
