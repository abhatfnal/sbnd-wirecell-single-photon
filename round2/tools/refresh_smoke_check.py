#!/usr/bin/env python3
"""READ-ONLY smoke comparison: refreshed Round-2 training CAFs (Haiwang's WCLocal2026Nov16-Aurora) vs aurora-r2.

  python refresh_smoke_check.py --sample bnb --new-root NEWROOT --old-manifest OLD.tsv.gz --units 3 --out OUT.json

For the first N units of node0 whose status is OK and whose two validations PASS, the same unit's aurora-r2 merged CAF
is looked up in our aurora-r2 manifest, and both are read with uproot (nothing is written next to them). Checks:
  trees      recTree, recTreeWireCell (dv2_split_move) and recTreeWireCell_dv2snap present
  branches   new recTreeWireCell vs aurora-r2 recTreeWireCell; dv2snap tree vs split-move tree
  keys       (run, subrun, event) sets of recTree and of both Wire-Cell trees, new vs old
  provenance Trun.wct_version, dl_weights, numu / nue XML names (as booked)
  builder    sp_retrain.build_tables.extract on old, new split-move and new snap (wc_tree argument)
  vertex     per matched candidate (run, subrun, event, cand): |delta T_tagger nu_xyz|; fraction of neutrino-partner
             candidates with dist_sce_cm < 1 cm (a smoke number, not a vertex study: BNB fold-1 events trained the DL)
  inputs     every SP numu / other / ncpi0 / nue input and the 74 nu_mu final inputs present; finite on filled rows;
             fraction of matched filled rows whose SP inputs changed
  rescoring  the stored numu_score re-scored offline from the stored inputs with the shipped XML (bit-identity)
Aggregates only are written. No table build, no training.
"""
import argparse
import gzip
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import build_tables, features, tmva_grad  # noqa: E402

TREES = ('recTree', 'recTreeWireCell', 'recTreeWireCell_dv2snap')
KEY = ['run', 'subrun', 'event', 'cand']
SP = ('single_photon_numu', 'single_photon_other', 'single_photon_ncpi0', 'single_photon_nue')


def unit_ok(udir):
    try:
        st = open(os.path.join(udir, 'status')).read().strip()
        v1 = json.load(open(os.path.join(udir, 'validate.json')))
        v2 = json.load(open(os.path.join(udir, 'validate-pr-dv2snap.json')))
    except Exception:
        return False
    return st == 'OK' and 'PASS' in json.dumps(v1) and 'PASS' in json.dumps(v2)


def old_paths(manifest):
    with gzip.open(manifest, 'rt') as f:
        df = pd.read_csv(f, sep='\t')
    return dict(zip(df.unit, df.path))


def strs(t, name):
    try:
        v = t[name].array(library='np', entry_stop=1)[0]
        return bytes(np.asarray(v, dtype=np.int8).tobytes()).decode(errors='replace') if not isinstance(v, (str, bytes)) else str(v)
    except Exception as e:
        return 'unreadable: %s' % str(e).splitlines()[0][:60]


def extract(path, tree):
    info, cands, truth = build_tables.extract(path, 'smoke', os.path.basename(path), 0, wc_tree=tree)
    return info, pd.DataFrame(cands)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--sample', required=True); ap.add_argument('--new-root', required=True)
    ap.add_argument('--old-manifest', required=True); ap.add_argument('--units', type=int, default=3)
    ap.add_argument('--numu-xml', required=True); ap.add_argument('--numu-final-inputs', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    import uproot
    old = old_paths(a.old_manifest)
    node = os.path.join(a.new_root, 'node0')
    units = []
    for u in sorted(os.listdir(node)):
        d = os.path.join(node, u)
        if os.path.isdir(d) and u in old and unit_ok(d):
            m = [x for x in os.listdir(os.path.join(d, 'merged')) if x.endswith('.wc.flat.caf.root')]
            if m:
                units.append((u, os.path.join(d, 'merged', m[0]), old[u]))
        if len(units) >= 3 * a.units:
            break
    numu_xml = tmva_grad.GradForest(a.numu_xml)
    numu_final = json.load(open(a.numu_final_inputs))
    sp_cols = {n: features.load(n).columns for n in SP}
    res = dict(sample=a.sample, new_root=a.new_root, old_manifest=os.path.basename(a.old_manifest), units=[])
    for u, pn, po in units:
        if len(res['units']) >= a.units:
            break
        fn, fo = uproot.open(pn), uproot.open(po)
        r = dict(unit=u, new=pn, old=po, trees_new={t: t in fn for t in TREES}, trees_old={t: t in fo for t in TREES})
        bn, bo = set(fn['recTreeWireCell'].keys()), set(fo['recTreeWireCell'].keys())
        bs = set(fn['recTreeWireCell_dv2snap'].keys())
        r['branches'] = dict(new=len(bn), old=len(bo), snap=len(bs), new_minus_old=sorted(bn - bo), old_minus_new=sorted(bo - bn),
                             split_minus_snap=len(bn - bs), snap_minus_split=sorted(bs - bn),
                             split_minus_snap_all_dlvtx_space=all('dlvtx_space' in b or 'space_cluster_id' in b or b.endswith('n_space') for b in bn - bs))
        ek = {}
        for lab, f, t in (('old', fo, 'recTreeWireCell'), ('new', fn, 'recTreeWireCell'), ('snap', fn, 'recTreeWireCell_dv2snap')):
            k = f[t].arrays(['wc.run', 'wc.subrun', 'wc.evt', 'wc.valid'], library='np')
            ek[lab] = set(zip(k['wc.run'].tolist(), k['wc.subrun'].tolist(), k['wc.evt'].tolist()))
            r.setdefault('valid', {})[lab] = int((k['wc.valid'] == 1).sum())
        h = fn['recTree'].arrays(['rec.hdr.run', 'rec.hdr.subrun', 'rec.hdr.evt'], library='np')
        ho = fo['recTree'].arrays(['rec.hdr.run', 'rec.hdr.subrun', 'rec.hdr.evt'], library='np')
        r['event_keys'] = dict(old=len(ek['old']), new=len(ek['new']), snap=len(ek['snap']), new_equals_old=ek['new'] == ek['old'],
                               snap_equals_new=ek['snap'] == ek['new'],
                               rectree_equal=set(zip(*[h[c].tolist() for c in h])) == set(zip(*[ho[c].tolist() for c in ho])))
        tn, to = fn['recTreeWireCell'], fo['recTreeWireCell']
        r['provenance'] = dict(wct_version_new=strs(tn, 'wc.Trun.wct_version'), wct_version_old=strs(to, 'wc.Trun.wct_version'),
                               wct_version_snap=strs(fn['recTreeWireCell_dv2snap'], 'wc.Trun.wct_version'),
                               dl_weights_new=strs(tn, 'wc.Trun.dl_weights'), dl_weights_old=strs(to, 'wc.Trun.dl_weights'),
                               dl_weights_snap=strs(fn['recTreeWireCell_dv2snap'], 'wc.Trun.dl_weights'),
                               numu_xml_new=strs(tn, 'wc.Trun.numu_xgboost_xml'), nue_xml_new=strs(tn, 'wc.Trun.nue_xgboost_xml'),
                               numu_xml_old=strs(to, 'wc.Trun.numu_xgboost_xml'), nue_xml_old=strs(to, 'wc.Trun.nue_xgboost_xml'))
        C = {}
        for lab, path, tree in (('old', po, 'recTreeWireCell'), ('new', pn, 'recTreeWireCell'), ('snap', pn, 'recTreeWireCell_dv2snap')):
            info, c = extract(path, tree)
            C[lab] = c
            r.setdefault('builder', {})[lab] = dict(error=info.get('error', ''), candidates=int(len(c)),
                                                    non_placeholder=int((c.is_placeholder == 0).sum()) if len(c) else 0,
                                                    filled=int((c.shw_sp_filled == 1).sum()) if len(c) else 0,
                                                    wct_version=info.get('wct_version', ''))
        if any(len(C[k]) == 0 for k in C):
            r['skipped'] = 'no candidate rows in at least one version'
            res.setdefault('skipped_units', []).append(r)
            continue
        need = sorted(set(sum(sp_cols.values(), [])) | set(numu_final))
        for lab in ('new', 'snap'):
            c = C[lab]
            miss = [n for n in need if n not in c.columns]
            filled = c[c.shw_sp_filled == 1]
            r.setdefault('inputs', {})[lab] = dict(
                required=len(need), missing=miss,
                per_model={n: dict(n=len(cols), missing=[x for x in cols if x not in c.columns],
                                   filled_rows=int(len(filled)),
                                   filled_rows_all_finite=int(np.isfinite(filled[[x for x in cols if x in c.columns]].to_numpy(np.float64)).all(1).sum()))
                           for n, cols in sp_cols.items()})
        # vertex and input migration on matched candidates
        for lab in ('new', 'snap'):
            m = C['old'].merge(C[lab], on=KEY, suffixes=('_o', '_n'))
            m = m[(m.is_placeholder_o == 0) & (m.is_placeholder_n == 0)]
            dv = np.sqrt(sum((m['nu_%s_o' % q] - m['nu_%s_n' % q]) ** 2 for q in 'xyz'))
            both = m[(m.shw_sp_filled_o == 1) & (m.shw_sp_filled_n == 1)]
            ch = {}
            for n, cols in sp_cols.items():
                A = both[[x + '_o' for x in cols]].to_numpy(np.float64); B = both[[x + '_n' for x in cols]].to_numpy(np.float64)
                ch[n] = float((~np.isclose(A, B, rtol=0, atol=0, equal_nan=True)).any(1).mean()) if len(both) else float('nan')
            nu_o = m[m.partner_kind_o.astype(str) == 'neutrino']; nu_n = m[m.partner_kind_n.astype(str) == 'neutrino']
            r.setdefault('migration', {})[lab] = dict(
                matched_candidates=int(len(m)), old_non_placeholder=int((C['old'].is_placeholder == 0).sum()),
                vertex_moved_gt_0p1cm=float((dv > 0.1).mean()) if len(m) else float('nan'),
                vertex_shift_median_cm=float(np.median(dv)) if len(m) else float('nan'),
                filled_old=int((m.shw_sp_filled_o == 1).sum()), filled_new=int((m.shw_sp_filled_n == 1).sum()),
                filled_both=int(len(both)), sp_inputs_changed_frac=ch,
                dist_sce_lt_1cm_old=float((nu_o.dist_sce_cm_o < 1).mean()) if len(nu_o) else float('nan'),
                dist_sce_lt_1cm_new=float((nu_n.dist_sce_cm_n < 1).mean()) if len(nu_n) else float('nan'),
                neutrino_partner_rows=[int(len(nu_o)), int(len(nu_n))])
        c = C['new'][C['new'].is_placeholder == 0]
        X = c[numu_xml.names].to_numpy(np.float64).astype(np.float32)
        s = tmva_grad.log10_odds(numu_xml.evaluate_mva(X)).astype(np.float32)
        r['numu_rescore_new'] = dict(candidates=int(len(c)), bit_identical=int((s == c.numu_score.to_numpy(np.float64).astype(np.float32)).sum()))
        res['units'].append(r)
        print(json.dumps(dict(unit=u, events=r['event_keys'], builder=r['builder'], migration=r['migration'],
                              numu=r['numu_rescore_new']), default=str), flush=True)
    U = res['units']
    agg = dict(units=len(U), skipped_units=len(res.get('skipped_units', [])), events=sum(u['event_keys']['new'] for u in U),
               all_trees_present=all(all(u['trees_new'].values()) for u in U),
               branches_new_equal_old=all(not u['branches']['new_minus_old'] and not u['branches']['old_minus_new'] for u in U),
               snap_lacks_only_dlvtx_space=all(u['branches']['split_minus_snap_all_dlvtx_space'] and not u['branches']['snap_minus_split'] for u in U),
               event_keys_equal=all(u['event_keys']['new_equals_old'] and u['event_keys']['snap_equals_new'] and u['event_keys']['rectree_equal'] for u in U),
               builder_errors=sum(bool(u['builder'][k]['error']) for u in U for k in u['builder']),
               missing_inputs={k: sorted(set(sum((u['inputs'][k]['missing'] for u in U), []))) for k in ('new', 'snap')},
               wct_versions=sorted({u['provenance']['wct_version_new'] for u in U} | {u['provenance']['wct_version_snap'] for u in U}),
               wct_versions_old=sorted({u['provenance']['wct_version_old'] for u in U}),
               dl_weights=sorted({u['provenance']['dl_weights_new'] for u in U}), dl_weights_snap=sorted({u['provenance']['dl_weights_snap'] for u in U}),
               dl_weights_old=sorted({u['provenance']['dl_weights_old'] for u in U}),
               numu_xml=sorted({u['provenance']['numu_xml_new'] for u in U}), nue_xml=sorted({u['provenance']['nue_xml_new'] for u in U}),
               numu_rescore=dict(candidates=sum(u['numu_rescore_new']['candidates'] for u in U), bit_identical=sum(u['numu_rescore_new']['bit_identical'] for u in U)))
    for lab in ('new', 'snap'):
        M = [u['migration'][lab] for u in U]; n = sum(m['matched_candidates'] for m in M)
        w = lambda k: float(sum(m[k] * m['matched_candidates'] for m in M if m[k] == m[k]) / max(n, 1))
        nuo = sum(m['neutrino_partner_rows'][0] for m in M); nun = sum(m['neutrino_partner_rows'][1] for m in M)
        agg['migration_' + lab] = dict(
            matched_candidates=n, old_non_placeholder=sum(m['old_non_placeholder'] for m in M),
            vertex_moved_gt_0p1cm=w('vertex_moved_gt_0p1cm'),
            filled_old=sum(m['filled_old'] for m in M), filled_new=sum(m['filled_new'] for m in M), filled_both=sum(m['filled_both'] for m in M),
            dist_sce_lt_1cm_old=float(sum(m['dist_sce_lt_1cm_old'] * m['neutrino_partner_rows'][0] for m in M if m['dist_sce_lt_1cm_old'] == m['dist_sce_lt_1cm_old']) / max(nuo, 1)),
            dist_sce_lt_1cm_new=float(sum(m['dist_sce_lt_1cm_new'] * m['neutrino_partner_rows'][1] for m in M if m['dist_sce_lt_1cm_new'] == m['dist_sce_lt_1cm_new']) / max(nun, 1)),
            neutrino_partner_rows=[nuo, nun])
    res['summary'] = agg
    json.dump(res, open(a.out, 'w'), indent=1, default=str)
    print(json.dumps(agg, indent=1, default=str))


if __name__ == '__main__':
    main()
