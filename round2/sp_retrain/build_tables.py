#!/usr/bin/env python3
"""Merged CAF(s) -> per-candidate / per-neutrino / per-file parquet tables for single-photon BDT retraining.

  python -m sp_retrain.build_tables SAMPLE OUT_DIR --list LIST [--slice A:B] [--nproc N] \
         --allowed-input-root DIR [...] --allowed-output-root DIR [...] [--holdout-file-ids FILE] [--tag TAG]

Rows
  cands_<sample>.parquet  one row per wc.T_tagger.nu_index entry of every wc.valid == 1 event (no candidate dropped,
                          no deduplication; empty placeholder rows flagged is_placeholder = 1). Columns: key, every
                          per-candidate T_tagger scalar under its T_tagger name, every per-candidate T_kine scalar
                          under its T_kine name (kine_pio_*, kine_nu_*_corr, ...), the T_match level-2 partner and the
                          partner neutrino's truth summary (prefix m_).
  truth_<sample>.parquet  one row per T_truth_nu interaction, none filtered: pdg, ccnc, mode, int_type, E, edep,
                          vertex, the SCE-shifted vertex, and truth INGREDIENTS for single-photon labels (primary pi0
                          count, photon counts by origin, photon conversion points vs the active volume, opening angle
                          of the pi0 photon pair, primary e / mu). No label is computed here.
  files_<sample>.parquet  one row per file, written even when it has no candidate: size, mtime, events, wc_events,
                          wct_version, read flags, hold-out flag. The recTree header POT is kept ONLY as
                          hdr_pot_sum_not_exposure: for filtered Aurora samples it is not the production exposure.

Semantics carried over from Xuyang Ning's spec_v1 builder (bdt-comm @ 2c499b9, steps/step4_tables/build_tables.py and
steps/step3_spec/spec_v1.py), re-implemented here: the key (sample, file_id, run, subrun, event, cand); the partner =
match_obj[0] of the level-2 side-0 row of the candidate, looked up among level-2 side-1 rows; truth_nu_idx < 0 or no
partner = cosmic / none; dist_sce_cm against T_dlvtx_call.truth_all_reco_* of the first call (raw fallback flagged);
label_unreadable when uproot cannot read a T_match branch; truth_pf_unreadable likewise for T_truth_pf.
Python 3.9 compatible.
"""
import argparse, hashlib, json, math, os, platform, subprocess, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import firewall  # noqa: E402

WC = 'recTreeWireCell'
KEY_CLASH = {'run', 'subrun', 'event', 'eventNo', 'runNo', 'subRunNo'}
HDR = ['rec.hdr.run', 'rec.hdr.subrun', 'rec.hdr.evt', 'rec.hdr.first_in_subrun', 'rec.hdr.pot', 'rec.hdr.ismc']
MATCH = ['level', 'side', 'obj', 'nu_index', 'truth_nu_idx', 'nmatch', 'mutual', 'match_obj', 'match_iou_n',
         'match_iou_q', 'match_obj..idx', 'match_iou_n..idx', 'match_iou_q..idx']
PF = ['nu_row', 'trackid', 'parent_trackid', 'mother_trackid', 'pdg', 'process', 'KE', 'start_px', 'start_py',
      'start_pz', 'end_x', 'end_y', 'end_z']
NU = ['nu_idx', 'pdg', 'ccnc', 'mode', 'int_type', 'E', 'edep', 'vtx_x', 'vtx_y', 'vtx_z']
DLV = ['pass', 'truth_all_nu_idx', 'truth_all_reco_x', 'truth_all_reco_y', 'truth_all_reco_z',
       'truth_all_reco_x..idx', 'truth_all_reco_x..length', 'truth_all_nu_idx..idx']
ACTIVE = dict(x=(-201.3, 201.3), y=(-203.73, 203.73), z=(0.0, 501.0))   # GDML volTPCActive (Matteo's cuts.ACTIVE)
PHOTON_KE_MIN_GEV = 0.020
WALL_MARGIN_CM = 3.0


def _inside(x, y, z, margin):
    return (ACTIVE['x'][0] + margin <= x <= ACTIVE['x'][1] - margin and ACTIVE['y'][0] + margin <= y <= ACTIVE['y'][1] - margin
            and ACTIVE['z'][0] + margin <= z <= ACTIVE['z'][1] - margin)


def _angle_deg(p1, p2):
    n1 = math.sqrt(sum(c * c for c in p1)); n2 = math.sqrt(sum(c * c for c in p2))
    if n1 == 0 or n2 == 0:
        return float('nan')
    c = max(-1.0, min(1.0, sum(a * b for a, b in zip(p1, p2)) / (n1 * n2)))
    return math.degrees(math.acos(c))


def _scalar_branches(keys, prefix):
    """Per-candidate scalar branches of a flattened tree: no '..', and no companion '<name>..idx' (that marks a list)."""
    lists = {k[:-len('..idx')] for k in keys if k.startswith(prefix) and k.endswith('..idx')}
    return sorted(k for k in keys if k.startswith(prefix) and '..' not in k and k != prefix and k not in lists)


def truth_summary(q, pf):
    """Single-photon truth ingredients of the neutrino in T_truth_nu row q. pf: dict of this event's T_truth_pf arrays."""
    out = dict(n_prim_pi0=0, n_pi0_all=0, n_prim_gamma=0, n_gamma_from_prim_pi0=0, n_gamma_ke20=0,
               n_gamma_ke20_conv_in3cm=0, n_gamma_from_prim_pi0_ke20_conv_in3cm=0, pi0_gamma_min_open_deg=float('nan'),
               n_prim_e=0, n_prim_mu=0, max_prim_mu_ke_mev=0.0, max_gamma_ke_mev=0.0)
    if pf is None:
        return out
    row = pf['nu_row']; pdg = pf['pdg']; par = pf['parent_trackid']; tid = pf['trackid']
    sel = np.where(row == q)[0]
    prim_pi0 = {int(tid[j]) for j in sel if pdg[j] == 111 and par[j] == 0}
    out['n_prim_pi0'] = len(prim_pi0)
    out['n_pi0_all'] = int(sum(1 for j in sel if pdg[j] == 111))
    mom_by_parent = {}
    for j in sel:
        if pdg[j] == 22:
            ke = float(pf['KE'][j]); conv = _inside(float(pf['end_x'][j]), float(pf['end_y'][j]), float(pf['end_z'][j]), WALL_MARGIN_CM)
            from_pi0 = int(par[j]) in prim_pi0
            out['n_prim_gamma'] += int(par[j] == 0)
            out['n_gamma_from_prim_pi0'] += int(from_pi0)
            out['max_gamma_ke_mev'] = max(out['max_gamma_ke_mev'], 1000.0 * ke)
            if ke > PHOTON_KE_MIN_GEV:
                out['n_gamma_ke20'] += 1
                out['n_gamma_ke20_conv_in3cm'] += int(conv)
                out['n_gamma_from_prim_pi0_ke20_conv_in3cm'] += int(from_pi0 and conv)
            if from_pi0:
                mom_by_parent.setdefault(int(par[j]), []).append((float(pf['start_px'][j]), float(pf['start_py'][j]), float(pf['start_pz'][j])))
        elif abs(int(pdg[j])) == 11 and par[j] == 0:
            out['n_prim_e'] += 1
        elif abs(int(pdg[j])) == 13 and par[j] == 0:
            out['n_prim_mu'] += 1
            out['max_prim_mu_ke_mev'] = max(out['max_prim_mu_ke_mev'], 1000.0 * float(pf['KE'][j]))
    angles = [_angle_deg(v[0], v[1]) for v in mom_by_parent.values() if len(v) == 2]
    if angles:
        out['pi0_gamma_min_open_deg'] = float(min(angles))
    return out


def extract(path, sample, file_id, holdout):
    import uproot
    st = os.stat(path)
    info = dict(sample=sample, file_id=file_id, path=path, size_bytes=st.st_size,
                mtime_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime)), holdout=int(holdout), events=0,
                wc_events=0, candidates=0, truth_rows=0, wct_version='', label_unreadable=0, truth_pf_unreadable=0,
                partner_missing=0, hdr_pot_sum_not_exposure=float('nan'), ismc=-1, error='')
    cands, truth = [], []
    f = uproot.open(path)
    try:
        h = f['recTree'].arrays(HDR, library='np')
        first = h['rec.hdr.first_in_subrun'] == 1
        info.update(events=int(len(h['rec.hdr.run'])), hdr_pot_sum_not_exposure=float(h['rec.hdr.pot'][first].sum()),
                    ismc=int(h['rec.hdr.ismc'][0]) if len(h['rec.hdr.ismc']) else -1)
    except Exception as e:
        info['error'] = 'HDR_FAIL ' + str(e).splitlines()[0][:120]
    t = f[WC]
    keys = set(t.keys())
    tag = [k for k in _scalar_branches(keys, 'wc.T_tagger.') if k.split('.', 2)[2] not in KEY_CLASH]
    tag_names = {k.split('.', 2)[2] for k in tag}
    # T_kine repeats run/subrun/event/nu_index (never let them overwrite the key) and cluster_id, has_vertex,
    # matched_flash_gid (kept under <name>__kine so the T_tagger value is not overwritten)
    kine = [k for k in _scalar_branches(keys, 'wc.T_kine.') if k.split('.', 2)[2] not in KEY_CLASH | {'nu_index'}]
    kine_col = {k: (k.split('.', 2)[2] + '__kine' if k.split('.', 2)[2] in tag_names else k.split('.', 2)[2]) for k in kine}
    has_truth = 'wc.T_truth_nu.nu_idx' in keys
    base = ['wc.run', 'wc.subrun', 'wc.evt', 'wc.valid', 'wc.Trun.wct_version', 'wc.T_kine.nu_index'] + tag + kine
    base += ['wc.T_dlvtx_call.' + n for n in DLV if 'wc.T_dlvtx_call.' + n in keys]
    if has_truth:
        base += ['wc.T_truth_nu.' + n for n in NU if 'wc.T_truth_nu.' + n in keys]
    a = t.arrays(base, library='np')
    pf = None
    if has_truth:
        try:
            pf = t.arrays(['wc.T_truth_pf.' + n for n in PF], library='np')
        except Exception:
            info['truth_pf_unreadable'] = 1
    m = None
    if any(k.startswith('wc.T_match.') for k in keys):
        try:
            m = t.arrays(['wc.T_match.' + n for n in MATCH], library='np')
        except Exception:
            info['label_unreadable'] = 1
    wv = a['wc.Trun.wct_version']
    info['wct_version'] = bytes(np.asarray(wv[0], dtype=np.uint8)).decode() if len(wv) and len(wv[0]) and np.asarray(wv[0]).dtype.kind in 'iu' else (str(wv[0][0]) if len(wv) and len(wv[0]) else '')
    info['wc_events'] = int((a['wc.valid'] == 1).sum())
    for i in range(len(a['wc.run'])):
        if a['wc.valid'][i] != 1:
            continue
        key = dict(sample=sample, file_id=file_id, run=int(a['wc.run'][i]), subrun=int(a['wc.subrun'][i]), event=int(a['wc.evt'][i]))
        sce = {}
        if 'wc.T_dlvtx_call.truth_all_reco_x..idx' in a and len(a['wc.T_dlvtx_call.pass'][i]):
            i0 = int(a['wc.T_dlvtx_call.truth_all_reco_x..idx'][i][0]); n0 = int(a['wc.T_dlvtx_call.truth_all_reco_x..length'][i][0])
            ids = a['wc.T_dlvtx_call.truth_all_nu_idx'][i][i0:i0 + n0] if len(a['wc.T_dlvtx_call.truth_all_nu_idx'][i]) >= i0 + n0 else range(n0)
            for k, ix in enumerate(ids):
                sce[int(ix)] = tuple(float(a['wc.T_dlvtx_call.truth_all_reco_' + c][i][i0 + k]) for c in 'xyz')
        tn = {n: a['wc.T_truth_nu.' + n][i] for n in NU if 'wc.T_truth_nu.' + n in a} if has_truth else {}
        pfi = None if pf is None else {n: pf['wc.T_truth_pf.' + n][i] for n in PF}
        by_idx = {int(ix): q for q, ix in enumerate(tn.get('nu_idx', []))}
        summaries = {}
        for q, ix in enumerate(tn.get('nu_idx', [])):
            s = truth_summary(q, pfi)
            summaries[int(ix)] = s
            r = dict(key, nu_idx=int(ix), pdg=int(tn['pdg'][q]), ccnc=int(tn['ccnc'][q]),
                     mode=int(tn['mode'][q]) if 'mode' in tn else -1, int_type=int(tn['int_type'][q]) if 'int_type' in tn else -1,
                     E=float(tn['E'][q]), edep_mev=1000.0 * float(tn['edep'][q]), vx=float(tn['vtx_x'][q]), vy=float(tn['vtx_y'][q]),
                     vz=float(tn['vtx_z'][q]), truth_pf_unreadable=info['truth_pf_unreadable'], label_unreadable=info['label_unreadable'])
            r['sce_x'], r['sce_y'], r['sce_z'] = sce.get(int(ix), (float('nan'),) * 3)
            r.update(s)
            truth.append(r)
        reco_row, truth_row_of_obj = {}, {}
        if m is not None:
            lv, sd = m['wc.T_match.level'][i], m['wc.T_match.side'][i]
            for k in range(len(lv)):
                if lv[k] != 2:
                    continue
                if sd[k] == 0:
                    reco_row[int(m['wc.T_match.nu_index'][i][k])] = k
                else:
                    truth_row_of_obj[int(m['wc.T_match.obj'][i][k])] = k
        kine_row = {int(v): c for c, v in enumerate(a['wc.T_kine.nu_index'][i])}
        for c, ni in enumerate(a['wc.T_tagger.nu_index'][i]):
            ni = int(ni)
            r = dict(key, cand=ni)
            for b in tag:
                v = a[b][i]
                r[b[len('wc.T_tagger.'):]] = float(v[c]) if c < len(v) else float('nan')
            kc = kine_row.get(ni)
            for b in kine:
                v = a[b][i]
                r[kine_col[b]] = float(v[kc]) if (kc is not None and kc < len(v)) else float('nan')
            rx, ry, rz = r.get('nu_x', float('nan')), r.get('nu_y', float('nan')), r.get('nu_z', float('nan'))
            r['is_placeholder'] = int(r.get('kine_reco_Enu', float('nan')) == 0.0 and r.get('neutrino_type', 0.0) == 0.0
                                      and rx == 0.0 and ry == 0.0 and rz == 0.0)
            r.update(partner_kind='none', nmatch=0, mutual=-1, iou_n=float('nan'), iou_q=float('nan'), m_nu_idx=-1,
                     dist_raw_cm=float('nan'), dist_sce_cm=float('nan'), sce_fallback=0, label_unreadable=info['label_unreadable'])
            if m is not None and reco_row.get(ni) is not None:
                k = reco_row[ni]
                r['nmatch'] = int(m['wc.T_match.nmatch'][i][k]); r['mutual'] = int(m['wc.T_match.mutual'][i][k])
                if r['nmatch'] > 0:
                    po = int(m['wc.T_match.match_obj'][i][int(m['wc.T_match.match_obj..idx'][i][k])])
                    r['iou_n'] = float(m['wc.T_match.match_iou_n'][i][int(m['wc.T_match.match_iou_n..idx'][i][k])])
                    r['iou_q'] = float(m['wc.T_match.match_iou_q'][i][int(m['wc.T_match.match_iou_q..idx'][i][k])])
                    tr = truth_row_of_obj.get(po)
                    if tr is None:
                        r['partner_kind'] = 'missing'; info['partner_missing'] += 1
                    else:
                        tni = int(m['wc.T_match.truth_nu_idx'][i][tr])
                        if tni >= 0 and tni in by_idx:
                            q = by_idx[tni]
                            vx, vy, vz = float(tn['vtx_x'][q]), float(tn['vtx_y'][q]), float(tn['vtx_z'][q])
                            r.update(partner_kind='neutrino', m_nu_idx=tni, m_pdg=int(tn['pdg'][q]), m_ccnc=int(tn['ccnc'][q]),
                                     m_mode=int(tn['mode'][q]) if 'mode' in tn else -1, m_E=float(tn['E'][q]),
                                     m_edep_mev=1000.0 * float(tn['edep'][q]), m_vx=vx, m_vy=vy, m_vz=vz)
                            r['dist_raw_cm'] = math.sqrt((vx - rx) ** 2 + (vy - ry) ** 2 + (vz - rz) ** 2)
                            if tni in sce:
                                sx, sy, sz = sce[tni]; r['dist_sce_cm'] = math.sqrt((sx - rx) ** 2 + (sy - ry) ** 2 + (sz - rz) ** 2)
                            else:
                                r['dist_sce_cm'] = r['dist_raw_cm']; r['sce_fallback'] = 1
                            r.update({'m_' + k2: v2 for k2, v2 in summaries[tni].items()})
                        else:
                            r['partner_kind'] = 'cosmic'
            cands.append(r)
    info['candidates'] = len(cands)
    info['truth_rows'] = len(truth)
    return info, cands, truth


def _worker(job):
    path, sample, fid, hold = job
    try:
        return extract(path, sample, fid, hold)
    except Exception as e:
        return dict(sample=sample, file_id=fid, path=path, error='EXC ' + str(e).splitlines()[0][:160]), [], []


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _git_state():
    try:
        d = os.path.dirname(HERE)
        head = subprocess.check_output(['git', '-C', d, 'rev-parse', 'HEAD'], text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', d, 'status', '--porcelain', '--', '.'], text=True).strip())
        return dict(commit=head, dirty=dirty)
    except Exception:
        return dict(commit='unknown', dirty=None)


def main():
    import pandas as pd
    import uproot
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('sample'); ap.add_argument('out_dir')
    ap.add_argument('--list', required=True, help='one merged-CAF path per line')
    ap.add_argument('--slice', default=None, help='start:stop lines of --list')
    ap.add_argument('--nproc', type=int, default=1)
    ap.add_argument('--allowed-input-root', action='append', required=True)
    ap.add_argument('--allowed-output-root', action='append', required=True)
    ap.add_argument('--holdout-file-ids', default=None, help='file ids (basenames) that are never trained on; flagged, kept')
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    firewall.check_sample_id(a.sample)
    out_dir = firewall.check_output_path(a.out_dir, a.allowed_output_root)
    lines = [l.strip() for l in open(a.list) if l.strip() and not l.startswith('#')]
    if a.slice:
        s0, s1 = a.slice.split(':'); lines = lines[int(s0 or 0):(int(s1) if s1 else None)]
    firewall.check_training_inputs(lines, a.allowed_input_root)
    hold = set(l.strip() for l in open(a.holdout_file_ids)) if a.holdout_file_ids else set()
    jobs = [(p, a.sample, os.path.basename(p), os.path.basename(p) in hold) for p in lines]
    t0 = time.time()
    if a.nproc > 1:
        import multiprocessing as mp
        with mp.Pool(a.nproc) as pool:
            res = pool.map(_worker, jobs, chunksize=2)
    else:
        res = [_worker(j) for j in jobs]
    os.makedirs(out_dir, exist_ok=True)
    sfx = ('_' + a.tag) if a.tag else ''
    F = pd.DataFrame([r[0] for r in res]); C = pd.DataFrame([x for r in res for x in r[1]]); T = pd.DataFrame([x for r in res for x in r[2]])
    for name, df in (('files', F), ('cands', C), ('truth', T)):
        df.to_parquet(os.path.join(out_dir, '%s_%s%s.parquet' % (name, a.sample, sfx)))
    summ = dict(sample=a.sample, list=os.path.abspath(a.list), list_sha256=_sha256(a.list), slice=a.slice, files=len(lines),
                errors=int((F.get('error', pd.Series(dtype=str)).fillna('') != '').sum()),
                label_unreadable_files=int(F.get('label_unreadable', pd.Series(dtype=float)).fillna(0).sum()),
                truth_pf_unreadable_files=int(F.get('truth_pf_unreadable', pd.Series(dtype=float)).fillna(0).sum()),
                holdout_files=int(F.get('holdout', pd.Series(dtype=float)).fillna(0).sum()),
                events=int(F.get('events', pd.Series(dtype=float)).fillna(0).sum()), candidates=len(C), truth_rows=len(T),
                wct_versions=sorted(set(F.get('wct_version', pd.Series(dtype=str)).dropna())), code=_git_state(),
                python=platform.python_version(), uproot=uproot.__version__, pandas=pd.__version__, wall_s=round(time.time() - t0, 1))
    with open(os.path.join(out_dir, 'build_%s%s.json' % (a.sample, sfx)), 'w') as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(summ))


if __name__ == '__main__':
    main()
