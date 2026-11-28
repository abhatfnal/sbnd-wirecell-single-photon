#!/usr/bin/env python3
"""Merged WCL1116 CAF(s) -> the inputs of the upstream Wire-Cell nu_mu / nu_e tagger BDTs, in the table schema of Xuyang
Ning's spec_v1 builder (Ningclover/sbnd-wirecell-bdt @ 0f13988d, tables/build_tables.py), for ONE Wire-Cell tree.

Why a separate extractor: the release scorers (release/score_release.py, training/numu/make_corrected_tables.py,
training/numu/score_numu_release.py) read cands_<sample>.parquet and objs_<model>_<sample>.parquet. Xuyang's builder reads
only recTreeWireCell and extracts truth matching and many other families; this one reads either tree and only what the
upstream taggers consume, so both vertex modes of the four SP development samples can be re-scored. Its output is
checked column-for-column against Xuyang's builder on a file subset (tools/check_upstream_extract_vs_builder.py).

Semantics copied from build_tables.py (same rules, same names):
  * events with wc.valid == 1; key (sample, file_id = CAF basename, run, subrun, event); one candidate row per
    wc.T_tagger.nu_index entry (cand = nu_index); a per-candidate scalar shorter than the candidate list gives NaN;
  * kine_reco_Enu from wc.T_kine matched on nu_index (NaN when absent);
  * is_placeholder = (kine_reco_Enu == 0 and neutrino_type == 0 and nu_x == nu_y == nu_z == 0);
  * objs_<model>: one row per object (key, cand, index, the model's per-object inputs, its per-candidate scalars,
    'flag' = the model's rule flag), n_obj_<model> on the candidate; a list shorter than the first gives NaN.
Extra (not in Xuyang's builder, all prefixed or named explicitly): the STORED upstream scores of the production
(shipped weights) and wct_version / wc_tree on the files table.

  python tools/extract_upstream_inputs.py SAMPLE OUT_DIR --list LIST --wc-tree recTreeWireCell [--slice A:B] [--nproc N] [--tag T]
"""
import argparse, hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc  # noqa: E402

WC_TREES = ('recTreeWireCell', 'recTreeWireCell_dv2snap')
KEY = ['sample', 'file_id', 'run', 'subrun', 'event']


def _sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def extract(path, sample, file_id, wc_tree):
    import uproot
    info = dict(sample=sample, file_id=file_id, path=path, wc_tree=wc_tree, events=0, wc_events=0, candidates=0,
                wct_version='', error='')
    cands, objs = [], {m: [] for m in uc.L1_ALL}
    try:
        f = uproot.open(path)
        t = f[wc_tree]
    except Exception as e:
        info['error'] = 'OPEN_FAIL ' + (str(e).splitlines() or [''])[0][:160]
        return info, cands, objs
    keys = set(t.keys())
    scal = [n for n in uc.CAND_SCALARS if 'wc.T_tagger.' + n in keys]
    info['missing_scalars'] = sorted(set(uc.CAND_SCALARS) - set(scal))
    lists = {}
    for m in uc.L1_ALL:
        d = uc.L1_SPEC[m]
        lb = ['wc.T_tagger.' + n for n in d['lists']]
        if all(b + '..idx' in keys for b in lb):
            fb = 'wc.T_tagger.' + d['flag'] if 'wc.T_tagger.' + d['flag'] + '..idx' in keys else None
            lists[m] = (lb, fb)
    info['missing_models'] = sorted(set(uc.L1_ALL) - set(lists))
    br = ['wc.run', 'wc.subrun', 'wc.evt', 'wc.valid', 'wc.Trun.wct_version', 'wc.T_tagger.nu_index',
          'wc.T_kine.nu_index', 'wc.T_kine.kine_reco_Enu'] + ['wc.T_tagger.' + n for n in scal]
    for lb, fb in lists.values():
        for b in lb + ([fb] if fb else []):
            br += [b, b + '..idx', b + '..length']
    br = list(dict.fromkeys(br))
    try:
        a = t.arrays(br, library='np')
    except Exception as e:
        info['error'] = 'READ_FAIL ' + (str(e).splitlines() or [''])[0][:160]
        return info, cands, objs
    info['events'] = int(len(a['wc.run']))
    info['wc_events'] = int((a['wc.valid'] == 1).sum())
    wv = a['wc.Trun.wct_version']
    # the string branch reads as a uint8 array per event (same decoding as sp_retrain/build_tables.py)
    info['wct_version'] = (bytes(np.asarray(wv[0], dtype=np.uint8)).decode() if len(wv) and len(wv[0]) and np.asarray(wv[0]).dtype.kind in 'iu'
                           else (str(wv[0][0]) if len(wv) and len(wv[0]) else ''))
    for i in range(len(a['wc.run'])):
        if a['wc.valid'][i] != 1:
            continue
        key = dict(sample=sample, file_id=file_id, run=int(a['wc.run'][i]), subrun=int(a['wc.subrun'][i]), event=int(a['wc.evt'][i]))
        kine = {int(v): c for c, v in enumerate(a['wc.T_kine.nu_index'][i])}
        enu = a['wc.T_kine.kine_reco_Enu'][i]
        for c, ni in enumerate(a['wc.T_tagger.nu_index'][i]):
            ni = int(ni)
            r = dict(key, cand=ni)
            for n in scal:
                v = a['wc.T_tagger.' + n][i]
                r[n] = float(v[c]) if c < len(v) else np.nan
            kc = kine.get(ni)
            r['kine_reco_Enu'] = float(enu[kc]) if kc is not None and kc < len(enu) else np.nan
            r['is_placeholder'] = int(r['kine_reco_Enu'] == 0.0 and r.get('neutrino_type', 0.0) == 0.0 and
                                      r.get('nu_x', np.nan) == 0.0 and r.get('nu_y', np.nan) == 0.0 and r.get('nu_z', np.nan) == 0.0)
            for m, (lb, fb) in lists.items():
                b0 = lb[0]
                n = int(a[b0 + '..length'][i][c]) if c < len(a[b0 + '..idx'][i]) else 0
                r['n_obj_' + m] = n
                if n == 0:
                    continue
                cols = lb + ([fb] if fb else [])
                st = {b: int(a[b + '..idx'][i][c]) for b in cols}
                ln = {b: int(a[b + '..length'][i][c]) for b in cols}
                sc = {sn: r.get(sn, np.nan) for sn in uc.L1_SPEC[m]['scalars']}
                for j in range(n):
                    o = dict(key, cand=ni, index=j)
                    for b in lb:
                        o[b[len('wc.T_tagger.'):]] = float(a[b][i][st[b] + j]) if j < ln[b] else np.nan
                    o.update(sc)
                    o['flag'] = float(a[fb][i][st[fb] + j]) if fb and j < ln[fb] else np.nan
                    objs[m].append(o)
            cands.append(r)
    info['candidates'] = len(cands)
    return info, cands, objs


def _worker(job):
    path, sample, wc_tree = job
    try:
        return extract(path, sample, os.path.basename(path), wc_tree)
    except Exception as e:
        return dict(sample=sample, file_id=os.path.basename(path), path=path, wc_tree=wc_tree,
                    error='EXC ' + (str(e).splitlines() or [''])[0][:160]), [], {}


def main():
    import pandas as pd
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('sample'); ap.add_argument('out_dir')
    ap.add_argument('--list', required=True); ap.add_argument('--slice')
    ap.add_argument('--wc-tree', required=True, choices=WC_TREES)
    ap.add_argument('--nproc', type=int, default=1); ap.add_argument('--tag', default='')
    a = ap.parse_args()
    lines = [l.strip() for l in open(a.list) if l.strip() and not l.startswith('#')]
    if a.slice:
        s0, s1 = a.slice.split(':'); lines = lines[int(s0 or 0):int(s1) if s1 else None]
    jobs = [(p, a.sample, a.wc_tree) for p in lines]
    t0 = time.time()
    if a.nproc > 1:
        import multiprocessing as mp
        with mp.Pool(a.nproc) as pool:
            res = pool.map(_worker, jobs, chunksize=4)
    else:
        res = [_worker(j) for j in jobs]
    os.makedirs(a.out_dir, exist_ok=True)
    sfx = ('_' + a.tag) if a.tag else ''
    F = pd.DataFrame([r[0] for r in res])
    for c in ('missing_scalars', 'missing_models'):
        if c in F:
            F[c] = F[c].apply(lambda v: ','.join(v) if isinstance(v, list) else '')
    C = pd.DataFrame([x for r in res for x in r[1]])
    F.to_parquet(os.path.join(a.out_dir, 'files_%s%s.parquet' % (a.sample, sfx)))
    C.to_parquet(os.path.join(a.out_dir, 'cands_%s%s.parquet' % (a.sample, sfx)))
    nobj = {}
    for m in uc.L1_ALL:
        rows = [x for r in res for x in r[2].get(m, [])]
        O = pd.DataFrame(rows) if rows else uc.empty_objs(m)
        nobj[m] = len(O)
        O.to_parquet(os.path.join(a.out_dir, 'objs_%s_%s%s.parquet' % (m, a.sample, sfx)))
    summ = dict(sample=a.sample, wc_tree=a.wc_tree, list=os.path.abspath(a.list), list_sha256=_sha256(a.list), slice=a.slice,
                files=len(lines), errors=int((F.error != '').sum()) if 'error' in F else 0,
                events=int(F.events.sum()) if 'events' in F else 0, wc_events=int(F.wc_events.sum()) if 'wc_events' in F else 0,
                candidates=len(C), object_rows=nobj, wct_versions=sorted(set(F.wct_version.dropna())) if 'wct_version' in F else [],
                extractor_sha256=_sha256(os.path.abspath(__file__)), chain_module_sha256=_sha256(uc.__file__),
                wall_s=round(time.time() - t0, 1))
    json.dump(summ, open(os.path.join(a.out_dir, 'extract_%s%s.json' % (a.sample, sfx)), 'w'), indent=1)
    print(json.dumps(summ))


if __name__ == '__main__':
    main()
