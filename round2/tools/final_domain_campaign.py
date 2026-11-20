#!/usr/bin/env python3
"""Final-domain SP BDT rerun: provenance gate, frozen-spec generation and the ordered rerun plan
(docs/SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md). Nothing is inferred; the campaign REFUSES while any field is missing.

  python final_domain_campaign.py check CAMPAIGN.yaml
  python final_domain_campaign.py specs CAMPAIGN.yaml --out-dir specs/            (after check passes)
  python final_domain_campaign.py plan  CAMPAIGN.yaml --out-dir $SP_WORK/final_domain/plan   (after check passes)

check   every production / upstream / input field present, not a placeholder, well formed (40-hex commit, 64-hex
        hashes, a closed list of exact stamps, a vertex mode with its tree); every list exists with the stated sha256 and
        file count and carries no official-evaluation marker; the beam-off staging record exists with the stated sha256,
        is VERIFIED with --expect-reco campaign by the stated verifier, names the same toolkit commit and beam-off list,
        and carries one of the stated stamps; the beam-off firewall exception is explicitly re-approved.
specs   the four frozen WCL1116 development specs re-generated for this domain: only the reconstruction block, the sample
        lists, the campaign and the approved EXT exception change (features, order, hyperparameters, seed unchanged).
plan    the ordered rerun (1 provenance, 2 tables, 3 census, 4 frozen specs, 5 training, 6 nested-validation reports,
        7 export, 8 Python equivalence, 9 C++ equivalence, 10 compact summary) as a shell script of existing tools.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import sys

import yaml

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROUND2)
sys.path.insert(0, ROUND2)
from sp_retrain import devtrain, firewall, provenance  # noqa: E402

CAMPAIGN = devtrain.CAMPAIGN_FINAL_CANDIDATE
PLACEHOLDERS = {'', 'TBD', 'TODO', 'REQUIRED', 'NULL', 'NONE', 'FILL_ME', 'PLACEHOLDER', 'UNKNOWN'}
HEX40, HEX64 = re.compile(r'^[0-9a-f]{40}$'), re.compile(r'^[0-9a-f]{64}$')
MODES = {'dv2_split_move', 'dv2_snap'}
MODELS = ('numu', 'ncpi0', 'other', 'nue')
LISTS = ('ncdr_list', 'bnb_list', 'nuecc_list', 'beamoff_train_list')
SAMPLE_OF = {'ncdr_list': 'aurora-ncdr', 'bnb_list': 'aurora-bnb', 'nuecc_list': 'aurora-nuecc', 'beamoff_train_list': 'fg-beamoff-train'}


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def absent(v):
    return v is None or (isinstance(v, str) and v.strip().upper() in PLACEHOLDERS) or (isinstance(v, (list, dict)) and not v)


def check(spec):
    """List of problems (empty = runnable)."""
    bad = []
    need = lambda path, v: bad.append('%s: missing / placeholder' % path) if absent(v) else None
    if spec.get('campaign') != CAMPAIGN:
        bad.append('campaign must be %s' % CAMPAIGN)
    p, u, i = spec.get('production') or {}, spec.get('upstream') or {}, spec.get('inputs') or {}
    for k in ('tag', 'toolkit_commit', 'toolkit_version_stamps', 'toolkit_stamp_evidence', 'dl_bundle', 'dl_bundle_sha256', 'vertex_mode',
              'wc_trees', 'effective_boundary_profile', 'effective_boundary_sha256'):
        need('production.' + k, p.get(k))
    for k in ('numu_model_fingerprint', 'nue_l1_fingerprints'):
        need('upstream.' + k, u.get(k))
    if not absent(p.get('toolkit_commit')) and not HEX40.match(str(p['toolkit_commit'])):
        bad.append('production.toolkit_commit: not a full 40-hex commit')
    for k, d in (('production.dl_bundle_sha256', p), ('production.effective_boundary_sha256', p), ('upstream.numu_model_fingerprint', u),
                 ('upstream.nue_l1_fingerprints', u)):
        v = d.get(k.split('.')[1])
        if not absent(v) and not HEX64.match(str(v)):
            bad.append('%s: not 64-hex' % k)
    st = p.get('toolkit_version_stamps')
    if not absent(st):
        if not isinstance(st, list) or not all(isinstance(s, str) and s and s == s.strip() for s in st) or len(set(st)) != len(st):
            bad.append('production.toolkit_version_stamps: must be a closed list of distinct exact strings')
    if not absent(p.get('vertex_mode')) and p['vertex_mode'] not in MODES:
        bad.append('production.vertex_mode: must be one of %s' % sorted(MODES))
    tr = p.get('wc_trees')
    if not absent(tr):
        if not isinstance(tr, dict) or not set(tr.values()) <= MODES or p.get('vertex_mode') not in tr.values():
            bad.append('production.wc_trees: must map stored trees to vertex modes and include vertex_mode')
    for k in LISTS:
        e = i.get(k) or {}
        for f in ('path', 'sha256', 'files'):
            need('inputs.%s.%s' % (k, f), e.get(f))
        if absent(e.get('path')) or not os.path.exists(str(e.get('path'))):
            if not absent(e.get('path')):
                bad.append('inputs.%s.path: does not exist' % k)
            continue
        if not absent(e.get('sha256')) and sha(e['path']) != e['sha256']:
            bad.append('inputs.%s.sha256: does not match the file' % k)
        lines = [l.strip() for l in open(e['path']) if l.strip()]
        if not absent(e.get('files')) and len(lines) != int(e['files']):
            bad.append('inputs.%s.files: %d lines in the list' % (k, len(lines)))
        if k != 'beamoff_train_list':
            marked = [l for l in lines if firewall.official_marker(l) is not None]
            if marked:
                bad.append('inputs.%s: %d official-evaluation paths, first %s' % (k, len(marked), marked[0]))
    sr = i.get('beamoff_staging_record') or {}
    need('inputs.beamoff_staging_record.path', sr.get('path')); need('inputs.beamoff_staging_record.sha256', sr.get('sha256'))
    need('inputs.beamoff_verifier_sha256', i.get('beamoff_verifier_sha256'))
    ex = i.get('beamoff_exception') or {}
    for f in ('approved_by', 'date', 'staged_dir'):
        need('inputs.beamoff_exception.' + f, ex.get(f))
    if not absent(sr.get('path')) and os.path.exists(str(sr['path'])):
        if not absent(sr.get('sha256')) and sha(sr['path']) != sr['sha256']:
            bad.append('inputs.beamoff_staging_record.sha256: does not match the file')
        r = json.load(open(sr['path']))
        if r.get('status') != 'VERIFIED' or r.get('expect_reco') != 'campaign':
            bad.append('beam-off staging record: not VERIFIED with --expect-reco campaign')
        if r.get('list_sha256') != (i.get('beamoff_train_list') or {}).get('sha256'):
            bad.append('beam-off staging record: list_sha256 differs from inputs.beamoff_train_list.sha256')
        if r.get('toolkit_commit') != p.get('toolkit_commit'):
            bad.append('beam-off staging record: toolkit_commit differs from production.toolkit_commit')
        if r.get('verifier_sha256') != i.get('beamoff_verifier_sha256'):
            bad.append('beam-off staging record: verifier_sha256 differs from inputs.beamoff_verifier_sha256')
        if not absent(st) and r.get('wct_version_stamp') not in (st or []):
            bad.append('beam-off staging record: stamp %r is not in production.toolkit_version_stamps' % r.get('wct_version_stamp'))
    elif not absent(sr.get('path')):
        bad.append('inputs.beamoff_staging_record.path: does not exist')
    return bad


def require(spec):
    bad = check(spec)
    if bad:
        raise SystemExit('REFUSED: the campaign spec is incomplete (%d problems):\n  ' % len(bad) + '\n  '.join(bad))


def sample_id(k):
    return '%s-%s' % ('r2final', SAMPLE_OF[k])


def make_specs(spec):
    """{model: spec dict} for the campaign's vertex mode, derived from the frozen WCL1116 development specs."""
    require(spec)
    p, i = spec['production'], spec['inputs']
    mode = p['vertex_mode']; tree = [t for t, m in p['wc_trees'].items() if m == mode][0]
    stg = json.load(open(i['beamoff_staging_record']['path']))
    out = {}
    for m in MODELS:
        base = yaml.safe_load(open(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (m, mode))))
        s = copy.deepcopy(base)
        s.update(campaign=CAMPAIGN, spec_version='final-domain-candidate-v1-%s' % mode, status='READY_FOR_DEVELOPMENT_TRAINING', status_reason='',
                 deployable=False, derived_from=dict(spec='round2/specs/single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (m, mode),
                                                     sha256=sha(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (m, mode)))))
        s['classifier'] = dict(s['classifier'], model_name='single_photon_%s_sbnd_r2final_%s_DEV_DO_NOT_DEPLOY' % (m, mode))
        s['reconstruction'] = dict(production=p['tag'], vertex_mode=mode, wc_tree=tree, toolkit_commit=p['toolkit_commit'],
                                   toolkit_version_stamps=list(p['toolkit_version_stamps']), dl_bundle=p['dl_bundle'], dl_bundle_sha256=p['dl_bundle_sha256'],
                                   effective_boundary_profile=p['effective_boundary_profile'], effective_boundary_sha256=p['effective_boundary_sha256'],
                                   note='generated by tools/final_domain_campaign.py from the campaign spec')
        s['upstream_fingerprints'] = dict(spec['upstream'])
        dev = []
        for k in ('ncdr_list', 'bnb_list') + (('nuecc_list',) if m == 'nue' else ()):
            dev.append(dict(id=sample_id(k), list=i[k]['path'], list_sha256=i[k]['sha256'], files=int(i[k]['files'])))
        if m == 'other':
            ex = copy.deepcopy(base['samples']['approved_exceptions'][0])
            ex.update(sample=sample_id('beamoff_train_list'), approved_by=i['beamoff_exception']['approved_by'], date=str(i['beamoff_exception']['date']),
                      scope='%s only: the pre-designated odd-run beam-off TRAINING half reprocessed in %s, hold-out files removed' % (CAMPAIGN, p['tag']),
                      path_prefix=None, path_prefixes=[i['beamoff_exception']['staged_dir'].rstrip('/') + '/'])
            dev.append(dict(id=sample_id('beamoff_train_list'), role='ext_beam_off', list=i['beamoff_train_list']['path'],
                            list_sha256=i['beamoff_train_list']['sha256'], files=int(i['beamoff_train_list']['files']),
                            staging_record=i['beamoff_staging_record']['path'], wct_version_stamp=stg['wct_version_stamp'], toolkit_commit=p['toolkit_commit']))
            s['samples']['approved_exceptions'] = [ex]
        s['samples']['development'] = dev
        s['samples']['input_manifest'] = None
        s['round2_domain_differences'] = ['reconstruction: %s, toolkit %s, DL bundle %s, effective boundary %s; tree %s (%s)'
                                          % (p['tag'], p['toolkit_commit'][:8], p['dl_bundle_sha256'][:8], p['effective_boundary_profile'], tree, mode)]
        out[m] = s
    return out


STEPS = ('1 provenance verification', '2 table building', '3 sample census', '4 frozen feature-spec loading', '5 model training',
         '6 nested-validation reports', '7 export', '8 Python equivalence', '9 C++ equivalence', '10 compact summary')


def plan(spec, out_dir):
    require(spec)
    p, i = spec['production'], spec['inputs']
    mode = p['vertex_mode']; tree = [t for t, m in p['wc_trees'].items() if m == mode][0]
    W = '$SP_WORK/final_domain'; T = '%s/tables/%s' % (W, mode)
    L = []
    L.append('# 1 provenance verification\npython round2/tools/final_domain_campaign.py check CAMPAIGN_SPEC || exit 2')
    builds = ['python -m sp_retrain.build_tables %s %s --list %s --wc-tree %s --tag dev --nproc 160 --allowed-input-root <production root> '
              '--allowed-output-root /lus/flare/projects/neutrinoGPU/abhat/sbnd' % (sample_id(k), T, i[k]['path'], tree) for k in ('ncdr_list', 'bnb_list', 'nuecc_list')]
    builds.append('python -m sp_retrain.build_tables %s %s --list %s --wc-tree %s --tag dev --allowed-input-root %s --allowed-output-root /lus/flare/projects/neutrinoGPU/abhat/sbnd '
                  '--approved-exceptions-spec round2/specs/single_photon_other_training_spec_r2final_%s.yaml'
                  % (sample_id('beamoff_train_list'), T, i['beamoff_train_list']['path'], tree, i['beamoff_exception']['staged_dir'], mode))
    L.append('# 2 table building (PBS, -A neutrinoGPU::WireCell_aurora; compute nodes only)\n' + '\n'.join(builds))
    L.append('# 3 sample census\npython round2/tools/sp_other_census.py --spec-template round2/specs/single_photon_other_training_spec_r2final_%%s.yaml --tag dev '
             '--tables-template %s/tables/%%s --out-json round2/validation/r2final_sp_other_census.json\n'
             'python round2/tools/sp_nue_census.py --spec-template round2/specs/single_photon_nue_training_spec_r2final_%%s.yaml --tag dev '
             '--tables-template %s/tables/%%s --out-json round2/validation/r2final_sp_nue_census.json' % (W, W))
    L.append('# 4 frozen feature-spec loading\npython round2/tools/final_domain_campaign.py specs CAMPAIGN_SPEC --out-dir round2/specs')
    L.append('# 5 model training\n' + '\n'.join('python round2/tools/train_wcl1116_dev_model.py --tables %s --tag dev --spec round2/specs/single_photon_%s_training_spec_r2final_%s.yaml '
                                              '--out-dir %s/models/%s/%s --manifest-out round2/manifests/r2final/single_photon_%s_%s_manifest.json' % (T, m, mode, W, mode, m, m, mode) for m in MODELS))
    L.append('# 6 nested-validation reports (same pre-registered machinery as WCL1116)\n' +
             '\n'.join('python round2/tools/wcl1116_full_dev_study.py --model %s --mode %s --tables %s --tag dev --bundle-root $SP_WORK/legacy_bdt_controls '
                       '--out-dir %s/studies/%s/%s --summary-out round2/validation/r2final_full_dev_%s_%s.json' % (m, mode, T, W, mode, m, m, mode) for m in MODELS) +
             '\npython round2/tools/sp_operating_points.py --mode %s --tables %s --tag dev --bundle-root $SP_WORK/legacy_bdt_controls --studies-dir %s/studies/%s '
             '--topology-dir %s/truth_topology --out-json round2/validation/r2final_operating_points_%s.json --tables-out round2/validation/op_tables_r2final --work-out %s/op/%s'
             % (mode, T, W, mode, W, mode, W, mode))
    L.append('# 7 export + 8 Python equivalence\npython round2/tools/export_equivalence_check.py --tables %s --tag dev --dev-models %s/models/%s --models numu ncpi0 other nue '
             '--out-root %s/export/%s --summary-out round2/validation/r2final_export_equivalence_%s.json '
             '--spec-template "round2/specs/single_photon_%%s_training_spec_r2final_%s.yaml" --manifest-template "round2/manifests/r2final/single_photon_%%s_%s_manifest.json"'
             % (T, W, mode, W, mode, mode, mode, mode))
    L.append('# 9 C++ equivalence (prepare per model, then the SL7 WCT compute-node job, then compare)\n' +
             '\n'.join('python round2/tools/cpp_equivalence_check.py prepare --xml %s/export/%s/%s/<model>.xml --model-json %s/models/%s/%s/<model>.json --tables %s --tag dev '
                       '--spec round2/specs/single_photon_%s_training_spec_r2final_%s.yaml --work %s/cpp/%s_%s' % (W, mode, m, W, mode, m, T, m, mode, W, mode, m) for m in MODELS) +
             '\nqsub <cpp_equivalence.pbs with dirs.txt = the four %s/cpp/%s_* dirs>\n' % (W, mode) +
             '\n'.join('python round2/tools/cpp_equivalence_check.py compare --xml ... --model-json ... --work %s/cpp/%s_%s --summary-out round2/validation/r2final_cpp_equivalence_%s_%s.json'
                       % (W, mode, m, mode, m) for m in MODELS))
    L.append('# 10 compact summary\npython round2/tools/sp_feature_stability.py ... ; write docs/SP_BDT_FINAL_DOMAIN_RESULTS.md from the validation JSONs')
    os.makedirs(out_dir, exist_ok=True)
    body = '#!/bin/bash\n# Final-domain SP BDT rerun plan for %s (%s, %s). Generated; review before running.\nset -e\n\n' % (p['tag'], mode, tree) + '\n\n'.join(L) + '\n'
    open(os.path.join(out_dir, 'plan.sh'), 'w').write(body)
    json.dump(dict(campaign=CAMPAIGN, production=p['tag'], vertex_mode=mode, steps=list(STEPS)), open(os.path.join(out_dir, 'plan.json'), 'w'), indent=1)
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['check', 'specs', 'plan']); ap.add_argument('campaign_spec'); ap.add_argument('--out-dir', default=None)
    a = ap.parse_args()
    spec = yaml.safe_load(open(a.campaign_spec))
    if a.command == 'check':
        bad = check(spec)
        print('RUNNABLE' if not bad else 'REFUSED (%d problems)\n  ' % len(bad) + '\n  '.join(bad))
        sys.exit(0 if not bad else 2)
    if not a.out_dir:
        raise SystemExit('--out-dir required')
    if a.command == 'specs':
        for m, s in make_specs(spec).items():
            path = os.path.join(a.out_dir, 'single_photon_%s_training_spec_r2final_%s.yaml' % (m, spec['production']['vertex_mode']))
            open(path, 'w').write('# GENERATED by tools/final_domain_campaign.py -- FINAL-DOMAIN CANDIDATE development spec, DO NOT DEPLOY.\n'
                                  + yaml.safe_dump(s, sort_keys=False, width=120))
            print(path)
    else:
        plan(spec, a.out_dir); print(os.path.join(a.out_dir, 'plan.sh'))


if __name__ == '__main__':
    main()
