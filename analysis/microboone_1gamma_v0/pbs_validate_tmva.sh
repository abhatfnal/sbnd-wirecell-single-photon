#!/bin/bash
#PBS -N tmva_xval
#PBS -l select=1:ncpus=4
#PBS -l filesystems=eagle:grand
#PBS -l walltime=00:30:00
#PBS -q by-gpu
#PBS -A neutrinoGPU::wirecell_2026
#PBS -o /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/analysis/microboone_1gamma_v0/logs/tmva_xval.log
#PBS -e /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/analysis/microboone_1gamma_v0/logs/tmva_xval.err
#PBS -j oe

# ROOT/TMVA cross-validation for single_photon BDTs.
# Uses ROOT v6_28_12 (e26/p3915) from /lus/grand with manual library compat shims.
# All missing CentOS7 .soX libs are shimmed via FAKELIBS symlinks.
# Validated working on Sophia login node 2026-10-05.

WORKDIR=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/analysis/microboone_1gamma_v0
ROOT_DIR=/lus/grand/projects/neutrinoGPU/software/larsoft/root/v6_28_12/Linux64bit+3.10-2.17-e26-p3915-prof
PYTHON39=/lus/grand/projects/neutrinoGPU/software/larsoft/python/v3_9_15/Linux64bit+3.10-2.17/bin/python3.9
PYTHON39_HOME=/lus/grand/projects/neutrinoGPU/software/larsoft/python/v3_9_15/Linux64bit+3.10-2.17
SQLITE_DIR=/lus/grand/projects/neutrinoGPU/software/larsoft/sqlite/v3_40_01_00/Linux64bit+3.10-2.17
TBB_LIB=/lus/grand/projects/neutrinoGPU/software/larsoft/tbb/v2021_7_0/Linux64bit+3.10-2.17-e20/lib
OPENBLAS_LIB=/lus/grand/projects/neutrinoGPU/software/larsoft/openblas/v0_3_23/Linux64bit+3.10-2.17-e26/lib
XXHASH_LIB=/lus/grand/projects/neutrinoGPU/software/spack_Jan25/spack/var/spack/environments/test/.spack-env/._view/xso65ocempdy3sy5cfh2huec6swmiv27/lib
# libssl.so.10 + libcrypto.so.10 from nsight (OpenSSL 1.0.x for UPS Python)
SSL_LIB=/lus/grand/projects/neutrinoGPU/software/spack_Jan25/spack/opt/spack/linux-zen3/cuda-12.1.0-2ocllw7o33avvz7empgcya7bmhg3jsut/nsight-systems-2023.1.2/target-linux-x64/CollectX

# FAKELIBS: CentOS7 .so.X shims pointing to RHEL9 equivalents
# libtinfo.so.5  -> /lib64/libtinfo.so.6    (ncurses, ROOT Cling)
# libffi.so.6    -> sphinx cffi.libs copy   (Python ctypes)
# libxxhash.so.0 -> spack xxhash            (cppyy)
# libexpat.so.1  -> /lib64/libexpat.so.1    (overrides spack expat/GLIBC_2.38)
FAKELIBS="${WORKDIR}/logs/fakelibs"
mkdir -p "${FAKELIBS}"
ln -sf /lib64/libtinfo.so.6 "${FAKELIBS}/libtinfo.so.5"
ln -sf /lib64/libexpat.so.1 "${FAKELIBS}/libexpat.so.1"
ln -sf /lus/grand/projects/neutrinoGPU/software/larsoft/sphinx/v3_5_4a/Linux64bit+3.10-2.17/lib/python3.9/site-packages/cffi.libs/libffi-806b1a9d.so.6.0.4 \
    "${FAKELIBS}/libffi.so.6"
ln -sf /lus/grand/projects/neutrinoGPU/software/spack_Jan25/spack/opt/spack/linux-zen3/xxhash-0.8.3-5uytefsxmxkt4gztn3j7c56bjjgehrah/lib/libxxhash.so.0 \
    "${FAKELIBS}/libxxhash.so.0"

mkdir -p "${WORKDIR}/logs"

echo "=== TMVA Cross-Validation PBS Job ==="
echo "Start: $(date)"
echo "Node: $(hostname)"
echo "ROOT_DIR: ${ROOT_DIR}"
echo "Python: ${PYTHON39} ($(${PYTHON39} --version 2>&1))"

# Validate key paths
[ ! -f "${ROOT_DIR}/bin/root.exe" ] && { echo "ERROR: ROOT missing"; exit 1; }
[ ! -f "${ROOT_DIR}/lib/libTMVA.so" ] && { echo "ERROR: libTMVA.so missing"; exit 1; }
echo "ROOT: OK"
echo "libTMVA.so: OK"

# Full library environment (fakelibs first to shadow bad spack libs, spack XXHASH_LIB last for libstdc++)
export ROOTSYS="${ROOT_DIR}"
export PYTHON_ROOT="${PYTHON39_HOME}"
export PYTHON_DIR="${PYTHON39_HOME}"
export SQLITE_FQ_DIR="${SQLITE_DIR}"
export PATH="${ROOT_DIR}/bin:${PYTHON39_HOME}/bin:${PATH}"
export LD_LIBRARY_PATH="${FAKELIBS}:${SSL_LIB}:${OPENBLAS_LIB}:${TBB_LIB}:${ROOT_DIR}/lib:${PYTHON39_HOME}/lib:${XXHASH_LIB}"
export PYTHONPATH="${ROOT_DIR}/lib"
export PYTHONHOME="${PYTHON39_HOME}"

# Test PyROOT
${PYTHON39} -c "
import ROOT
ROOT.gROOT.SetBatch(True)
print('PyROOT OK, ROOT version:', ROOT.gROOT.GetVersion())
" 2>&1 | grep -v "cling::\|Error in <TInterpreter"
[ $? -ne 0 ] && { echo "ERROR: PyROOT not available"; exit 1; }

echo "Running cross-validation..."
cd "${WORKDIR}"
${PYTHON39} validate_tmva_pyroot.py 2>&1 | grep -v "cling::\|Error in <TInterpreter\|AutoloadLibrary"
EXIT_CODE=${PIPESTATUS[0]}

echo "Exit code: ${EXIT_CODE}"
echo "Complete: $(date)"
exit ${EXIT_CODE}
