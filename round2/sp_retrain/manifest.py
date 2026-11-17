#!/usr/bin/env python3
"""Input manifest of a training sample: one row per listed merged CAF (path, size, mtime, file_id, unit), plus a summary
with the list's own sha256. No ROOT file is opened; only stat() on the listed paths (no directory walk on Lustre).

  python sp_retrain/manifest.py SAMPLE LIST OUT_DIR --allowed-input-root DIR [--threads 16]

Writes manifest_<sample>.tsv.gz and manifest_<sample>.json. Per-file checksums of ~900 GB of merged CAFs are not
practical on a login node; size + mtime + path pin the inputs, and a rebuilt file changes at least the mtime.
"""
import argparse, gzip, hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sp_retrain import firewall  # noqa: E402


def _stat(p):
    try:
        s = os.stat(p)
        return p, s.st_size, int(s.st_mtime), ''
    except OSError as e:
        return p, -1, -1, type(e).__name__


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('sample'); ap.add_argument('list'); ap.add_argument('out_dir')
    ap.add_argument('--allowed-input-root', action='append', required=True)
    ap.add_argument('--threads', type=int, default=16)
    a = ap.parse_args()
    firewall.check_sample_id(a.sample)
    paths = [l.strip() for l in open(a.list) if l.strip() and not l.startswith('#')]
    firewall.check_training_inputs(paths, a.allowed_input_root)
    t0 = time.time()
    with ThreadPoolExecutor(a.threads) as ex:
        rows = list(ex.map(_stat, paths, chunksize=64))
    os.makedirs(a.out_dir, exist_ok=True)
    tsv = os.path.join(a.out_dir, 'manifest_%s.tsv.gz' % a.sample)
    with gzip.open(tsv, 'wt') as f:
        f.write('file_id\tunit\tsize_bytes\tmtime_unix\terror\tpath\n')
        for p, sz, mt, err in rows:
            f.write('%s\t%s\t%d\t%d\t%s\t%s\n' % (os.path.basename(p), os.path.basename(os.path.dirname(os.path.dirname(p))), sz, mt, err, p))
    h = hashlib.sha256(open(a.list, 'rb').read()).hexdigest()
    fids = [os.path.basename(p) for p, *_ in rows]
    summ = dict(sample=a.sample, list=os.path.abspath(a.list), list_sha256=h, list_mtime_unix=int(os.stat(a.list).st_mtime),
                files=len(rows), missing=sum(1 for r in rows if r[3]), duplicate_file_ids=len(fids) - len(set(fids)),
                total_bytes=sum(r[1] for r in rows if r[1] > 0), newest_mtime_unix=max(r[2] for r in rows),
                oldest_mtime_unix=min(r[2] for r in rows if r[2] > 0), manifest=os.path.abspath(tsv),
                manifest_sha256=hashlib.sha256(open(tsv, 'rb').read()).hexdigest(), stat_seconds=round(time.time() - t0, 1))
    json.dump(summ, open(os.path.join(a.out_dir, 'manifest_%s.json' % a.sample), 'w'), indent=1)
    print(json.dumps(summ))


if __name__ == '__main__':
    main()
