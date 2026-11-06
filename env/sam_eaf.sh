#!/bin/bash
# Read-only SAM access from EAF. Usage:  env/sam_eaf.sh <samweb subcommand and args>   e.g.  env/sam_eaf.sh server-info
# Runs samweb in a CLEAN subshell (env -i) so the UPS/LArSoft environment never mixes with the conda analysis environment, and
# nothing is installed or changed. Requires a Kerberos ticket (`kinit <user>@FNAL.GOV`); authentication is then automatic.
# UPS bootstrap: the `setup` function comes from the Fermilab common setups.sh, which must be sourced BEFORE setup_sbnd.sh in a clean
# shell (in an interactive Jupyter shell it is usually already defined). `setup_sbnd.sh` prints a harmless "Product 'mrb' has no current chain".
exec env -i HOME="$HOME" PATH=/usr/bin:/bin KRB5CCNAME="${KRB5CCNAME:-FILE:/tmp/krb5cc_$(id -u)}" bash -c '
  source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setups.sh >/dev/null 2>&1
  source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh >/dev/null 2>&1
  setup sam_web_client >/dev/null 2>&1 || { echo "setup sam_web_client failed" >&2; exit 97; }
  exec samweb -e sbnd "$@"' _ "$@"
