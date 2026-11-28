"""The level-1 small per-object models of the Wire-Cell taggers, as shipped (MicroBooNE weights), from wcgpu1's reading of
the shipped TMVA XML files and of UbooneNueBDTScorer (project record, issues #1 and #14, 2026-11-10 / 2026-11-18).

Each model scores every object of one list of a candidate; the list is pooled to one number per candidate by `pool`
(min or max); an empty list gets `empty`. `lists` are the per-object inputs in the order the TMVA reader expects
(wc.T_tagger.<name>, jagged per candidate, all of equal length within a model); `scalars` are per-candidate inputs copied
to every object (only pio_2 has one); `flag` is the model's hand-written rule, itself a per-object list of the same
length (MicroBooNE's labelling A keeps the background objects where it fired); `score` is the pooled score stored per
candidate by the shipped software. The 15 nu_e models are the ones round 2 retrains; the three nu_mu / cosmic ones are
kept for completeness. `pre_cut` is the candidate-level condition under which the shipped software runs the model at all.

Reader order: the TMVA reader binds inputs BY POSITION, and the order it expects is `lists + scalars` (the one scalar,
pio_mip_id, is the last input of pio_2's weight file). A future model with a scalar in the middle must not use this
concatenation. `protect` lists the input protections the C++ applies before evaluating (value replaced when the condition
holds); they matter only when a retrained model is scored, never when tables are built. Checked against the 18 shipped
weight files by wcgpu1 (project record, wcgpu/level1/scripts/check_l1_models_spec.py, 2026-11-18): all match.
"""

L1_MODELS = {
 'numu_1':     dict(lists=['numu_cc_1_particle_type', 'numu_cc_1_length', 'numu_cc_1_medium_dQ_dx', 'numu_cc_1_dQ_dx_cut', 'numu_cc_1_direct_length', 'numu_cc_1_n_daughter_tracks', 'numu_cc_1_n_daughter_all'],
                   scalars=[], flag='numu_cc_flag_1', pool='max', empty=-0.4, ntrees=850, score='numu_1_score', flavour='numu', pre_cut='cosmict_flag_1 == 0', protect={'numu_cc_1_dQ_dx_cut': ('inf', 10.0)}),
 'numu_2':     dict(lists=['numu_cc_2_length', 'numu_cc_2_total_length', 'numu_cc_2_n_daughter_tracks', 'numu_cc_2_n_daughter_all'],
                   scalars=[], flag='numu_cc_flag_2', pool='max', empty=-0.1, ntrees=850, score='numu_2_score', flavour='numu', pre_cut='cosmict_flag_1 == 0'),
 'cosmict_10': dict(lists=['cosmict_10_vtx_z', 'cosmict_10_flag_shower', 'cosmict_10_flag_dir_weak', 'cosmict_10_angle_beam', 'cosmict_10_length'],
                   scalars=[], flag='cosmict_flag_10', pool='min', empty=0.7, ntrees=400, score='cosmict_10_score', flavour='cosmic', pre_cut='cosmict_flag_1 == 0', protect={'cosmict_10_angle_beam': ('nan', 0.0)}),
 'br3_3':      dict(lists=['br3_3_v_energy', 'br3_3_v_angle', 'br3_3_v_dir_length', 'br3_3_v_length'],
                   scalars=[], flag='br3_3_v_flag', pool='min', empty=0.3, ntrees=850, score='br3_3_score', flavour='nue', pre_cut=''),
 'br3_5':      dict(lists=['br3_5_v_dir_length', 'br3_5_v_total_length', 'br3_5_v_flag_avoid_muon_check', 'br3_5_v_n_seg', 'br3_5_v_angle', 'br3_5_v_sg_length', 'br3_5_v_energy', 'br3_5_v_n_segs', 'br3_5_v_shower_main_length', 'br3_5_v_shower_total_length'],
                   scalars=[], flag='br3_5_v_flag', pool='min', empty=0.42, ntrees=850, score='br3_5_score', flavour='nue', pre_cut=''),
 'br3_6':      dict(lists=['br3_6_v_angle', 'br3_6_v_angle1', 'br3_6_v_flag_shower_trajectory', 'br3_6_v_direct_length', 'br3_6_v_length', 'br3_6_v_n_other_vtx_segs', 'br3_6_v_energy'],
                   scalars=[], flag='br3_6_v_flag', pool='min', empty=0.75, ntrees=850, score='br3_6_score', flavour='nue', pre_cut=''),
 'pio_2':      dict(lists=['pio_2_v_dis2', 'pio_2_v_angle2', 'pio_2_v_acc_length'],
                   scalars=['pio_mip_id'], flag='pio_2_v_flag', pool='min', empty=0.2, ntrees=850, score='pio_2_score', flavour='nue', pre_cut='pio_filled == 1 and pio_flag_pio == 0'),
 'stw_2':      dict(lists=['stw_2_v_medium_dQ_dx', 'stw_2_v_energy', 'stw_2_v_angle', 'stw_2_v_dir_length', 'stw_2_v_max_dQ_dx'],
                   scalars=[], flag='stw_2_v_flag', pool='min', empty=0.7, ntrees=850, score='stw_2_score', flavour='nue', pre_cut=''),
 'stw_3':      dict(lists=['stw_3_v_angle', 'stw_3_v_dir_length', 'stw_3_v_energy', 'stw_3_v_medium_dQ_dx'],
                   scalars=[], flag='stw_3_v_flag', pool='min', empty=0.5, ntrees=850, score='stw_3_score', flavour='nue', pre_cut=''),
 'stw_4':      dict(lists=['stw_4_v_angle', 'stw_4_v_dis', 'stw_4_v_energy'],
                   scalars=[], flag='stw_4_v_flag', pool='min', empty=0.7, ntrees=850, score='stw_4_score', flavour='nue', pre_cut=''),
 'sig_1':      dict(lists=['sig_1_v_angle', 'sig_1_v_flag_single_shower', 'sig_1_v_energy', 'sig_1_v_energy_1'],
                   scalars=[], flag='sig_1_v_flag', pool='min', empty=0.59, ntrees=850, score='sig_1_score', flavour='nue', pre_cut=''),
 'sig_2':      dict(lists=['sig_2_v_energy', 'sig_2_v_shower_angle', 'sig_2_v_flag_single_shower', 'sig_2_v_medium_dQ_dx', 'sig_2_v_start_dQ_dx'],
                   scalars=[], flag='sig_2_v_flag', pool='min', empty=0.55, ntrees=850, score='sig_2_score', flavour='nue', pre_cut=''),
 'lol_1':      dict(lists=['lol_1_v_energy', 'lol_1_v_vtx_n_segs', 'lol_1_v_nseg', 'lol_1_v_angle'],
                   scalars=[], flag='lol_1_v_flag', pool='min', empty=0.85, ntrees=850, score='lol_1_score', flavour='nue', pre_cut=''),
 'lol_2':      dict(lists=['lol_2_v_length', 'lol_2_v_angle', 'lol_2_v_type', 'lol_2_v_vtx_n_segs', 'lol_2_v_energy', 'lol_2_v_shower_main_length', 'lol_2_v_flag_dir_weak'],
                   scalars=[], flag='lol_2_v_flag', pool='min', empty=0.7, ntrees=850, score='lol_2_score', flavour='nue', pre_cut=''),
 'tro_1':      dict(lists=['tro_1_v_particle_type', 'tro_1_v_flag_dir_weak', 'tro_1_v_min_dis', 'tro_1_v_sg1_length', 'tro_1_v_shower_main_length', 'tro_1_v_max_n_vtx_segs', 'tro_1_v_tmp_length', 'tro_1_v_medium_dQ_dx', 'tro_1_v_dQ_dx_cut', 'tro_1_v_flag_shower_topology'],
                   scalars=[], flag='tro_1_v_flag', pool='min', empty=0.28, ntrees=850, score='tro_1_score', flavour='nue', pre_cut=''),
 'tro_2':      dict(lists=['tro_2_v_energy', 'tro_2_v_stem_length', 'tro_2_v_iso_angle', 'tro_2_v_max_length', 'tro_2_v_angle'],
                   scalars=[], flag='tro_2_v_flag', pool='min', empty=0.35, ntrees=850, score='tro_2_score', flavour='nue', pre_cut=''),
 'tro_4':      dict(lists=['tro_4_v_dir2_mag', 'tro_4_v_angle', 'tro_4_v_angle1', 'tro_4_v_angle2', 'tro_4_v_length', 'tro_4_v_length1', 'tro_4_v_medium_dQ_dx', 'tro_4_v_end_dQ_dx', 'tro_4_v_energy', 'tro_4_v_shower_main_length', 'tro_4_v_flag_shower_trajectory'],
                   scalars=[], flag='tro_4_v_flag', pool='min', empty=0.33, ntrees=850, score='tro_4_score', flavour='nue', pre_cut=''),
 'tro_5':      dict(lists=['tro_5_v_max_angle', 'tro_5_v_min_angle', 'tro_5_v_max_length', 'tro_5_v_iso_angle', 'tro_5_v_n_vtx_segs', 'tro_5_v_min_count', 'tro_5_v_max_count', 'tro_5_v_energy'],
                   scalars=[], flag='tro_5_v_flag', pool='min', empty=0.5, ntrees=850, score='tro_5_score', flavour='nue', pre_cut=''),
}
for _d in L1_MODELS.values(): _d.setdefault('protect', {})

# MicroBooNE's labelling rule, per model (wcgpu1's audit of the MicroBooNE trainers, uboone_nusel_app/apps/*.cxx; project record,
# issue #14, 2026-11-19): `narrows` says which side the rule flag restricts, `fired` which flag value restricts it; the other side
# is unrestricted (beyond the model's pre_cut, which sits on both sides). Three of the four combinations occur:
#   the 15 nu_e models: background objects kept only where flag == 0; every signal object kept.
#   numu_1, numu_2:     signal objects kept only where flag == 1; every background object kept.
#   cosmict_10:         background objects kept only where flag == 1; every signal object kept (neither of the two groups above).
RULE_A = {m: dict(narrows='background', fired=0) for m in L1_MODELS if L1_MODELS[m]['flavour'] == 'nue'}
RULE_A.update(numu_1=dict(narrows='signal', fired=1), numu_2=dict(narrows='signal', fired=1), cosmict_10=dict(narrows='background', fired=1))
for _m, _r in RULE_A.items(): L1_MODELS[_m]['rule_a'] = _r
NUE_L1 = [m for m, d in L1_MODELS.items() if d['flavour'] == 'nue']   # the 15 of the nu_e tagger, in the shipped order
