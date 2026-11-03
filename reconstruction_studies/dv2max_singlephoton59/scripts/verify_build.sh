#!/usr/bin/env bash
# DV2-MAX x SP59 (2026-11-02): post-build hard gates (inside the slf7 container).
#   G1 HAVE_PYTHON_INC in BuildConfig.h          G2 libWCPPyUtil exports WCPPyUtil::DV2_Vertex
#   G3 libWireCellClus: DV2 placement strings, Fix2-v2 strings, provenance stamp, links WCPPyUtil
#   G4 lib_lightgbm.so loads under glibc 2.17    G5 pure-Python DV2 smoke (larsoft python 3.9)
#   G6 C++ bridge smoke (WCPPyUtil::DV2_Vertex -> DV2_Vertex.py -> bundle -> point)
set -uo pipefail
W=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102
WCT_INSTALL=$W/build/install/wct
WCT_BUILD=$W/build/wct-build
SITE=$W/build/pyenv/site39
BUNDLE=$W/source/wct-int/cfg/dv2max/r7_cloud/bundle.json
OUT=$W/build/validation
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
# larsoft libtorch v2_1_1b is on the sbndcode LD_LIBRARY_PATH; LD_LIBRARY_PATH beats the torch
# wheel's RUNPATH $ORIGIN, so the wheel's libtorch_python.so would bind the larsoft libtorch_cpu.so
# (undefined symbol).  The lar job never loads larsoft libtorch (LD_DEBUG of the CAND reco job), so the
# directory is dropped from the search path -- identically in both arms.
export LD_LIBRARY_PATH="$(echo "${LD_LIBRARY_PATH:-}" | tr ':' '\n' | grep -v '/scisoft/larsoft/libtorch/' | grep -v '^$' | tr '\n' ':' | sed 's/:$//')"
FAIL=0
gate() { if [ "$2" = 0 ]; then echo "GATE $1 PASS"; else echo "GATE $1 FAIL"; FAIL=1; fi; }
echo "=== verify_build: $(date) host $(hostname) glibc $(ldd --version | head -1)"

grep -n "HAVE_PYTHON" "$WCT_BUILD/WireCellUtil/BuildConfig.h"; grep -q "define HAVE_PYTHON_INC" "$WCT_BUILD/WireCellUtil/BuildConfig.h"; gate G1_HAVE_PYTHON_INC $?

PYU=$(ls "$WCT_INSTALL"/lib/libWCPPyUtil.so 2>/dev/null)
nm -DC "$PYU" | grep " T " | grep "WCPPyUtil::DV2_Vertex\|WCPPyUtil::SCN_Vertex"
nm -DC "$PYU" | grep " T " | grep -q "WCPPyUtil::DV2_Vertex"; gate G2_DV2_SYMBOL $?

CL=$WCT_INSTALL/lib/libWireCellClus.so
readelf -d "$CL" | grep NEEDED | grep -i "pyutil\|python"
n_dv2=$(strings "$CL" | grep -c "vertex_method {}: main vertex = {}\|vertex_method dv2_split_move: main vertex moved\|no DV2-MAX prediction")
n_fix2=$(strings "$CL" | grep -c "fix2_v2:")
n_diag=$(strings "$CL" | grep -c "fix2_diag:")
n_prov=$(strings "$CL" | grep -c "stamp_matching_bundle_id")
echo "strings: dv2=$n_dv2 fix2_v2=$n_fix2 fix2_diag=$n_diag(expect 0) provenance=$n_prov"
nm -DC "$CL" | grep "U WCPPyUtil::DV2_Vertex" || true
[ "$n_dv2" -ge 3 ] && [ "$n_fix2" -ge 4 ] && [ "$n_diag" -eq 0 ] && [ "$n_prov" -ge 1 ] && readelf -d "$CL" | grep -q "libWCPPyUtil.so"; gate G3_CLUS_CONTENT $?

LGB=$SITE/lightgbm/lib/lib_lightgbm.so
echo "lightgbm max GLIBC: $(objdump -T "$LGB" | grep -o 'GLIBC_[0-9.]*' | sort -V -u | tail -1)"
ldd "$LGB" | grep -i "not found\|gomp\|stdc"
! ldd "$LGB" 2>&1 | grep -q "not found\|version .* not found"; gate G4_LIGHTGBM_LOADS $?

export PYTHONPATH="$SITE:$WCT_INSTALL/python:${PYTHONPATH:-}"
export DV2_STRICT=1
echo "python: $(which python3) $(python3 --version 2>&1) PYTHONHOME=${PYTHONHOME:-}"
python3 "$W/scripts/dv2_py_smoke.py" "$SITE" "$WCT_INSTALL/python" "$BUNDLE" 2>&1 | tee "$OUT/dv2_py_smoke_container.txt" | tail -6
grep -q "^out \[" "$OUT/dv2_py_smoke_container.txt" && ! grep -q "Traceback" "$OUT/dv2_py_smoke_container.txt"; gate G5_PY_SMOKE $?

"$COMPILER_PATH/g++" -std=c++17 -O1 -I"$WCT_INSTALL/include" -I"$PYTHON_INCLUDE" "$W/scripts/dv2_cxx_smoke.cxx" \
    -L"$WCT_INSTALL/lib" -lWCPPyUtil -L"$PYTHON_LIB" -lpython3.9 -Wl,-rpath,"$WCT_INSTALL/lib" -Wl,-rpath,"$PYTHON_LIB" \
    -o "$W/build/validation/dv2_cxx_smoke" && \
LD_LIBRARY_PATH="$WCT_INSTALL/lib:$PYTHON_LIB:${LD_LIBRARY_PATH:-}" "$W/build/validation/dv2_cxx_smoke" "$BUNDLE" 2>&1 | tee "$OUT/dv2_cxx_smoke_container.txt" | tail -4
grep -q "DV2_CXX_SMOKE_PASS" "$OUT/dv2_cxx_smoke_container.txt"; gate G6_CXX_BRIDGE_SMOKE $?

{ echo "# $(date -u +%FT%TZ) $(hostname)"; sha256sum "$WCT_INSTALL"/lib/*.so "$W"/build/lwc-install/lib/*.so "$LGB" "$BUNDLE" "$(dirname "$BUNDLE")"/*.pt "$(dirname "$BUNDLE")"/*.txt "$(dirname "$BUNDLE")"/isotonic*.json 2>/dev/null; } > "$OUT/build_sha256.txt"
md5sum "$CL" "$PYU"
[ "$FAIL" = 0 ] && echo "VERIFY_BUILD_PASS" || echo "VERIFY_BUILD_FAIL"
