#!/usr/bin/env python3
"""Machine-readable TRAINING-MEMBERSHIP manifest of the four Aurora development samples (one vertex tree per run), for the
EAF disjointness checks (V7) and the upstream-overlap bookkeeping. Reads only Aurora development tables, the permitted beam-off
TRAINING half, production logs and Xuyang's spec code; never an official FermiGrid evaluation sample.

Per candidate (OUT/membership_candidates_<mode>.parquet):
  identity    sample, file_id, run, subrun, event, cand (= wc.T_tagger.nu_index)
  SP          sp_preselected; sp_split (train / test = the existing outer holdout: MC odd subrun, beam-off run % 4 == 1);
              sp_nested_role (fit / nval / test, nested_v1 per (sample, run, subrun)); per SP model in_<m> (row in that model's
              development dataset) and cls_<m> (1 / 0)
  upstream    xn_split_v11 (Xuyang's spec_v1.split_v11 role of the row's unit: dev = early-stopping slice, train = fitted);
              up_numu_pool / up_numu_role and up_nue_pool / up_nue_role: 'fit' (in the training pool, train slice), 'early_stop'
              (in the pool, dev slice), 'ineligible' (outside the pool). Pools from his training code (repo 0f13988d):
                numu_round3af  training/numu/train_numu_l2.py: samples bnb, ncdr (NC partner rows only: partner_kind ==
                               'neutrino' & iou_n > 0 & m_ccnc == 1), beam-off train; is_placeholder == 0, label_unreadable == 0,
                               reco vertex (nu_x, nu_y, nu_z) in spec_v1.in_fv. (Small models: additionally cosmict_flag_1 == 0
                               and rule A on objects: up_numu_l1_pool.)
                nue_round4_ruleA_v2  training/round2/train_l2.py: samples nuecc, bnb, ncdr, beam-off train; is_placeholder == 0,
                               label_unreadable == 0, spec_v1.pool_mask (br_filled == 1 and reco vertex in FV); BNB rows of the
                               spills spec_v1.filtered_spills holds dropped.
  generator   gen_duplicate_group: BNB events whose generated neutrino list is identical to another event's (same event number,
              pdg, energy, vertex; GEN master-seed collisions under the 'random' seed policy); -1 otherwise
  dl_vertex   dlvtx_training_status: what is known of the DV2-MAX aurora_space training use of the event's production units

Per event (OUT/membership_events.parquet; split-move run only): identity, roles, generator job (production, instance, group),
log location, computed linearMapping seeds (configL samples) or the parsed master seed (BNB duplicate groups).
Per file (OUT/membership_files.parquet). Summary JSON with counts and sha256 of every parquet: --summary-json (committed).

  python tools/build_training_membership_manifest.py --mode M --sp-tables T --tag dev --spec-v1 CLONE/spec --out-dir OUT --summary-json J [--events]
"""
import argparse, glob, hashlib, importlib.util, io, json, os, re, sys, tarfile, time

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devstudy as dv, devtrain, firewall, labels, upstream_overlay as uo  # noqa: E402
import sp_operating_points as spo  # noqa: E402
from legacy_control_compare import load_cands  # noqa: E402

B = '/lus/flare/projects/neutrinoGPU/abhat/sbnd'
NCDR, BNB, NUECC, EXT = spo.NCDR, spo.BNB, spo.NUECC, spo.EXT
SAMPLES = (NCDR, BNB, NUECC, EXT)
ALLOWED_OUTPUT = [B]
# generator productions (Avinay's Aurora Gen-2 productions; numbering in their driver code, verified on logs)
CONFIGL = {NCDR: dict(prod=B + '/gen2-sbnd-ncdeltarad-train-configL-reco1-flatcaf-v100205-wct0319-20261029', first_run=7000000, spc=100,
                      offsets=dict(gen=75000000, g4=87000000, detsim=88000000, reco1=89000000)),
           NUECC: dict(prod=B + '/gen2-sbnd-ccnue-configL-300k-reco1-flatcaf-v100205-wct0319-20261027', first_run=6700000, spc=51,
                       offsets=dict(gen=0, g4=4000000, detsim=5000000, reco1=6000000))}
SEED_K = dict(noise=1, corsika_gen=2, corsika_pois=3, generator=4, largeantcosmic=5, largeantnu=6)
BNB_PRODS = [(2100000, B + '/gen2-wct0319-bnb-1m-restartable-20261013-shard01'), (2105000, B + '/gen2-wct0319-bnb-1m-restartable-20261013-shard02'),
             (2110000, B + '/gen2-wct0319-bnb-1m-restartable-20261013-shard03')] + \
            [(5000000 + 100 * (k - 1), B + '/gen2-wct0319-bnb-1m-capacity-20261016-batch%02d' % k) for k in range(1, 11)]
DLVTX = {BNB: 'production units shared with the DV2-MAX aurora_space training sample (aurora-r2 BNB); per-event fold (training vs 15k hold-out) NOT recoverable on Aurora -- request from Snehadri',
         NUECC: 'production units shared with the DV2-MAX aurora_space training sample (aurora-r2 intrinsic nu_e CC); per-event fold NOT recoverable on Aurora -- request from Snehadri',
         NCDR: 'not listed in the DV2-MAX aurora_space training data (bundle README)', EXT: 'not listed in the DV2-MAX aurora_space training data (bundle README)'}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def spec_v1(path):
    s = importlib.util.spec_from_file_location('spec_v1', os.path.join(path, 'spec_v1.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def duplicate_groups(truth):
    t = truth.sort_values(['run', 'subrun', 'event', 'pdg', 'E'])
    k = (t.event.astype(str) + '|' + t.pdg.astype(str) + '|' + t.E.map('{:.6f}'.format) + '|' + t.vx.map('{:.3f}'.format) + '|' +
         t.vy.map('{:.3f}'.format) + '|' + t.vz.map('{:.3f}'.format))
    sig = k.groupby([t.run, t.subrun, t.event]).agg(';'.join)
    d = sig[sig.duplicated(keep=False)].rename('sig').reset_index()
    d['gen_duplicate_group'] = pd.factorize(d.sig)[0]
    return d[['run', 'subrun', 'event', 'gen_duplicate_group']]


def bnb_job(run, subrun):
    first, prod = max(((f, p) for f, p in BNB_PRODS if f < run), key=lambda x: x[0])
    inst = (run - first - 1) * 100 + subrun
    return prod, inst, '%s/%06d/%06d/subrun_%06d' % (prod, inst // 1000, inst // 100, inst)


def gen_seeds(logdir):
    """(master seed, 'generator' engine seed) from the NuRandomService summary in the GEN-stage log; (None, None) if absent."""
    p = os.path.join(logdir, 'messages_gen.log')
    if not os.path.exists(p):
        return None, None
    txt = open(p, errors='replace').read()
    m = re.search(r'master seed: (\d+)', txt)
    g = re.search(r'^\s+(\d+)\s+\(same\)\s+generator\s*$', txt, re.M)
    return (int(m.group(1)) if m else None), (int(g.group(1)) if g else None)


def configl_seed_check(sample, events, n=3):
    """Read the GEN log of n events from the group tars and compare the generator seed with 10*(offset + inst) + 4."""
    c = CONFIGL[sample]; out = []
    for r in events.iloc[np.linspace(0, len(events) - 1, n).astype(int)].itertuples():
        inst = (r.run - c['first_run'] - 1) * 100 + r.subrun; g = inst // c['spc']
        tp = '%s/logs/%06d/group_%06d.tar' % (c['prod'], g // 1000, g)
        got = None
        try:
            t = tarfile.open(tp); m = [x for x in t.getnames() if x.endswith('subrun_%08d.ok.tgz' % inst)]
            inner = tarfile.open(fileobj=io.BytesIO(t.extractfile(m[0]).read()), mode='r:gz')
            txt = ''.join(inner.extractfile(x).read().decode(errors='replace') for x in inner.getnames() if 'messages' in x and 'gen' in x.lower())
            s = [int(a) for a, l in re.findall(r'^\s+(\d+)\s+\(same\)\s+(\S+)', txt, re.M) if 'generator' in l]
            got = s[0] if s else None
        except Exception as e:
            got = 'ERROR %s' % e
        out.append(dict(run=int(r.run), subrun=int(r.subrun), inst=int(inst), logged_generator_seed=got,
                        computed=10 * (c['offsets']['gen'] + inst) + SEED_K['generator']))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--mode', '--sp-tables', '--tag', '--spec-v1', '--out-dir', '--summary-json'):
        ap.add_argument(k, required=True)
    ap.add_argument('--events', action='store_true', help='also write the per-event and per-file tables (run once, split-move)')
    a = ap.parse_args()
    t0 = time.time()
    firewall.check_output_path(a.out_dir, ALLOWED_OUTPUT); os.makedirs(a.out_dir, exist_ok=True)
    X = spec_v1(a.spec_v1)
    need = devtrain.ROW_KEY + ['is_placeholder', 'label_unreadable', 'br_filled', 'nu_x', 'nu_y', 'nu_z', 'partner_kind', 'iou_n', 'm_ccnc',
                               'shw_sp_n_20mev_showers', 'cosmict_flag_1']
    parts, files = [], []
    other = spo.spec_of('other', a.mode); stamp = json.load(open(os.path.join(os.path.dirname(ROUND2), other['samples']['input_manifest'])))['reconstruction']['wct_version_stamp']
    import pyarrow.parquet as pq
    for s in SAMPLES:
        F = pd.read_parquet(os.path.join(a.sp_tables, 'files_%s_%s.parquet' % (s, a.tag)))
        p = os.path.join(a.sp_tables, 'cands_%s_%s.parquet' % (s, a.tag)); have = set(pq.read_schema(p).names)
        C = pd.read_parquet(p, columns=[c for c in need if c in have])
        for c in need:
            if c not in C.columns:
                C[c] = {'partner_kind': 'none', 'label_unreadable': 0}.get(c, np.nan)
        files.append(F.assign(sample=s))
        parts.append(C)
    C = pd.concat(parts, ignore_index=True)
    smp = C['sample'].astype(str).to_numpy()
    C['sp_preselected'] = labels.preselection(C, ext_ids=(EXT,))
    C['sp_split'] = np.where(smp == EXT, np.where(C.run % 4 == 1, 'test', 'train'), np.where(C.subrun % 2 == 1, 'test', 'train'))
    C['sp_nested_role'] = dv.nested_roles(C.rename(columns={'sp_split': 'split'})[['sample', 'run', 'subrun', 'split']])
    for m in spo.ORDER:                                   # rows of each SP model's development dataset (stamp-checked files, classes, finite)
        spec = spo.spec_of(m, a.mode)
        ds = devtrain.build_dataset(load_cands(a.sp_tables, a.tag, spec, []), spec)
        k = ds['keys'][devtrain.ROW_KEY].assign(**{'in_' + m: True, 'cls_' + m: ds['y']})
        for c in ('run', 'subrun', 'event', 'cand'):
            k[c] = k[c].astype(np.int64)
        C = C.merge(k, on=devtrain.ROW_KEY, how='left')
        C['in_' + m] = C['in_' + m].fillna(False).astype(bool); C['cls_' + m] = C['cls_' + m].fillna(-1).astype(np.int8)
    C['xn_split_v11'] = uo.xn_split_v11(C['sample'], C['run'], C['subrun'])
    base = (C.is_placeholder.to_numpy() == 0) & (C.label_unreadable.fillna(0).to_numpy() == 0)
    fv = X.in_fv(C.nu_x, C.nu_y, C.nu_z)
    ncdr_nc = (C.partner_kind.astype(str).to_numpy() == 'neutrino') & (C.iou_n.fillna(0).to_numpy() > 0) & (C.m_ccnc.to_numpy() == 1)
    numu_pool = base & fv & (np.isin(smp, [BNB, EXT]) | ((smp == NCDR) & ncdr_nc))
    nue_pool = base & X.pool_mask(C.br_filled, C.nu_x, C.nu_y, C.nu_z) & np.isin(smp, [NUECC, BNB, NCDR, EXT])
    truth_bnb = pd.read_parquet(os.path.join(a.sp_tables, 'truth_%s_%s.parquet' % (BNB, a.tag)), columns=['file_id', 'run', 'subrun', 'event', 'pdg', 'ccnc', 'E', 'vx', 'vy', 'vz'])
    spills = X.filtered_spills(truth_bnb)
    hit = C[['file_id', 'run', 'subrun', 'event']].astype({'file_id': str}).merge(spills.astype({'file_id': str}).assign(_h=1), on=['file_id', 'run', 'subrun', 'event'],
                                                                                    how='left')['_h'].notna().to_numpy() & (smp == BNB)
    nue_pool &= ~hit
    role = lambda pool: np.where(~pool, 'ineligible', np.where(C.xn_split_v11.to_numpy() == 'dev', 'early_stop', 'fit')).astype(object)
    C['up_numu_pool'] = numu_pool; C['up_numu_role'] = role(numu_pool)
    C['up_numu_l1_pool'] = numu_pool & (C.cosmict_flag_1.to_numpy() == 0)
    C['up_nue_pool'] = nue_pool; C['up_nue_role'] = role(nue_pool)
    C['up_nue_bnb_filtered_spill_dropped'] = hit
    dups = duplicate_groups(truth_bnb)
    C = C.merge(dups.assign(sample=BNB), on=['sample', 'run', 'subrun', 'event'], how='left')
    C['gen_duplicate_group'] = C.gen_duplicate_group.fillna(-1).astype(np.int32)
    C['dlvtx_training_status'] = C['sample'].map(DLVTX)
    keep = devtrain.ROW_KEY + ['is_placeholder', 'sp_preselected', 'sp_split', 'sp_nested_role'] + ['in_' + m for m in spo.ORDER] + ['cls_' + m for m in spo.ORDER] + \
        ['xn_split_v11', 'up_numu_pool', 'up_numu_role', 'up_numu_l1_pool', 'up_nue_pool', 'up_nue_role', 'up_nue_bnb_filtered_spill_dropped', 'gen_duplicate_group',
         'dlvtx_training_status']
    C = C[keep]
    out_c = os.path.join(a.out_dir, 'membership_candidates_%s.parquet' % a.mode)
    C.to_parquet(out_c, index=False)
    summ = dict(label='TRAINING-MEMBERSHIP MANIFEST (Aurora development samples; DEVELOPMENT ONLY; no official evaluation event read)', mode=a.mode,
                tree=dict(dv2_split_move='recTreeWireCell', dv2_snap='recTreeWireCell_dv2snap')[a.mode],
                definitions={k: v for k, v in (
                    ('sp_split', 'outer development holdout: MC subrun % 2 == 1, beam-off run % 4 == 1 -> test; else train'),
                    ('sp_nested_role', 'nested_v1: sha256("nested_v1|sample|run|subrun") / 2^32 < 0.20 -> nval, else fit (train side only)'),
                    ('xn_split_v11', 'Xuyang spec_v1.split_v11: MC subrun % 10 == 0 -> dev; beam-off run % 10 == 1 -> dev; else train'),
                    ('up_numu_pool', 'training/numu/train_numu_l2.py @0f13988d: bnb, ncdr NC-partner rows, beam-off; placeholder 0, label readable, reco vertex in spec_v1.in_fv'),
                    ('up_nue_pool', 'training/round2/train_l2.py @0f13988d: nuecc, bnb, ncdr, beam-off; placeholder 0, label readable, spec_v1.pool_mask; BNB filtered spills dropped'),
                    ('up_*_role', 'fit = in pool and xn train (rows the released trees were fitted on); early_stop = in pool and xn dev (early stopping only); '
                                  'ineligible = outside the pool. The released models are the early-stopped fits on the train rows (no 100 % retrain; '
                                  'training/numu/freeze_numu_l2.py, nue chain_v2 f0.5)'),
                    ('gen_duplicate_group', 'BNB events with an identical generated neutrino list (event number, pdg, E to 1e-6 GeV, vertex to 1e-3 cm) as another event'),
                    ('dlvtx_training_status', 'DV2-MAX aurora_space bundle README: trained on aurora-r2 BNB + intrinsic nu_e CC (fold 0 = 15k-event hold-out); per-event folds not on Aurora'))},
                candidates=int(len(C)), sha256=dict(membership_candidates=sha256(out_c)), counts={})
    for s in SAMPLES:
        q = C['sample'] == s
        summ['counts'][s] = dict(candidates=int(q.sum()), sp_preselected=int((q & C.sp_preselected).sum()),
                                 sp_nested_role={k: int(v) for k, v in C[q].sp_nested_role.value_counts().items()},
                                 xn_split_v11={k: int(v) for k, v in C[q].xn_split_v11.value_counts().items()},
                                 up_numu_role={k: int(v) for k, v in C[q].up_numu_role.value_counts().items()},
                                 up_nue_role={k: int(v) for k, v in C[q].up_nue_role.value_counts().items()},
                                 in_model={m: int((q & C['in_' + m]).sum()) for m in spo.ORDER},
                                 sp_holdout_rows_fitted_upstream=dict(
                                     numu=int((q & (C.sp_split == 'test') & (C.up_numu_role == 'fit')).sum()),
                                     nue=int((q & (C.sp_split == 'test') & (C.up_nue_role == 'fit')).sum()),
                                     either=int((q & (C.sp_split == 'test') & ((C.up_numu_role == 'fit') | (C.up_nue_role == 'fit'))).sum())))
        cross = C[q & C.sp_preselected]
        summ['counts'][s]['preselected_crosstab_sp_role_x_up_numu_role'] = {f'{a_}|{b_}': int(v) for (a_, b_), v in cross.groupby(['sp_nested_role', 'up_numu_role']).size().items()}
        summ['counts'][s]['preselected_crosstab_sp_role_x_up_nue_role'] = {f'{a_}|{b_}': int(v) for (a_, b_), v in cross.groupby(['sp_nested_role', 'up_nue_role']).size().items()}
    summ['upstream_bnb_filtered_spills'] = dict(spills=int(len(spills)), candidate_rows_dropped=int(hit.sum()))
    g = C[C.gen_duplicate_group >= 0]
    summ['generator_duplicates_bnb'] = dict(groups=int(dups.gen_duplicate_group.nunique()), events=int(len(dups)),
                                            candidates_in_groups=int(len(g)))
    if a.events:
        T = []
        for s in (NCDR, BNB, NUECC):
            t = pd.read_parquet(os.path.join(a.sp_tables, 'truth_%s_%s.parquet' % (s, a.tag)), columns=['file_id', 'run', 'subrun', 'event'])
            T.append(t.drop_duplicates().assign(sample=s))
        cev = C[['sample', 'file_id', 'run', 'subrun', 'event']].drop_duplicates()
        E = pd.concat(T + [cev[cev['sample'] == EXT]], ignore_index=True)
        E = pd.concat([E, cev], ignore_index=True).drop_duplicates(['sample', 'file_id', 'run', 'subrun', 'event']).reset_index(drop=True)
        se = E['sample'].to_numpy()
        E['sp_split'] = np.where(se == EXT, np.where(E.run % 4 == 1, 'test', 'train'), np.where(E.subrun % 2 == 1, 'test', 'train'))
        E['sp_nested_role'] = dv.nested_roles(E.rename(columns={'sp_split': 'split'})[['sample', 'run', 'subrun', 'split']])
        E['xn_split_v11'] = uo.xn_split_v11(E['sample'], E['run'], E['subrun'])
        E = E.merge(dups.assign(sample=BNB), on=['sample', 'run', 'subrun', 'event'], how='left')
        E['gen_duplicate_group'] = E.gen_duplicate_group.fillna(-1).astype(np.int32)
        E['gen_production'] = ''; E['gen_instance'] = -1; E['gen_group'] = -1; E['gen_log'] = ''
        for k in SEED_K:
            E['seed_gen_' + k] = -1
        E['seed_g4_largeantnu'] = -1; E['seed_detsim_noise'] = -1; E['seed_source'] = ''
        for s, c in CONFIGL.items():
            q = (se == s)
            inst = (E.run[q] - c['first_run'] - 1) * 100 + E.subrun[q]; grp = inst // c['spc']
            E.loc[q, 'gen_production'] = os.path.basename(c['prod']); E.loc[q, 'gen_instance'] = inst; E.loc[q, 'gen_group'] = grp
            E.loc[q, 'gen_log'] = ['logs/%06d/group_%06d.tar:subrun_%08d.ok.tgz' % (g_ // 1000, g_, i_) for g_, i_ in zip(grp, inst)]
            for k, kk in SEED_K.items():
                E.loc[q, 'seed_gen_' + k] = 10 * (c['offsets']['gen'] + inst) + kk
            E.loc[q, 'seed_g4_largeantnu'] = 10 * (c['offsets']['g4'] + grp) + SEED_K['largeantnu']
            E.loc[q, 'seed_detsim_noise'] = 10 * (c['offsets']['detsim'] + grp) + SEED_K['noise']
            E.loc[q, 'seed_source'] = 'computed: NuRandomService linearMapping, seed = 10*(offset + job) + k (GEN job = instance, later stages = group)'
        q = se == BNB
        jobs = [bnb_job(int(r), int(s_)) for r, s_ in zip(E.run[q], E.subrun[q])]
        E.loc[q, 'gen_production'] = [os.path.basename(j[0]) for j in jobs]; E.loc[q, 'gen_instance'] = [j[1] for j in jobs]
        E.loc[q, 'gen_log'] = [os.path.relpath(j[2], B) for j in jobs]
        E.loc[q, 'seed_source'] = "NuRandomService 'random' policy: seeds only in the per-subrun logs (gen_log/messages_<stage>.log); master seed parsed for duplicate groups"
        dq = q & (E.gen_duplicate_group.to_numpy() >= 0)
        sd = [gen_seeds(os.path.join(B, p)) for p in E.gen_log[dq]]
        E.loc[dq, 'seed_gen_master'] = [x[0] for x in sd]; E.loc[dq, 'seed_gen_generator'] = [x[1] for x in sd]
        E.loc[se == EXT, 'seed_source'] = 'data (beam-off): no generator'
        out_e = os.path.join(a.out_dir, 'membership_events.parquet'); E.to_parquet(out_e, index=False)
        Fa = pd.concat(files, ignore_index=True)[['sample', 'file_id', 'path', 'size_bytes', 'events', 'wc_events', 'candidates', 'wct_version', 'ismc']]
        out_f = os.path.join(a.out_dir, 'membership_files.parquet'); Fa.to_parquet(out_f, index=False)
        logs_found = int(sum(os.path.isdir(os.path.join(B, p)) for p in E.gen_log[q].iloc[np.linspace(0, int(q.sum()) - 1, 50).astype(int)]))
        dg = E[dq]
        summ['events'] = dict(rows=int(len(E)), by_sample={k: int(v) for k, v in E['sample'].value_counts().items()},
                              files_events_total={s: int(Fa[Fa['sample'] == s].events.sum()) for s in SAMPLES},
                              note='MC events = truth-table events plus candidate events; beam-off events = events with a Wire-Cell candidate (file and run lists are complete)',
                              run_subrun_event_unique_across_mc=bool(not E[E['sample'] != EXT].duplicated(['run', 'subrun', 'event']).any()),
                              bnb_log_dirs_found_of_50_sampled=logs_found,
                              configl_seed_check={s: configl_seed_check(s, E[se == s]) for s in CONFIGL},
                              bnb_duplicate_groups_with_equal_master_seed=int(dg.groupby('gen_duplicate_group').seed_gen_master.nunique().eq(1).sum()),
                              bnb_duplicate_groups_with_equal_generator_engine_seed=int(dg.groupby('gen_duplicate_group').seed_gen_generator.nunique().eq(1).sum()),
                              bnb_duplicate_subrun_pairs=int(dg.groupby('gen_duplicate_group').apply(lambda x: tuple(sorted(zip(x.run, x.subrun)))).nunique()),
                              bnb_duplicate_groups_straddling=dict(sp_split=int(dg.groupby('gen_duplicate_group').sp_split.nunique().gt(1).sum()),
                                                                   sp_nested_role=int(dg.groupby('gen_duplicate_group').sp_nested_role.nunique().gt(1).sum()),
                                                                   xn_split_v11=int(dg.groupby('gen_duplicate_group').xn_split_v11.nunique().gt(1).sum())),
                              beamoff=dict(files=int((Fa['sample'] == EXT).sum()), runs_with_candidates=sorted(int(x) for x in set(C[C['sample'] == EXT].run)),
                                           runs_from_file_names=sorted(set(int(re.search(r'_run(\d+)_', f).group(1)) for f in Fa[Fa['sample'] == EXT].file_id)),
                                           all_runs_odd=bool((C[C['sample'] == EXT].run % 2 == 1).all())))
        summ['sha256'].update(membership_events=sha256(out_e), membership_files=sha256(out_f))
    summ['wall_s'] = round(time.time() - t0, 1)
    json.dump(summ, open(a.summary_json, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print(json.dumps(dict(mode=a.mode, candidates=len(C), wall_s=summ['wall_s'])))


if __name__ == '__main__':
    main()
