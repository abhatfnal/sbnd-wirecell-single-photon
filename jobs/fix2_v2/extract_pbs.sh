#!/bin/bash
#PBS -N fix2_extract
#PBS -A neutrinoGPU::wirecell_2026
#PBS -q by-gpu
#PBS -l select=1:ncpus=4:ngpus=1:mem=32gb
#PBS -l walltime=00:10:00
#PBS -l filesystems=eagle:grand:home
#PBS -o /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005/logs/extract_pbs.out
#PBS -e /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005/logs/extract_pbs.err

set -euo pipefail

CONTAINER=/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif
LARSOFT_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs
SBND_SQ=/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/sbnd-v10_14_02_04_delta.squashfs
DEV=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005
SCRIPT=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005/build/extract_ttagger.py

module use /soft/modulefiles
module load spack-pe-base
module load apptainer

apptainer exec --fakeroot \
    --bind /lus/eagle,/lus/grand,/tmp \
    --overlay "$LARSOFT_SQ":ro \
    --overlay "$SBND_SQ":ro \
    "$CONTAINER" \
    bash -lc "
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env 2>/dev/null || true
python3 '$SCRIPT'
" 2>&1 | tee "$DEV/logs/extract_ttagger.log"

echo "EXTRACT_DONE"
