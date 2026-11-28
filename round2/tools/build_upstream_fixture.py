#!/usr/bin/env python3
"""Build the small DEVELOPMENT cross-site fixture for the common upstream-chain scoring bundle (wc_upstream_chain) and the SP
input / prediction chain. Authorized by Avinay (2026-11-28) for Aurora development samples and the permitted beam-off TRAINING
half only. No official FermiGrid evaluation sample, no beam-on, no even-run beam-off, no Run-3 BNB, no open data.

Output (work area, never git):
  OUT/FIXTURE_MANIFEST.json, OUT/SHA256SUMS, OUT/README_FIXTURE.md
  OUT/mc/cases/<sample>/<mode>/          simulated NC Delta, BNB, nu_e CC, both vertex trees
  OUT/beamoff_restricted/cases/wcl1116-fg-beamoff-train/<mode>/   beam-off TRAINING-half rows (data: training-half restrictions)
    cands.parquet          inputs in Xuyang's cands_ schema (+ sample, fixture_tags)
    objs_<model>.parquet   per-object inputs of the 18 level-1 models for these candidates
    expected_upstream.parquet   stored_* (CAF, shipped weights), ship_* (shipped final models on stored level-1: == stored),
                           chain_release_* (toolkit-equivalent released weights; kind mc/data), chain_release_noscale_* (MC diagnostic),
                           official_xgb_* (the release's standalone xgboost scripts, for the split-crossing cases), diag_*, fixture_tags
    sp_rows.parquet        rows of these candidates that pass the SP preselection: key, nested_v1 role, xn_split_v11, signal, class, topology
    sp_features_A.parquet / sp_features_D.parquet   the union of the four SP input vectors in domains A and D
    sp_predictions.parquet  per SP model: legacy XML on A, domain-A development model on A, domain-D development model on D
  OUT/mc/caf/<unit>/{production,released_chain}/*.wc.flat.caf.root   the 18 in-chain test units (simulation only)
  OUT/mc/caf/units.tsv, identity_map.parquet, expected_released_chain_scores.parquet
  OUT/mc/models/DEV_DO_NOT_DEPLOY_*.json   the development SP boosters the predictions came from (never deploy)

  python tools/build_upstream_fixture.py --out DIR --work W --releases CLONE/releases --shipped WCD [--per-tag 25 --random 150]
"""
import argparse, hashlib, json, os, shutil, sys, time

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools')); sys.path.insert(0, os.path.join(ROUND2, 'upstream_chain_bundle'))
import wc_upstream_chain as wuc  # noqa: E402
from wc_upstream_chain import spec as S  # noqa: E402
from sp_retrain import devstudy as dv, devtrain, features, firewall, upstream_overlay as uo  # noqa: E402
import sp_operating_points as spo  # noqa: E402

MODES = {'dv2_split_move': 'recTreeWireCell', 'dv2_snap': 'recTreeWireCell_dv2snap'}
SAMPLES = {'wcl1116-aurora-ncdr': 'mc', 'wcl1116-aurora-bnb': 'mc', 'wcl1116-aurora-nuecc': 'mc', 'wcl1116-fg-beamoff-train': 'data'}
KEY = ['sample'] + wuc.DEFAULT_KEY
ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']
NAME = 'upstream_r4_dev_fixture_v1'
AUTH = ('DEVELOPMENT fixture authorized by Avinay Bhat on 2026-11-28 (Aurora development samples NC Delta / BNB / nu_e CC and the '
        'permitted odd-run beam-off TRAINING half only). Not an evaluation sample; no official FermiGrid, beam-on, even-run beam-off, '
        'Run-3 BNB or open-data event. Development models inside are DEV_DO_NOT_DEPLOY.')


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def hsel(df, n, salt):
    """Deterministic pseudo-random choice of n rows (sha256 of the key)."""
    if len(df) <= n:
        return df
    h = (df['file_id'].astype(str) + '|' + df['run'].astype(str) + '|' + df['subrun'].astype(str) + '|' + df['event'].astype(str) + '|' +
         df['cand'].astype(str)).map(lambda s: hashlib.sha256((salt + s).encode()).hexdigest())
    return df.assign(_h=h.to_numpy()).sort_values('_h').head(n).drop(columns='_h')


def tags_for(C, R, Bd, Off, kind):
    """Edge-case tags per candidate (boolean columns)."""
    t = {}
    nue_n = np.column_stack([C['n_obj_' + m].to_numpy() for m in S.L1_NUE])
    t['all_nue_lists_empty'] = (nue_n.sum(1) == 0) & (C.br_filled.to_numpy() == 1)
    t['some_list_empty'] = (nue_n == 0).any(1) & (nue_n > 0).any(1)
    t['br_filled_0'] = C.br_filled.to_numpy() != 1
    g = (C.pio_filled.to_numpy() == 1) & (C.pio_flag_pio.to_numpy() == 0)
    t['pio2_objects_gate_blocks'] = (C.n_obj_pio_2.to_numpy() > 0) & ~g
    t['pio2_objects_gate_passes'] = (C.n_obj_pio_2.to_numpy() > 0) & g
    t['placeholder'] = C.is_placeholder.to_numpy() == 1
    t['l1_nan_object'] = Bd.diag_l1_models_with_nan_object.to_numpy() > 0
    t['numu_final_nan_input'] = Bd.diag_numu_final_nan_input.to_numpy().astype(bool)
    t['nue_final_nan_input'] = Bd.diag_nue_final_nan_input.to_numpy().astype(bool)
    for col, lab in (('mip_min_dis', 'cap_mip_min_dis'), ('mip_quality_shortest_length', 'cap_mip_quality_shortest_length')):
        t[lab] = C[col].to_numpy() > 1000
    for col in ('mip_quality_shortest_angle', 'stem_dir_ratio', 'cosmict_4_angle_beam', 'cosmict_7_angle_beam'):
        t['nan_' + col] = np.isnan(C[col].to_numpy(np.float64))
    t['multi_candidate_event'] = C.groupby(['file_id', 'run', 'subrun', 'event']).cand.transform('size').to_numpy() >= 3
    if kind == 'mc':
        t['numu_cc_flag_switched_off'] = Bd.diag_numu_cc_flag_switched_off.to_numpy().astype(bool)
        d = np.abs(R.r3af_numu_score.to_numpy(np.float64) - R.r3af_noscale_numu_score.to_numpy(np.float64))
        t['sim_scale_moves_numu_score_gt_0p1'] = d > 0.1
    # split crossings: chain (TMVA XML) vs the release's standalone xgboost scripts
    if Off is not None:
        for col, off in (('numu_score', 'official_xgb_numu_score'), ('nue_score', 'official_xgb_nue_score'), ('numu_1_score', 'official_xgb_numu_1_score')):
            ch = R[('r3af_' if col.startswith('numu') else 'nueA2_') + col].to_numpy(np.float64)
            ofv = Off[off].to_numpy(np.float64)
            dd = np.abs(ch - ofv); dd[np.isnan(dd)] = -1
            top = np.argsort(-dd)[:15]
            m = np.zeros(len(C), bool); m[top[dd[top] > 1e-6]] = True
            t['split_crossing_' + col] = m
        l1d = np.max(np.column_stack([np.abs(R['nueA2_%s_score' % mm].to_numpy(np.float64) - Off['official_xgb_%s_score' % mm].to_numpy(np.float64)) for mm in S.L1_NUE]), 1)
        l1d[np.isnan(l1d)] = -1; top = np.argsort(-l1d)[:15]
        m = np.zeros(len(C), bool); m[top[l1d[top] > 0]] = True
        t['split_crossing_nue_l1'] = m
    return pd.DataFrame(t)


def official(off_dir, s, C):
    p_mu, p_e = os.path.join(off_dir, 'numu_%s.parquet' % s), os.path.join(off_dir, 'nue_%s.parquet' % s)
    if not (os.path.exists(p_mu) and os.path.exists(p_e)):
        return None
    K = wuc.DEFAULT_KEY
    mu = pd.read_parquet(p_mu); e = pd.read_parquet(p_e)
    O = C[K].copy()
    mu = mu.assign(official_xgb_numu_score=(2 / np.log(10) * mu.d6_f0.to_numpy(np.float64)).astype(np.float32),
                   official_xgb_numu_1_score=mu.l1_numu_1, official_xgb_numu_2_score=mu.l1_numu_2, official_xgb_cosmict_10_score=mu.l1_cosmict_10)
    O = O.merge(mu[K + ['official_xgb_numu_score', 'official_xgb_numu_1_score', 'official_xgb_numu_2_score', 'official_xgb_cosmict_10_score']], on=K, how='left')
    e = e.rename(columns=dict({'l1_' + m: 'official_xgb_%s_score' % m for m in S.L1_NUE}, score='official_xgb_nue_score'))
    O = O.merge(e[K + ['official_xgb_%s_score' % m for m in S.L1_NUE] + ['official_xgb_nue_score']], on=K, how='left')
    if len(O) != len(C):
        raise SystemExit('official join changed rows for %s' % s)
    return O


def sp_block(sel, J, mode, a):
    """SP preselected rows of the selected candidates, both domains, with predictions of the development models."""
    import xgboost as xgb
    k = J[devtrain.ROW_KEY].copy()
    for c in ('run', 'subrun', 'event', 'cand'):
        k[c] = k[c].astype(np.int64)
    s = sel[devtrain.ROW_KEY].copy()
    for c in ('run', 'subrun', 'event', 'cand'):
        s[c] = s[c].astype(np.int64)
    idx = k.reset_index().merge(s, on=devtrain.ROW_KEY, how='inner')['index'].to_numpy()
    JA = J.iloc[idx].reset_index(drop=True)
    if not len(JA):
        return None
    JD = uo.apply(JA, 'D', a.overlay_root + '/' + mode)
    cols_union = sorted(set(sum((features.load(spo.CLF[m]).columns for m in spo.ORDER), [])))
    rows = JA[devtrain.ROW_KEY + ['role', 'signal', 'bkg_class', 'topology']].copy()
    rows['xn_split_v11'] = uo.xn_split_v11(rows['sample'], rows['run'], rows['subrun'])
    FA = JA[devtrain.ROW_KEY + cols_union].copy(); FD = JD[devtrain.ROW_KEY + cols_union].copy()
    pred = JA[devtrain.ROW_KEY].copy()
    models = {}
    for m in spo.ORDER:
        clf = spo.CLF[m]; cols = features.load(clf).columns
        dD = {'numu': 'B', 'other': 'B', 'ncpi0': 'C', 'nue': 'A'}[m]
        fA = os.path.join(a.studies_root, mode, m, 'FIT_BASELINE_%s_%s.json' % (m, mode))
        fD = os.path.join(a.retrained_root, mode, 'RETRAINED_%s_%s_%s.json' % (m, mode, dD))
        bA = xgb.Booster(); bA.load_model(fA); bD = xgb.Booster(); bD.load_model(fD)
        for dom, Jx in (('A', JA), ('D', JD)):
            X64 = Jx[cols].to_numpy(np.float64); fin = np.isfinite(X64).all(1) & np.isfinite(X64.astype(np.float32)).all(1)
            X = np.nan_to_num(X64, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
            pred['%s_finite_inputs_%s' % (m, dom)] = fin
            if dom == 'A':
                pred['%s_legacy_xml_on_A' % m] = np.where(fin, dv.legacy_scores(a.bundle_root, clf, X, cols), -999.0)
                pred['%s_devA_on_A' % m] = np.where(fin, dv.margin(xgb, bA, X, cols), -np.inf)
            else:
                pred['%s_devD_on_D' % m] = np.where(fin, dv.margin(xgb, bD, X, cols), -np.inf)
        models[m] = dict(devA=fA, devD=fD, features=cols)
    return rows, FA, FD, pred, models


def caf_part(a, out, units_tsv):
    import uproot
    U = pd.read_csv(units_tsv, sep='\t')
    U = U.rename(columns={'#sample': 'sample'})
    rows, ident, exp = [], [], []
    for r in U.itertuples():
        base = os.path.basename(r.caf)
        new = os.path.join(a.work, 'chain', 'runs', 'new', r.id, 'merged', base)
        d = os.path.join(out, 'caf', r.id)
        for sub, src in (('production', r.caf), ('released_chain', new)):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
            dst = os.path.join(d, sub, base)
            if not os.path.exists(dst):
                shutil.copyfile(src, dst)
        rows.append(dict(unit=r.id, sample=r.sample, reality=r.reality, file_id=base, production_sha256=sha256(os.path.join(d, 'production', base)),
                         released_chain_sha256=sha256(os.path.join(d, 'released_chain', base)), events=int(r.nev)))
        for mode, tree in MODES.items():
            for sub in ('production', 'released_chain'):
                t = uproot.open(os.path.join(d, sub, base))[tree]
                br = ['wc.run', 'wc.subrun', 'wc.evt', 'wc.valid', 'wc.T_tagger.nu_index'] + ['wc.T_tagger.' + s for s in S.UPSTREAM_OUTPUTS]
                A = t.arrays(br, library='np')
                for i in range(len(A['wc.run'])):
                    if A['wc.valid'][i] != 1:
                        continue
                    for pos, ni in enumerate(A['wc.T_tagger.nu_index'][i]):
                        k = dict(unit=r.id, file_id=base, tree=tree, mode=mode, entry=i, run=int(A['wc.run'][i]), subrun=int(A['wc.subrun'][i]),
                                 event=int(A['wc.evt'][i]), cand=int(ni), position=pos)
                        if sub == 'production':
                            ident.append(k)
                        else:
                            exp.append(dict(k, **{s: float(A['wc.T_tagger.' + s][i][pos]) for s in S.UPSTREAM_OUTPUTS}))
    T = pd.DataFrame(rows); T.to_csv(os.path.join(out, 'caf', 'units.tsv'), sep='\t', index=False)
    pd.DataFrame(ident).to_parquet(os.path.join(out, 'caf', 'identity_map.parquet'), index=False)
    E = pd.DataFrame(exp)
    for s in S.UPSTREAM_OUTPUTS:
        E[s] = E[s].astype(np.float32)
    E.to_parquet(os.path.join(out, 'caf', 'expected_released_chain_scores.parquet'), index=False)
    return T, E


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--out', '--work', '--releases', '--shipped', '--sp-tables-root', '--studies-root', '--retrained-root', '--overlay-root',
              '--bundle-root', '--topology-dir', '--bundle-scores-root', '--units-tsv'):
        ap.add_argument(k, required=True)
    ap.add_argument('--per-tag', type=int, default=25); ap.add_argument('--random', type=int, default=150)
    a = ap.parse_args()
    t0 = time.time()
    firewall.check_output_path(a.out, ALLOWED_OUTPUT)
    if os.path.exists(os.path.join(a.out, 'FIXTURE_MANIFEST.json')):
        raise SystemExit('%s exists: fixtures are versioned, never overwritten' % a.out)
    os.makedirs(a.out, exist_ok=True)
    units = pd.read_csv(a.units_tsv, sep='\t').rename(columns={'#sample': 'sample'})
    unit_files = set(os.path.basename(p) for p in units.caf)
    topo = spo.load_topology(a.topology_dir)
    cases, model_files = [], {}
    for mode in MODES:
        ns = argparse.Namespace(tables=os.path.join(a.sp_tables_root, mode), tag='dev')
        J = spo.joint_frame(mode, ns, topo, roles=(dv.ROLE_FIT, dv.ROLE_NVAL, dv.ROLE_TEST)).reset_index(drop=True)
        for s, kind in SAMPLES.items():
            part = 'mc' if kind == 'mc' else 'beamoff_restricted'
            T = os.path.join(a.work, 'tables', mode)
            C = pd.read_parquet(os.path.join(T, 'cands_%s.parquet' % s))
            R = pd.read_parquet(os.path.join(a.work, 'rescore', mode, 'rescore_%s.parquet' % s))
            Bd = pd.read_parquet(os.path.join(a.bundle_scores_root, mode, 'bundle_%s.parquet' % s))
            for X in (R, Bd):
                if not X[KEY].reset_index(drop=True).equals(C[KEY].reset_index(drop=True)):
                    raise SystemExit('row order differs between the extracted table and %s' % s)
            Off = official(os.path.join(a.work, 'official', mode), s, C)
            tg = tags_for(C, R, Bd, Off, kind)
            if kind == 'mc':
                tg['in_chain_unit'] = C.file_id.isin(unit_files).to_numpy()
            pick = set(hsel(C, a.random, 'rand|%s|%s|' % (s, mode)).index)
            for col in tg.columns:
                q = C[tg[col].to_numpy()]
                pick |= set(q.index if col == 'in_chain_unit' else hsel(q, a.per_tag, '%s|%s|%s|' % (col, s, mode)).index)
            # SP coverage: a few preselected rows of every class present in this sample
            Js = J[J['sample'] == s]
            for cls in sorted(set(Js.bkg_class)):
                q = Js[Js.bkg_class == cls][devtrain.ROW_KEY]
                q = hsel(q, 10, 'sp|%s|%s|%s|' % (cls, s, mode))
                ki = C.reset_index().merge(q, on=devtrain.ROW_KEY, how='inner')['index']
                pick |= set(ki)
            idx = np.array(sorted(pick))
            Cs = C.iloc[idx].reset_index(drop=True)
            tag_str = tg.iloc[idx].apply(lambda r: ','.join(c for c in tg.columns if r[c]), axis=1).to_numpy()
            d = os.path.join(a.out, part, 'cases', s, mode); os.makedirs(d, exist_ok=True)
            Cs.assign(fixture_tags=tag_str).to_parquet(os.path.join(d, 'cands.parquet'), index=False)
            ks = Cs[KEY]
            for m in S.L1_ALL:
                p = os.path.join(T, 'objs_%s_%s.parquet' % (m, s))
                O = pd.read_parquet(p) if os.path.exists(p) else wuc_empty(m)
                O = O.merge(ks, on=KEY, how='inner') if len(O) else O
                O.to_parquet(os.path.join(d, 'objs_%s.parquet' % m), index=False)
            E = ks.copy()
            Rs = R.iloc[idx].reset_index(drop=True); Bs = Bd.iloc[idx].reset_index(drop=True)
            for c in S.STORED_SCORES:
                E['stored_' + c] = Rs['stored_' + c].to_numpy(np.float32)
            E['ship_numu_score'] = Rs.ship_numu_score.to_numpy(np.float32); E['ship_nue_score'] = Rs.ship_nue_score.to_numpy(np.float32)
            for c in S.NUMU_SCORES:
                E['chain_release_' + c] = Rs['r3af_' + c].to_numpy(np.float32)
            for c in S.NUE_L1_SCORES + ['nue_score']:
                E['chain_release_' + c] = Rs['nueA2_' + c].to_numpy(np.float32)
            if kind == 'mc':
                for c in S.NUMU_SCORES:
                    E['chain_release_noscale_' + c] = Rs['r3af_noscale_' + c].to_numpy(np.float32)
            for c in Bs.columns:
                if c.startswith('diag_'):
                    E[c] = Bs[c].to_numpy()
            if Off is not None:
                for c in Off.columns:
                    if c.startswith('official_xgb_'):
                        E[c] = Off[c].iloc[idx].to_numpy(np.float32)
            E['fixture_tags'] = tag_str
            E.to_parquet(os.path.join(d, 'expected_upstream.parquet'), index=False)
            spb = sp_block(Cs, J, mode, a)
            n_sp = 0
            if spb is not None:
                rows, FA, FD, pred, models = spb; n_sp = len(rows)
                rows.to_parquet(os.path.join(d, 'sp_rows.parquet'), index=False)
                FA.to_parquet(os.path.join(d, 'sp_features_A.parquet'), index=False); FD.to_parquet(os.path.join(d, 'sp_features_D.parquet'), index=False)
                pred.to_parquet(os.path.join(d, 'sp_predictions.parquet'), index=False)
                for m, v in models.items():
                    model_files[(mode, m)] = v
            cases.append(dict(dir=os.path.relpath(d, a.out), part=part, sample=s, mode=mode, tree=MODES[mode], kind=kind, key=KEY,
                              candidates=int(len(Cs)), sp_rows=int(n_sp), tags={c: int(tg[c].to_numpy()[idx].sum()) for c in tg.columns}))
            print('case', s, mode, len(Cs), 'sp', n_sp, flush=True)
    # development models (DEV_DO_NOT_DEPLOY), feature lists
    md = os.path.join(a.out, 'mc', 'models'); os.makedirs(md, exist_ok=True)
    mods = []
    for (mode, m), v in sorted(model_files.items()):
        for tagn in ('devA', 'devD'):
            dst = os.path.join(md, 'DEV_DO_NOT_DEPLOY_%s_%s_%s.json' % (m, mode, tagn))
            shutil.copyfile(v[tagn], dst)
            mods.append(dict(file=os.path.relpath(dst, a.out), sp_model=m, mode=mode, domain=tagn[-1], source=v[tagn], sha256=sha256(dst)))
    json.dump({m: features.load(spo.CLF[m]).columns for m in spo.ORDER}, open(os.path.join(md, 'sp_feature_lists.json'), 'w'), indent=1)
    shutil.copyfile(os.path.join(md, 'sp_feature_lists.json'), os.path.join(a.out, 'beamoff_restricted', 'sp_feature_lists.json'))
    T, E = caf_part(a, os.path.join(a.out, 'mc'), a.units_tsv)
    inv = wuc.release_inventory()
    man = dict(name=NAME, schema='wc_upstream_chain.fixture/1', created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), authorization=AUTH,
               bundle_version=wuc.__version__, release_commit=inv['release_commit'], canonical_inventory_fingerprint=inv['fingerprints']['canonical_inventory'],
               chain_fingerprints=inv['chain_fingerprints'], parts=dict(
                   mc='simulation (NC Delta, BNB, nu_e CC); transferable to FNAL; never to a public repository',
                   beamoff_restricted='beam-off TRAINING half (odd runs): experimental data under the existing training-half restrictions; FNAL only, never public'),
               cases=cases, models=mods, caf_units=T.to_dict('records'), caf_expected_rows=int(len(E)),
               conventions='see wc_upstream_chain CONVENTIONS.md; expected values are float32 bit patterns; compare exactly',
               how_to_check='python -m wc_upstream_chain check-fixture <this dir> --releases <clone>/releases --shipped <wire-cell-data>')
    json.dump(man, open(os.path.join(a.out, 'FIXTURE_MANIFEST.json'), 'w'), indent=1, default=str)
    with open(os.path.join(a.out, 'SHA256SUMS'), 'w') as f:
        for root, _, files in os.walk(a.out):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                if fn != 'SHA256SUMS':
                    f.write('%s  %s\n' % (sha256(p), os.path.relpath(p, a.out)))
    print(json.dumps(dict(out=a.out, cases=len(cases), candidates=sum(c['candidates'] for c in cases), caf_units=len(T), wall_s=round(time.time() - t0, 1))))


def wuc_empty(m):
    cols = {'sample': 'object', 'file_id': 'object', 'run': 'int64', 'subrun': 'int64', 'event': 'int64', 'cand': 'int64', 'index': 'int64'}
    for n in S.L1[m]['lists'] + S.L1[m]['scalars'] + ['flag']:
        cols[n] = 'float64'
    return pd.DataFrame({c: pd.Series(dtype=t) for c, t in cols.items()})


if __name__ == '__main__':
    main()
