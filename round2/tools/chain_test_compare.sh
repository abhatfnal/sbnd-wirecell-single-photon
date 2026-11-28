#!/bin/bash
# In-chain test comparisons (run after chain_test_node.sh; login node is fine: a few dozen small CAFs).
#   tools/chain_test_compare.sh CHAIN_DIR OUT_DIR
# Per arm and unit: every branch vs production (compare_chain_test.py). Per arm and tree: extract the test CAFs'
# upstream inputs, re-score them with the arm's expectation (upstream_rescore.py) and compare with what the chain stored
# (compare_chain_scores.py); for the 'new' arm also the SP feature vectors / predictions (compare_chain_sp_predictions.py).
set -u
C=${1:?chain dir}; O=${2:?out dir}
W=/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117; U=$W/upstream_r4_20261128
R2=$(cd "$(dirname "$0")/.." && pwd); PY=$W/env/bin/python
REL=$W/upstream_release_audit/sbnd-wirecell-bdt/releases; SHIP=/lus/flare/projects/neutrinoGPU/yuhw/wcd-0.38.0
mkdir -p $O; cd $R2
EXP_NEW="numu_score,numu_1_score,numu_2_score,cosmict_10_score,nue_score,br3_3_score,br3_5_score,br3_6_score,pio_2_score,stw_2_score,stw_3_score,stw_4_score,sig_1_score,sig_2_score,lol_1_score,lol_2_score,tro_1_score,tro_2_score,tro_4_score,tro_5_score"
while IFS=$'\t' read -r sample id real r1 caf nev pdir arms; do
  [ "${sample:0:1}" = "#" ] && continue
  prod=$(ls $pdir/merged/*.wc.flat.caf.root)
  for arm in $arms; do
    t=$(ls $C/runs/$arm/$id/merged/*.wc.flat.caf.root 2>/dev/null) || { echo "MISSING $arm $id"; continue; }
    exp=""; [ $arm = new ] || [ $arm = noscale ] || [ $arm = gate ] && exp=$EXP_NEW
    $PY tools/compare_chain_test.py --prod $prod --test $t --out $O/branches_${arm}_${id}.json --expect-changed "$exp" > $O/branches_${arm}_${id}.log 2>&1
    echo "BRANCHES $arm $sample $id rc=$? $(tail -c 300 $O/branches_${arm}_${id}.log)"
  done
done < $C/units.tsv
SID() { case $1 in ncdr) echo wcl1116-aurora-ncdr;; bnb) echo wcl1116-aurora-bnb;; nuecc) echo wcl1116-aurora-nuecc;; esac; }
for arm in new noscale gate ctl prodbuild; do
  for m in dv2_split_move:recTreeWireCell dv2_snap:recTreeWireCell_dv2snap; do
    mode=${m%%:*}; tree=${m#*:}
    for s in ncdr bnb nuecc; do
      ls $C/runs/$arm/*/merged/*.wc.flat.caf.root 2>/dev/null | while read f; do u=$(basename $(dirname $(dirname $f))); grep -q "^$s	$u	" $C/units.tsv && echo $f; done > $O/list_${arm}_${s}.txt
      [ -s $O/list_${arm}_${s}.txt ] || continue
      sid=$(SID $s); T=$O/tables_${arm}_${mode}
      $PY tools/extract_upstream_inputs.py $sid $T --list $O/list_${arm}_${s}.txt --wc-tree $tree --nproc 8 --tag x > /dev/null 2>&1
      for k in cands objs_numu_1 objs_numu_2 objs_cosmict_10 objs_br3_3 objs_br3_5 objs_br3_6 objs_pio_2 objs_stw_2 objs_stw_3 objs_stw_4 objs_sig_1 objs_sig_2 objs_lol_1 objs_lol_2 objs_tro_1 objs_tro_2 objs_tro_4 objs_tro_5 files; do
        mv $T/${k}_${sid}_x.parquet $T/${k}_${sid}.parquet; done
      kind=mc; [ $arm = gate ] && kind=data
      $PY tools/upstream_rescore.py $T $sid $T --kind $kind --shipped $SHIP --numu-release $REL/numu_round3af/wirecell \
          --nue-release $REL/nue_round4_ruleA_v2/wirecell/main --sim-scale 1.071 --nue-final > $T/rescore_$sid.log 2>&1
      if [ $arm = new ] || [ $arm = noscale ] || [ $arm = gate ]; then
        $PY tools/compare_chain_scores.py $T/rescore_$sid.parquet $arm $O/scores_${arm}_${mode}_${s}.json
      else
        echo "SHIPPED-FINAL CLOSURE $arm $mode $s $(tail -1 $T/rescore_$sid.log)"
      fi
    done
  done
done
$PY tools/compare_chain_sp_predictions.py --units $C/units.tsv --runs $C/runs --arm new --tables $W/wcl1116_dev_tables --tag dev \
    --overlay-root $U/overlay --domain-root $U/domain --studies-root $W/wcl1116_full_dev/studies --bundle-root $W/legacy_bdt_controls \
    --out $O/sp_predictions_new.json
echo "CHAIN_COMPARE_DONE"
