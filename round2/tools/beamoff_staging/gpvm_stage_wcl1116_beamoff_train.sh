#!/bin/bash
# Stage the PRE-DESIGNATED refreshed beam-off TRAINING partition (WCL1116) from FermiGrid dCache to Aurora.
# RUN BY AVINAY on a Fermilab SBND gpvm (e.g. sbndgpvm01), in his own session. Route = the one Xuyang used for
# fg1-beam-off-train on 2026-11-10 (bdt-comm PLAN.md line 83, inbox/updates-1828.md section 4): rsync over ssh pushed
# from the gpvm, --copy-links through a links directory, then a checksum comparison on Aurora. No Fermilab credential
# is moved to Aurora; ALCF asks for the one-time passcode once (ssh ControlMaster keeps the session).
#
#   bash gpvm_stage_wcl1116_beamoff_train.sh <membership_ids.txt> [aurora_user]
#
# membership_ids.txt: the 558 pair ids of round2/manifests/wcl1116_dev_v1/beamoff_train_membership.tsv.gz (column 1,
# header skipped), e.g.  zcat beamoff_train_membership.tsv.gz | tail -n +2 | cut -f1 > membership_ids.txt
# The membership is FROZEN (odd runs, Xin's 14 hold-out files removed). Nothing else is copied: no even-run evaluation
# file, no hold-out file, no other wcl1116-fg sample. A missing pair is reported, never substituted.
set -euo pipefail
IDS=${1:?membership_ids.txt}
AU=${2:-$USER}
SRC=/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/beam-off
DEST=/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117/wcl1116_beamoff_train
WORK=${WORK:-/exp/sbnd/data/users/$USER/wcl1116_beamoff_train_stage}
mkdir -p "$WORK/links"
n=$(grep -c . "$IDS"); [ "$n" -eq 558 ] || { echo "expected 558 ids, got $n" >&2; exit 2; }
: > "$WORK/source_manifest.tsv"; : > "$WORK/files.txt"; : > "$WORK/missing.txt"
echo -e "caf\tbytes\tadler32_dcache" > "$WORK/source_manifest.tsv"
while read -r id; do
  [ -n "$id" ] || continue
  d=$SRC/$id
  mapfile -t f < <(ls "$d"/*.wc.flat.caf.root 2>/dev/null || true)
  if [ "${#f[@]}" -ne 1 ]; then echo -e "$id\t${#f[@]} merged CAFs" >> "$WORK/missing.txt"; continue; fi
  b=$(basename "${f[0]}")
  bytes=$(stat -c %s "${f[0]}")
  ad=$(cat "$d/.(get)($b)(checksum)" 2>/dev/null | tr ' ' '\n' | grep -i '^ADLER32:' | head -1 | cut -d: -f2)
  echo -e "$id/$b\t$bytes\t${ad:-unknown}" >> "$WORK/source_manifest.tsv"
  mkdir -p "$WORK/links/$id"; ln -sfn "${f[0]}" "$WORK/links/$id/$b"
  echo "$id/$b" >> "$WORK/files.txt"
done < "$IDS"
echo "staged list: $(wc -l < "$WORK/files.txt") files; missing: $(wc -l < "$WORK/missing.txt")"
cp "$WORK/source_manifest.tsv" "$WORK/missing.txt" "$WORK/links/"
# one ssh master connection (one ALCF passcode), then rsync through it
CM=/tmp/cm-aurora-$USER
ssh -o ControlMaster=yes -o ControlPath=$CM -o ControlPersist=2h -fN "$AU@aurora.alcf.anl.gov"
ssh -o ControlPath=$CM "$AU@aurora.alcf.anl.gov" "mkdir -p $DEST"
rsync -av --copy-links --files-from="$WORK/files.txt" -e "ssh -o ControlPath=$CM" "$WORK/links/" "$AU@aurora.alcf.anl.gov:$DEST/"
rsync -av -e "ssh -o ControlPath=$CM" "$WORK/links/source_manifest.tsv" "$WORK/links/missing.txt" "$AU@aurora.alcf.anl.gov:$DEST/"
ssh -o ControlPath=$CM -O exit "$AU@aurora.alcf.anl.gov" || true
echo "done. On Aurora run: round2/tools/verify_staged_beamoff.py (see round2/tools/beamoff_staging/README.md)"
