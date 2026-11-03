#!/usr/bin/env bash
# DV2-MAX x SP59 (2026-11-02): path-redirected copy of
# latest_wct_master_migration_candidate_20260930/scripts/run_candidate_clean_lwc_build.sh
# (same larwirecell source, same cmake recipe; only WCT install / build / install / log dirs moved into W).
# run_candidate_clean_lwc_build.sh
#
# Rebuild larwirecell against the clean WCT install ($CAND/install/wct-clean).
# Clean build dirs: build/lwc-build-clean + build/lwc-install-clean.
#
# Precondition: CANDIDATE_CLEAN_WCT_BUILD_PASS must already be complete.
# Critical: removes -I$BASE_OPT/include from CMAKE_CXX_FLAGS (was haiwang-current).
#           Uses clean-fmt-include for fmt headers instead.
#
# Produces:
#   $CAND/build/lwc-build-clean/    cmake build dir
#   $CAND/build/lwc-install-clean/  larwirecell install
#   $CAND/validation/clean_lwc_rpath_audit.txt
#   $CAND/validation/clean_candidate_dependency_gate.txt
# Ends with: CANDIDATE_CLEAN_LWC_BUILD_PASS or CANDIDATE_CLEAN_LWC_BUILD_FAIL

set -euo pipefail
echo "=== Candidate Clean LWC Build ==="
echo "Host: $(hostname)"
echo "Job: ${PBS_JOBID:-local}"
date

CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
LWC_SRC=$CAND/larwirecell-src
WCT_INSTALL_CLEAN=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102/build/install/wct
LWC_BUILD_CLEAN=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102/build/lwc-build
LWC_INSTALL_CLEAN=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102/build/lwc-install
LOGDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102/logs/build
VALDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102/build/validation
CLEAN_PKGCONFIG=$CAND/config/clean-pkgconfig
CLEAN_FMT_INC=$CAND/config/clean-fmt-include

mkdir -p "$LWC_BUILD_CLEAN" "$LWC_INSTALL_CLEAN/lib" "$LOGDIR" "$VALDIR"

LOG="$LOGDIR/clean_lwc_build.log"
exec > >(tee -a "$LOG") 2>&1

# Preconditions
[ -d "$LWC_SRC" ] || { echo "FATAL: larwirecell source missing: $LWC_SRC"; exit 1; }
[ -d "$WCT_INSTALL_CLEAN/lib" ] || { echo "FATAL: clean WCT install missing: $WCT_INSTALL_CLEAN"; exit 1; }
[ -f "$WCT_INSTALL_CLEAN/lib/libWireCellAux.so" ] || { echo "FATAL: libWireCellAux.so missing from clean WCT install"; exit 1; }
[ -f "$CLEAN_PKGCONFIG/spdlog.pc" ] || { echo "FATAL: clean spdlog.pc missing"; exit 1; }
[ -d "$CLEAN_FMT_INC/fmt" ] || { echo "FATAL: clean-fmt-include/fmt missing"; exit 1; }
echo "All preconditions met."

echo ""
echo "WCT_INSTALL_CLEAN: $WCT_INSTALL_CLEAN"
echo "Clean WCT libs:"
ls "$WCT_INSTALL_CLEAN/lib/libWireCell"*.so 2>/dev/null | head -10 || true   # DV2SP59: '|| true' added (logging pipe; SIGPIPE under pipefail)

echo ""
echo "============================================================"
echo "STEP 1: Source sbndcode env and strip haiwang-current/opt"
echo "============================================================"

source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true

_strip_path() {
    echo "${1:-}" | tr ':' '\n' | grep -v 'haiwang-current\|wct-ap-yuhw' | grep -v '^$' | tr '\n' ':' | sed 's/:$//'
}

export PKG_CONFIG_PATH=$(_strip_path "${PKG_CONFIG_PATH:-}")
export LD_LIBRARY_PATH=$(_strip_path "${LD_LIBRARY_PATH:-}")
export PATH=$(_strip_path "${PATH:-}")
export CPATH=$(_strip_path "${CPATH:-}")
export C_INCLUDE_PATH=$(_strip_path "${C_INCLUDE_PATH:-}")
export CPLUS_INCLUDE_PATH=$(_strip_path "${CPLUS_INCLUDE_PATH:-}")
export LIBRARY_PATH=$(_strip_path "${LIBRARY_PATH:-}")
export CMAKE_PREFIX_PATH=$(_strip_path "${CMAKE_PREFIX_PATH:-}")
export ROOT_INCLUDE_PATH=$(_strip_path "${ROOT_INCLUDE_PATH:-}")

while IFS='=' read -r var val; do
    case "$val" in
        *haiwang-current/opt*|*wct-ap-yuhw*) unset "$var" 2>/dev/null || true ;;
    esac
done < <(env | grep -E 'haiwang-current/opt|wct-ap-yuhw' || true)

export PKG_CONFIG_PATH="$CLEAN_PKGCONFIG:${PKG_CONFIG_PATH:-}"

echo ""
echo "============================================================"
echo "STEP 2: Hard gate"
echo "============================================================"

CONTAMINATED_VARS=$(env | grep -E 'haiwang-current/opt|wct-ap-yuhw' || true)
if [ -n "$CONTAMINATED_VARS" ]; then
    echo "FATAL: haiwang-current/opt or wct-ap-yuhw still in environment:"
    echo "$CONTAMINATED_VARS"
    echo "CLEAN_ENV_GATE_FAIL"
    exit 1
fi
echo "CLEAN_ENV_GATE_PASS"

echo ""
echo "============================================================"
echo "STEP 2b: Compiler setup (explicit GCC — override any icpx/icc from env)"
echo "============================================================"
GCC_BIN=$(dirname "$(which gcc)")
export CC="$GCC_BIN/gcc"
export CXX="$GCC_BIN/g++"
echo "CC:  $CC  ($(${CC} --version | head -1))"
echo "CXX: $CXX  ($(${CXX} --version | head -1))"

echo ""
echo "============================================================"
echo "STEP 3: Override WireCell env to clean install"
echo "============================================================"

export WIRECELL_FQ_DIR="$WCT_INSTALL_CLEAN"
export WIRECELL_INC="$WCT_INSTALL_CLEAN/include"
export WIRECELL_LIB="$WCT_INSTALL_CLEAN/lib"
export WIRECELL_VERSION="0.0.0-dv2int-feb3ddeb-sp"
export LD_LIBRARY_PATH="$WCT_INSTALL_CLEAN/lib:${LD_LIBRARY_PATH:-}"
export PATH="$WCT_INSTALL_CLEAN/bin:$PATH"

echo "WIRECELL_FQ_DIR=$WIRECELL_FQ_DIR"
echo "wire-cell binary: $(ls $WCT_INSTALL_CLEAN/bin/wire-cell 2>/dev/null && echo OK || echo MISSING)"

echo ""
echo "============================================================"
echo "STEP 4: Find cmake"
echo "============================================================"

source /lus/flare/projects/neutrinoGPU/scisoft/larsoft/setup 2>/dev/null || true

LARSOFT_CMAKE_BASE=/lus/flare/projects/neutrinoGPU/scisoft/larsoft/cmake
CMAKE=""
for VER in v3_27_4 v3_26_4 v3_25_2 v3_24_1 v3_22_2; do
    CAND_CM="$LARSOFT_CMAKE_BASE/$VER/Linux64bit+3.10-2.17/bin/cmake"
    if [ -x "$CAND_CM" ]; then CMAKE="$CAND_CM"; break; fi
done
[ -n "$CMAKE" ] || { echo "FATAL: cmake not found"; exit 1; }
echo "cmake: $($CMAKE --version | head -1)"

echo ""
echo "============================================================"
echo "STEP 5: Discover cetmodules and package dirs"
echo "============================================================"

ENV_FILE=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env

FQ_DIRS=$(grep 'declare -x [A-Z0-9_]*_FQ_DIR=' "$ENV_FILE" 2>/dev/null \
    | sed 's/declare -x [A-Z0-9_]*_FQ_DIR="\([^"]*\)"/\1/' \
    | grep '^/' | sort -u | tr '\n' ';')

PLAIN_DIRS=$(grep 'declare -x [A-Z0-9_]*_DIR=' "$ENV_FILE" 2>/dev/null \
    | grep -v '_FQ_DIR=\|_BUILDDIR=\|_BUILDBASE=\|_INC=\|_LIB=\|_BIN=' \
    | sed 's/declare -x [A-Z0-9_]*_DIR="\([^"]*\)"/\1/' \
    | grep '^/lus/flare' | sort -u | tr '\n' ';')

ALL_FQ_DIRS="${FQ_DIRS}${PLAIN_DIRS}"
ALL_FQ_DIRS="${ALL_FQ_DIRS%;}"

set +e  # package discovery find/grep may exit non-zero

CETMODULES_BASE=/lus/flare/projects/neutrinoGPU/scisoft/larsoft/cetmodules
CETMODULES_CFG=$(find $CETMODULES_BASE -name 'cetmodulesConfig.cmake' -maxdepth 8 2>/dev/null | grep "v3_24" | head -1)
if [ -z "$CETMODULES_CFG" ]; then
    CETMODULES_CFG=$(find $CETMODULES_BASE -name 'cetmodulesConfig.cmake' -maxdepth 8 2>/dev/null | tail -1)
fi
if [ -n "$CETMODULES_CFG" ]; then
    _d=$(dirname "$CETMODULES_CFG"); _d=$(dirname "$_d"); _d=$(dirname "$_d"); CETMODULES_DIR=$(dirname "$_d")
    CETMODULES_CMAKE_DIR=$(dirname "$CETMODULES_CFG")
else
    CETMODULES_DIR=$CETMODULES_BASE/v3_24_00/slf7.x86_64
    CETMODULES_CMAKE_DIR="$CETMODULES_DIR"
fi

PKG_CFG_DIRS=$(echo "$ALL_FQ_DIRS" | tr ';' '\n' | while read d; do
    [ -d "$d/lib/pkgconfig" ]   && echo "$d/lib/pkgconfig"
    [ -d "$d/lib64/pkgconfig" ] && echo "$d/lib64/pkgconfig"
    true
done | sort -u | tr '\n' ':')

# Prepend clean pkgconfig (NOT haiwang-current); filter haiwang-current from PKG_CFG_DIRS
PKG_CFG_DIRS_CLEAN=$(echo "$PKG_CFG_DIRS" | tr ':' '\n' | grep -v 'haiwang-current\|wct-ap-yuhw' | tr '\n' ':' | sed 's/:$//')
export PKG_CONFIG_PATH="$CLEAN_PKGCONFIG:${PKG_CFG_DIRS_CLEAN}:${PKG_CONFIG_PATH:-}"

ALL_PREFIX="$WCT_INSTALL_CLEAN;$CETMODULES_DIR;$ALL_FQ_DIRS"

add_pkg_dir() {
    local pkg_lower="$1" fq_dir="$2" cmake_subdir="${3:-$1}" cfg_dir=""
    [ -z "$fq_dir" ] && return 0
    if   [ -d "$fq_dir/lib/$cmake_subdir/cmake" ];   then cfg_dir="$fq_dir/lib/$cmake_subdir/cmake"
    elif [ -d "$fq_dir/lib/cmake/$cmake_subdir" ];    then cfg_dir="$fq_dir/lib/cmake/$cmake_subdir"
    elif [ -d "$fq_dir/share/cmake/$cmake_subdir" ];  then cfg_dir="$fq_dir/share/cmake/$cmake_subdir"
    elif [ -d "$fq_dir/share/$cmake_subdir/cmake" ];  then cfg_dir="$fq_dir/share/$cmake_subdir/cmake"
    else
        local found_cfg
        found_cfg=$(find "$fq_dir" -maxdepth 8 -name "${cmake_subdir}Config.cmake" 2>/dev/null | head -1)
        if [ -n "$found_cfg" ]; then cfg_dir=$(dirname "$found_cfg"); fi
    fi
    if [ -n "$cfg_dir" ]; then
        PKG_DIR_FLAGS="$PKG_DIR_FLAGS -D${pkg_lower}_DIR=$cfg_dir"
        echo "  ${pkg_lower}_DIR=$cfg_dir"
    else
        echo "  WARNING: no cmake config for $pkg_lower in $fq_dir"
    fi
    return 0
}

PKG_DIR_FLAGS=""
add_pkg_dir "canvas"              "$CANVAS_FQ_DIR"
add_pkg_dir "messagefacility"     "$MESSAGEFACILITY_FQ_DIR"
add_pkg_dir "fhiclcpp"            "$FHICLCPP_FQ_DIR"
add_pkg_dir "cetlib"              "$CETLIB_FQ_DIR"
add_pkg_dir "cetlib_except"       "$CETLIB_EXCEPT_FQ_DIR"
add_pkg_dir "hep_concurrency"     "$HEP_CONCURRENCY_FQ_DIR"
add_pkg_dir "art"                 "$ART_FQ_DIR"
add_pkg_dir "art_root_io"         "$ART_ROOT_IO_FQ_DIR"
add_pkg_dir "canvas_root_io"      "$CANVAS_ROOT_IO_FQ_DIR"
add_pkg_dir "artg4tk"             "${ARTG4TK_FQ_DIR:-}"
add_pkg_dir "larsim"              "$LARSIM_FQ_DIR"
add_pkg_dir "larcore"             "$LARCORE_FQ_DIR"
add_pkg_dir "lardata"             "$LARDATA_FQ_DIR"
add_pkg_dir "larevt"              "$LAREVT_FQ_DIR"
add_pkg_dir "lardataobj"          "$LARDATAOBJ_FQ_DIR"
add_pkg_dir "larcoreobj"          "$LARCOREOBJ_FQ_DIR"
add_pkg_dir "larcorealg"          "$LARCOREALG_FQ_DIR"
add_pkg_dir "lardataalg"          "$LARDATAALG_FQ_DIR"
add_pkg_dir "larvecutils"         "${LARVECUTILS_FQ_DIR:-}"
add_pkg_dir "larana"              "$LARANA_FQ_DIR"
add_pkg_dir "larreco"             "$LARRECO_FQ_DIR"
add_pkg_dir "larsoft"             "${LARSOFT_FQ_DIR:-}"
add_pkg_dir "nusimdata"           "$NUSIMDATA_FQ_DIR"
add_pkg_dir "sbnobj"              "${SBNOBJ_FQ_DIR:-}"
add_pkg_dir "sbnalg"              "${SBNALG_FQ_DIR:-}"
add_pkg_dir "sbncode"             "${SBNCODE_FQ_DIR:-}"
add_pkg_dir "nugen"               "${NUGEN_FQ_DIR:-}"
add_pkg_dir "nug4"                "${NUG4_FQ_DIR:-}"
add_pkg_dir "nurandom"            "${NURANDOM_FQ_DIR:-}"
add_pkg_dir "nutools"             "${NUTOOLS_FQ_DIR:-}"
add_pkg_dir "ifdh_art"            "${IFDH_ART_FQ_DIR:-}"
add_pkg_dir "larg4"               "${LARG4_FQ_DIR:-}"
add_pkg_dir "gallery"             "${GALLERY_FQ_DIR:-}"
add_pkg_dir "systematicstools"    "${SYSTEMATICSTOOLS_FQ_DIR:-}"
add_pkg_dir "nusystematics"       "${NUSYSTEMATICS_FQ_DIR:-}"
add_pkg_dir "hep_hpc"             "${HEP_HPC_FQ_DIR:-}"
add_pkg_dir "geant4reweight"      "${GEANT4REWEIGHT_FQ_DIR:-}"
add_pkg_dir "ppfx"                "${PPFX_FQ_DIR:-}"

H5CPP_CMAKE="${HEP_HPC_FQ_DIR:-}/lib/hep_hpc/cmake"
[ -d "$H5CPP_CMAKE" ] && PKG_DIR_FLAGS="$PKG_DIR_FLAGS -Dh5cpp_DIR=$H5CPP_CMAKE"

if [ -n "${CLHEP_BASE:-}" ] && [ -n "${CLHEP_LIB:-}" ]; then
    _clhep_cmake="$CLHEP_BASE/lib/$CLHEP_LIB"
    [ -d "$_clhep_cmake" ] && PKG_DIR_FLAGS="$PKG_DIR_FLAGS -DCLHEP_DIR=$_clhep_cmake"
fi
if [ -n "${XERCESCROOT:-}" ]; then
    _xerces_cmake="$XERCESCROOT/lib/cmake/XercesC"
    [ -d "$_xerces_cmake" ] && PKG_DIR_FLAGS="$PKG_DIR_FLAGS -DXercesC_DIR=$_xerces_cmake"
fi
if [ -n "${GEANT4_FQ_DIR:-}" ]; then
    _g4_cmake=$(find "$GEANT4_FQ_DIR/lib64" -maxdepth 1 -name 'Geant4-*' -type d 2>/dev/null | head -1)
    [ -n "$_g4_cmake" ] && PKG_DIR_FLAGS="$PKG_DIR_FLAGS -DGeant4_DIR=$_g4_cmake"
fi
if [ -n "${NUFINDER_DIR:-}" ]; then
    _nufinder_cmake="$NUFINDER_DIR/share/nufinder/cmake"
    [ -d "$_nufinder_cmake" ] && PKG_DIR_FLAGS="$PKG_DIR_FLAGS -Dnufinder_DIR=$_nufinder_cmake"
fi

CRY_FQ=/lus/flare/projects/neutrinoGPU/scisoft/larsoft/cry/v1_7q/Linux64bit+3.10-2.17-e26-prof/cry_v1.7
EXTRA_FLAGS=""
[ -f "$CRY_FQ/lib/libCRY.so" ] && EXTRA_FLAGS="-DCRY_LIBRARY=$CRY_FQ/lib/libCRY.so -DCRY_INCLUDE_DIRS=$CRY_FQ/src -DCRY_FOUND=TRUE"

set -e

echo ""
echo "============================================================"
echo "STEP 6: cmake configure (larwirecell against clean WCT)"
echo "============================================================"
echo "LWC_SRC:          $LWC_SRC"
echo "LWC_BUILD_CLEAN:  $LWC_BUILD_CLEAN"
echo "LWC_INSTALL_CLEAN: $LWC_INSTALL_CLEAN"
echo "Time: $(date)"

$CMAKE \
    -S "$LWC_SRC" \
    -B "$LWC_BUILD_CLEAN" \
    -DCMAKE_PREFIX_PATH="$ALL_PREFIX" \
    -DCMAKE_INSTALL_PREFIX="$LWC_INSTALL_CLEAN" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DWIRECELL_FQ_DIR="$WCT_INSTALL_CLEAN" \
    -DWIRE-CELL="$WCT_INSTALL_CLEAN/bin/wire-cell" \
    -DWireCell_INCLUDE_DIR="$WCT_INSTALL_CLEAN/include" \
    -Dcetmodules_DIR="$CETMODULES_CMAKE_DIR" \
    -DBOOST_ROOT="$BOOST_FQ_DIR" \
    -DBoost_INCLUDE_DIR="$BOOST_INC" \
    -DBoost_LIBRARY_DIR_RELEASE="$BOOST_LIB" \
    -DBoost_LIBRARY_DIR_DEBUG="$BOOST_LIB" \
    -DTBB_ROOT="${TBBROOT:-}" \
    -DTBB_DIR="${TBB_FQ_DIR:-}/lib/cmake/TBB" \
    $PKG_DIR_FLAGS \
    $EXTRA_FLAGS \
    -DCMAKE_CXX_FLAGS="-DSPDLOG_FMT_EXTERNAL -DSPDLOG_SHARED_LIB -DSPDLOG_COMPILED_LIB -I$CLEAN_FMT_INC" \
    2>&1 | tee "$LOGDIR/clean_lwc_cmake.log" | tail -60
CMAKE_EXIT=$?
echo "cmake configure exit: $CMAKE_EXIT  Time: $(date)"
[ "$CMAKE_EXIT" -ne 0 ] && { echo "CANDIDATE_CLEAN_LWC_BUILD_FAIL (cmake configure)"; tail -40 "$LOGDIR/clean_lwc_cmake.log"; exit 1; }

echo "Cmake cache WireCell check:"
grep "WireCell_INCLUDE_DIR\|WireCell_Util_LIBRARY\|WireCell_FQ_DIR" "$LWC_BUILD_CLEAN/CMakeCache.txt" 2>/dev/null | head -8 || true   # DV2SP59: '|| true' added (logging pipe; SIGPIPE under pipefail)

# Verify cmake cache points to clean WCT (not original install or haiwang-current)
if grep -qE 'haiwang-current|wct-ap-yuhw|install/wct[^-]' "$LWC_BUILD_CLEAN/CMakeCache.txt" 2>/dev/null; then
    echo "WARNING: suspicious cmake cache entries:"
    grep -E 'haiwang-current|wct-ap-yuhw|install/wct[^-]' "$LWC_BUILD_CLEAN/CMakeCache.txt" | head -10 || true   # DV2SP59: '|| true' added (logging pipe; SIGPIPE under pipefail)
fi

echo ""
echo "============================================================"
echo "STEP 7: cmake build + install"
echo "============================================================"
echo "Time: $(date)"

$CMAKE --build "$LWC_BUILD_CLEAN" -j8 2>&1 | tee "$LOGDIR/clean_lwc_build.log" | tail -20
LWC_BUILD_EXIT=${PIPESTATUS[0]}
echo "cmake build exit: $LWC_BUILD_EXIT  Time: $(date)"
[ "$LWC_BUILD_EXIT" -ne 0 ] && { echo "CANDIDATE_CLEAN_LWC_BUILD_FAIL (cmake build)"; tail -50 "$LOGDIR/clean_lwc_build.log"; exit 1; }

$CMAKE --install "$LWC_BUILD_CLEAN" 2>&1 | tail -10

# Copy larwirecell libs to install/lib (standard step)
find "$LWC_BUILD_CLEAN" -name 'libWireCell*.so' 2>/dev/null | while read lib; do
    cp "$lib" "$LWC_INSTALL_CLEAN/lib/"
    echo "  Copied: $(basename $lib)"
done
echo "LWC installed libs:"
ls "$LWC_INSTALL_CLEAN/lib/"

echo ""
echo "============================================================"
echo "STEP 8: LWC RPATH audit"
echo "============================================================"

LWC_RPATH_CONTAMINATED=0
{
    echo "LWC RPATH AUDIT — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Install: $LWC_INSTALL_CLEAN"
    echo ""
    for lib in "$LWC_INSTALL_CLEAN/lib/libWireCell"*.so; do
        [ -f "$lib" ] || continue
        RPATH=$(readelf -d "$lib" 2>/dev/null | grep -E 'RPATH|RUNPATH' | sed 's/.*\[//;s/\]//' || echo "NONE")
        if echo "$RPATH" | grep -qE 'haiwang-current|wct-ap-yuhw'; then
            echo "CONTAMINATED: $(basename $lib)"
            echo "  RPATH: $RPATH"
            LWC_RPATH_CONTAMINATED=$((LWC_RPATH_CONTAMINATED+1))
        else
            echo "CLEAN: $(basename $lib)"
            echo "  RPATH: $RPATH"
        fi
    done
    echo ""
    if [ "$LWC_RPATH_CONTAMINATED" -eq 0 ]; then
        echo "LWC_RPATH_AUDIT_PASS"
    else
        echo "LWC_RPATH_AUDIT_FAIL: $LWC_RPATH_CONTAMINATED contaminated DSOs"
    fi
} | tee "$VALDIR/clean_lwc_rpath_audit.txt"

if [ "$LWC_RPATH_CONTAMINATED" -ne 0 ]; then
    echo "CANDIDATE_CLEAN_LWC_BUILD_FAIL (lwc_rpath_audit)"
    exit 1
fi

echo ""
echo "============================================================"
echo "STEP 9: Static dependency gate"
echo "============================================================"

{
    echo "CLEAN_CANDIDATE_DEPENDENCY_GATE — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "INTEGRATION_WCT_BASE=feb3ddeb (PR 543 head) + SP port, uncommitted"
    echo "LARWIRECELL_HEAD=9295e2a34c32b5f92ad6483b83dd4895a00b4c9b"
    echo ""
    echo "=== ldd of libWireCellAIML.so (key larwirecell lib) ==="
    AIML="$LWC_INSTALL_CLEAN/lib/libWireCellAIML.so"
    if [ -f "$AIML" ]; then
        LD_LIBRARY_PATH="$WCT_INSTALL_CLEAN/lib:$LWC_INSTALL_CLEAN/lib:${LD_LIBRARY_PATH:-}" \
            ldd "$AIML" 2>/dev/null | grep WireCell | head -20 || echo "ldd failed"
        AIML_AUX=$(LD_LIBRARY_PATH="$WCT_INSTALL_CLEAN/lib:$LWC_INSTALL_CLEAN/lib:${LD_LIBRARY_PATH:-}" \
            ldd "$AIML" 2>/dev/null | grep libWireCellAux || echo "NOT FOUND")
        echo ""
        echo "libWireCellAux resolution for libWireCellAIML.so:"
        echo "$AIML_AUX"
        if echo "$AIML_AUX" | grep -q "$WCT_INSTALL_CLEAN"; then
            echo "DEPENDENCY_GATE_AUX_PASS: resolves to clean WCT"
        elif echo "$AIML_AUX" | grep -q 'haiwang-current\|v0_32_1'; then
            echo "DEPENDENCY_GATE_AUX_FAIL: resolves to frozen/old WCT"
        else
            echo "DEPENDENCY_GATE_AUX_UNKNOWN"
        fi
    else
        echo "WARNING: libWireCellAIML.so not found"
    fi
    echo ""
    echo "=== WCT clean install lib checksums ==="
    sha256sum "$WCT_INSTALL_CLEAN/lib/libWireCellAux.so" 2>/dev/null || echo "MISSING"
    sha256sum "$WCT_INSTALL_CLEAN/lib/libWireCellGen.so" 2>/dev/null || echo "MISSING"
    sha256sum "$WCT_INSTALL_CLEAN/lib/libWireCellClus.so" 2>/dev/null || echo "MISSING"
    echo ""
    echo "WCT_RPATH_AUDIT=$(grep 'RPATH_AUDIT' $VALDIR/clean_wct_rpath_audit.txt | tail -1 || echo NOT_FOUND)"
    echo "LWC_RPATH_AUDIT=$(grep 'LWC_RPATH_AUDIT' $VALDIR/clean_lwc_rpath_audit.txt | tail -1 || echo NOT_FOUND)"
} | tee "$VALDIR/clean_candidate_dependency_gate.txt"

echo ""
echo "CANDIDATE_CLEAN_LWC_BUILD_PASS"
date
