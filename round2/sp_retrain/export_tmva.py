"""Native XGBoost JSON -> TMVA "BDT::BDT" weight file (BoostType=Grad), for the single-photon BDTs.

Infrastructure only. The exported file is what Round-2 production would book; whether a model may be exported for
deployment is decided by its training spec, not here (development models are fixtures: their names carry
DO_NOT_DEPLOY and the export records the spec's campaign and deployable flag).

Layout. Element for element the inherited MicroBooNE single-photon XMLs (Creator "xgboost2TMVA") and the toolkit's
numu_scalars_scores_0923.xml / XGB_nue_seed2_0923.xml, which TMVA::Reader (MicroBooNE bdt_convert, SBND
UbooneNumuBDTScorer / UbooneNueBDTScorer with Float_t bindings) and the toolkit's TmvaGradForest already read in
production:
  <MethodSetup Method="BDT::BDT">
    <Variables NVar=n> <Variable VarIndex Type="D" Expression Label Title Unit Internal Min Max/> ... </Variables>
    <GeneralInfo> Creator, AnalysisType=Classification, + provenance Info entries (ignored by both readers) </GeneralInfo>
    <Options> NodePurityLimit, BoostType=Grad, NTrees </Options>
    <Weights NTrees=k AnalysisType="1">   (regression leaves: the leaf "res" is the response)
      <BinaryTree type="DecisionTree" boostWeight="1.0e+00" itree=i> nested <Node .../> </BinaryTree> ...
Type="D" is what every inherited file carries (with Float_t reader bindings); it can be switched with var_type.
No <Transformations> element (= none, as in the inherited files; both readers refuse NTransformations != 0).

Node semantics (proved per row and at exact thresholds by tools/export_equivalence_check.py and the tests):
  XGBoost: go to left_children ("yes") when x < split_condition (float32 compare), else right_children.
  TMVA:    DecisionTreeNode::GoesRight = (x >= Cut), inverted when cType == 0.
  => every split is written cType="1", Cut = split_condition, left child pos="l" = XGBoost yes-branch.
  Leaves: XGBoost leaf value (split_conditions of the leaf; the learning rate is already in it) -> res, nType="-99",
  IVar="-1", as in the inherited files (both readers stop at nType != 0).
  Floats are written with %.9g, so float32 -> text -> atof -> Float_t is exact.

Margin offset (base_score). Under objective binary:logitraw, XGBoost 3.4.1 adds base_score to the margin unchanged
(logitraw's ProbToMargin is the identity): margin = base_score + sum(leaves). Our SP specs use base_score = 0, so the
margin is the leaf sum and nothing else is exported. A nonzero offset (e.g. Xuyang's base_score = 0.5) is refused
unless fold_base_margin=True, which appends ONE extra tree whose root is a leaf with res = offset (TMVA and
TmvaGradForest return a root leaf's response directly); the file then records BaseMarginFoldedAsTree.

Missing values. XGBoost routes NaN along default_left; TMVA::Reader returns -999 for any NaN input, which the
production transform maps to the minimum score. Policy: rows with a non-finite input are not trained on and not
scored offline; production -999 means "rejected". The exporter cannot carry default_left and does not try.

Refused: booster other than gbtree; objective other than binary:logitraw; num_class > 0 or num_target != 1; vector
leaves; categorical splits; num_parallel_tree != 1; a feature-name list that differs from the feature list's table
columns; a nonzero base margin without fold_base_margin. Python 3.9 compatible.
"""
import hashlib
import json
import os
import re

import numpy as np

EXPORTER = 'sbnd-sp-export_tmva'
EXPORTER_VERSION = '1'
_BAD_ATTR = re.compile(r'[<>&"\n\r]')


class ExportError(ValueError):
    pass


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _f9(x):
    """%.9g of a float32 value: round-trips exactly through atof -> Float_t."""
    return '%.9g' % float(np.float32(x))


def _attr(v):
    s = str(v)
    if _BAD_ATTR.search(s):
        raise ExportError('attribute value contains a forbidden character (<>&" or newline): %r' % s)
    return s


def base_margin(model):
    """The margin offset XGBoost adds before the leaf sum, for objective binary:logitraw (= base_score)."""
    s = model['learner']['learner_model_param']['base_score'].strip()
    if s.startswith('['):
        vals = [v for v in s.strip('[]').split(',') if v.strip()]
        if len(vals) != 1:
            raise ExportError('base_score %r is not a single value' % s)
        s = vals[0]
    return float(s)


def check_model(model, columns):
    """Refusals (see module docstring). Returns the list of tree dicts."""
    L = model['learner']
    gb = L['gradient_booster']
    if gb.get('name') != 'gbtree':
        raise ExportError('booster %r is not gbtree' % gb.get('name'))
    obj = L['objective']['name']
    if obj != 'binary:logitraw':
        raise ExportError('objective %r is not binary:logitraw' % obj)
    lp = L['learner_model_param']
    if int(lp.get('num_class', '0')) not in (0, 1) or int(lp.get('num_target', '1')) != 1:
        raise ExportError('multi-class or multi-target model')
    gm = gb['model']
    if int(gm['gbtree_model_param'].get('num_parallel_tree', '1')) != 1:
        raise ExportError('num_parallel_tree != 1')
    if any(int(t) != 0 for t in gm.get('tree_info', [])):
        raise ExportError('trees for more than one output group')
    names = L.get('feature_names') or []
    if list(names) != list(columns):
        raise ExportError('model feature names differ from the feature list columns (names or order)')
    ftypes = L.get('feature_types') or []
    if any(t not in ('float', 'q', 'int', 'i') for t in ftypes):
        raise ExportError('non-numerical feature types: %s' % sorted(set(ftypes)))
    trees = gm['trees']
    if int(gm['gbtree_model_param']['num_trees']) != len(trees):
        raise ExportError('num_trees does not match the tree list')
    for t in trees:
        if t.get('categories_nodes') or any(int(s) != 0 for s in t.get('split_type', [])):
            raise ExportError('tree %d has categorical splits' % t['id'])
        if int(t['tree_param'].get('size_leaf_vector', '1')) > 1:
            raise ExportError('tree %d has vector leaves' % t['id'])
        if int(t['tree_param']['num_feature']) != len(columns):
            raise ExportError('tree %d num_feature != number of inputs' % t['id'])
    return trees


def preorder(tree):
    """XGBoost node ids of one tree in the order the XML writes them (root, left subtree, right subtree)."""
    lc, rc = tree['left_children'], tree['right_children']
    out, stack = [], [0]
    while stack:
        n = stack.pop()
        out.append(n)
        if lc[n] != -1:
            stack.append(rc[n])
            stack.append(lc[n])
    return out


def _node_xml(tree, n, pos, depth, nvar, parts):
    lc, rc = tree['left_children'], tree['right_children']
    sc, si = tree['split_conditions'], tree['split_indices']
    if lc[n] == -1:
        if rc[n] != -1:
            raise ExportError('tree %d node %d has one child' % (tree['id'], n))
        parts.append('<Node pos="%s" depth="%d" NCoef="0" IVar="-1" Cut="0.0e+00" cType="1" res="%s" rms="0.0e+00" '
                     'purity="0.0e+00" nType="-99" />' % (pos, depth, _f9(sc[n])))
        return
    if rc[n] == -1:
        raise ExportError('tree %d node %d has one child' % (tree['id'], n))
    iv = int(si[n])
    if not 0 <= iv < nvar:
        raise ExportError('tree %d node %d splits on input %d of %d' % (tree['id'], n, iv, nvar))
    cut = np.float32(sc[n])
    if not np.isfinite(cut):
        raise ExportError('tree %d node %d has a non-finite split' % (tree['id'], n))
    parts.append('<Node pos="%s" depth="%d" NCoef="0" IVar="%d" Cut="%s" cType="1" res="0.0e+00" rms="0.0e+00" '
                 'purity="0.0e+00" nType="0">' % (pos, depth, iv, _f9(cut)))
    _node_xml(tree, lc[n], 'l', depth + 1, nvar, parts)
    _node_xml(tree, rc[n], 'r', depth + 1, nvar, parts)
    parts.append('</Node>')


def to_tmva_xml(model, var_names, columns, info=None, fold_base_margin=False, var_type='D'):
    """(xml_text, record). var_names = XML expressions in model order; columns = the model's feature names."""
    if len(var_names) != len(columns):
        raise ExportError('var_names and columns differ in length')
    if var_type not in ('D', 'F'):
        raise ExportError('var_type must be D or F')
    trees = check_model(model, columns)
    off = base_margin(model)
    if off != 0.0 and not fold_base_margin:
        raise ExportError('base margin %r != 0: retrain with base_score 0 or pass fold_base_margin=True' % off)
    nvar = len(var_names)
    p = ['<MethodSetup Method="BDT::BDT"><Variables NVar="%d">' % nvar]
    for i, v in enumerate(var_names):
        v = _attr(v)
        p.append('<Variable VarIndex="%d" Type="%s" Expression="%s" Label="%s" Title="%s" Unit="" Internal="%s" '
                 'Min="0.0e+00" Max="0.0e+00" />' % (i, var_type, v, v, v, v))
    p.append('</Variables><GeneralInfo>')
    gi = [('Creator', EXPORTER), ('AnalysisType', 'Classification'), ('ExporterVersion', EXPORTER_VERSION),
          ('SourceObjective', 'binary:logitraw'), ('SourceBaseMargin', repr(off)),
          ('BaseMarginFoldedAsTree', 'true' if (off != 0.0 and fold_base_margin) else 'false'),
          ('SourceXGBoostVersion', '.'.join(str(x) for x in model.get('version', [])))]
    for k, v in (info or {}).items():
        gi.append((k, v))
    for k, v in gi:
        p.append('<Info name="%s" value="%s" />' % (_attr(k), _attr(v)))
    ntrees = len(trees) + (1 if (off != 0.0 and fold_base_margin) else 0)
    p.append('</GeneralInfo><Options><Option name="NodePurityLimit" modified="No">5.00e-01</Option>'
             '<Option name="BoostType" modified="Yes">Grad</Option><Option name="NTrees" modified="Yes">%d</Option>'
             '</Options><Weights NTrees="%d" AnalysisType="1">' % (ntrees, ntrees))
    order = []
    for k, t in enumerate(trees):
        p.append('<BinaryTree type="DecisionTree" boostWeight="1.0e+00" itree="%d">' % k)
        _node_xml(t, 0, 's', 0, nvar, p)
        p.append('</BinaryTree>')
        order.append(preorder(t))
    if off != 0.0 and fold_base_margin:
        p.append('<BinaryTree type="DecisionTree" boostWeight="1.0e+00" itree="%d"><Node pos="s" depth="0" NCoef="0" '
                 'IVar="-1" Cut="0.0e+00" cType="1" res="%s" rms="0.0e+00" purity="0.0e+00" nType="-99" />'
                 '</BinaryTree>' % (len(trees), _f9(off)))
    p.append('</Weights></MethodSetup>')
    rec = dict(ntrees_xgboost=len(trees), ntrees_xml=ntrees, nvar=nvar, base_margin=off,
               base_margin_folded=bool(off != 0.0 and fold_base_margin), var_type=var_type,
               nodes=int(sum(len(o) for o in order)))
    return ''.join(p), rec, order


def export(model_json, feature_list, out_dir, name, info=None, fold_base_margin=False, var_type='D'):
    """Write <name>.xml, <name>.json (copy of the native model), <name>.features.json and <name>.sha256 into out_dir.
    feature_list: sp_retrain.features.FeatureList. Returns a record with paths, hashes and the per-tree node order."""
    with open(model_json) as f:
        model = json.load(f)
    src_sha = _sha256(model_json)
    info = dict(info or {})
    info.setdefault('SourceJSONsha256', src_sha)
    info.setdefault('FeatureList', os.path.basename(feature_list.path))
    info.setdefault('FeatureListSha256', _sha256(feature_list.path))
    xml, rec, order = to_tmva_xml(model, feature_list.names, feature_list.columns, info, fold_base_margin, var_type)
    os.makedirs(out_dir, exist_ok=True)
    paths = dict(xml=os.path.join(out_dir, name + '.xml'), json=os.path.join(out_dir, name + '.json'),
                 features=os.path.join(out_dir, name + '.features.json'))
    with open(paths['xml'], 'w') as f:
        f.write(xml)
    with open(model_json, 'rb') as fi, open(paths['json'], 'wb') as fo:
        fo.write(fi.read())
    feats = dict(model=feature_list.model, source=os.path.basename(feature_list.path),
                 source_sha256=_sha256(feature_list.path), n_inputs=len(feature_list.names),
                 inputs=[dict(index=i, xml_name=n, table_column=c, caf_branch=b) for i, (n, c, b) in
                         enumerate(zip(feature_list.names, feature_list.columns, feature_list.branches))])
    with open(paths['features'], 'w') as f:
        json.dump(feats, f, indent=1)
    sums = {k: _sha256(v) for k, v in paths.items()}
    paths['sha256'] = os.path.join(out_dir, name + '.sha256')
    with open(paths['sha256'], 'w') as f:
        for k in ('xml', 'json', 'features'):
            f.write('%s  %s\n' % (sums[k], os.path.basename(paths[k])))
    rec.update(paths=paths, sha256=sums, source_json_sha256=src_sha, node_order=order)
    if sums['json'] != src_sha:
        raise ExportError('copied model JSON differs from the source')
    return rec


def forest_leaves(forest, X):
    """Index (into forest node arrays) of the leaf each row reaches in each tree, and the number of visited splits
    where x == Cut exactly (TMVA routing: right when x >= cut, inverted for cType 0). X: (n, nvar) float32."""
    X = np.ascontiguousarray(X, dtype=np.float32)
    rows = np.arange(len(X))
    out = np.empty((len(X), forest.ntrees), np.int64)
    eq = 0
    for t, r in enumerate(forest.roots):
        cur = np.full(len(X), r, np.int32)
        live = ~forest.leaf[cur]
        while live.any():
            c = cur[live]
            x = X[rows[live], forest.ivar[c]]
            eq += int((x == forest.cut[c]).sum())
            go_right = x >= forest.cut[c]
            go_right = np.where(forest.ctype[c], go_right, ~go_right)
            cur[live] = np.where(go_right, forest.right[c], forest.left[c])
            live = ~forest.leaf[cur]
        out[:, t] = cur
    return out, eq


def xml_leaf_to_xgb_node(forest, order, leaves):
    """Map forest leaf indices (from forest_leaves) to XGBoost node ids via the writer's preorder."""
    res = np.empty_like(leaves)
    for t in range(len(order)):
        o = np.asarray(order[t], np.int64)
        res[:, t] = o[leaves[:, t] - int(forest.roots[t])]
    return res


def visits(forest, X, tree, node_index):
    """Bool per row: does the TMVA walk of `tree` pass through forest node `node_index`?"""
    X = np.ascontiguousarray(X, dtype=np.float32)
    rows = np.arange(len(X))
    cur = np.full(len(X), forest.roots[tree], np.int32)
    seen = cur == node_index
    live = ~forest.leaf[cur]
    while live.any():
        c = cur[live]
        go_right = X[rows[live], forest.ivar[c]] >= forest.cut[c]
        go_right = np.where(forest.ctype[c], go_right, ~go_right)
        cur[live] = np.where(go_right, forest.right[c], forest.left[c])
        seen |= cur == node_index
        live = ~forest.leaf[cur]
    return seen
