import math
import numpy as np
from sbnd_single_photon import bdt as B

XML = """<?xml version="1.0"?>
<MethodSetup Method="BDT">
 <Variables NVar="2">
  <Variable VarIndex="0" Expression="a"/><Variable VarIndex="1" Expression="b"/>
 </Variables>
 <Weights NTrees="2">
  <BinaryTree type="DecisionTree" boostWeight="0.5" itree="0">
   <Node pos="s" IVar="-1"><Node pos="l" IVar="0" Cut="1.0" res="0.0"><Node pos="l" IVar="-1" res="-1.0"/><Node pos="r" IVar="-1" res="2.0"/></Node>
   <Node pos="r" IVar="-1" res="0.3"/></Node>
  </BinaryTree>
  <BinaryTree type="DecisionTree" boostWeight="0.25" itree="1">
   <Node pos="s" IVar="1" Cut="0.0"><Node pos="l" IVar="-1" res="1.0"/><Node pos="r" IVar="-1" res="-2.0"/></Node>
  </BinaryTree>
 </Weights>
</MethodSetup>"""


def _scalar(model_xml_root, x):
    """Scalar copy of the validated tree walk in analysis/microboone_1gamma_v0/score_microboone_bdts.py."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(model_xml_root)

    def walk(node):
        kids = [c for c in node if c.tag == "Node"]
        if not kids:
            return float(node.get("res"))
        l = next(c for c in kids if c.get("pos") == "l"); r = next(c for c in kids if c.get("pos") == "r")
        return walk(l) if x[int(node.get("IVar"))] <= float(node.get("Cut")) else walk(r)

    return math.tanh(sum(float(bt.get("boostWeight")) * walk(bt.find("Node"))
                         for bt in root.find("Weights").findall("BinaryTree")))


def test_vectorised_matches_scalar_tree_walk(tmp_path):
    # NOTE: the synthetic root node of tree 0 has IVar=-1 with children; make tree 0 a single internal root instead
    xml = XML.replace('<Node pos="s" IVar="-1"><Node pos="l" IVar="0" Cut="1.0" res="0.0">',
                      '<Node pos="s" IVar="0" Cut="1.0"><Node pos="l" IVar="1" Cut="0.5" res="0.0">')
    p = tmp_path / "m.xml"; p.write_text(xml)
    m = B.TmvaBdt("toy", p, check_nvars=False)
    rng = np.random.default_rng(1)
    X = rng.normal(size=(200, 2))
    got = m.decision(X)
    want = np.array([_scalar(xml, x) for x in X])
    np.testing.assert_allclose(got, want, rtol=0, atol=1e-12)


def test_nonfinite_rows_return_nan(tmp_path):
    xml = XML.replace('<Node pos="s" IVar="-1"><Node pos="l" IVar="0" Cut="1.0" res="0.0">',
                      '<Node pos="s" IVar="0" Cut="1.0"><Node pos="l" IVar="1" Cut="0.5" res="0.0">')
    p = tmp_path / "m.xml"; p.write_text(xml)
    m = B.TmvaBdt("toy", p, check_nvars=False)
    out = m.decision(np.array([[0.0, 0.0], [np.nan, 0.0]]))
    assert np.isfinite(out[0]) and np.isnan(out[1])


def test_input_branch_mapping():
    assert B.input_branch("other", "reco_nuvtxY") == "wc.T_kine.kine_nu_y_corr"
    assert B.input_branch("ncpi0", "kine_pio_mass") == "wc.T_kine.kine_pio_mass"
    assert B.input_branch("numu", "numu_cc_flag_3") == "wc.T_tagger.numu_cc_flag_3"
