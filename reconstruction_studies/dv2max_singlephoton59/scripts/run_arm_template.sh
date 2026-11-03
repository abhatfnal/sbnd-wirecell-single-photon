#!/usr/bin/env bash
# DV2-MAX x SP59 (2026-11-02) per-event lar run, ARM O (vertex_method=original) or
# ARM D (vertex_method=dv2_split_move).  Derived from
# fix2_vertex_shower_onehop_20261005/ab59/jobs/run_ab59_template.sh (same input, same
# --nskip/-n 1, same prod fcl, same container + sbndcode env).  Differences:
#   - libraries: the integration build W/build/install/wct (+ larwirecell rebuilt
#     against it, W/build/lwc-install) instead of CAND + the Fix2 lib
#   - WIRECELL_PATH: W/config/arm$ARM (pr-operating-point.jsonnet: vertex_method,
#     dl_weights='') : W/config/common (byte-identical copies of config-final) :
#     W/config/sce-override (integration clus.jsonnet, SCE path as CAND's override) :
#     W/source/wct-int/cfg (includes dv2max/r7_cloud bundle)
#   - Python: PYTHONPATH = W/build/pyenv/site39 (torch 2.5.1+cpu, numpy 2.0.2,
#     scipy 1.13.1, lightgbm 4.6.0) : W/build/install/wct/python (DV2_Vertex.py +
#     dv2max_vertexer); libpython3.9 preloaded; DV2_STRICT=1 -- identical in BOTH arms
#   - outputs only under W/runs/$RUNSET/arm$ARM, logs under W/logs/$RUNSET/arm$ARM
# Usage: ARM=O|D RUNSET=smoke|main EVT_IDX=N bash run_arm_template.sh
set -euo pipefail
ARM="${ARM:?ARM must be O or D}"; RUNSET="${RUNSET:?}"; EVT_IDX="${EVT_IDX:?}"
case "$ARM" in O) VM=original;; D) VM=dv2_split_move;; *) echo "GUARD_FAIL ARM=$ARM"; exit 5;; esac
case "$RUNSET" in smoke|main) ;; *) echo "GUARD_FAIL RUNSET=$RUNSET"; exit 5;; esac
EVT_TAG="$(printf 'evt_%04d' "$EVT_IDX")"
PFX="DV2$ARM"

W=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102
SNAPSHOT=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data
INFILE=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root
WCT=$W/build/install/wct
LWC=$W/build/lwc-install
SITE=$W/build/pyenv/site39
EXPECTED_MD5=$(cat "$W/build/validation/libWireCellClus.so.md5")

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

export LD_LIBRARY_PATH="$WCT/lib:$LWC/lib:$PYTHON_LIB:${LD_LIBRARY_PATH:-}"
# larsoft libtorch v2_1_1b is on the sbndcode LD_LIBRARY_PATH; LD_LIBRARY_PATH beats the torch
# wheel's RUNPATH $ORIGIN, so the wheel's libtorch_python.so would bind the larsoft libtorch_cpu.so
# (undefined symbol).  The lar job never loads larsoft libtorch (LD_DEBUG of the CAND reco job), so the
# directory is dropped from the search path -- identically in both arms.
export LD_LIBRARY_PATH="$(echo "${LD_LIBRARY_PATH:-}" | tr ':' '\n' | grep -v '/scisoft/larsoft/libtorch/' | grep -v '^$' | tr '\n' ':' | sed 's/:$//')"
export CET_PLUGIN_PATH="$LWC/lib:$WCT/lib:${CET_PLUGIN_PATH:-}"
export WIRECELL_PATH="$SNAPSHOT:$W/config/arm$ARM:$W/config/common:$W/config/sce-override:$W/source/wct-int/cfg"
export FHICL_FILE_PATH="$W/config/common:${FHICL_FILE_PATH:-}"

LIB=""
IFS=':' read -ra DIRS <<< "$LD_LIBRARY_PATH"
for d in "${DIRS[@]}"; do [ -f "$d/libWireCellClus.so" ] && { LIB="$d/libWireCellClus.so"; break; }; done
LIBMD5=$(md5sum "$LIB" | cut -d' ' -f1)
echo "[$PFX $EVT_TAG] Library: $LIB md5=$LIBMD5"
[ "$LIBMD5" = "$EXPECTED_MD5" ] || { echo "GUARD_FAIL library md5 $LIBMD5 != $EXPECTED_MD5"; exit 3; }
MAINJ=""; OPJ=""
IFS=':' read -ra WP <<< "$WIRECELL_PATH"
for d in "${WP[@]}"; do [ -z "$MAINJ" ] && [ -f "$d/wcls-img-clus-matching-xin.jsonnet" ] && MAINJ="$d/wcls-img-clus-matching-xin.jsonnet"; done
for d in "${WP[@]}"; do [ -z "$OPJ" ] && [ -f "$d/pr-operating-point.jsonnet" ] && OPJ="$d/pr-operating-point.jsonnet"; done
echo "[$PFX $EVT_TAG] Main jsonnet: $MAINJ"
echo "[$PFX $EVT_TAG] Operating point: $OPJ"
[ "$MAINJ" = "$W/config/common/wcls-img-clus-matching-xin.jsonnet" ] || { echo "GUARD_FAIL main jsonnet $MAINJ"; exit 4; }
[ "$OPJ" = "$W/config/arm$ARM/pr-operating-point.jsonnet" ] || { echo "GUARD_FAIL op point $OPJ"; exit 4; }
grep -q "^    vertex_method='$VM',$" "$OPJ" || { echo "GUARD_FAIL vertex_method $VM not in $OPJ"; exit 4; }
if grep -v "^ *//" "$OPJ" | grep -q "main_vertex_swap_apply"; then echo "GUARD_FAIL swap_apply set"; exit 4; fi

[ "$RUNSET" = smoke ] && LDDBG=1 || LDDBG=""
echo "[$PFX $EVT_TAG] libtorch dirs left on LD_LIBRARY_PATH: $(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -c libtorch)"
echo "[$PFX $EVT_TAG] vertex_method=$VM Start: $(date) host=$(hostname)"
T0=$(date +%s)
cd "$OUTDIR"
set +e
env LD_PRELOAD="$PYTHON_LIB/libpython3.9.so.1.0" \
    PYTHONPATH="$SITE:$WCT/python:$ORIG_PYTHONPATH" \
    DV2_STRICT=1 DV2_HOOK_LOG="$OUTDIR/dv2_hook.jsonl" \
    ${LDDBG:+LD_DEBUG=files LD_DEBUG_OUTPUT="$OUTDIR/lddebug"} \
    lar --nskip "$EVT_IDX" -n 1 \
        -c wcls-img-clus-matching-xin-prod.fcl \
        -s "$INFILE" \
        --no-output \
        > "$LOGFILE" 2>&1
LAR_EXIT=$?
set -e
echo "[$PFX $EVT_TAG] lar exit: $LAR_EXIT  runtime_sec=$(( $(date +%s) - T0 ))"

if [ -f "$OUTDIR/tracking-pr.root" ]; then
    PYTHONPATH="$ORIG_PYTHONPATH" python3 - <<PYEOF
import sys
try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    f = ROOT.TFile('$OUTDIR/tracking-pr.root')
    t = f.Get('T_tagger')
    if not t or t.GetEntries() == 0:
        print('${PFX}_RESULT $EVT_TAG: has_tagger=0'); sys.exit(0)
    t.GetEntry(0)
    print(f"${PFX}_RESULT $EVT_TAG: has_tagger=1 cluster_id={getattr(t,'cluster_id',-1)} "
          f"nu=({getattr(t,'nu_x',0):.2f},{getattr(t,'nu_y',0):.2f},{getattr(t,'nu_z',0):.2f}) "
          f"shw_sp_filled={getattr(t,'shw_sp_filled',-1)} shw_sp_n_20br1={getattr(t,'shw_sp_n_20br1_showers',-1)}")
except Exception as e:
    print(f'ROOT_CHECK_ERROR $EVT_TAG: {e}'); sys.exit(1)
PYEOF
else
    echo "${PFX}_RESULT $EVT_TAG: tracking-pr.root NOT FOUND (lar_exit=$LAR_EXIT)"
fi
echo "=== vertex / DV2 lines for $EVT_TAG ==="
grep -h "vertex_method\|DV2\|DL vertex failed\|dual_chain: OFF pass\|mvsa:\|selected main cluster" "$LOGFILE" 2>/dev/null | cut -c1-400 || echo "(none)"
echo "DV2_HOOK_LINES=$(cat "$OUTDIR/dv2_hook.jsonl" 2>/dev/null | wc -l)"
[ $LAR_EXIT -ne 0 ] && { echo "[WARN] lar non-zero for $EVT_TAG"; tail -20 "$LOGFILE"; }
echo "${PFX}_JOB_DONE_$EVT_TAG"
