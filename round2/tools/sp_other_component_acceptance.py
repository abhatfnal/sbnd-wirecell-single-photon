#!/usr/bin/env python3
"""SP other: background acceptance PER NEGATIVE COMPONENT on the development holdout rows (diagnostic; no training).

  python sp_other_component_acceptance.py --bundle-root LEGACY --tag dev --out-json OUT.json \
      --tables-template $SP_WORK/wcl1116_dev_tables/%s --spec-template specs/single_photon_other_training_spec_dev_wcl1116_%s.yaml \
      --model-dir-template $SP_WORK/wcl1116_dev_models/%s/other --legacy-dir-template $SP_WORK/wcl1116_legacy_controls/%s/other

The legacy XML at its historical cut (0.2) and the development model at the ROC-equivalent threshold of the legacy
control (point A: equal signal efficiency, read from legacy_vs_dev.json), on the identical holdout rows.
DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC -- NOT ROUND2 CUT.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devtrain, features, labels, legacy_control as lc  # noqa: E402
from legacy_control_compare import load_cands  # noqa: E402
from sp_other_census import component  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--bundle-root', '--tag', '--out-json', '--tables-template', '--spec-template', '--model-dir-template', '--legacy-dir-template'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    out = dict(label='DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC -- NOT ROUND2 CUT (SP other, per negative component, holdout rows)', modes={})
    for mode in ('dv2_split_move', 'dv2_snap'):
        spec = labels.load_spec(os.path.join(ROUND2, a.spec_template % mode)); devtrain.require_development_spec(spec)
        fl = features.load('single_photon_other'); cols = fl.columns
        C = load_cands(a.tables_template % mode, a.tag, spec, [])
        ds = devtrain.build_dataset(C, spec)
        te = (ds['keys'].split == 'test').to_numpy()
        keys = ds['keys'][te].reset_index(drop=True); X = ds['X'][te]; y = ds['y'][te]
        st = pd.read_parquet(os.path.join(a.model_dir_template % mode, 'margins_test.parquet'))
        if not keys[devtrain.ROW_KEY].equals(st[devtrain.ROW_KEY].reset_index(drop=True)):
            raise SystemExit('holdout rows differ from the stored development rows')
        lv = json.load(open(os.path.join(a.legacy_dir_template % mode, 'legacy_vs_dev.json')))
        tA = lv['point_A_same_signal_efficiency']['new_threshold_native_margin']
        forest = lc.load_control(a.bundle_root, 'single_photon_other', fl.names)
        s_leg = lc.legacy_score(forest, lc.legacy_matrix(X, cols, 'single_photon_other'))[1]
        m = st.margin.to_numpy()
        R = keys.merge(C.drop_duplicates(devtrain.ROW_KEY), on=devtrain.ROW_KEY, how='left')
        cls = np.where(y == 1, 1, 0)
        ext = R['sample'].astype(str).isin(labels.ext_sample_ids(spec)).to_numpy()
        comp = component(R, cls, ext)
        per = {}
        for cc in ('signal', 'nc_no_pi0', 'dirt', 'out_of_fv_in_tpc', 'cosmic_matched_mc', 'beam_off_ext'):
            q = comp == cc
            per[cc] = dict(rows=int(q.sum()), legacy_pass=float((s_leg[q] > lc.LEGACY_CUT['single_photon_other']).mean()) if q.any() else None,
                           dev_pass_at_point_A=float((m[q] > tA).mean()) if q.any() else None)
        out['modes'][mode] = dict(point_A_threshold_native_margin=tA, legacy_cut=lc.LEGACY_CUT['single_photon_other'], components=per)
        print(mode, json.dumps(per))
    json.dump(out, open(a.out_json, 'w'), indent=1)


if __name__ == '__main__':
    main()
