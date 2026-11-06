#!/usr/bin/env bash
# Source this on EAF:   source env/setup_eaf.sh
# Contains NO credentials. The bearer token is obtained separately (see docs/analysis/EAF_QUICKSTART.md).

_sp_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SP_ENV="${SP_ENV:-/exp/sbnd/data/users/abhat/envs/sp-ncdelta}"
export SP_REPO="${_sp_root}"
export PATH="${SP_ENV}/bin:${PATH}"
export PYTHONPATH="${SP_REPO}/src:${PYTHONPATH:-}"
export XRD_NETWORKSTACK=IPv4
export SP_XRD_DOOR="root://fndcadoor.fnal.gov"
# scratch/cache: local, large, ephemeral (lost on pod restart). Never HOME.
export SP_SCRATCH="${SP_SCRATCH:-/tmp/${USER}/sp_cache}"
mkdir -p "${SP_SCRATCH}"
# derived (persistent, large) output area
export SP_DATA="${SP_DATA:-/exp/sbnd/data/users/abhat/single_photon_ncdelta}"

if [ -z "${BEARER_TOKEN_FILE:-}" ] || [ ! -s "${BEARER_TOKEN_FILE}" ]; then
  echo "[setup_eaf] WARNING: no usable bearer token (BEARER_TOKEN_FILE unset/empty). Run: htgettoken -a htvaultprod.fnal.gov -i sbnd" >&2
fi
echo "[setup_eaf] python=$(command -v python) repo=${SP_REPO}"
