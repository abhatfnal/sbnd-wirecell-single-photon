#!/usr/bin/env python3
"""Verify a staged copy of the pre-designated beam-off TRAINING partition against its frozen membership (read-only).

  python verify_staged_beamoff.py --staged DIR --membership round2/manifests/wcl1116_dev_v1/beamoff_train_membership.tsv.gz \
      --frozen-list xning/bdt-comm/data/fg1-beam-off-train.list.tsv --source-manifest DIR/source_manifest.tsv \
      --out-json OUT.json --out-tsv OUT.tsv.gz --write-list LIST.txt [--expect-reco wcl1116] [--limit N]

Every staged file must:
  * sit in <staged>/<pair id>/<name>.wc.flat.caf.root with a pair id in the frozen 558-pair membership
    (fg1-beamoff-train, odd runs, Xin's hold-out files removed) -- unknown, hold-out or duplicate ids fail;
  * carry an ODD run in its name and in its recTree header, equal to the membership run (even run = evaluation half);
  * match the source manifest written on the gpvm (bytes, dCache ADLER32), and get a sha256 here;
  * be refreshed WCL1116 reconstruction (--expect-reco wcl1116): recTree, recTreeWireCell AND recTreeWireCell_dv2snap
    present; in both Wire-Cell trees a wct_version that is EXACTLY one of the WCLocal2026Nov16 strings of toolkit
    c935e30d ("0.38.0" Aurora build, "HEAD-0.38.0" FermiGrid/gpVM build; sp_retrain.provenance, approved 2026-11-19),
    the same string in both trees, and dl_weights EXACTLY "<mode>:dv2max/sbnd/aurora_space/bundle.json@sha256:51588842..."
    for that tree's vertex mode; rec.hdr.ismc == 0 (real off-beam data).
Every staged file must carry the same stamp (one build per sample); that stamp and the campaign provenance are written
to the record. The old fg1 reconstruction (one Wire-Cell tree, wct_version ...-g78f81c64) and any post-tag or branch
stamp fail the reco check, so reconstructions can never mix. Only if every file passes is --write-list written; the
JSON record is written either way. Nothing is written next to the staged files.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import zlib

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import firewall, provenance  # noqa: E402

BUNDLE_SHA = provenance.WCL1116_BUNDLE_SHA256
MODE_OF_TREE = {'recTreeWireCell': 'dv2_split_move', 'recTreeWireCell_dv2snap': 'dv2_snap'}
RUN = re.compile(r'_run(\d+)_')
TREES = ('recTree', 'recTreeWireCell', 'recTreeWireCell_dv2snap')


def read_tsv(path):
    op = gzip.open if path.endswith('.gz') else open
    rows, hdr = [], None
    with op(path, 'rt') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            v = line.rstrip('\n').split('\t')
            if hdr is None:
                hdr = v
                continue
            rows.append(dict(zip(hdr, v)))
    return rows


def holdout_ids(frozen):
    out = set()
    for r in read_tsv(frozen):
        f = lambda k: int(float(r.get(k, '0') or 0))
        if f('holdout') == 1 or f('holdout_file') == 1 or f('holdout_events') > 0:
            out.add(r['file_id'])
    return out


def checksums(path):
    a, h = 1, hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            a = zlib.adler32(b, a); h.update(b)
    return '%08x' % (a & 0xffffffff), h.hexdigest()


def text(t, name):
    try:
        v = t[name].array(library='np', entry_stop=1)[0]
        return bytes(v.astype('int8').tobytes()).decode(errors='replace') if hasattr(v, 'astype') else str(v)
    except Exception:
        return ''


def reco_check(path, expect):
    import uproot
    f = uproot.open(path)
    r = dict(trees={t: t in f for t in TREES})
    h = f['recTree'].arrays(['rec.hdr.run', 'rec.hdr.ismc'], library='np')
    r['hdr_runs'] = sorted(set(int(x) for x in h['rec.hdr.run']))
    r['ismc'] = sorted(set(int(x) for x in h['rec.hdr.ismc']))
    for t in ('recTreeWireCell', 'recTreeWireCell_dv2snap'):
        if t in f:
            r[t] = dict(wct_version=text(f[t], 'wc.Trun.wct_version'), dl_weights=text(f[t], 'wc.Trun.dl_weights'))
    bad = wcl1116_problems(r) if expect == 'wcl1116' else []
    if r['ismc'] != [0]:
        bad.append('not real data (ismc %s)' % r['ismc'])
    return r, bad


def wcl1116_problems(r):
    """Reconstruction problems of one file's metadata r (trees present; per Wire-Cell tree wct_version, dl_weights)."""
    bad = []
    if not all(r['trees'].values()):
        bad.append('missing tree %s' % [t for t, ok in r['trees'].items() if not ok])
    for t, mode in MODE_OF_TREE.items():
        if t not in r:
            continue
        if not provenance.wcl1116_stamp_ok(r[t]['wct_version']):
            bad.append('%s not WCL1116 (wct_version %r)' % (t, r[t]['wct_version']))
        if r[t]['dl_weights'] != provenance.wcl1116_dl_weights(mode):
            bad.append('%s not WCL1116 (dl_weights %r)' % (t, r[t]['dl_weights'][:80]))
    st = [r[t]['wct_version'] for t in MODE_OF_TREE if t in r]
    if len(set(st)) > 1:
        bad.append('trees carry different stamps %s' % st)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--staged', '--membership', '--frozen-list', '--out-json'):
        ap.add_argument(k, required=True)
    ap.add_argument('--source-manifest', default=None); ap.add_argument('--out-tsv', default=None); ap.add_argument('--write-list', default=None)
    ap.add_argument('--expect-reco', default='wcl1116', choices=['wcl1116', 'any']); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    for p in (a.out_json, a.out_tsv, a.write_list):
        if p:
            firewall.check_output_path(p, ['/lus/flare/projects/neutrinoGPU/abhat/sbnd'])
    mem = {r['file_id']: r for r in read_tsv(a.membership)}
    hold = holdout_ids(a.frozen_list)
    src = {}
    if a.source_manifest and os.path.exists(a.source_manifest):
        for r in read_tsv(a.source_manifest):
            src[r['caf']] = r
    staged = []
    for d in sorted(os.listdir(a.staged)):
        p = os.path.join(a.staged, d)
        if os.path.isdir(p):
            for fn in sorted(os.listdir(p)):
                if fn.endswith('.root'):
                    staged.append((d, fn))
    if a.limit:
        staged = staged[:a.limit]
    rows, seen = [], {}
    for pid, fn in staged:
        rel = '%s/%s' % (pid, fn)
        path = os.path.join(a.staged, rel)
        fails = []
        if pid in hold:
            fails.append('hold-out file')
        if pid not in mem:
            fails.append('not in the frozen membership')
        seen[pid] = seen.get(pid, 0) + 1
        m = RUN.search(fn); run = int(m.group(1)) if m else -1
        if run < 0 or run % 2 == 0:
            fails.append('even or unknown run %d (evaluation half)' % run)
        if pid in mem and int(mem[pid]['run']) != run:
            fails.append('run %d != membership run %s' % (run, mem[pid]['run']))
        size = os.path.getsize(path)
        ad, sha = checksums(path)
        s = src.get(rel)
        if src:
            if s is None:
                fails.append('not in the gpvm source manifest')
            else:
                if int(s['bytes']) != size:
                    fails.append('size %d != source %s' % (size, s['bytes']))
                if s.get('adler32_dcache', 'unknown') not in ('unknown', '') and s['adler32_dcache'].lower().zfill(8) != ad:
                    fails.append('adler32 %s != dCache %s' % (ad, s['adler32_dcache']))
        try:
            reco, bad = reco_check(path, a.expect_reco)
            fails += bad
            if reco['hdr_runs'] and reco['hdr_runs'] != [run]:
                fails.append('header runs %s != name run %d' % (reco['hdr_runs'], run))
        except Exception as e:
            reco = {}; fails.append('unreadable: %s' % str(e).splitlines()[0][:80])
        rows.append(dict(pair_id=pid, file=fn, run=run, bytes=size, adler32=ad, sha256=sha, role='training_ext_beam_off',
                         source=(s or {}).get('caf', ''), wct_version=(reco.get('recTreeWireCell') or {}).get('wct_version', ''),
                         wct_version_snap=(reco.get('recTreeWireCell_dv2snap') or {}).get('wct_version', ''),
                         trees=','.join(t for t, ok in reco.get('trees', {}).items() if ok), ok=not fails, fails=';'.join(fails)))
    dup = sorted(k for k, v in seen.items() if v > 1)
    for r in rows:
        if r['pair_id'] in dup:
            r['ok'] = False; r['fails'] = (r['fails'] + ';duplicate pair id').strip(';')
    good = [r for r in rows if r['ok']]
    expected = set(mem) - hold
    res = dict(staged_dir=a.staged, membership=a.membership, expected=len(expected), staged_files=len(rows), verified=len(good),
               missing=sorted(expected - set(r['pair_id'] for r in rows))[:600], n_missing=len(expected - set(r['pair_id'] for r in rows)),
               evaluation_half_files=sum('even or unknown run' in r['fails'] for r in rows),
               holdout_files=sum('hold-out' in r['fails'] for r in rows), unknown_files=sum('not in the frozen membership' in r['fails'] for r in rows),
               duplicate_ids=len(dup), reco_failures=sum(('not WCL1116' in r['fails']) or ('missing tree' in r['fails']) or ('different stamps' in r['fails']) for r in rows),
               checksum_failures=sum(('adler32' in r['fails']) or ('size' in r['fails']) for r in rows),
               data_mc_failures=sum('not real data' in r['fails'] for r in rows),
               expect_reco=a.expect_reco, source_manifest=a.source_manifest, failures=[dict(pair_id=r['pair_id'], fails=r['fails']) for r in rows if not r['ok']][:50])
    stamps = {}
    for r in rows:
        stamps[r['wct_version']] = stamps.get(r['wct_version'], 0) + 1
    res['wct_version_stamps'] = stamps
    res['wct_version_stamp'] = next(iter(stamps)) if len(stamps) == 1 else None    # one build per sample
    res['uniform_stamp'] = len(stamps) == 1
    if a.expect_reco == 'wcl1116':
        res['wct_provenance'] = provenance.WCL1116_PROVENANCE
        res['toolkit_commit'] = provenance.WCL1116_TOOLKIT_COMMIT
    res['status'] = 'VERIFIED' if (res['verified'] == res['expected'] == res['staged_files'] and not res['failures'] and res['uniform_stamp']) else 'NOT VERIFIED'
    if a.out_tsv:
        cols = ['pair_id', 'file', 'run', 'bytes', 'adler32', 'sha256', 'role', 'source', 'wct_version', 'wct_version_snap', 'trees', 'ok', 'fails']
        body = '\t'.join(cols) + '\n' + ''.join('\t'.join(str(r[c]) for c in cols) + '\n' for r in rows)
        with gzip.open(a.out_tsv, 'wt') as f:
            f.write(body)
        res['out_tsv_content_sha256'] = hashlib.sha256(body.encode()).hexdigest()
    if a.write_list and res['status'] == 'VERIFIED':
        open(a.write_list, 'w').write(''.join(os.path.join(a.staged, r['pair_id'], r['file']) + '\n' for r in good))
        res['list'] = os.path.abspath(a.write_list)
        res['list_sha256'] = hashlib.sha256(open(a.write_list, 'rb').read()).hexdigest()
    json.dump(res, open(a.out_json, 'w'), indent=1)        # the record is written whether or not the staging verifies
    print(json.dumps({k: v for k, v in res.items() if k not in ('missing', 'failures', 'wct_provenance')}, indent=1))
    if res['failures']:
        print('first failures:', res['failures'][:3])
    if a.write_list and res['status'] != 'VERIFIED':
        raise SystemExit('staging NOT VERIFIED: no training list written (%s)' % json.dumps({k: res[k] for k in ('expected', 'staged_files', 'verified', 'n_missing')}))


if __name__ == '__main__':
    main()
