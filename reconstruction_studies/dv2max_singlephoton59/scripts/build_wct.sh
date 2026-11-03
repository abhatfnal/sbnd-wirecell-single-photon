#!/usr/bin/env bash
# DV2-MAX x SP59 (2026-11-02): full WCT build of the integration tree
#   W/source/wct-int = PR #543 head feb3ddeb + Fix2-v2 (net NTSP) + bundle-provenance
#   stamp (uncommitted; see W/source/PATCH.diff)
# Recipe = latest_wct_master_migration_candidate_20260930/scripts/run_candidate_clean_wct_build.sh
# (same container, same larsoft externals, same clean spdlog/bzip2 wrappers, same
# CXXFLAGS) with ONE addition: the embedded Python (larsoft python v3_9_15), so
# pyutil (WCPPyUtil: SCN_Vertex + DV2_Vertex) is built and HAVE_PYTHON_INC is defined.
set -euo pipefail
W=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102
CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
WCT_SRC=$W/source/wct-int
WCT_BUILD=$W/build/wct-build
WCT_INSTALL=$W/build/install/wct
LOGDIR=$W/logs/build
CLEAN_PKGCONFIG=$CAND/config/clean-pkgconfig
CLEAN_BZ2=$CAND/config/clean-bzip2
mkdir -p "$WCT_BUILD" "$WCT_INSTALL" "$LOGDIR"
echo "=== build_wct: $(date) host $(hostname)"

source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
_strip_path() { echo "${1:-}" | tr ':' '\n' | grep -v 'haiwang-current\|wct-ap-yuhw' | grep -v '^$' | tr '\n' ':' | sed 's/:$//'; }
for v in PKG_CONFIG_PATH LD_LIBRARY_PATH PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH CMAKE_PREFIX_PATH ROOT_INCLUDE_PATH; do
    export $v="$(_strip_path "${!v:-}")"
done
while IFS='=' read -r var val; do
    case "$val" in *haiwang-current/opt*|*wct-ap-yuhw*) unset "$var" 2>/dev/null || true ;; esac
done < <(env | grep -E 'haiwang-current/opt|wct-ap-yuhw' || true)
export PKG_CONFIG_PATH="$CLEAN_PKGCONFIG:${PKG_CONFIG_PATH:-}"
if env | grep -qE 'haiwang-current/opt|wct-ap-yuhw'; then echo "CLEAN_ENV_GATE_FAIL"; exit 1; fi
echo "CLEAN_ENV_GATE_PASS"

GCC_BIN=$(dirname "$(which gcc)")
export CC="$GCC_BIN/gcc" CXX="$GCC_BIN/g++" FORT="$GCC_BIN/gfortran"
export CXXFLAGS='-Wno-misleading-indentation -Wno-int-in-bool-context -Wvla -Wno-unused-variable'
echo "CXX: $CXX ($($CXX --version | head -1))"
echo "PYTHON_INCLUDE=$PYTHON_INCLUDE"
echo "PYTHON_LIB=$PYTHON_LIB"
ls -la "$PYTHON_INCLUDE/Python.h" "$PYTHON_LIB"/libpython3.9*.so* || { echo "WCT_BUILD_FAIL: python headers/lib missing"; exit 1; }

cd "$WCT_SRC"
python3 "$WCT_SRC/wcb" configure \
    --out="$WCT_BUILD" \
    --prefix="$WCT_INSTALL" \
    --with-jsoncpp="$JSONCPP_FQ_DIR" \
    --with-jsonnet="$GOJSONNET_FQ_DIR" \
    --with-spdlog=yes \
    --with-eigen-include="$EIGEN_INC" \
    --with-fftw="$FFTW_FQ_DIR" \
    --with-fftw-include="$FFTW_INC" \
    --with-fftw-lib="$FFTW_LIBRARY" \
    --boost-includes="$BOOST_INC" \
    --boost-libs="$BOOST_LIB" \
    --boost-mt \
    --with-hdf5="$HDF5_FQ_DIR" \
    --with-tbb=no \
    --with-root="$ROOTSYS" \
    --with-bzip2-include="$CLEAN_BZ2/include" \
    --with-bzip2-lib="$CLEAN_BZ2/lib" \
    --with-python-include="$PYTHON_INCLUDE" \
    --with-python-lib="$PYTHON_LIB" \
    --with-python-libs=python3.9 \
    2>&1 | tee "$LOGDIR/wct_configure.log" | tail -40
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "WCT_BUILD_FAIL (configure)"; exit 1; }
if grep -q 'Removing package "pyutil"' "$LOGDIR/wct_configure.log"; then echo "WCT_BUILD_FAIL: pyutil removed (no Python)"; exit 1; fi
grep -q "HAVE_PYTHON_INC" "$WCT_BUILD/WireCellUtil/BuildConfig.h" || { echo "WCT_BUILD_FAIL: HAVE_PYTHON_INC not in BuildConfig.h"; exit 1; }
echo "PYTHON_CONFIG_GATE_PASS"
if grep -q 'haiwang-current\|wct-ap-yuhw' "$WCT_BUILD/c4che/_cache.py"; then echo "WCT_BUILD_FAIL (waf cache contaminated)"; exit 1; fi

python3 "$WCT_SRC/wcb" -j"${NCPU:-32}" --notests install 2>&1 | tee "$LOGDIR/wct_build.log" | tail -20
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "WCT_BUILD_FAIL (build)"; tail -80 "$LOGDIR/wct_build.log"; exit 1; }
find "$WCT_SRC" -name 'miniz.h' -exec cp {} "$WCT_INSTALL/include/WireCellUtil/custard/" \; 2>/dev/null || true
ls "$WCT_INSTALL/lib/"
sha256sum "$WCT_INSTALL/lib/"*.so | sort -k2 > "$W/build/validation/wct_install_sha256.txt"
echo "WCT_BUILD_PASS"
