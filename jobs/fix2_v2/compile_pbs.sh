#!/bin/bash
#PBS -N fix2_compile
#PBS -A neutrinoGPU::wirecell_2026
#PBS -q by-gpu
#PBS -l select=1:ncpus=4:ngpus=1:mem=32gb
#PBS -l walltime=00:15:00
#PBS -l filesystems=eagle:grand:home
#PBS -o /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005/build/compile_pbs.out
#PBS -e /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005/build/compile_pbs.err

set -euo pipefail

CONTAINER=/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif
LARSOFT_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs
SBND_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/sbnd-v10_14_02_04_delta.squashfs

DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005
CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930

echo "=== PBS Fix2 Compile Job ==="
echo "Node: $(hostname)"
echo "Date: $(date)"

module use /soft/modulefiles
module load spack-pe-base
module load apptainer

apptainer exec --fakeroot \
    --bind /lus/eagle \
    --bind /lus/grand \
    --overlay "$LARSOFT_SQ":ro \
    --overlay "$SBND_SQ":ro \
    "$CONTAINER" \
    bash -lc "$(cat <<'INNEREOF'
set -euo pipefail

DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005
CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930

echo "=== Fix 2 Compile (inside container) ==="
echo "Container host: $(hostname)"
date

# Source sbndcode env for library paths (sets COMPILER_PATH to GCC 12)
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true

# Use the GCC 12 from larsoft (same compiler as original WCT build)
GCC12=/lus/flare/projects/neutrinoGPU/scisoft/larsoft/gcc/v12_1_0/Linux64bit+3.10-2.17/bin
if [ -x "$GCC12/g++" ]; then
    CXX="$GCC12/g++"
else
    CXX=$(which g++)
fi
echo "CXX: $CXX"
echo "GCC version: $($CXX --version | head -1)"

CXXFLAGS=(
  -Wno-misleading-indentation -Wno-int-in-bool-context -Wvla -Wno-unused-variable
  -std=c++17 -DEIGEN_HAS_CXX11 -fPIC -O2 -ggdb3 -DEIGEN_FFTW_DEFAULT=1
  -Werror -Wall -Werror=return-type -pedantic -Wno-unused-local-typedefs
  -DSPDLOG_SHARED_LIB -DSPDLOG_COMPILED_LIB -DSPDLOG_FMT_EXTERNAL
  -DHAVE_SPDLOG -DHAVE_SPDLOG_INC
)

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
strings "$OBJ" | grep "fix2_onehop" | head -3 && echo "FIX2_STRINGS_IN_OBJ" || echo "WARNING: fix2 strings not found in obj"

echo ""
echo "=== Relinking libWireCellClus.so ==="
ALL_OBJ=($(find "$CAND/build/wct-build-clean/clus/src" -name "*.o" 2>/dev/null | sort))
FILTERED_OBJ=()
for o in "${ALL_OBJ[@]}"; do
    if [[ "$o" != *"NeutrinoTaggerSinglePhoton"* ]]; then
        FILTERED_OBJ+=("$o")
    fi
done
FILTERED_OBJ+=("$OBJ")
echo "Objects to link: ${#FILTERED_OBJ[@]}"

LINK_LIBS=(
  -L"$CAND/build/wct-build-clean/aux"       -lWireCellAux
  -L"$CAND/build/wct-build-clean/iface"     -lWireCellIface
  -L"$CAND/build/wct-build-clean/mcs"       -lWireCellMcs
  -L"$CAND/build/wct-build-clean/util"      -lWireCellUtil
  -L"$CAND/build/wct-build-clean/quickhull" -lWCPQuickhull
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/boost/v1_82_0/Linux64bit+3.10-2.17-e26-prof/lib
  -lboost_iostreams -lboost_filesystem -lboost_system
  -lboost_graph -lboost_thread -lboost_program_options -lboost_regex
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/spdlog/v1_9_2/Linux64bit+3.10-2.17-e26-prof/lib64
  -lspdlog
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/jsoncpp/v1_9_5a/Linux64bit+3.10-2.17-e26-prof/lib
  -ljsoncpp
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/gojsonnet/v0_18_0/Linux64bit+3.10-2.17-e26/lib
  -ljsonnet
  -L/lus/flare/projects/neutrinoGPU/scisoft/larsoft/fftw/v3_3_10/Linux64bit+3.10-2.17/lib
  -lfftw3f
  -lz -ldl
)

set -x
"$CXX" -shared -fPIC -o "$DEV_SO" "${FILTERED_OBJ[@]}" "${LINK_LIBS[@]}" 2>&1
{ set +x; } 2>/dev/null

echo ""
echo "=== Dev library: $(ls -lh $DEV_SO) ==="
file "$DEV_SO"
strings "$DEV_SO" | grep "fix2_onehop" | head -3 && echo "FIX2_STRINGS_PRESENT" || echo "WARNING: fix2 strings not found"
echo ""
echo "BUILD_COMPLETE"
date
INNEREOF
)" 2>&1 | tee "$DEV/build/compile_container.log"
CONTAINER_EXIT="${PIPESTATUS[0]}"

echo ""
echo "Container exit: $CONTAINER_EXIT"
if [ "$CONTAINER_EXIT" -eq 0 ]; then
    echo "FIX2_BUILD_PASS"
else
    echo "FIX2_BUILD_FAIL"
    exit 1
fi
