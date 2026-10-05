#!/bin/bash
# Compile the Fix 2 patched NeutrinoTaggerSinglePhoton.cxx and relink libWireCellClus.so
# Run inside the sbndcode container.
set -euo pipefail

CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005

echo "=== Fix 2 Build ==="
echo "Container: $(hostname)"
date

# Use GCC 12.1.0 from larsoft (same compiler used for original WCT build)
GCC12=/lus/flare/projects/neutrinoGPU/scisoft/larsoft/gcc/v12_1_0/Linux64bit+3.10-2.17/bin
if [ -x "$GCC12/g++" ]; then
    export PATH="$GCC12:$PATH"
fi
echo "GCC: $(which g++ 2>/dev/null || echo 'NOT FOUND')"
echo "GCC version: $(g++ --version 2>/dev/null | head -1 || echo 'unknown')"

CXX=$(which g++ 2>/dev/null || echo "$GCC12/g++")

# Exact flags from waf c4che (clus package)
CXXFLAGS=(
  -Wno-misleading-indentation -Wno-int-in-bool-context -Wvla -Wno-unused-variable
  -std=c++17 -DEIGEN_HAS_CXX11 -fPIC -O2 -ggdb3 -DEIGEN_FFTW_DEFAULT=1
  -Werror -Wall -Werror=return-type -pedantic -Wno-unused-local-typedefs
  -DSPDLOG_SHARED_LIB -DSPDLOG_COMPILED_LIB -DSPDLOG_FMT_EXTERNAL
  -DHAVE_SPDLOG -DHAVE_SPDLOG_INC
)

# Include paths (from waf c4che INCLUDES_* variables)
INC=(
  -I"$CAND/install/wct-clean/include"
  -I"$CAND/wct/clus/inc"
  -I"$CAND/wct/util/inc"
  -I"$CAND/wct/iface/inc"
  -I"$CAND/wct/aux/inc"
  -I"$CAND/build/wct-build-clean"
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/boost/v1_82_0/Linux64bit+3.10-2.17-e26-prof/include
  -I"$CAND/config/clean-bzip2/include"
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/eigen/v23_08_01_66e8f/include/eigen3
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/fftw/v3_3_10/Linux64bit+3.10-2.17/include
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/hdf5/v1_12_2a/Linux64bit+3.10-2.17-e26-prof/include
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/jsoncpp/v1_9_5a/Linux64bit+3.10-2.17-e26-prof/include
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/gojsonnet/v0_18_0/Linux64bit+3.10-2.17-e26/include
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/root/v6_28_12/Linux64bit+3.10-2.17-e26-p3915-prof/include
  -I/lus/flare/projects/neutrinoGPU/scisoft/larsoft/spdlog/v1_9_2/Linux64bit+3.10-2.17-e26-prof/include
  -I"$CAND/config/clean-fmt-include"
)

SRC="$DEV/wct-dev/clus/src/NeutrinoTaggerSinglePhoton.cxx"
OBJ="$DEV/build/NeutrinoTaggerSinglePhoton.cxx.2.o"
PROD_OBJ="$CAND/build/wct-build-clean/clus/src/NeutrinoTaggerSinglePhoton.cxx.2.o"
PROD_SO="$CAND/build/wct-build-clean/clus/libWireCellClus.so"
DEV_SO="$DEV/build/libWireCellClus.so"

echo ""
echo "=== Compiling ==="
echo "Source: $SRC"
echo "Output: $OBJ"
set -x
"$CXX" "${CXXFLAGS[@]}" "${INC[@]}" -c "$SRC" -o "$OBJ"
{ set +x; } 2>/dev/null

echo ""
echo "Object file: $(ls -lh $OBJ)"
echo ""

# Verify the object contains the fix2_onehop symbol (SPDLOG_LOGGER_DEBUG is inlined but the string will be there)
nm "$OBJ" | grep -i "singlephoton_tagger\|candidate_showers" | head -5 || true
strings "$OBJ" | grep "fix2_onehop" | head -5 || true

echo ""
echo "=== Relinking libWireCellClus.so ==="
echo "All .o files from production build EXCEPT the patched one, plus our new .o"

# Get all object files from the production clus build directory
ALL_OBJ=($(find "$CAND/build/wct-build-clean/clus/src" -name "*.o" 2>/dev/null | sort))
FILTERED_OBJ=()
for o in "${ALL_OBJ[@]}"; do
    if [[ "$o" != *"NeutrinoTaggerSinglePhoton"* ]]; then
        FILTERED_OBJ+=("$o")
    fi
done
FILTERED_OBJ+=("$OBJ")  # add our patched object

echo "Objects to link: ${#FILTERED_OBJ[@]} (replacing NeutrinoTaggerSinglePhoton.cxx.2.o)"

# Link flags: same libraries as production libWireCellClus.so
# Get from production .so's link (nm, ldd)
LINK_LIBS=(
  -L"$CAND/build/wct-build-clean/aux"   -lWireCellAux
  -L"$CAND/build/wct-build-clean/iface" -lWireCellIface
  -L"$CAND/build/wct-build-clean/mcs"   -lWireCellMcs
  -L"$CAND/build/wct-build-clean/util"  -lWireCellUtil
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/root/v6_28_12/Linux64bit+3.10-2.17-e26-p3915-prof/lib
  -lCore -lRIO -lHist -lTree -lMathCore -lGpad -lGraf -lGraf3d
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/boost/v1_82_0/Linux64bit+3.10-2.17-e26-prof/lib
  -lboost_iostreams -lboost_filesystem -lboost_system
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/spdlog/v1_9_2/Linux64bit+3.10-2.17-e26-prof/lib
  -lspdlog
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/hdf5/v1_12_2a/Linux64bit+3.10-2.17-e26-prof/lib
  -lhdf5 -lhdf5_hl
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/jsoncpp/v1_9_5a/Linux64bit+3.10-2.17-e26-prof/lib
  -ljsoncpp
)

set -x
"$CXX" -shared -fPIC -o "$DEV_SO" "${FILTERED_OBJ[@]}" "${LINK_LIBS[@]}" 2>&1
{ set +x; } 2>/dev/null

echo ""
echo "=== Dev library: $(ls -lh $DEV_SO) ==="
file "$DEV_SO"

# Verify fix2_onehop string is present in the new .so
strings "$DEV_SO" | grep "fix2_onehop" | head -5 && echo "FIX2_STRINGS_PRESENT" || echo "WARNING: fix2 strings not found"
echo ""
echo "BUILD_COMPLETE"
date
