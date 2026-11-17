#!/usr/bin/env python3
"""READ-ONLY census / list builder for a refreshed Round-2 training production (Haiwang's per-unit layout).

  python make_refresh_list.py --sample ncdr --root ROOT --pairs PAIRS.tsv --census-out CENSUS.json
         [--write-list LIST.txt --manifest-out MANIFEST.tsv.gz] [--allow-partial-units] [--allow-incomplete]

ROOT is <production>/full/<sample> with node<k>/<unit>/{status, validate.json, validate-pr-dv2snap.json,
merged/<unit>.wc.flat.caf.root}. PAIRS.tsv is the production's pair list (first column = unit id). For every listed unit
the status and both validations are read; nothing is written next to them.

  census      always: units listed / with a status / OK / PARTIAL / FAIL / no status; both validations PASS
  list        only with --write-list, and REFUSED unless every listed unit has a final status (or --allow-incomplete,
              which stamps the manifest INCOMPLETE). Units in the list: status OK and both validations PASS
              (--allow-partial-units also takes PARTIAL units whose validations PASS: their missing events have
              valid = 0, which the table builder already drops).
Outputs go to our own area only (firewall.check_output_path).
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


def _unit(job):
    u, d = job
    st, caf = '', ''
    if d:
        try:
            st = open(os.path.join(d, 'status')).read().strip()
        except OSError:
            st = ''
        try:
            xs = [x for x in os.listdir(os.path.join(d, 'merged')) if x.endswith('.wc.flat.caf.root')]
        except OSError:
            xs = []
        caf = os.path.join(d, 'merged', xs[0]) if xs else ''
    v = bool(d) and all(passed(os.path.join(d, x)) for x in VALIDATIONS)
    return dict(unit=u, status=st, validations_pass=v, caf=caf)


def census(root, pairs, threads=1):
    """Metadata-bound on Lustre (about 4 small reads per unit): run it on a compute node, or with a few threads."""
    ids = [l.split('\t', 1)[0].strip() for l in open(pairs) if l.strip() and not l.startswith('#')]
    dirs = unit_dirs(root)
    jobs = [(u, dirs.get(u)) for u in ids]
    if threads > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(threads) as ex:
            rows = list(ex.map(_unit, jobs, chunksize=64))
    else:
        rows = [_unit(j) for j in jobs]
    c = dict(listed=len(ids), dirs_found=sum(d is not None for _, d in jobs), OK=0, PARTIAL=0, FAIL=0, other_status=0,
             no_status=0, both_validations_pass=sum(r['validations_pass'] for r in rows))
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--sample', required=True); ap.add_argument('--root', required=True); ap.add_argument('--pairs', required=True)
    ap.add_argument('--census-out', required=True); ap.add_argument('--write-list', default=None); ap.add_argument('--manifest-out', default=None)
    ap.add_argument('--allow-partial-units', action='store_true'); ap.add_argument('--allow-incomplete', action='store_true')
    ap.add_argument('--threads', type=int, default=1, help='parallel per-unit reads (metadata-bound on Lustre)')
    a = ap.parse_args()
    for p in (a.census_out, a.write_list, a.manifest_out):
        if p:
            firewall.check_output_path(p, ALLOWED_OUTPUT)
    t0 = time.time()
    c, rows = census(a.root, a.pairs, a.threads)
    c.update(sample=a.sample, root=a.root, pairs=a.pairs, pairs_sha256=hashlib.sha256(open(a.pairs, 'rb').read()).hexdigest(),
             census_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), seconds=round(time.time() - t0, 1))
    if a.write_list:
        if not c['complete'] and not a.allow_incomplete:
            raise SystemExit('%s: %d units have no final status; refusing to write a training list' % (a.sample, c['no_status']))
        take = ('OK', 'PARTIAL') if a.allow_partial_units else ('OK',)
        sel = [r for r in rows if r['status'] in take and r['validations_pass'] and r['caf']]
        firewall.check_training_inputs([r['caf'] for r in sel], [a.root])
        with open(a.write_list, 'w') as f:
            f.write(''.join(r['caf'] + '\n' for r in sel))
        c['list'] = dict(path=os.path.abspath(a.write_list), files=len(sel), sha256=hashlib.sha256(open(a.write_list, 'rb').read()).hexdigest(),
                         units_taken=list(take), stamp='COMPLETE' if c['complete'] else 'INCOMPLETE')
        if a.manifest_out:
            with gzip.open(a.manifest_out, 'wt') as f:
                f.write('unit\tstatus\tvalidations_pass\tsize_bytes\tmtime_unix\tpath\n')
                for r in sel:
                    st = os.stat(r['caf'])
                    f.write('%s\t%s\t%d\t%d\t%d\t%s\n' % (r['unit'], r['status'], r['validations_pass'], st.st_size, int(st.st_mtime), r['caf']))
    json.dump(c, open(a.census_out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in c.items() if k not in ('root', 'pairs')}))


if __name__ == '__main__':
    main()
