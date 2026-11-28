#!/usr/bin/env python3
"""Regenerate the data files of the portable upstream-chain scoring bundle (round2/upstream_chain_bundle/wc_upstream_chain/data)
from their sources, so that every number in the bundle is traceable:

  numu_l2_inputs_74.txt, nue_l2_inputs_258.txt   verbatim copies of round2/config/upstream/ (Xuyang's spec, byte-identical)
  l1_models.json                                  round2/config/upstream/l1_models_xning_0f13988d.py as JSON (tuples -> lists)
  release_inventory.json                          the CANONICAL inventory of the pinned release (Ningclover/sbnd-wirecell-bdt @
                                                  0f13988d): every model file named by the two manifests (57 unique paths),
                                                  the 8 auxiliary files, the 20 chain XMLs the toolkit resolves, fingerprints
  shipped_inventory.json                          sha256 of the shipped wire-cell-data 99c6497f files the chain falls back to

  python tools/build_upstream_chain_bundle_data.py --releases CLONE/releases --shipped WCD/ [--eaf-hash-csv CSV]

--eaf-hash-csv (optional): EAF's tables/upstream_release/release_file_hashes.csv; the generator then proves both sites list the
same 57 (path, sha256) pairs and records the comparison in release_inventory.json.
"""
import argparse, hashlib, importlib.util, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROUND2 = os.path.dirname(HERE)
CFG = os.path.join(ROUND2, 'config', 'upstream')
DATA = os.path.join(ROUND2, 'upstream_chain_bundle', 'wc_upstream_chain', 'data')
RELEASE_REPO = 'https://github.com/Ningclover/sbnd-wirecell-bdt'
RELEASE_COMMIT = '0f13988db44423a227789e151b0a374e25771abd'
SHIPPED_DATA = 'wire-cell-data 99c6497f (WCLocal2026Nov16 worktree; /lus/flare/projects/neutrinoGPU/yuhw/wcd-0.38.0 on Aurora)'
NUE_L1 = ['br3_3', 'br3_5', 'br3_6', 'pio_2', 'stw_2', 'stw_3', 'stw_4', 'sig_1', 'sig_2', 'lol_1', 'lol_2', 'tro_1', 'tro_2', 'tro_4', 'tro_5']
CHAIN_FILES = dict(numu_1='numu_tagger1.weights.xml', numu_2='numu_tagger2.weights.xml', numu_3='numu_tagger3.weights.xml',
                   cosmict_10='cos_tagger_10.weights.xml', numu_final='numu_scalars_scores_0923.xml', nue_final='XGB_nue_seed2_0923.xml')
CHAIN_FILES.update({m: '%s_BDT.weights.xml' % m for m in NUE_L1})
FP_SETS = dict(numu_model_fingerprint=['numu_1', 'numu_2', 'numu_3', 'cosmict_10', 'numu_final'], nue_l1_fingerprints=NUE_L1,
               nue_chain_fingerprint=NUE_L1 + ['nue_final'])


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def lines_fp(lines):
    return hashlib.sha256(('\n'.join(sorted(lines)) + '\n').encode()).hexdigest()


def l1_json():
    spec = importlib.util.spec_from_file_location('l1', os.path.join(CFG, 'l1_models_xning_0f13988d.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    out = {}
    for m, d in mod.L1_MODELS.items():
        out[m] = dict(lists=list(d['lists']), scalars=list(d['scalars']), flag=d['flag'], pool=d['pool'], empty=float(d['empty']),
                      score=d['score'], flavour=d['flavour'], pre_cut=d['pre_cut'],
                      protect={k: [v[0], float(v[1])] for k, v in d.get('protect', {}).items()})
    return dict(source='round2/config/upstream/l1_models_xning_0f13988d.py (Xuyang Ning, sbnd-wirecell-bdt spec, byte-identical copy)',
                note=('pre_cut is the TRAINING-table pre-cut of the spec; in the toolkit 0.38.0 chain only pio_2 is gated '
                      '(pio_filled == 1 and pio_flag_pio == 0); numu_1 / numu_2 / cosmict_10 run on every candidate (no cosmict_flag_1 '
                      'gate) and the 15 nu_e models run without a br_filled gate. The bundle implements the CHAIN behaviour.'),
                chain_gated=dict(pio_2='pio_filled == 1 and pio_flag_pio == 0'),
                nue_l1_order=list(mod.NUE_L1), models=out)


def release_inventory(rel, eaf_csv=None):
    nue_dir, numu_dir = os.path.join(rel, 'nue_round4_ruleA_v2'), os.path.join(rel, 'numu_round3af')
    nm, um = json.load(open(os.path.join(nue_dir, 'manifest.json'))), json.load(open(os.path.join(numu_dir, 'manifest.json')))
    ent = {}

    def add(folder, rel_path, sha, role):
        p = 'releases/%s/%s' % (folder, rel_path)
        e = ent.setdefault(p, dict(path=p, sha256_manifest=sha, roles=[]))
        if e['sha256_manifest'] != sha:
            raise SystemExit('two manifest hashes for %s' % p)
        e['roles'].append(role)
    for m, v in nm['level1']['models'].items():
        add('nue_round4_ruleA_v2', v['file'], v['sha256'], 'nue level1 %s (xgboost json)' % m)
    for var, v in nm['level2'].items():
        add('nue_round4_ruleA_v2', v['file'], v['sha256'], 'nue level2 %s (xgboost json)' % var)
    for var, v in nm['wirecell']['variants'].items():
        for fn, sha in v['sha256'].items():
            add('nue_round4_ruleA_v2', v['weights_dir'] + '/' + fn, sha, 'nue chain %s' % var)
    for m, v in um['level1']['models'].items():
        add('numu_round3af', v['file'], v['sha256'], 'numu level1 %s (xgboost json)' % m)
    for m, v in um['models'].items():
        add('numu_round3af', v['file'], v['sha256'], 'numu level2 %s (xgboost json)' % m)
    for m, v in um['wirecell']['files'].items():
        add('numu_round3af', v['file'], v['sha256'], 'numu chain %s (manifest.json wirecell.files)' % m)
    cw = json.load(open(os.path.join(numu_dir, 'wirecell', 'chain_weights.json')))
    dup = 0
    for m, v in cw['files'].items():          # the second listing of the same four numu chain XMLs (Aurora counted these: 61 = 57 + 4)
        add('numu_round3af', 'wirecell/uboone/weights/' + v['xml'], v['sha256'], 'numu chain %s (wirecell/chain_weights.json)' % m); dup += 1
    files = sorted(ent.values(), key=lambda e: e['path'])
    for e in files:
        p = os.path.join(os.path.dirname(rel), e['path'])
        e['sha256_found'] = sha256(p)
        e['ok'] = e['sha256_found'] == e['sha256_manifest']
        e['bytes'] = os.path.getsize(p)
    aux_rel = ['README.md', 'numu_round3af/manifest.json', 'numu_round3af/correction.json', 'numu_round3af/wirecell/chain_weights.json',
               'numu_round3af/wirecell/patches/wct-0.38.0-numu_sim_dqdx_scale.patch', 'numu_round3af/wirecell/patches/step2-numu_sim_dqdx_scale.patch',
               'nue_round4_ruleA_v2/manifest.json', 'nue_round4_ruleA_v2/wirecell/main/chain_weights.json']
    aux = [dict(path='releases/' + a, sha256=sha256(os.path.join(rel, a)), bytes=os.path.getsize(os.path.join(rel, a))) for a in aux_rel]
    chain = {}
    for m, fn in CHAIN_FILES.items():
        if m in NUE_L1 or m == 'nue_final':
            p = 'releases/nue_round4_ruleA_v2/wirecell/main/uboone/weights/' + fn
        elif m == 'numu_3':
            p = None                            # not released: the chain falls back to the shipped file
        else:
            p = 'releases/numu_round3af/wirecell/uboone/weights/' + fn
        chain[m] = dict(file=fn, release_path=p, sha256=(ent[p]['sha256_found'] if p else None),
                        resolution=('release (first on WIRECELL_PATH)' if p else 'shipped fallback (wire-cell-data uboone/weights)'))
    uniq_content = len(set(e['sha256_found'] for e in files))
    inv = dict(
        schema='wc_upstream_chain.release_inventory/1', release_repository=RELEASE_REPO, release_commit=RELEASE_COMMIT,
        models=dict(nue='nue_round4_ruleA_v2 (variant main = wirecell/main; default per manifest)', numu='numu_round3af'),
        manifest_sha256={'releases/nue_round4_ruleA_v2/manifest.json': sha256(os.path.join(nue_dir, 'manifest.json')),
                         'releases/numu_round3af/manifest.json': sha256(os.path.join(numu_dir, 'manifest.json'))},
        simulation_correction=dict(um['simulation_correction'], correction_json=json.load(open(os.path.join(numu_dir, 'correction.json')))),
        canonical_rule=('CANONICAL MODEL-FILE INVENTORY = the unique repository paths named by the two manifests (nue: level1, level2, '
                        'wirecell.variants.*.sha256; numu: level1, models, wirecell.files) = %d files. numu_round3af/wirecell/'
                        'chain_weights.json lists the same 4 numu chain XMLs a second time; counting those listings separately gives '
                        'the Aurora audit total 61 = 57 + 4 (no extra file). The 15 nogap-variant level-1 XMLs are byte-identical to '
                        'the main ones (same sha256, different path): %d distinct contents.' % (len(files), uniq_content)),
        counts=dict(canonical_files=len(files), aurora_audit_checks=len(files) + dup, eaf_audit_files=len(files),
                    duplicate_listings_chain_weights_json=dup, distinct_contents=uniq_content, auxiliary_files=len(aux),
                    chain_xmls_resolved_from_release=sum(1 for v in chain.values() if v['release_path'])),
        canonical_files=files, auxiliary_files=aux, chain_set=chain,
        fingerprints=dict(
            rule=('sha256 of the sorted lines "<path> <sha256>" joined by "\\n" with a trailing "\\n" (paths repository-relative, '
                  'starting with releases/)'),
            canonical_inventory=lines_fp(['%s %s' % (e['path'], e['sha256_found']) for e in files]),
            auxiliary=lines_fp(['%s %s' % (a['path'], a['sha256']) for a in aux])))
    if eaf_csv:
        import csv
        rows = list(csv.DictReader(open(eaf_csv)))
        eaf = {r['path']: r['sha256_manifest'] for r in rows}
        ours = {e['path']: e['sha256_found'] for e in files}
        inv['eaf_cross_check'] = dict(file=os.path.basename(eaf_csv), eaf_rows=len(rows), same_path_set=set(eaf) == set(ours),
                                      same_hashes=all(eaf.get(p) == s for p, s in ours.items()),
                                      eaf_fingerprint=lines_fp(['%s %s' % kv for kv in eaf.items()]))
    return inv


def shipped_inventory(shipped):
    out = {}
    for m, fn in CHAIN_FILES.items():
        p = os.path.join(shipped, 'uboone', 'weights', fn)
        out[m] = dict(file=fn, sha256=sha256(p), bytes=os.path.getsize(p))
    return dict(schema='wc_upstream_chain.shipped_inventory/1', source=SHIPPED_DATA,
                note=('The weights a WCLocal2026Nov16 production ran (domain A). The 18 shipped level-1 XMLs are TMVA AdaBoost with '
                      'VarTransform D,P,U,G,D,N: the numpy evaluator refuses them (their stored CAF values are closed bit-exact with ROOT '
                      'TMVA on Aurora, validation/upstream_r4/l1_tmva_closure_*.json). The two shipped FINAL models are TMVA Grad and are '
                      'evaluated by the bundle (closure: stored_l1=True).'),
                files=out)


def chain_fingerprints(release_inv, shipped_inv):
    out = {}
    for route in ('release', 'shipped'):
        fps = {}
        for name, models in FP_SETS.items():
            lines = []
            for m in models:
                c = release_inv['chain_set'][m]
                sha = c['sha256'] if (route == 'release' and c['sha256']) else shipped_inv['files'][m]['sha256']
                lines.append('%s %s' % (CHAIN_FILES[m], sha))
            fps[name] = lines_fp(lines)
        out[route] = fps
    out['rule'] = ('sp_retrain.upstream_chain.fingerprint / wc_upstream_chain.chain_fingerprints: sha256 over the sorted lines '
                   '"<file name> <sha256>" of the files the chain resolves along WIRECELL_PATH; numu_model_fingerprint = numu_tagger1/2/3, '
                   'cos_tagger_10, numu_scalars_scores_0923 (numu_tagger3 is the shipped file in both routes); nue_l1_fingerprints = the '
                   '15 nu_e level-1 files; nue_chain_fingerprint = those + XGB_nue_seed2_0923.xml')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--releases', required=True); ap.add_argument('--shipped', required=True); ap.add_argument('--eaf-hash-csv')
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    for f in ('numu_l2_inputs_74.txt', 'nue_l2_inputs_258.txt'):
        shutil.copyfile(os.path.join(CFG, f), os.path.join(DATA, f))
    json.dump(l1_json(), open(os.path.join(DATA, 'l1_models.json'), 'w'), indent=1)
    rel = release_inventory(os.path.abspath(a.releases), a.eaf_hash_csv)
    shp = shipped_inventory(a.shipped)
    rel['chain_fingerprints'] = chain_fingerprints(rel, shp)
    json.dump(rel, open(os.path.join(DATA, 'release_inventory.json'), 'w'), indent=1)
    json.dump(shp, open(os.path.join(DATA, 'shipped_inventory.json'), 'w'), indent=1)
    bad = [e['path'] for e in rel['canonical_files'] if not e['ok']]
    print(json.dumps(dict(counts=rel['counts'], mismatches=bad, fingerprints=rel['fingerprints'], chain=rel['chain_fingerprints'],
                          eaf=rel.get('eaf_cross_check')), indent=1))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
