"""Canonical file inventory and fingerprints of the pinned upstream release and of the shipped fallback files.

Canonical model-file inventory (common to Aurora and EAF): the 57 unique repository paths named by the two release manifests
(data/release_inventory.json, `canonical_files`). Aurora's audit reported 61 checks = these 57 + the 4 numu chain XMLs listed
a second time in numu_round3af/wirecell/chain_weights.json; EAF's audit reported the 57 files. Same files, same hashes.
"""
import hashlib
import json
import os

from . import spec as S
from .chain import resolve, sha256, split_path

RELEASE_COMMIT = '0f13988db44423a227789e151b0a374e25771abd'
RELEASE_REPOSITORY = 'https://github.com/Ningclover/sbnd-wirecell-bdt'
FINGERPRINT_SETS = dict(numu_model_fingerprint=['numu_1', 'numu_2', 'numu_3', 'cosmict_10', 'numu_final'],
                        nue_l1_fingerprints=list(S.L1_NUE), nue_chain_fingerprint=list(S.L1_NUE) + ['nue_final'])


def _load(name):
    with open(os.path.join(S.DATA, name)) as f:
        return json.load(f)


def release_inventory():
    return _load('release_inventory.json')


def shipped_inventory():
    return _load('shipped_inventory.json')


def lines_fingerprint(lines):
    """sha256 of the sorted lines joined by '\\n' with a trailing '\\n'."""
    return hashlib.sha256(('\n'.join(sorted(lines)) + '\n').encode()).hexdigest()


def verify_release(releases_dir, head_commit=None):
    """Check a local copy of <clone>/releases against the canonical inventory: every canonical file and auxiliary file by
    sha256, the manifest invariants the scorer relies on, and the inventory fingerprint. Never raises on a failed check."""
    inv = release_inventory()
    root = os.path.dirname(os.path.abspath(releases_dir))
    checks = []

    def chk(name, ok, detail=''):
        checks.append(dict(check=name, ok=bool(ok), detail=str(detail)))
    if head_commit is not None:
        chk('clone HEAD == pinned release commit', head_commit == RELEASE_COMMIT, head_commit)
    got = {}
    for e in inv['canonical_files']:
        p = os.path.join(root, e['path'])
        got[e['path']] = sha256(p) if os.path.isfile(p) else ''
    bad = [p for p, e in zip(got, inv['canonical_files']) if got[e['path']] != e['sha256_manifest']]
    chk('all %d canonical model files match the pinned sha256' % len(got), not bad, '%d mismatches %s' % (len(bad), bad[:3]))
    fp = lines_fingerprint(['%s %s' % kv for kv in got.items()])
    chk('canonical inventory fingerprint', fp == inv['fingerprints']['canonical_inventory'], fp)
    abad = []
    for a in inv['auxiliary_files']:
        p = os.path.join(root, a['path'])
        if not os.path.isfile(p) or sha256(p) != a['sha256']:
            abad.append(a['path'])
    chk('all %d auxiliary files (manifests, correction.json, patches, README) match' % len(inv['auxiliary_files']), not abad, abad)
    try:
        nm = json.load(open(os.path.join(releases_dir, 'nue_round4_ruleA_v2', 'manifest.json')))
        um = json.load(open(os.path.join(releases_dir, 'numu_round3af', 'manifest.json')))
        cj = json.load(open(os.path.join(releases_dir, 'numu_round3af', 'correction.json')))
        chk('nu_e default variant is main', nm['default']['variant'] == 'main', nm['default'])
        chk('nu_e main declares the 258 final inputs in the bundle order', nm['level2']['main']['inputs'] is not None and
            len(nm['level2']['main']['inputs']) == len(S.NUE_FINAL_INPUTS))
        chk('nu_mu 74 final inputs equal the bundle order', list(um['inputs']) == S.NUMU_FINAL_INPUTS)
        sc = um['simulation_correction']
        chk('correction uniform k == %.3f on the seven dQ/dx inputs, flag update on' % S.SIM_DQDX_SCALE,
            cj.get('mode') == 'uniform' and cj.get('k') == S.SIM_DQDX_SCALE and list(sc['inputs']) == S.SIM_DQDX_INPUTS and sc['update_flag1'] is True,
            (cj, sc.get('inputs')))
        cw = json.load(open(os.path.join(releases_dir, 'numu_round3af', 'wirecell', 'chain_weights.json')))
        chk('numu chain empty constants == the bundle (toolkit) constants',
            all(abs(cw['files'][m]['empty_value'] - float(S.EMPTY[m])) < 1e-6 for m in S.L1_NUMU), {m: cw['files'][m]['empty_value'] for m in S.L1_NUMU})
        tr = nm['level1']['chain_transform']['models']
        chk('nu_e chain empty constants == the bundle (toolkit) constants',
            all(abs(tr[m]['empty_value'] - float(S.EMPTY[m])) < 1e-6 for m in S.L1_NUE))
    except Exception as e:                                                  # a broken clone is a failed check, not a crash
        chk('manifest invariants readable', False, repr(e))
    return dict(ok=all(c['ok'] for c in checks), release_commit=RELEASE_COMMIT, n_canonical_files=len(got),
                n_auxiliary_files=len(inv['auxiliary_files']), inventory_fingerprint=fp, checks=checks)


def chain_fingerprints(weights_path):
    """The upstream fingerprints of the final-domain contract for the files the chain resolves along `weights_path`
    (identical to sp_retrain.upstream_chain.fingerprint on Aurora). Returns {name: (fingerprint, lines)}."""
    dirs = split_path(weights_path)
    out = {}
    for name, models in FINGERPRINT_SETS.items():
        lines = ['%s %s' % (S.CHAIN_FILES[m], sha256(resolve(dirs, S.CHAIN_FILES[m]))) for m in models]
        out[name] = (lines_fingerprint(lines), sorted(lines))
    return out


def identify_route(weights_path):
    """'release' / 'shipped' / 'mixed' / 'unknown' for the numu and nu_e level-1 sets resolved along weights_path."""
    inv = release_inventory()['chain_fingerprints']
    fp = {k: v[0] for k, v in chain_fingerprints(weights_path).items()}
    out = {}
    for name in ('numu_model_fingerprint', 'nue_l1_fingerprints', 'nue_chain_fingerprint'):
        out[name] = 'release' if fp[name] == inv['release'][name] else 'shipped' if fp[name] == inv['shipped'][name] else 'unknown'
    return out, fp


def bundle_fingerprint():
    """sha256 over the sorted lines '<path relative to the package> <sha256>' of every .py / .json / .txt file of the installed
    wc_upstream_chain package: proves that a vendored copy is byte-identical to the released bundle."""
    root = os.path.dirname(os.path.abspath(__file__))
    lines = []
    for d, _, fs in os.walk(root):
        if '__pycache__' in d:
            continue
        for f in fs:
            if f.endswith(('.py', '.json', '.txt')):
                p = os.path.join(d, f)
                lines.append('%s %s' % (os.path.relpath(p, root), sha256(p)))
    return lines_fingerprint(lines), sorted(lines)
