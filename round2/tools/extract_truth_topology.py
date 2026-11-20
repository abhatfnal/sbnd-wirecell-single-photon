#!/usr/bin/env python3
"""Per-neutrino TRUTH TOPOLOGY of the WCL1116 training-side MC (read-only; reads only recTree truth).

  python extract_truth_topology.py SAMPLE OUT.parquet --list LIST [--nproc N]

For every rec.mc.nu of every event, using the ESTABLISHED NC-Delta analysis definition
(src/sbnd_single_photon/truth_signal.py, analysis branches; proton_category()):
  n_p35        post-FSI GENIE primaries (rec.mc.nu.prim) with pdg 2212 and KE = (genE - m_p) > 35 MeV
  topology     0 / 1 / 2 (= >= 2) from n_p35
plus descriptive fields: pdg, E, vertex, isnc, genie_mode, resnum, hitnuc (struck nucleon). For an NC resonance the
Delta charge equals the struck-nucleon charge (NC does not change charge): hitnuc 2212 -> Delta+, 2112 -> Delta0.
Rows are matched to the SP tables' T_match partner (m_pdg, m_E, m_v*) in sp_retrain.devstudy.attach_topology.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

PROTON_MASS_GEV = 0.938272
PROTON_KE_MEV = 35.0
BR = ['rec.hdr.run', 'rec.hdr.subrun', 'rec.hdr.evt', 'rec.mc.nu.pdg', 'rec.mc.nu.E', 'rec.mc.nu.isnc', 'rec.mc.nu.genie_mode',
      'rec.mc.nu.resnum', 'rec.mc.nu.hitnuc', 'rec.mc.nu.position.x', 'rec.mc.nu.position.y', 'rec.mc.nu.position.z',
      'rec.mc.nu.prim.pdg', 'rec.mc.nu.prim.genE', 'rec.mc.nu.prim..idx', 'rec.mc.nu.prim..length']
# flat CAF: rec.mc.nu.prim.* is ONE flat array per event; neutrino k owns [prim..idx[k], prim..idx[k] + prim..length[k])


def one(job):
    path, sample = job
    import uproot
    fid = os.path.basename(path)
    try:
        t = uproot.open(path)['recTree']
        a = t.arrays(BR, library='ak')
    except Exception as e:
        return dict(sample=sample, file_id=fid, error=str(e).splitlines()[0][:160]), []
    rows = []
    for i in range(len(a['rec.hdr.run'])):
        pdg = a['rec.mc.nu.pdg'][i]
        P = np.asarray(a['rec.mc.nu.prim.pdg'][i]); PE = np.asarray(a['rec.mc.nu.prim.genE'][i], dtype=np.float64)
        i0 = np.asarray(a['rec.mc.nu.prim..idx'][i]); nn = np.asarray(a['rec.mc.nu.prim..length'][i])
        if len(i0) != len(pdg) or int(nn.sum()) != len(P):
            return dict(sample=sample, file_id=fid, error='prim index mismatch in event %d' % i), []
        for k in range(len(pdg)):
            pp = P[i0[k]:i0[k] + nn[k]]; pe = PE[i0[k]:i0[k] + nn[k]]
            ke = (pe - PROTON_MASS_GEV) * 1000.0
            isp = pp == 2212
            n35 = int((isp & (ke > PROTON_KE_MEV)).sum())
            rows.append(dict(sample=sample, file_id=fid, run=int(a['rec.hdr.run'][i]), subrun=int(a['rec.hdr.subrun'][i]),
                             event=int(a['rec.hdr.evt'][i]), mc_nu=k, pdg=int(pdg[k]), E=float(a['rec.mc.nu.E'][i][k]),
                             vx=float(a['rec.mc.nu.position.x'][i][k]), vy=float(a['rec.mc.nu.position.y'][i][k]),
                             vz=float(a['rec.mc.nu.position.z'][i][k]), isnc=int(a['rec.mc.nu.isnc'][i][k]),
                             genie_mode=int(a['rec.mc.nu.genie_mode'][i][k]), resnum=int(a['rec.mc.nu.resnum'][i][k]),
                             hitnuc=int(a['rec.mc.nu.hitnuc'][i][k]), n_p35=n35, n_p_all=int(isp.sum()), n_prim=int(nn[k]),
                             max_p_ke_mev=float(ke[isp].max()) if isp.any() else float('nan'), topology=int(min(n35, 2))))
    return dict(sample=sample, file_id=fid, error=''), rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('sample'); ap.add_argument('out'); ap.add_argument('--list', required=True); ap.add_argument('--nproc', type=int, default=1)
    a = ap.parse_args()
    paths = [l.strip() for l in open(a.list) if l.strip()]
    jobs = [(p, a.sample) for p in paths]
    if a.nproc > 1:
        import multiprocessing as mp
        with mp.Pool(a.nproc) as pool:
            res = pool.map(one, jobs, chunksize=4)
    else:
        res = [one(j) for j in jobs]
    T = pd.DataFrame([r for _, rs in res for r in rs])
    E = [i for i, _ in res if i['error']]
    T.to_parquet(a.out, index=False)
    import json, hashlib
    json.dump(dict(sample=a.sample, list=os.path.abspath(a.list), list_sha256=hashlib.sha256(open(a.list, 'rb').read()).hexdigest(),
                   files=len(paths), errors=len(E), first_errors=E[:5], neutrinos=int(len(T)),
                   definition='n_p35 = rec.mc.nu.prim pdg 2212 with (genE - 0.938272 GeV) > 35 MeV; topology = min(n_p35, 2)'),
              open(a.out.replace('.parquet', '.json'), 'w'), indent=1)
    print(a.sample, len(paths), 'files', len(E), 'errors', len(T), 'neutrinos')


if __name__ == '__main__':
    sys.exit(main())
