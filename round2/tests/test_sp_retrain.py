"""Unit tests for round2/sp_retrain. Run: python -m pytest -q round2/tests"""
import csv
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROUND2)
sys.path.insert(0, ROUND2)
from sp_retrain import features, firewall, labels, split, tmva_grad  # noqa: E402

TABLE = os.path.join(REPO, 'baseline_v0', 'tables', 'microboone_single_photon_bdt_inputs.csv')
NUE_L1 = {'br3_3_score', 'br3_5_score', 'br3_6_score', 'pio_2_score', 'stw_2_score', 'stw_3_score', 'stw_4_score',
          'sig_1_score', 'sig_2_score', 'lol_1_score', 'lol_2_score', 'tro_1_score', 'tro_2_score', 'tro_4_score',
          'tro_5_score'}


# ---------------------------------------------------------------- feature lists
@pytest.mark.parametrize('model,n', [('single_photon_ncpi0', 45), ('single_photon_other', 146),
                                     ('single_photon_numu', 73), ('single_photon_nue', 56)])
def test_feature_list_matches_xml_table(model, n):
    fl = features.load(model)
    rows = sorted((r for r in csv.DictReader(open(TABLE)) if r['model'] == model), key=lambda r: int(r['input_order']))
    assert len(fl.names) == n == len(rows)
    assert fl.names == [r['xml_expression'] for r in rows]          # exact XML order
    assert fl.cfg['n_missing_from_schema'] == 0


def test_upstream_dependencies_are_what_the_xml_lists():
    assert {n for _, n, _, _ in features.load('single_photon_ncpi0').upstream_inputs()} == NUE_L1
    assert {n for _, n, _, _ in features.load('single_photon_other').upstream_inputs()} == {
        'cosmict_10_score', 'numu_1_score', 'numu_2_score', 'numu_score'}
    assert {n for _, n, _, _ in features.load('single_photon_numu').upstream_inputs()} == {'numu_1_score', 'numu_score'}
    assert features.load('single_photon_nue').upstream_inputs() == []
    # no single-photon BDT consumes another single-photon score, nor nue_score
    for m in ('ncpi0', 'other', 'numu', 'nue'):
        names = features.load('single_photon_' + m).names
        assert not any(x.startswith('single_photon_') for x in names) and 'nue_score' not in names


def test_reco_nuvtxY_maps_to_kine_nu_y_corr():
    fl = features.load('single_photon_other')
    i = fl.names.index('reco_nuvtxY')
    assert fl.columns[i] == 'kine_nu_y_corr' and fl.branches[i] == 'wc.T_kine.kine_nu_y_corr'


# ---------------------------------------------------------------- firewall
AURORA = '/lus/flare/projects/neutrinoGPU/yuhw/production-prep/dlspace'


@pytest.mark.parametrize('path', [
    '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/mc-cv/x/merged.wc.flat.caf.root',
    '/lus/flare/projects/neutrinoGPU/xning/data/fg1-beam-off-train/data_filtered_decoded_reco1-0003/x.root',
    AURORA + '/../fg1/beam-off-eval/a.root'])
def test_firewall_refuses_official_samples(path):
    with pytest.raises(firewall.FirewallError):
        firewall.check_training_inputs([path], [AURORA, '/lus/flare/projects/neutrinoGPU/xning/data'])


def test_firewall_accepts_aurora_and_refuses_outside_roots():
    ok = AURORA + '/ncdr/node0/reco1-detsim-g4-filter-gen-0011-dddd-1d03-7a79/merged/reco2-x.wc.flat.caf.root'
    assert firewall.check_training_inputs([ok], [AURORA]) == 1
    with pytest.raises(firewall.FirewallError):
        firewall.check_training_inputs(['/lus/flare/projects/neutrinoGPU/abhat/sbnd/gen2-x/flatcaf/a.root'], [AURORA])
    for s in ('fg1-mc-ncdr', 'fg1-beam-off-train', 'run3-bnb-data'):
        with pytest.raises(firewall.FirewallError):
            firewall.check_sample_id(s)
    firewall.check_sample_id('aurora-r2-ncdr')


def test_firewall_refuses_writing_into_other_areas(tmp_path):
    for p in ('/lus/flare/projects/neutrinoGPU/xning/BDT/out', '/lus/flare/projects/neutrinoGPU/yuhw/x'):
        with pytest.raises(firewall.FirewallError):
            firewall.check_output_path(p, ['/lus/flare/projects/neutrinoGPU'])
    assert firewall.check_output_path(str(tmp_path / 'o'), [str(tmp_path)]).endswith('/o')


# ---------------------------------------------------------------- split
def _frame():
    rng = np.random.default_rng(1)
    rows = []
    for s in ('aurora-r2-ncdr', 'aurora-r2-bnb'):
        for run in range(3):
            for sub in range(40):
                for ev in range(int(rng.integers(1, 4))):
                    for c in range(int(rng.integers(1, 4))):      # several candidates per event
                        rows.append(dict(sample=s, file_id='f%d_%d' % (run, sub // 7), run=run, subrun=sub, event=ev, cand=c))
    return pd.DataFrame(rows)


def test_split_is_event_and_subrun_safe_and_deterministic():
    f = _frame()
    f['split'] = split.assign(f['sample'], f.run, f.subrun)
    split.check_event_safe(f)
    again = split.assign(f['sample'], f.run, f.subrun)
    assert (again == f['split'].to_numpy()).all()
    assert set(f.loc[f.subrun % 2 == 1, 'split']) == {'test'}
    assert set(f.loc[f.subrun % 2 == 0, 'split']) == {'train', 'validation'}
    other_seed = split.assign(f['sample'], f.run, f.subrun, seed=split.DEFAULT_SEED + 1)
    assert (other_seed != f['split'].to_numpy()).any()     # the seed matters for train vs validation only


def test_split_check_catches_a_straddling_event():
    f = _frame()
    f['split'] = split.assign(f['sample'], f.run, f.subrun)
    f.loc[f.index[0], 'split'] = 'test' if f.loc[f.index[0], 'split'] != 'test' else 'train'
    with pytest.raises(AssertionError):
        split.check_event_safe(f)


# ---------------------------------------------------------------- TMVA Grad evaluator
XML = """<?xml version="1.0"?>
<MethodSetup Method="BDT::BDT">
  <GeneralInfo><Info name="Creator" value="unit-test"/></GeneralInfo>
  <Options><Option name="BoostType" modified="Yes">Grad</Option></Options>
  <Variables NVar="2">
    <Variable VarIndex="0" Expression="a" Label="a" Title="a" Unit="" Internal="a" Type="F" Min="0" Max="1"/>
    <Variable VarIndex="1" Expression="b" Label="b" Title="b" Unit="" Internal="b" Type="F" Min="0" Max="1"/>
  </Variables>
  <Transformations NTransformations="0"/>
  <Weights NTrees="2" AnalysisType="1">
    <BinaryTree type="DecisionTree" boostWeight="1" itree="0">
      <Node pos="s" depth="0" NCoef="0" IVar="0" Cut="1.5" cType="1" res="0" rms="0" purity="0" nType="0">
        <Node pos="l" depth="1" NCoef="0" IVar="-1" Cut="0" cType="1" res="-0.25" rms="0" purity="0" nType="-99"/>
        <Node pos="r" depth="1" NCoef="0" IVar="-1" Cut="0" cType="1" res="0.5" rms="0" purity="0" nType="1"/>
      </Node>
    </BinaryTree>
    <BinaryTree type="DecisionTree" boostWeight="1" itree="1">
      <Node pos="s" depth="0" NCoef="0" IVar="1" Cut="0" cType="0" res="0" rms="0" purity="0" nType="0">
        <Node pos="l" depth="1" NCoef="0" IVar="-1" Cut="0" cType="1" res="0.1" rms="0" purity="0" nType="-99"/>
        <Node pos="r" depth="1" NCoef="0" IVar="-1" Cut="0" cType="1" res="-0.3" rms="0" purity="0" nType="1"/>
      </Node>
    </BinaryTree>
  </Weights>
</MethodSetup>
"""


def test_tmva_grad_routing_and_conventions(tmp_path):
    p = tmp_path / 'toy.xml'
    p.write_text(XML)
    f = tmva_grad.GradForest(str(p), expected_names=['a', 'b'])
    X = np.array([[1.0, 1.0], [1.5, 1.0], [2.0, -1.0], [np.nan, 0.0]])
    # tree 0: right when a >= 1.5 (TMVA: equality goes RIGHT). tree 1: cType=0 inverts, right when b < 0.
    assert np.allclose(f.raw(X)[:3], [-0.25 + 0.1, 0.5 + 0.1, 0.5 - 0.3])
    v = f.evaluate_mva(X)
    assert np.allclose(v[:3], np.tanh(f.raw(X)[:3])) and v[3] == tmva_grad.SENTINEL_NAN
    lo = tmva_grad.log10_odds(v[:3])
    assert np.allclose(lo, 2.0 / math.log(10.0) * f.raw(X)[:3])     # log10-odds = 0.8686 * raw
    with pytest.raises(ValueError):
        tmva_grad.GradForest(str(p), expected_names=['b', 'a'])


def test_frozen_thresholds_in_tanh_space():
    t = {k: tmva_grad.threshold_in_tanh_space(c) for k, c in dict(numu=0.4, other=0.2, ncpi0=-0.05, nue=-1.0).items()}
    assert abs(t['numu'] - 0.43050) < 1e-4 and abs(t['other'] - 0.22630) < 1e-4
    assert abs(t['ncpi0'] + 0.05750) < 1e-4 and abs(t['nue'] + 0.81818) < 1e-4   # nue > -1.0 is a real cut


# ---------------------------------------------------------------- builder helpers
def test_scalar_branches_excludes_lists():
    from sp_retrain import build_tables
    keys = {'wc.T_kine.kine_pio_mass', 'wc.T_kine.kine_energy_particle', 'wc.T_kine.kine_energy_particle..idx',
            'wc.T_kine.kine_energy_particle..length', 'wc.T_tagger.shw_sp_filled'}
    assert build_tables._scalar_branches(keys, 'wc.T_kine.') == ['wc.T_kine.kine_pio_mass']


def test_truth_summary_counts_pi0_photons_and_leptons():
    from sp_retrain import build_tables
    # neutrino row 0: primary pi0 (tid 5) -> photons 6 (0.10 GeV, converts inside) and 7 (0.01 GeV, below 20 MeV);
    # a primary photon 8 (0.20 GeV, converts inside); a primary mu- 9 (0.05 GeV). Row 1 owns another pi0 (ignored).
    pf = dict(nu_row=np.array([0, 0, 0, 0, 0, 1]), trackid=np.array([5, 6, 7, 8, 9, 20]),
              parent_trackid=np.array([0, 5, 5, 0, 0, 0]), mother_trackid=np.array([1, 5, 5, 1, 1, 1]),
              pdg=np.array([111, 22, 22, 22, 13, 111]), process=np.zeros(6, int),
              KE=np.array([0.3, 0.10, 0.01, 0.20, 0.05, 0.4]),
              start_px=np.array([0, 1, 0, 0, 0, 0.]), start_py=np.array([0, 0, 1, 0, 0, 0.]), start_pz=np.zeros(6),
              end_x=np.array([0, 10, 205, 0, 0, 0.]), end_y=np.zeros(6), end_z=np.array([0, 250, 250, 100, 0, 0.]))
    s = build_tables.truth_summary(0, pf)
    assert s['n_prim_pi0'] == 1 and s['n_pi0_all'] == 1
    assert s['n_gamma_from_prim_pi0'] == 2 and s['n_prim_gamma'] == 1
    assert s['n_gamma_ke20'] == 2 and s['n_gamma_ke20_conv_in3cm'] == 2 and s['n_gamma_from_prim_pi0_ke20_conv_in3cm'] == 1
    assert abs(s['pi0_gamma_min_open_deg'] - 90.0) < 1e-9
    assert s['n_prim_mu'] == 1 and abs(s['max_prim_mu_ke_mev'] - 50.0) < 1e-9 and s['n_prim_e'] == 0


# ---------------------------------------------------------------- label guard
def test_labels_refuse_blocked_specs():
    for m in ('ncpi0', 'other'):
        spec = labels.load_spec(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_v0.1.yaml' % m))
        assert spec['status'] == 'BLOCKED'
        with pytest.raises(labels.TargetBlockedError):
            labels.training_labels(None, spec)
