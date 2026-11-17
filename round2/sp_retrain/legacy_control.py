"""Legacy MicroBooNE single-photon XMLs as controls for the development models (AURORA DEVELOPMENT, NOT OFFICIAL).

Bundle: the EAF transfer legacy_sp_bdt_bundle_20261117 (tarball sha256 below), byte-identical copies of
/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/single_photon_*_bdt_final.xml. Never the similarly
named *_bdt_test.xml. Never added to git.

Scoring is the validated sp_retrain.tmva_grad evaluator (TMVA semantics: right when x >= cut, inverted for cType 0;
v = EvaluateMVA = tanh(raw), -999 for a NaN input) followed ONCE by the production transform
score = log10((1 + v) / (1 - v)). For the LEGACY ncpi0 control only, kine_pio_flag is set to 0 before scoring, as
MicroBooNE production does (bdt_convert.cxx:4166-4167). The new SBND ncpi0 model keeps the real flag (Policy B).
"""
import hashlib
import os

import numpy as np

from sp_retrain import devtrain, tmva_grad

TARBALL = 'legacy_sp_bdt_bundle_20261117.tar.gz'
TARBALL_SHA256 = '90239e2a1b9357526e962d0f64cf569368d5f4d8a77e41e1412fb4e71c808cd8'
BUNDLE_SUBDIR = 'legacy_sp_bdt_bundle_20261117'
XML = {  # model: (filename, sha256, n inputs, n trees, max depth in split levels)
    'single_photon_numu': ('single_photon_numu_bdt_final.xml', '5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961', 73, 300, 5),
    'single_photon_other': ('single_photon_other_bdt_final.xml', '8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16', 146, 215, 5),
    'single_photon_ncpi0': ('single_photon_ncpi0_bdt_final.xml', '983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3', 45, 400, 6),
    'single_photon_nue': ('single_photon_nue_bdt_final.xml', '8580ba04b4a9e3c7aefbb4d5da5006cff2a131804a7b594843461a7cd6f3758a', 56, 300, 5),
}
CONTROL_MODELS = ('single_photon_numu', 'single_photon_ncpi0',
                  'single_photon_other', 'single_photon_nue')   # 2026-11-17: other / nue added as DIAGNOSTIC controls (WCL1116 domain study)
LEGACY_CUT = {'single_photon_numu': 0.4, 'single_photon_other': 0.2, 'single_photon_ncpi0': -0.05, 'single_photon_nue': -1.0}
EAF_AUDIT_COMMIT = '0148e879ae44c0c61f0fb7874079734a4cead3fa'
EAF_BASELINE_COMMIT = 'daf95442515b601eecda41c6c586931a5ae38c54'


class BundleError(RuntimeError):
    pass


def _sha(path):
    return devtrain.sha256_file(path)


def xml_path(bundle_root, model):
    name = XML[model][0]
    if '_test' in name or not name.endswith('_bdt_final.xml'):
        raise BundleError('refusing %s: only *_bdt_final.xml are legacy controls' % name)
    return os.path.join(bundle_root, BUNDLE_SUBDIR, name)


def verify_bundle(bundle_root):
    """Tarball sha, SHA256SUMS (four lines, all matching), and each XML against the expected sha. Returns a record."""
    tb = os.path.join(bundle_root, TARBALL)
    got = _sha(tb)
    if got != TARBALL_SHA256:
        raise BundleError('tarball sha256 %s != %s' % (got, TARBALL_SHA256))
    d = os.path.join(bundle_root, BUNDLE_SUBDIR)
    sums = {}
    for line in open(os.path.join(d, 'SHA256SUMS')):
        if line.strip():
            h, f = line.split()
            sums[f.lstrip('*')] = h
    want = {v[0]: v[1] for v in XML.values()}
    if sums != want:
        raise BundleError('SHA256SUMS does not list exactly the four expected files and hashes')
    rec = dict(bundle_root=os.path.abspath(bundle_root), tarball=TARBALL, tarball_sha256=got, xml={})
    for model, (name, h, *_rest) in XML.items():
        p = xml_path(bundle_root, model)
        got = _sha(p)
        if got != h:
            raise BundleError('%s sha256 %s != %s' % (name, got, h))
        rec['xml'][model] = dict(file=name, sha256=got)
    return rec


def max_depth(forest):
    """Split levels on the longest root-to-leaf path (a stump has depth 1), as in the EAF audit."""
    best = 0
    for r in forest.roots:
        stack = [(int(r), 0)]
        while stack:
            k, d = stack.pop()
            if forest.leaf[k]:
                best = max(best, d)
            else:
                stack.append((int(forest.left[k]), d + 1)); stack.append((int(forest.right[k]), d + 1))
    return best


def load_control(bundle_root, model, names):
    """GradForest of the legacy XML, with the structure checks (inputs, order, trees, depth)."""
    if model not in CONTROL_MODELS:
        raise BundleError('%s is not a control in this study' % model)
    p = xml_path(bundle_root, model)
    name, h, nvar, ntrees, depth = XML[model]
    if _sha(p) != h:
        raise BundleError('%s sha256 mismatch' % name)
    f = tmva_grad.GradForest(p, expected_names=names)       # raises if names or order differ
    got = (len(f.names), f.ntrees, max_depth(f))
    if got != (nvar, ntrees, depth):
        raise BundleError('%s structure %s != expected %s' % (name, got, (nvar, ntrees, depth)))
    return f


def legacy_matrix(X, names, model):
    """Input matrix for the LEGACY control: ncpi0 gets kine_pio_flag = 0 (MicroBooNE production); numu unchanged."""
    if model == 'single_photon_ncpi0':
        return devtrain.forced_flag_matrix(X, names, 0.0)
    return np.array(X, copy=True)


def legacy_score(forest, X):
    """(v, score): v = TMVA EvaluateMVA, score = log10((1+v)/(1-v)) applied exactly once."""
    v = forest.evaluate_mva(X)
    return v, tmva_grad.log10_odds(v)


def raw_left_if_le(forest, X):
    """Raw sum with the EAF Python-scorer routing (left if x <= cut), only to count equality-routing differences."""
    X = np.ascontiguousarray(X, dtype=np.float32)
    rows = np.arange(len(X)); total = np.zeros(len(X))
    for r in forest.roots:
        cur = np.full(len(X), r, np.int32); live = ~forest.leaf[cur]
        while live.any():
            c = cur[live]
            go_right = X[rows[live], forest.ivar[c]] > forest.cut[c]
            go_right = np.where(forest.ctype[c], go_right, ~go_right)
            cur[live] = np.where(go_right, forest.right[c], forest.left[c]); live = ~forest.leaf[cur]
        total += forest.res[cur].astype(np.float64)
    return total


def operating_point(y, s, cut):
    """Counts and rates for 'pass = s > cut'."""
    y = np.asarray(y); p = np.asarray(s) > cut
    tp = int((p & (y == 1)).sum()); fn = int((~p & (y == 1)).sum()); fp = int((p & (y == 0)).sum()); tn = int((~p & (y == 0)).sum())
    return dict(cut=float(cut), tp=tp, fn=fn, fp=fp, tn=tn, signal_efficiency=tp / max(tp + fn, 1),
                background_acceptance=fp / max(fp + tn, 1), background_rejection=tn / max(fp + tn, 1))


def threshold_for_rate(s, rate):
    """Threshold t with fraction(s > t) as close as possible to `rate` (midpoint between ranked scores)."""
    s = np.sort(np.asarray(s, np.float64))[::-1]
    k = int(round(rate * len(s)))
    if k <= 0:
        return float(s[0]) + 1.0
    if k >= len(s):
        return float(s[-1]) - 1.0
    return 0.5 * (s[k - 1] + s[k])


def flips(pass_a, pass_b):
    a = np.asarray(pass_a, bool); b = np.asarray(pass_b, bool)
    return dict(both_pass=int((a & b).sum()), legacy_pass_dev_fail=int((a & ~b).sum()),
                legacy_fail_dev_pass=int((~a & b).sum()), both_fail=int((~a & ~b).sum()))


def sha_of_git_blob(repo, commit, path):
    import subprocess
    out = subprocess.run(['git', '-C', repo, 'show', '%s:%s' % (commit, path)], capture_output=True, check=True).stdout
    return hashlib.sha256(out).hexdigest()
