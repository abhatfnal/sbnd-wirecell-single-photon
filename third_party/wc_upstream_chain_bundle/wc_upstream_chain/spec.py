"""Feature specifications of the upstream Wire-Cell taggers, loaded from the bundle's data files (no code is executed).

Ordered lists (the TMVA reader binds inputs BY POSITION; the order is part of the model):
  NUMU_FINAL_INPUTS  74 inputs of numu_scalars_scores_0923.xml (data/numu_l2_inputs_74.txt)
  NUE_FINAL_INPUTS   258 inputs of XGB_nue_seed2_0923.xml (data/nue_l2_inputs_258.txt)
  L1[m]['lists'] + L1[m]['scalars']   inputs of level-1 model m (data/l1_models.json)
"""
import json
import os

import numpy as np

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def _lines(name):
    with open(os.path.join(DATA, name)) as f:
        return [l.strip() for l in f if l.strip()]


def _json(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


NUMU_FINAL_INPUTS = _lines('numu_l2_inputs_74.txt')
NUE_FINAL_INPUTS = _lines('nue_l2_inputs_258.txt')
_L1 = _json('l1_models.json')
L1 = {m: dict(d, protect={k: (v[0], float(v[1])) for k, v in d['protect'].items()}) for m, d in _L1['models'].items()}
L1_NUMU = ['numu_1', 'numu_2', 'cosmict_10']
L1_NUE = list(_L1['nue_l1_order'])
L1_ALL = L1_NUMU + L1_NUE
EMPTY = {m: np.float32(L1[m]['empty']) for m in L1_ALL}           # value stored for a candidate with no object (or failed pio_2 gate)

NUMU_SCORES = ['numu_1_score', 'numu_2_score', 'cosmict_10_score', 'numu_score']
NUE_L1_SCORES = [m + '_score' for m in L1_NUE]
UPSTREAM_OUTPUTS = NUMU_SCORES + NUE_L1_SCORES + ['nue_score']     # the 20 values a production with the releases changes
STORED_SCORES = ['numu_score', 'numu_1_score', 'numu_2_score', 'numu_3_score', 'cosmict_10_score', 'nue_score'] + NUE_L1_SCORES

CHAIN_FILES = dict(numu_1='numu_tagger1.weights.xml', numu_2='numu_tagger2.weights.xml', numu_3='numu_tagger3.weights.xml',
                   cosmict_10='cos_tagger_10.weights.xml', numu_final='numu_scalars_scores_0923.xml', nue_final='XGB_nue_seed2_0923.xml')
CHAIN_FILES.update({m: '%s_BDT.weights.xml' % m for m in L1_NUE})

# nu_mu simulation charge correction (release numu_round3af/correction.json; toolkit patch numu_sim_dqdx_scale)
SIM_DQDX_SCALE = 1.071
SIM_DQDX_L1 = ('numu_1', 'numu_cc_1_medium_dQ_dx')                # the per-segment input of numu_1
SIM_DQDX_FINAL = [('cosmict_2_filled', 'cosmict_2_dQ_dx_end'), ('cosmict_2_filled', 'cosmict_2_dQ_dx_front'),
                  ('cosmict_3_filled', 'cosmict_3_dQ_dx_end'), ('cosmict_3_filled', 'cosmict_3_dQ_dx_front'),
                  ('cosmict_7_filled', 'cosmict_7_dQ_dx_end'), ('cosmict_7_filled', 'cosmict_7_dQ_dx_front')]
SIM_DQDX_INPUTS = [SIM_DQDX_L1[1]] + [c for _, c in SIM_DQDX_FINAL]
# raw quantities that are NEVER modified in the stored tables / SP inputs (the chain changes only the copies it hands the nu_mu BDTs)
RAW_MUST_STAY_RAW = [c for _, c in SIM_DQDX_FINAL] + ['numu_cc_flag']

NUMU_NAN_TO_0 = ['cosmict_4_angle_beam', 'cosmict_7_angle_beam', 'cosmict_7_theta', 'cosmict_7_phi']
NUE_FINAL_PROTECT = [('mip_min_dis', 'cap', 1000.0), ('mip_quality_shortest_length', 'cap', 1000.0),
                     ('mip_quality_shortest_angle', 'nan', 0.0), ('stem_dir_ratio', 'nan', 1.0)]
PIO_2_GATE = ('pio_filled', 'pio_flag_pio')                       # pio_2 runs only when pio_filled == 1 and pio_flag_pio == 0
NUE_RUN_GATE = 'br_filled'                                        # nue_score = -15 unless br_filled == 1 (level-1 models are NOT gated)

NUMU_GATES = ['numu_cc_flag_3', 'cosmict_2_filled', 'cosmict_3_filled', 'cosmict_7_filled']   # read by the simulation correction
NUE_GATES = ['br_filled', 'pio_filled', 'pio_flag_pio']
_L1_OUT = set(NUMU_SCORES) | set(NUE_L1_SCORES)


def candidate_inputs(numu=True, nue=True):
    """Candidate-level columns the scorer reads (beyond the key): the final-model inputs that are not level-1 outputs, and the gates."""
    names = (NUMU_FINAL_INPUTS + NUMU_GATES if numu else []) + (NUE_FINAL_INPUTS + NUE_GATES if nue else [])
    return list(dict.fromkeys(n for n in names if n not in _L1_OUT))


def object_inputs(model, sim_correction=False):
    """Per-object columns of a level-1 model (beyond the key): lists + scalars, and 'flag' for numu_1 / numu_2 when the
    simulation correction is applied (the internal numu_cc_flag update reads them)."""
    d = L1[model]
    return d['lists'] + d['scalars'] + (['flag'] if sim_correction and model in ('numu_1', 'numu_2') else [])
