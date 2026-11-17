#!/usr/bin/env python3
"""READ-ONLY census / list / manifest builder for a refreshed Round-2 training production (Haiwang's per-unit layout).

  python make_refresh_list.py --sample ncdr --root ROOT --pairs PAIRS.tsv --census-out CENSUS.json
         [--sample-id wcl1116-aurora-ncdr --production WCLocal2026Nov16-Aurora --role training]
         [--write-list LIST.txt --manifest-out MANIFEST.tsv.gz] [--allow-partial-units] [--allow-incomplete] [--threads N]

ROOT is <production>/full/<sample> with node<k>/<unit>/{status, validate.json, validate-pr-dv2snap.json,
merged/{<caf>.wc.flat.caf.root, merge.json, merge-pr-dv2snap.json}}. PAIRS.tsv is the production's pair list (first
column = unit id). For every listed unit the status, both validations and both merge records are read; nothing is
written next to them.

  census      always: units listed / with a status / OK / PARTIAL / FAIL / no status; both validations PASS; the
              excluded units with their status and event counts (the loss of not taking them)
  list        only with --write-list, and REFUSED unless every listed unit has a final status (or --allow-incomplete,
              which stamps the manifest INCOMPLETE). Units in the list: status OK, both validations PASS and both
              Wire-Cell trees merged (--allow-partial-units also takes PARTIAL units whose validations PASS).
  manifest    one row per listed file: sample id, production, unit, role, status, the two validation results, the trees
              present, CAF events and Wire-Cell events per tree (merge records), size, mtime, path
Outputs go to our own area only (firewall.check_output_path). Metadata-bound on Lustre (about 7 small reads per unit):
run it on a compute node with --threads.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import firewall  # noqa: E402

ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']
VALIDATIONS = ('validate.json', 'validate-pr-dv2snap.json')
MERGES = (('merge.json', 'recTreeWireCell'), ('merge-pr-dv2snap.json', 'recTreeWireCell_dv2snap'))
COLUMNS = ['sample', 'production', 'unit', 'role', 'status', 'validate_split', 'validate_snap', 'trees', 'n_caf_events',
           'n_wc_events_split', 'n_wc_events_snap', 'size_bytes', 'mtime_unix', 'path']


def passed(path):
    try:
        return 'PASS' in json.dumps(json.load(open(path)))
    except Exception:
        return False


def unit_dirs(root):
    """node<k>/<unit> directories; scandir's d_type avoids one stat per entry on Lustre."""
    out = {}
    for n in sorted(e.name for e in os.scandir(root) if e.name.startswith('node') and e.is_dir()):
        for e in os.scandir(os.path.join(root, n)):
            if e.is_dir():
                out[e.name] = e.path
    return out


def _merge(d, name):
    try:
        return json.load(open(os.path.join(d, 'merged', name)))
    except Exception:
        return None


def _unit(job):
    u, d = job
    r = dict(unit=u, status='', validate_split=False, validate_snap=False, validations_pass=False, caf='', trees='',
             n_caf_events=-1, n_wc_events_split=-1, n_wc_events_snap=-1, size_bytes=-1, mtime_unix=-1)
    if not d:
        return r
    try:
        r['status'] = open(os.path.join(d, 'status')).read().strip()
    except OSError:
        pass
    r['validate_split'], r['validate_snap'] = (passed(os.path.join(d, x)) for x in VALIDATIONS)
    r['validations_pass'] = r['validate_split'] and r['validate_snap']
    trees = []
    for (name, tree), key in zip(MERGES, ('n_wc_events_split', 'n_wc_events_snap')):
        m = _merge(d, name)
        if m is not None:
            trees.append(m.get('tree', tree))
            r[key] = int(m.get('n_wirecell_events', -1))
            r['n_caf_events'] = int(m.get('n_caf_events', r['n_caf_events']))
            if m.get('caf'):
                r['source_caf'] = m['caf']
    r['trees'] = ','.join(trees)
    try:
        xs = [x for x in os.listdir(os.path.join(d, 'merged')) if x.endswith('.wc.flat.caf.root')]
    except OSError:
        xs = []
    if xs:
        r['caf'] = os.path.join(d, 'merged', xs[0])
        st = os.stat(r['caf'])
        r['size_bytes'], r['mtime_unix'] = int(st.st_size), int(st.st_mtime)
    return r


def census(root, pairs, threads=1):
    ids = [l.split('\t', 1)[0].strip() for l in open(pairs) if l.strip() and not l.startswith('#')]
    dirs = unit_dirs(root)
    jobs = [(u, dirs.get(u)) for u in ids]
    if threads > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(threads) as ex:
            rows = list(ex.map(_unit, jobs, chunksize=64))
    else:
        rows = [_unit(j) for j in jobs]
    c = dict(listed=len(ids), duplicate_ids=len(ids) - len(set(ids)), dirs_found=sum(d is not None for _, d in jobs),
             OK=0, PARTIAL=0, FAIL=0, other_status=0, no_status=0, both_validations_pass=sum(r['validations_pass'] for r in rows))
    for r in rows:
        st = r['status']
        if not st:
            c['no_status'] += 1
        elif st in ('OK', 'PARTIAL', 'FAIL'):
            c[st] += 1
        else:
            c['other_status'] += 1
    c['complete'] = c['no_status'] == 0
    return c, rows


def selected(rows, allow_partial=False):
    take = ('OK', 'PARTIAL') if allow_partial else ('OK',)
    return [r for r in rows if r['status'] in take and r['validations_pass'] and r['caf']
            and r['trees'] == 'recTreeWireCell,recTreeWireCell_dv2snap']


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--sample', required=True); ap.add_argument('--root', required=True); ap.add_argument('--pairs', required=True)
    ap.add_argument('--census-out', required=True); ap.add_argument('--write-list', default=None); ap.add_argument('--manifest-out', default=None)
    ap.add_argument('--sample-id', default=None); ap.add_argument('--production', default='WCLocal2026Nov16-Aurora')
    ap.add_argument('--role', default='training')
    ap.add_argument('--allow-partial-units', action='store_true'); ap.add_argument('--allow-incomplete', action='store_true')
    ap.add_argument('--threads', type=int, default=1, help='parallel per-unit reads (metadata-bound on Lustre)')
    a = ap.parse_args()
    sid = a.sample_id or a.sample
    firewall.check_sample_id(sid)
    for p in (a.census_out, a.write_list, a.manifest_out):
        if p:
            firewall.check_output_path(p, ALLOWED_OUTPUT)
    t0 = time.time()
    c, rows = census(a.root, a.pairs, a.threads)
    c.update(sample=a.sample, sample_id=sid, production=a.production, role=a.role, root=a.root, pairs=a.pairs,
             pairs_sha256=hashlib.sha256(open(a.pairs, 'rb').read()).hexdigest(),
             census_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), seconds=round(time.time() - t0, 1))
    sel = selected(rows, a.allow_partial_units)
    keep = set(r['unit'] for r in sel)
    exc = [r for r in rows if r['unit'] not in keep]
    c['selection'] = dict(rule='status OK' + (' or PARTIAL' if a.allow_partial_units else '') + ', both validations PASS, both trees merged',
                          files=len(sel), caf_events=sum(max(r['n_caf_events'], 0) for r in sel),
                          wc_events_split=sum(max(r['n_wc_events_split'], 0) for r in sel),
                          wc_events_snap=sum(max(r['n_wc_events_snap'], 0) for r in sel),
                          excluded_units=len(exc), excluded_caf_events=sum(max(r['n_caf_events'], 0) for r in exc),
                          excluded_wc_events_split=sum(max(r['n_wc_events_split'], 0) for r in exc),
                          excluded=[dict(unit=r['unit'], status=r['status'], validations_pass=r['validations_pass'], trees=r['trees'],
                                         n_caf_events=r['n_caf_events'], n_wc_events_split=r['n_wc_events_split'],
                                         n_wc_events_snap=r['n_wc_events_snap']) for r in exc[:200]])
    if a.write_list:
        if not c['complete'] and not a.allow_incomplete:
            raise SystemExit('%s: %d units have no final status; refusing to write a training list' % (a.sample, c['no_status']))
        firewall.check_training_inputs([r['caf'] for r in sel], [a.root])
        with open(a.write_list, 'w') as f:
            f.write(''.join(r['caf'] + '\n' for r in sel))
        c['list'] = dict(path=os.path.abspath(a.write_list), files=len(sel), sha256=hashlib.sha256(open(a.write_list, 'rb').read()).hexdigest(),
                         stamp='COMPLETE' if c['complete'] else 'INCOMPLETE')
        if a.manifest_out:
            body = '\t'.join(COLUMNS) + '\n' + ''.join('\t'.join(str(v) for v in (
                sid, a.production, r['unit'], a.role, r['status'], int(r['validate_split']), int(r['validate_snap']), r['trees'],
                r['n_caf_events'], r['n_wc_events_split'], r['n_wc_events_snap'], r['size_bytes'], r['mtime_unix'], r['caf'])) + '\n'
                for r in sel)
            with gzip.open(a.manifest_out, 'wt') as f:
                f.write(body)
            c['manifest'] = dict(path=os.path.abspath(a.manifest_out), content_sha256=hashlib.sha256(body.encode()).hexdigest(),
                                 total_bytes=sum(r['size_bytes'] for r in sel), columns=COLUMNS)
    json.dump(c, open(a.census_out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in c.items() if k not in ('root', 'pairs', 'selection')}))
    print(json.dumps({k: v for k, v in c['selection'].items() if k != 'excluded'}))


if __name__ == '__main__':
    main()
