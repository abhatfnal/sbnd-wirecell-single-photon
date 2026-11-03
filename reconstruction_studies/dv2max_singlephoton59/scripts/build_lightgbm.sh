#!/usr/bin/env bash
# DV2-MAX x SP59 (2026-11-02): rebuild LightGBM 4.6.0's lib_lightgbm.so from the
# PyPI sdist (sha256 cb1c5972...) INSIDE the slf7 container with the larsoft GCC 12,
# because the only 4.x x86_64 wheel (manylinux_2_28) references logf@GLIBC_2.27 and
# the container has glibc 2.17.  Same version, same sources; only the build host
# differs.  The wheel's own .so is kept next to it as lib_lightgbm.so.wheel_manylinux_2_28.
set -euo pipefail
W=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102
SRC=$W/build/pyenv/src/lightgbm-4.6.0
BLD=$W/build/lightgbm-build
SITE=$W/build/pyenv/site39
CMAKE=$W/build/pyenv/tools/cmake/data/bin/cmake
echo "=== build_lightgbm: $(date) host $(hostname)"
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
export CC="$COMPILER_PATH/gcc" CXX="$COMPILER_PATH/g++"
echo "CXX: $CXX ($($CXX --version | head -1))"
echo "cmake: $($CMAKE --version | head -1)"
echo "glibc: $(ldd --version | head -1)"
rm -rf "$BLD"; mkdir -p "$BLD"
"$CMAKE" -S "$SRC" -B "$BLD" -DCMAKE_BUILD_TYPE=Release -D__BUILD_FOR_PYTHON=ON -DBUILD_CLI=OFF -DUSE_OPENMP=ON
"$CMAKE" --build "$BLD" -j "${NCPU:-16}"
LIB=$(find "$BLD" "$SRC" -name lib_lightgbm.so -newer "$BLD/CMakeCache.txt" | head -1)
[ -n "$LIB" ] || { echo "LIGHTGBM_BUILD_FAIL: lib_lightgbm.so not found"; exit 1; }
echo "built: $LIB"
DST=$SITE/lightgbm/lib/lib_lightgbm.so
[ -f "$DST.wheel_manylinux_2_28" ] || cp --preserve=timestamps "$DST" "$DST.wheel_manylinux_2_28"
cp --preserve=timestamps "$LIB" "$DST"
echo "max GLIBC symbol: $(objdump -T "$DST" | grep -o 'GLIBC_[0-9.]*' | sort -V -u | tail -1)"
sha256sum "$DST" "$DST.wheel_manylinux_2_28"
echo "LIGHTGBM_BUILD_PASS"
