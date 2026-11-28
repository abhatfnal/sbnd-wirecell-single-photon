#!/usr/bin/env python3
"""Upstream-to-downstream dependency matrix: every input of the four downstream single-photon (SP) BDTs against Xuyang
Ning's upstream Wire-Cell CC taggers (nu_mu numu_round3af, nu_e nue_round4_ruleA_v2), from the code of record:
  SP inputs        config/features/single_photon_*_inputs_v0.json (XML order)
  upstream inputs  config/upstream/numu_l2_inputs_74.txt, nue_l2_inputs_258.txt, l1_models_xning_0f13988d.py
  release          releases/numu_round3af/manifest.json (retrained models, simulation correction), nue_round4_ruleA_v2
  chain            wire-cell-toolkit c935e30d UbooneNumuBDTScorer / UbooneNueBDTScorer + the numu_sim_dqdx_scale patch
Distinguishes Xuyang's UPSTREAM CC BDTs (nu_mu / nu_e taggers) from our DOWNSTREAM SP BDTs. Writes CSV + JSON.

  python tools/upstream_dependency_matrix.py RELEASE_DIR OUT_DIR
"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc  # noqa: E402

SP = ['numu', 'other', 'ncpi0', 'nue']
NUMU_RETRAINED = {'numu_1_score': 'numu_tagger1 (numu_1)', 'numu_2_score': 'numu_tagger2 (numu_2)', 'cosmict_10_score': 'cos_tagger_10 (cosmict_10)',
                  'numu_score': 'numu_scalars_scores_0923 (final, 74 inputs)'}
NUMU_SIM_SCALED = ['numu_cc_1_medium_dQ_dx', 'cosmict_2_dQ_dx_end', 'cosmict_2_dQ_dx_front', 'cosmict_3_dQ_dx_end', 'cosmict_3_dQ_dx_front',
                   'cosmict_7_dQ_dx_end', 'cosmict_7_dQ_dx_front']


def main():
    rel, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    mnumu = json.load(open(os.path.join(rel, 'numu_round3af', 'manifest.json')))
    mnue = json.load(open(os.path.join(rel, 'nue_round4_ruleA_v2', 'manifest.json')))
    assert mnumu['inputs'] == uc.NUMU_FINAL_INPUTS, 'numu final input list differs from the release manifest'
    assert mnumu['simulation_correction']['inputs'] == NUMU_SIM_SCALED
    nue_l2 = mnue['level2']['main']['inputs']
    assert [x if not x.startswith('l1_') else x[3:] + '_score' for x in nue_l2] == uc.NUE_FINAL_INPUTS, 'nue final input list differs'
    numu_l1_obj = {n: m for m in uc.L1_NUMU for n in uc.L1_SPEC[m]['lists']}
    nue_l1_obj = {n: m for m in uc.L1_NUE for n in uc.L1_SPEC[m]['lists'] + uc.L1_SPEC[m]['scalars']}
    rows = []
    for sp in SP:
        cfg = json.load(open(os.path.join(os.path.dirname(HERE), 'config', 'features', 'single_photon_%s_inputs_v0.json' % sp)))
        for i, f in enumerate(cfg['inputs']):
            n = f['name'] if isinstance(f, dict) else f
            kind = f.get('kind') if isinstance(f, dict) else ''
            r = dict(sp_model='single_photon_' + sp, index=i, input=n, kind=kind, upstream_role='reco only (no upstream tagger dependence)',
                     numu_round3af='UNCHANGED', nue_round4_ruleA_v2='UNCHANGED', overlay_domain='-', note='')
            if n in NUMU_RETRAINED:
                r.update(upstream_role='nu_mu tagger OUTPUT: ' + NUMU_RETRAINED[n], numu_round3af='REPLACED (retrained model; simulation dQ/dx x 1.071 + numu_cc_flag copy)',
                         overlay_domain='B, D')
                if n == 'numu_score':
                    r['note'] = 'indirect: depends on numu_1/numu_2/cosmict_10 scores and 71 raw tagger inputs (6 cosmict dQ/dx scaled on simulation inside the BDT copy)'
            elif n in uc.NUE_L1_SCORES:
                r.update(upstream_role='nu_e tagger LEVEL-1 OUTPUT: %s_BDT (min over objects)' % n[:-6], nue_round4_ruleA_v2='REPLACED (retrained, chain-transformed tanh(scale*margin+offset), empty constant)',
                         overlay_domain='C, D')
            elif n == 'nue_score':
                r.update(upstream_role='nu_e tagger FINAL OUTPUT', nue_round4_ruleA_v2='REPLACED')
            elif n == 'numu_3_score':
                r.update(upstream_role='nu_mu tagger level-1 output (numu_tagger3, NOT retrained)')
            if n in uc.NUMU_FINAL_INPUTS and n not in NUMU_RETRAINED:
                r['upstream_role'] = 'raw INPUT of the nu_mu final model (stored value)'
                if n in NUMU_SIM_SCALED:
                    r['numu_round3af'] = 'UNCHANGED as stored (x1.071 only in the copy handed to the nu_mu BDT, simulation only)'
                elif n == 'numu_cc_flag':
                    r['numu_round3af'] = 'UNCHANGED as stored (the nu_mu BDT copy may switch 1 -> 0 on simulation)'
            if n in numu_l1_obj:
                r['upstream_role'] = 'raw per-object INPUT of %s' % numu_l1_obj[n]
            if n in nue_l1_obj:
                r['upstream_role'] = 'raw per-object INPUT of %s' % nue_l1_obj[n]
            if n in uc.NUE_FINAL_INPUTS and n not in uc.NUE_L1_SCORES and r['upstream_role'].startswith('reco only'):
                r['upstream_role'] = 'raw INPUT of the nu_e final model (stored value, unchanged)'
            rows.append(r)
    with open(os.path.join(out, 'sp_upstream_dependency_matrix.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    summ = {}
    for sp in SP:
        R = [r for r in rows if r['sp_model'] == 'single_photon_' + sp]
        summ['single_photon_' + sp] = dict(
            inputs=len(R),
            replaced_by_numu_round3af=[r['input'] for r in R if r['numu_round3af'].startswith('REPLACED')],
            replaced_by_nue_round4_ruleA_v2=[r['input'] for r in R if r['nue_round4_ruleA_v2'].startswith('REPLACED')],
            raw_numu_final_inputs_stored_unchanged=[r['input'] for r in R if r['upstream_role'].startswith('raw INPUT of the nu_mu final')],
            raw_nue_final_inputs_stored_unchanged=[r['input'] for r in R if r['upstream_role'].startswith('raw INPUT of the nu_e final')],
            sim_scaled_in_bdt_copy_only=[r['input'] for r in R if 'x1.071 only in the copy' in r['numu_round3af']],
            unaffected=sum(1 for r in R if r['numu_round3af'] == 'UNCHANGED' and r['nue_round4_ruleA_v2'] == 'UNCHANGED' and r['upstream_role'].startswith('reco only')))
    upstream = dict(
        numu_final=dict(inputs=len(uc.NUMU_FINAL_INPUTS), retrained_inputs=['cosmict_10_score', 'numu_1_score', 'numu_2_score'],
                        sim_scaled_inputs_in_bdt_copy=NUMU_SIM_SCALED[1:], flag_copy='numu_cc_flag', nan_to_0=uc.NUMU_NAN_TO_0),
        numu_level1={m: dict(inputs=uc.L1_SPEC[m]['lists'], pool=uc.L1_SPEC[m]['pool'], empty=uc.L1_SPEC[m]['empty'],
                             retrained=m in ('numu_1', 'numu_2', 'cosmict_10')) for m in uc.L1_NUMU},
        numu_3='numu_tagger3 NOT retrained, not an input of the nu_mu final model nor of any SP model',
        nue_final=dict(inputs=len(uc.NUE_FINAL_INPUTS), level1_inputs=uc.NUE_L1_SCORES, reads_numu_outputs=False),
        nue_level1={m: dict(inputs=uc.L1_SPEC[m]['lists'] + uc.L1_SPEC[m]['scalars'], pool='min', empty=uc.L1_SPEC[m]['empty'],
                            pre_cut=uc.L1_SPEC[m]['pre_cut'] or None) for m in uc.L1_NUE},
        families_independent='the nu_e final model reads no nu_mu output and the nu_mu final model reads no nu_e output')
    json.dump(dict(sp=summ, upstream=upstream, rows=len(rows)), open(os.path.join(out, 'sp_upstream_dependency_matrix.json'), 'w'), indent=1)
    for k, v in summ.items():
        print(k, v['inputs'], 'numu-replaced', v['replaced_by_numu_round3af'], 'nue-replaced', len(v['replaced_by_nue_round4_ruleA_v2']),
              'raw numu-final inputs', len(v['raw_numu_final_inputs_stored_unchanged']), 'unaffected', v['unaffected'])


if __name__ == '__main__':
    main()
