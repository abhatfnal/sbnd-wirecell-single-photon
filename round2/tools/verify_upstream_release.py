#!/usr/bin/env python3
"""Verify the sha256 of every model file of the two recommended upstream releases against their own manifests
(Ningclover/sbnd-wirecell-bdt): nue_round4_ruleA_v2 (level1.models[*], level2.{main,nogap}, wirecell.variants.{main,nogap})
and numu_round3af (level1.models[*], models.d6_f0, wirecell.files[*], wirecell/chain_weights.json). Also records the
sha256 of the patches, correction.json and every manifest, the repository commit, and the files on disk that no manifest
lists. Exit 1 on any mismatch or missing file.

  python tools/verify_upstream_release.py REPO_DIR OUT.json
"""
import hashlib, json, os, subprocess, sys


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    repo, out = sys.argv[1], sys.argv[2]
    rel = os.path.join(repo, 'releases')
    rows, listed = [], set()

    def check(release, role, rel_path, expect):
        p = os.path.join(rel, release, rel_path)
        got = sha(p) if os.path.exists(p) else None
        rows.append(dict(release=release, role=role, file=rel_path, expected=expect, actual=got, ok=(got == expect)))
        listed.add(os.path.normpath(p))

    n = json.load(open(os.path.join(rel, 'nue_round4_ruleA_v2', 'manifest.json')))
    for m, d in n['level1']['models'].items():
        check('nue_round4_ruleA_v2', 'level1 ' + m, d['file'], d['sha256'])
    for v, d in n['level2'].items():
        check('nue_round4_ruleA_v2', 'level2 ' + v, d['file'], d['sha256'])
    for v, d in n['wirecell']['variants'].items():
        for f, s in d['sha256'].items():
            check('nue_round4_ruleA_v2', 'wirecell %s' % v, os.path.join(d['weights_dir'], f), s)
    u = json.load(open(os.path.join(rel, 'numu_round3af', 'manifest.json')))
    for m, d in u['level1']['models'].items():
        check('numu_round3af', 'level1 ' + m, d['file'], d['sha256'])
    for m, d in u['models'].items():
        check('numu_round3af', 'final ' + m, d['file'], d['sha256'])
    for m, d in u['wirecell']['files'].items():
        check('numu_round3af', 'wirecell ' + m, d['file'], d['sha256'])
    cw = json.load(open(os.path.join(rel, 'numu_round3af', 'wirecell', 'chain_weights.json')))
    for m, d in cw['files'].items():
        check('numu_round3af', 'chain_weights ' + m, os.path.join('wirecell', 'uboone', 'weights', d['xml']), d['sha256'])
    corr = json.load(open(os.path.join(rel, 'numu_round3af', 'correction.json')))
    aux = {}
    for p in ['numu_round3af/correction.json', 'numu_round3af/manifest.json', 'numu_round3af/wirecell/chain_weights.json',
              'numu_round3af/wirecell/patches/wct-0.38.0-numu_sim_dqdx_scale.patch', 'numu_round3af/wirecell/patches/step2-numu_sim_dqdx_scale.patch',
              'nue_round4_ruleA_v2/manifest.json', 'nue_round4_ruleA_v2/wirecell/main/chain_weights.json', 'README.md']:
        aux[p] = sha(os.path.join(rel, p))
    unlisted = []
    for r in ('nue_round4_ruleA_v2', 'numu_round3af'):
        for dp, _, fs in os.walk(os.path.join(rel, r)):
            for f in fs:
                p = os.path.normpath(os.path.join(dp, f))
                if p not in listed and (f.endswith('.json') and ('/l1/' in p or '/l2/' in p) or f.endswith('.xml')):
                    unlisted.append(os.path.relpath(p, rel))
    commit = subprocess.run(['git', '-C', repo, 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
    rep = dict(repository='https://github.com/Ningclover/sbnd-wirecell-bdt', commit=commit, files_checked=len(rows),
               mismatches=[r for r in rows if not r['ok']], unlisted_model_files=sorted(unlisted), correction=corr,
               simulation_correction_manifest=u['simulation_correction'], operating_points=dict(numu=u['operating_point'], nue=dict(cut=n['operating_cut'], default=n['default'])),
               auxiliary_sha256=aux, files=rows)
    rep['verdict'] = 'ALL_MATCH' if not rep['mismatches'] else 'MISMATCH'
    json.dump(rep, open(out, 'w'), indent=1)
    print(json.dumps(dict(commit=commit, files_checked=len(rows), mismatches=len(rep['mismatches']), unlisted=rep['unlisted_model_files'], verdict=rep['verdict'])))
    sys.exit(0 if not rep['mismatches'] else 1)


if __name__ == '__main__':
    main()
