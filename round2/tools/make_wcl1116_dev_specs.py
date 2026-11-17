#!/usr/bin/env python3
"""Write the WCL1116 development specs (one per model per vertex mode) and the campaign input manifest.

  python make_wcl1116_dev_specs.py --census-dir DIR [--check]

Every spec is DERIVED from the frozen Round-1-domain development spec of the same model (numu, ncpi0) or from the
SP other spec v0.2.3, and differs from it ONLY in: campaign, spec_version, model_name, the reconstruction block
(production, vertex mode, Wire-Cell tree, toolkit, DL bundle), the sample lists (WCL1116 Aurora training lists from
tools/make_refresh_list.py) and labels (UPSTREAM_NUMU = SHIPPED_CONTROL; development holdout). The two vertex modes of
one model are identical except the reconstruction block and the model name (checked by tests). Hyperparameters,
features, split, labels, preselection and weights are copied unchanged.
"""
import argparse
import copy
import hashlib
import json
import os
import sys

import yaml

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROUND2)
CAMPAIGN = 'development_wcl1116_v1'
MODES = {'dv2_split_move': 'recTreeWireCell', 'dv2_snap': 'recTreeWireCell_dv2snap'}
SAMPLES = ('wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb')
PROV = os.path.join(ROUND2, 'manifests', 'wcl1116_aurora_v0', 'production_provenance.json')
BEAMOFF = os.path.join(ROUND2, 'manifests', 'wcl1116_dev_v1', 'beamoff_train_membership.json')
OUT_MAN = os.path.join(ROUND2, 'manifests', 'wcl1116_dev_v1', 'inputs.json')
EVAL_EXCLUDED = ['wcl1116-fg-cv', 'wcl1116-fg-nuecc', 'wcl1116-fg-beamoff (even-run evaluation half and the full sample)',
                 'wcl1116-fg-run3bnb', 'wcl1116-fg-opendata', 'official NC Delta (ncdr, SAM EX_ncdeltarad)',
                 'fg1-* evaluation samples', 'selected data', "Xin hold-out lists"]


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def rel(path):
    return os.path.relpath(path, REPO)


def inputs_manifest(census_dir):
    prov = json.load(open(PROV))
    out = dict(campaign=CAMPAIGN, label='WCL1116_DEVELOPMENT_DO_NOT_DEPLOY', date='2026-11-17',
               role='Aurora TRAINING / DEVELOPMENT inputs only (catalogue side "training"). No WCLocal2026Nov16-FermiGrid, fg1 or other official evaluation product is an input.',
               production_tag='WCLocal2026Nov16-Aurora (Haiwang Yu; ai-helper issue 48)',
               reconstruction=dict(wct_version_stamp='0.38.0', toolkit_commit=prov['toolkit']['commit'],
                                   wire_cell_data_commit=prov['wire_cell_data']['commit'], larwirecell='ad5d9421 (step 1 of aurora-r1, reused)',
                                   sbndcode=prov['sbndcode'], dl_bundle=prov['dl_vertex']['bundle'], dl_bundle_sha256=prov['dl_vertex']['bundle_sha256'],
                                   modes={m: dict(wc_tree=t, schema_md5=('af9c87c88815199dccf5204ac71dbe44' if t == 'recTreeWireCell' else 'd4396a3490ea5aec4b02f0c34fa9db33'))
                                          for m, t in MODES.items()},
                                   upstream_bdt_weights='shipped MicroBooNE-trained (36 files, = aurora-r2); numu_score / nu_e L1 are SHIPPED_CONTROL'),
               provenance_manifest=rel(PROV), provenance_manifest_sha256=sha(PROV),
               pot_caveat='rec.hdr.pot is not the exposure of the filtered NC Delta sample; the fit is unweighted.',
               samples=[], beam_off_training_half=None)
    for sid in SAMPLES:
        c = json.load(open(os.path.join(census_dir, 'census_%s.json' % sid)))
        if not c.get('complete') or 'list' not in c:
            raise SystemExit('%s: census incomplete or no list' % sid)
        s = c['selection']
        out['samples'].append(dict(
            id=sid, list=c['list']['path'], list_sha256=c['list']['sha256'], files=c['list']['files'],
            selection=s['rule'], units_listed=c['listed'], units_OK=c['OK'], units_PARTIAL=c['PARTIAL'], units_FAIL=c['FAIL'],
            caf_events=s['caf_events'], wc_events_split=s['wc_events_split'], wc_events_snap=s['wc_events_snap'],
            excluded_units=s['excluded_units'], excluded_caf_events=s['excluded_caf_events'],
            excluded=[dict(unit=e['unit'], status=e['status'], n_caf_events=e['n_caf_events'], n_wc_events_split=e['n_wc_events_split'])
                      for e in s['excluded']],
            file_manifest=rel(os.path.join(ROUND2, 'manifests', 'wcl1116_dev_v1', 'manifest_%s.tsv.gz' % sid)),
            file_manifest_content_sha256=c['manifest']['content_sha256'], total_bytes=c['manifest']['total_bytes'],
            pairs=c['pairs'], pairs_sha256=c['pairs_sha256'], census_utc=c['census_utc']))
    if os.path.exists(BEAMOFF):
        b = json.load(open(BEAMOFF))
        out['beam_off_training_half'] = {k: b[k] for k in ('source_list_sha256', 'pairs', 'holdout_files_removed', 'kept', 'all_runs_odd',
                                                         'overlap_with_even_run_evaluation_half', 'accessible_from_aurora', 'status',
                                                         'membership_tsv_content_sha256', 'firewall_exception')}
    return out


def derive(base, model, mode, man):
    sp = copy.deepcopy(base)
    tree = MODES[mode]
    sp['spec_version'] = 'dev-wcl1116-v1-' + mode
    sp['campaign'] = CAMPAIGN
    sp['date'] = '2026-11-17'
    sp['derived_from'] = dict(spec=base.get('_path'), sha256=base.get('_sha256'))
    sp.pop('_path', None); sp.pop('_sha256', None)
    sp['classifier']['model_name'] = 'single_photon_%s_sbnd_wcl1116_%s_DEV_DO_NOT_DEPLOY' % (model, mode)
    r = man['reconstruction']
    sp['reconstruction'] = dict(production='WCLocal2026Nov16-Aurora', vertex_mode=mode, wc_tree=tree,
                                schema_md5=r['modes'][mode]['schema_md5'], toolkit_commit=r['toolkit_commit'],
                                wct_version_stamp=r['wct_version_stamp'], dl_bundle=r['dl_bundle'], dl_bundle_sha256=r['dl_bundle_sha256'],
                                note='the ONLY intended difference between the two vertex-mode specs of this model')
    up = 'SHIPPED_CONTROL' if model in ('numu', 'other') else 'NOT_A_DIRECT_INPUT'
    sp['inputs']['upstream_numu'] = up
    if model == 'ncpi0':
        sp['inputs']['upstream_scores'] = '15 nu_e level-1 scores as stored in WCL1116 (shipped models on the refreshed reconstruction; fixed in Xuyang\'s workflow)'
    sp['split']['holdout_kind'] = 'DEVELOPMENT HOLDOUT (the upstream DL vertex was trained on Aurora events): not an independent end-to-end test'
    dev = [dict(id=s['id'], list=s['list'], list_sha256=s['list_sha256'], files=s['files']) for s in man['samples']]
    sp['samples']['development'] = dev
    sp['samples']['input_manifest'] = rel(OUT_MAN)
    sp['samples']['excluded_official_evaluation'] = EVAL_EXCLUDED
    sp['round2_domain_differences'] = [
        'reconstruction: WCLocal2026Nov16-Aurora, WCT 0.38.0 c935e30d, DV2-MAX aurora_space; tree %s (%s)' % (tree, mode),
        'upstream nu_mu / nu_e scores: SHIPPED models on the refreshed reconstruction (not the Round-2 upstream models)',
        'CURRENT SBND DEVELOPMENT DOMAIN, not automatically the final Round-2 training domain (a cosmic-tagger-boundary production may follow)']
    return sp


def other_spec(mode, man):
    base = yaml.safe_load(open(os.path.join(ROUND2, 'specs', 'single_photon_other_training_spec_v0.2.yaml')))
    ncpi0 = yaml.safe_load(open(os.path.join(ROUND2, 'specs', 'single_photon_ncpi0_training_spec_dev_round1_domain_v1.yaml')))
    sp = dict(spec_id='single_photon_other_training_spec', campaign=CAMPAIGN, date='2026-11-17',
              author='Avinay Bhat (prepared with Claude Code)', deployable=False,
              derived_from=dict(spec='round2/specs/single_photon_other_training_spec_v0.2.yaml',
                                sha256=sha(os.path.join(ROUND2, 'specs', 'single_photon_other_training_spec_v0.2.yaml'))),
              classifier=dict(name='single_photon_other', thesis_xml_fingerprint=base['classifier']['thesis_model_vs_xml']['verdict']),
              inputs=dict(feature_list=base['inputs']['feature_list'], feature_list_sha256=base['inputs']['feature_list_sha256'],
                          n_inputs=146, order='XML <Variables> order', dtype='float32', preprocessing='none',
                          non_finite_policy=ncpi0['inputs']['non_finite_policy']),
              label=dict(definition=dict(implementation='sp_retrain.labels.development_classes (single_photon_other)',
                                         positive='T_match level-2 partner neutrino fits the inclusive single-photon signal',
                                         negative='partner NCBkg or outFVBkg (dirt included), cosmic-matched / unmatched MC candidates, every preselected EXT (beam-off training half) row',
                                         excluded='every other preselected row, and rows with a non-finite input')),
              preselection=ncpi0['preselection'],
              split=dict(scheme=ncpi0['split']['scheme'], unit=ncpi0['split']['unit'],
                         ext_rule='beam-off: run % 4 == 1 -> development holdout (every file has art subrun 1)'),
              weights=ncpi0['weights'])
    sp['xgboost'] = dict(ncpi0['xgboost'], max_depth=5, n_estimators=215)
    sp['samples'] = dict(development=[dict(id=s['id'], list=s['list'], list_sha256=s['list_sha256'], files=s['files']) for s in man['samples']]
                         + [dict(id='wcl1116-fg-beamoff-train', role='ext_beam_off', list=None, list_sha256=None, files=None,
                                 membership='round2/manifests/wcl1116_dev_v1/beamoff_train_membership.tsv.gz')],
                         input_manifest=rel(OUT_MAN), excluded_official_evaluation=EVAL_EXCLUDED,
                         approved_exceptions=[dict(man['beam_off_training_half']['firewall_exception'],
                                                   path_prefix='/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/beam-off/',
                                                   membership_list_sha256=man['beam_off_training_half']['source_list_sha256'])])
    acc = man['beam_off_training_half']['accessible_from_aurora']
    sp['status'] = 'READY_FOR_DEVELOPMENT_TRAINING' if acc else 'BLOCKED_DATA_STAGING'
    sp['status_reason'] = ('SP-OTHER DEVELOPMENT BLOCKED ONLY ON DATA ACCESS/STAGING: the refreshed odd-run beam-off half '
                           'exists only on FermiGrid dCache, not readable from Aurora. Evaluation beam-off is never a substitute.') if not acc else ''
    sp['inputs']['upstream_numu'] = 'SHIPPED_CONTROL'
    sp = derive(dict(sp, spec_version='', _path='round2/specs/single_photon_other_training_spec_v0.2.yaml'), 'other', mode, man) | {
        'samples': sp['samples'], 'status': sp['status'], 'status_reason': sp['status_reason']}
    sp['derived_from'] = dict(spec='round2/specs/single_photon_other_training_spec_v0.2.yaml',
                              sha256=sha(os.path.join(ROUND2, 'specs', 'single_photon_other_training_spec_v0.2.yaml')))
    return sp


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--census-dir', required=True)
    a = ap.parse_args()
    man = inputs_manifest(a.census_dir)
    json.dump(man, open(OUT_MAN, 'w'), indent=1)
    written = []
    for model in ('numu', 'ncpi0'):
        bp = os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_round1_domain_v1.yaml' % model)
        base = yaml.safe_load(open(bp)); base['_path'] = rel(bp); base['_sha256'] = sha(bp)
        for mode in MODES:
            sp = derive(base, model, mode, man)
            p = os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (model, mode))
            open(p, 'w').write('# GENERATED by tools/make_wcl1116_dev_specs.py -- WCL1116 DEVELOPMENT spec, DO NOT DEPLOY.\n'
                               + yaml.safe_dump(sp, sort_keys=False, width=120))
            written.append(rel(p))
    for mode in MODES:
        sp = other_spec(mode, man)
        p = os.path.join(ROUND2, 'specs', 'single_photon_other_training_spec_dev_wcl1116_%s.yaml' % mode)
        open(p, 'w').write('# GENERATED by tools/make_wcl1116_dev_specs.py -- WCL1116 DEVELOPMENT spec, DO NOT DEPLOY.\n'
                           + yaml.safe_dump(sp, sort_keys=False, width=120))
        written.append(rel(p))
    print(json.dumps(dict(inputs=rel(OUT_MAN), specs=written), indent=1))


if __name__ == '__main__':
    main()
