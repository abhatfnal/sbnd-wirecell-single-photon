#!/usr/bin/env python3
"""Frozen fg1-beamoff-train membership mapped onto the WCLocal2026Nov16 beam-off rerun (read-only; no data read).

  python make_beamoff_train_membership.py --train-list fg1-beam-off-train.list.tsv --wcl1116-lists DIR \
      --out-tsv OUT.tsv.gz --out-json OUT.json

The training-side beam-off partition was frozen BEFORE this campaign (Haiwang's catalogue, owner split 2026-11-09:
odd runs = fg1-beamoff-train, even runs = fg1-beamoff-eval). Its membership list (Xuyang's
bdt-comm/data/fg1-beam-off-train.list.tsv, sha256 acb69100...) is the ONLY source of pair ids here. The WCL1116 rerun
keeps the pair ids (data_filtered_decoded_reco1-<uuid>), so a training pair's refreshed CAF is expected under
  /pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/beam-off/<id>/
which is NOT readable from Aurora (no /pnfs). Checks: list sha256; every run odd (=> zero overlap with the even-run
evaluation half by construction); Xin's hold-out files removed (holdout == 1 | holdout_file == 1 | holdout_events > 0);
no duplicate id; the WCL1116 pair-id lists visible on Aurora (porting pilot / from-reco1 subsets) agree in id form.
Development firewall exception: Avinay Bhat, 2026-11-17, development_wcl1116_v1 only, this odd-run membership only.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import firewall  # noqa: E402

FROZEN_SHA256 = 'acb69100fc1bb337de01748e823ba8c811522306cc8675231b2c198b7160ea64'
WCL1116_BEAMOFF = '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/beam-off'
ID = re.compile(r'data_filtered_decoded_reco1-[0-9a-f-]+')
EXCEPTION = dict(sample='wcl1116-fg-beamoff-train', approved_by='Avinay Bhat', date='2026-11-17',
                 scope='development_wcl1116_v1 only: the pre-designated odd-run fg1-beamoff-train membership, hold-out files removed',
                 not_permitted=['the even-run evaluation half (fg1-beamoff-eval)', 'the full 50k beam-off as a whole',
                                "Xin's hold-out events / files", 'any other wcl1116-fg-* sample'])


def read_train(path):
    rows = []
    hdr = None
    for line in open(path):
        if line.startswith('#') or not line.strip():
            continue
        f = line.rstrip('\n').split('\t')
        if hdr is None:
            hdr = f
            continue
        rows.append(dict(zip(hdr, f)))
    return rows


def flag(r, k):
    try:
        return int(float(r.get(k, '0') or 0))
    except ValueError:
        return 0


def membership(rows):
    ids = [r['file_id'] for r in rows]
    hold = [r for r in rows if flag(r, 'holdout') == 1 or flag(r, 'holdout_file') == 1 or flag(r, 'holdout_events') > 0]
    hold_ids = set(r['file_id'] for r in hold)
    keep = [r for r in rows if r['file_id'] not in hold_ids]
    runs = sorted(set(int(r['run']) for r in rows))
    return dict(pairs=len(rows), unique_ids=len(set(ids)), holdout_files=len(hold_ids), kept=len(keep),
                all_runs_odd=all(x % 2 == 1 for x in runs), runs=len(runs), even_runs=[x for x in runs if x % 2 == 0],
                kept_ids=[r['file_id'] for r in keep], kept_rows=keep, holdout_ids=sorted(hold_ids))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--train-list', required=True); ap.add_argument('--wcl1116-lists', required=True)
    ap.add_argument('--out-tsv', required=True); ap.add_argument('--out-json', required=True)
    a = ap.parse_args()
    for p in (a.out_tsv, a.out_json):
        firewall.check_output_path(p, ['/lus/flare/projects/neutrinoGPU/abhat/sbnd'])
    sha = hashlib.sha256(open(a.train_list, 'rb').read()).hexdigest()
    if sha != FROZEN_SHA256:
        raise SystemExit('training-half list sha256 %s differs from the frozen %s' % (sha, FROZEN_SHA256))
    m = membership(read_train(a.train_list))
    seen = {}
    for fn in sorted(os.listdir(a.wcl1116_lists)):
        if 'beam-off' in fn:
            ids = set(ID.findall(open(os.path.join(a.wcl1116_lists, fn)).read()))
            seen[fn] = dict(ids=len(ids), in_training_half=len(ids & set(m['kept_ids']) | (ids & set(m['holdout_ids']))))
    body = 'file_id\trun\tsubrun\tevents\texpected_wcl1116_dir\trole\n' + ''.join(
        '%s\t%s\t%s\t%s\t%s/%s/\ttraining_ext_beam_off\n' % (r['file_id'], r['run'], r['subrun'], r['events'], WCL1116_BEAMOFF, r['file_id'])
        for r in m['kept_rows'])
    with gzip.open(a.out_tsv, 'wt') as f:
        f.write(body)
    out = dict(source_list=os.path.abspath(a.train_list), source_list_sha256=sha, frozen_before_campaign='2026-11-09 (owner split)',
               pairs=m['pairs'], unique_ids=m['unique_ids'], holdout_files_removed=m['holdout_files'], kept=m['kept'],
               runs=m['runs'], all_runs_odd=m['all_runs_odd'], even_runs=m['even_runs'],
               overlap_with_even_run_evaluation_half=0 if m['all_runs_odd'] else None,
               wcl1116_location=WCL1116_BEAMOFF, accessible_from_aurora=os.path.isdir(WCL1116_BEAMOFF),
               status='SP-OTHER DEVELOPMENT BLOCKED ONLY ON DATA ACCESS/STAGING' if not os.path.isdir(WCL1116_BEAMOFF) else 'ACCESSIBLE',
               wcl1116_id_lists_on_aurora=seen, membership_tsv=os.path.abspath(a.out_tsv),
               membership_tsv_content_sha256=hashlib.sha256(body.encode()).hexdigest(), firewall_exception=EXCEPTION,
               split='by run: run % 4 == 1 -> development holdout, else train (every beam-off file has art subrun 1)')
    json.dump(out, open(a.out_json, 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'firewall_exception'}, indent=1))


if __name__ == '__main__':
    main()
