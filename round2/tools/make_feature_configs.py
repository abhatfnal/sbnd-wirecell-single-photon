#!/usr/bin/env python3
"""Write the ordered input lists of the four frozen MicroBooNE single-photon BDTs as versioned JSON configs.

The order comes from baseline_v0/tables/microboone_single_photon_bdt_inputs.csv, which was extracted from each XML's
<Variables> block (VarIndex order) on 2026-10-05. Each input is mapped to its merged-CAF branch and checked against the
recTreeWireCell schema JSON that Haiwang's merge step writes (schema md5 af9c87c8 for aurora-r2).

  python make_feature_configs.py --schema <recTreeWireCell-...schema.json> --out-dir ../config/features

No ROOT file is opened. Re-running with the same inputs gives byte-identical JSON.
"""
import argparse, csv, hashlib, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TABLE = os.path.join(REPO, 'baseline_v0', 'tables', 'microboone_single_photon_bdt_inputs.csv')

XML_SHA256 = {   # provenance/software_versions.yaml of this repository
    'single_photon_numu': '5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961',
    'single_photon_other': '8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16',
    'single_photon_ncpi0': '983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3',
    'single_photon_nue': '8580ba04b4a9e3c7aefbb4d5da5006cff2a131804a7b594843461a7cd6f3758a',
}
# Inputs that are the OUTPUT of another classifier. Producer and empty-list default are read from the SBND toolkit at
# the aurora-r2 production pin a2785870 (root/src/UbooneNumuBDTScorer.cxx:473-476, root/src/UbooneNueBDTScorer.cxx:1697-1711).
UPSTREAM = {
    'numu_score': ('nu_mu final BDT', 'UbooneNumuBDTScorer', 'numu_scalars_scores_0923.xml', None),
    'numu_1_score': ('nu_mu level-1 BDT', 'UbooneNumuBDTScorer', 'numu_tagger1.weights.xml', -0.4),
    'numu_2_score': ('nu_mu level-1 BDT', 'UbooneNumuBDTScorer', 'numu_tagger2.weights.xml', -0.1),
    'cosmict_10_score': ('nu_mu level-1 BDT', 'UbooneNumuBDTScorer', 'cos_tagger_10.weights.xml', 0.7),
}
for _n, _d in [('br3_3', 0.3), ('br3_5', 0.42), ('br3_6', 0.75), ('pio_2', 0.2), ('stw_2', 0.7), ('stw_3', 0.5),
               ('stw_4', 0.7), ('sig_1', 0.59), ('sig_2', 0.55), ('lol_1', 0.85), ('lol_2', 0.7), ('tro_1', 0.28),
               ('tro_2', 0.35), ('tro_4', 0.33), ('tro_5', 0.5)]:
    UPSTREAM[_n + '_score'] = ('nu_e level-1 BDT', 'UbooneNueBDTScorer', _n + '_BDT.weights.xml', _d)

KINE_INPUTS = {'kine_pio_mass', 'kine_pio_flag', 'kine_pio_vtx_dis', 'kine_pio_energy_1', 'kine_pio_energy_2',
               'kine_pio_theta_1', 'kine_pio_theta_2', 'kine_pio_phi_1', 'kine_pio_phi_2', 'kine_pio_dis_1',
               'kine_pio_dis_2', 'kine_pio_angle'}
RENAMED = {'reco_nuvtxY': 'kine_nu_y_corr'}   # MicroBooNE pfeval.reco_nuvtxY; SBND T_kine (baseline_v0/docs/RECO_NUVTX_MAPPING.md)
NOTES = {
    'kine_pio_flag': ('MicroBooNE reference scorer feeds 0 for the single-photon BDTs (apps/bdt_convert.cxx '
                      '"temp_kine_pio_flag = 0", eyandel 47b1f0c 2024-02-26 "break pi0 flag for sp only"); the SBND '
                      'baseline_v0 scorer fed the real T_kine value. Int_t in the CAF. Treatment for retraining: OPEN.'),
    'reco_nuvtxY': 'MicroBooNE pfeval.reco_nuvtxY; SBND equivalent T_kine.kine_nu_y_corr (baseline_v0/docs/RECO_NUVTX_MAPPING.md).',
    'numu_cc_3_track_length': 'MicroBooNE C++ feeds tagger.numu_cc_3_acc_track_length into this XML name; SBND branch is numu_cc_3_track_length.',
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--schema', required=True, help='recTreeWireCell schema JSON written by the merge step')
    ap.add_argument('--out-dir', default=os.path.join(REPO, 'round2', 'config', 'features'))
    a = ap.parse_args()
    schema = {b['name']: b for b in json.load(open(a.schema))['branches']}
    rows = list(csv.DictReader(open(TABLE)))
    os.makedirs(a.out_dir, exist_ok=True)
    for model in XML_SHA256:
        rs = sorted((r for r in rows if r['model'] == model), key=lambda r: int(r['input_order']))
        assert [int(r['input_order']) for r in rs] == list(range(len(rs))), model
        inputs = []
        for r in rs:
            name = r['xml_expression']
            column = RENAMED.get(name, name)
            tree = 'T_kine' if (name in KINE_INPUTS or name in RENAMED) else 'T_tagger'
            branch = 'wc.%s.%s' % (tree, column)
            s = schema.get(branch)
            up = UPSTREAM.get(name)
            inputs.append(dict(index=int(r['input_order']), name=name, caf_tree=tree, caf_branch=branch,
                               caf_type=s['type'] if s else None, in_schema=bool(s), table_column=column,
                               kind='upstream_score' if up else 'reco',
                               upstream=None if not up else dict(family=up[0], producer=up[1], weights=up[2], empty_default=up[3]),
                               microboone_cpp_source=r['cpp_source_object'], notes=NOTES.get(name, r['notes'] or None)))
        out = dict(model=model, feature_list_version='v0', n_inputs=len(inputs),
                   order_authority='XML <Variables> VarIndex, via baseline_v0/tables/microboone_single_photon_bdt_inputs.csv',
                   source=dict(xml=model + '_bdt_final.xml', xml_sha256=XML_SHA256[model],
                               variable_table='baseline_v0/tables/microboone_single_photon_bdt_inputs.csv',
                               variable_table_sha256=sha256(TABLE),
                               microboone_scorer='brb-rightback/wcp-uboone-bdt-eyandel@0100d4b6 apps/bdt_convert.cxx'),
                   caf_schema=dict(file=os.path.basename(a.schema), md5=hashlib.md5(open(a.schema, 'rb').read()).hexdigest()),
                   n_upstream_score_inputs=sum(1 for i in inputs if i['kind'] == 'upstream_score'),
                   n_missing_from_schema=sum(1 for i in inputs if not i['in_schema']),
                   inputs=inputs)
        path = os.path.join(a.out_dir, '%s_inputs_v0.json' % model)
        with open(path, 'w') as f:
            json.dump(out, f, indent=1, sort_keys=False)
            f.write('\n')
        print('%-22s %3d inputs  upstream-score %2d  missing-from-schema %d  -> %s' % (
            model, out['n_inputs'], out['n_upstream_score_inputs'], out['n_missing_from_schema'], path))


if __name__ == '__main__':
    main()
