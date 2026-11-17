#!/usr/bin/env python3
"""Post-training provenance and legacy-control registration for the development campaign (no training).

  python record_dev_provenance.py --content-commit SHA --bundle-root DIR --results-dir DIR

1. For each manifests/dev_round1domain_v1/single_photon_<m>_dev_manifest.json, ADD a 'post_training_provenance' block.
   The original execution record (code.git.head = the HEAD at run time, its dirty paths, the file sha256s) is left
   unchanged. The block states that training ran from HEAD <execution head> with uncommitted training code, and
   proves, file by file, that those sha256s equal the files committed in --content-commit.
2. Write manifests/dev_round1domain_v1/legacy_controls.json: the verified legacy bundle (tarball and XML sha256, EAF
   commits) and the compact legacy-vs-development results of tools/legacy_control_compare.py.
"""
import argparse
import json
import os
import sys

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROUND2)
sys.path.insert(0, ROUND2)
from sp_retrain import devtrain, legacy_control as lc  # noqa: E402

MDIR = os.path.join(ROUND2, 'manifests', 'dev_round1domain_v1')


def post_training_block(man, commit):
    files = {}
    for f, h in man['code']['sha256'].items():
        c = lc.sha_of_git_blob(REPO, commit, 'round2/' + f)
        files[f] = dict(execution_sha256=h, content_commit_sha256=c, match=c == h)
    spec_c = lc.sha_of_git_blob(REPO, commit, 'round2/' + man['spec']['path'])
    fl_c = lc.sha_of_git_blob(REPO, commit, man['feature_list']['path'])
    ok = all(v['match'] for v in files.values()) and spec_c == man['spec']['sha256'] and fl_c == man['feature_list']['sha256']
    return dict(
        training_execution_repo_head=man['code']['git']['head'],
        training_execution_worktree_had_uncommitted_training_code=bool(man['code']['git']['dirty_paths']),
        training_code_content_commit=commit,
        training_code_content_hash_match=ok,
        files=files,
        spec=dict(path=man['spec']['path'], execution_sha256=man['spec']['sha256'], content_commit_sha256=spec_c),
        feature_list=dict(path=man['feature_list']['path'], execution_sha256=man['feature_list']['sha256'], content_commit_sha256=fl_c),
        note=('Training ran before the commit existed: the execution record above is kept as written. Every training code '
              'file, the spec and the feature list used at run time are byte-identical to the files committed in %s.' % commit))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--content-commit', required=True); ap.add_argument('--bundle-root', required=True); ap.add_argument('--results-dir', required=True)
    a = ap.parse_args()
    for m in ('numu', 'ncpi0'):
        p = os.path.join(MDIR, 'single_photon_%s_dev_manifest.json' % m)
        man = json.load(open(p))
        man['post_training_provenance'] = post_training_block(man, a.content_commit)
        json.dump(man, open(p, 'w'), indent=1, default=str)
        print(m, 'content hash match:', man['post_training_provenance']['training_code_content_hash_match'])
    bundle = lc.verify_bundle(a.bundle_root)
    res = {}
    for m in ('numu', 'ncpi0'):
        r = json.load(open(os.path.join(a.results_dir, m, 'legacy_vs_dev.json')))
        res[r['classifier']] = dict(
            label=r['label'], legacy_xml=r['legacy_xml'], legacy_xml_sha256=r['legacy_xml_sha256'], legacy_structure=r['legacy_structure'],
            legacy_convention=r['legacy_convention'], rows=r['rows'], alignment=r['alignment'], auc=r['auc'],
            legacy_at_historical_cut=r['legacy_at_historical_cut'],
            point_A_same_signal_efficiency={k: r['point_A_same_signal_efficiency'][k] for k in ('new_threshold_native_margin', 'new', 'background_acceptance_abs_diff', 'background_acceptance_ratio')},
            point_B_same_background_acceptance={k: r['point_B_same_background_acceptance'][k] for k in ('new_threshold_native_margin', 'new', 'signal_efficiency_abs_diff', 'signal_efficiency_ratio')},
            flips_A={k: r['flips_A'][k] for k in ('all', 'positive', 'negative')}, flips_B={k: r['flips_B'][k] for k in ('all', 'positive', 'negative')},
            correlation=r['correlation'], routing_check=r['routing_check'], score_check=r['score_check'],
            **({'legacy_with_real_flag_diagnostic': r['legacy_with_real_flag_diagnostic']} if 'legacy_with_real_flag_diagnostic' in r else {}),
            results_file=os.path.join(os.path.abspath(a.results_dir), m, 'legacy_vs_dev.json'),
            results_file_sha256=devtrain.sha256_file(os.path.join(a.results_dir, m, 'legacy_vs_dev.json')))
    reg = dict(
        campaign=devtrain.CAMPAIGN, label='AURORA DEVELOPMENT SAMPLE -- LEGACY MICROBOONE CONTROL (not official SBND performance)',
        bundle=bundle, eaf_thesis_xml_compatibility_audit_commit=lc.EAF_AUDIT_COMMIT,
        eaf_corrected_round1_baseline_commit=lc.EAF_BASELINE_COMMIT,
        bundle_origin='EAF staging /exp/uboone/data/users/abhat/single_photon_legacy_bdt_bundle_20261117, byte-identical copies of '
                      '/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/single_photon_*_bdt_final.xml (bundle manifest)',
        not_in_git='the tarball and the XMLs stay under $SP_WORK/legacy_bdt_controls',
        evaluator=dict(module='sp_retrain/tmva_grad.py', sha256=devtrain.sha256_file(os.path.join(ROUND2, 'sp_retrain/tmva_grad.py')),
                       semantics='TMVA: right when x >= cut (cType 1), v = tanh(raw), -999 for NaN; score = log10((1+v)/(1-v)) once',
                       validated='bit-identical to the toolkit stored nue_score (validation/nue_xml_vs_stored_*.json)'),
        controls_used=['single_photon_numu', 'single_photon_ncpi0'], not_used=['single_photon_other', 'single_photon_nue'],
        results=res)
    json.dump(reg, open(os.path.join(MDIR, 'legacy_controls.json'), 'w'), indent=1, default=float)
    print('wrote', os.path.join(MDIR, 'legacy_controls.json'))


if __name__ == '__main__':
    main()
