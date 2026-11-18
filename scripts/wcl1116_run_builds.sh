#!/usr/bin/env bash
# Build the candidate/event/file tables of the Nov16 replay, sequentially, resumable (existing pieces are skipped). <= 24 workers.
#   source env/setup_eaf.sh && bash scripts/wcl1116_run_builds.sh [new|old|all]
set -u
cd "$(dirname "$0")/.."; W=${WORKERS:-24}
NEW=$SP_DATA/wcl1116_nov16/analysis_tables_new; OLD=$SP_DATA/wcl1116_nov16/analysis_tables_old; mkdir -p $NEW $OLD
build() { # root sample manifest
  python scripts/build_analysis_table.py "$2" --manifest "$3" --root "$1" --workers $W && python scripts/build_analysis_table.py "$2" --manifest "$3" --root "$1" --merge; }
which=${1:-all}
if [ $which = new ] || [ $which = all ]; then
  for s in official_gen2_ncdelta nuecc beam_off run3bnb beam_on_open bnb_cv; do build $NEW $s manifests/wcl1116/$s.tsv.gz; done
fi
if [ $which = old ] || [ $which = all ]; then   # old (fg1 / ncdr / open-data) reconstruction, rebuilt with the same code for the samples that have no rescored old table
  for s in nuecc beam_off beam_on_open; do build $OLD $s manifests/$s.tsv.gz; done
fi
echo ALL_BUILDS_DONE
