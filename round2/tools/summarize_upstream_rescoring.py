#!/usr/bin/env python3
"""Collect the offline upstream re-scoring evidence of both vertex modes into one committed JSON:
extraction merge records, builder equivalence, shipped final-model closure, NaN-object counts, numu_cc_flag copies,
the official-standalone vs chain-emulation comparison, and (if present) the official correction log counts.

  python tools/summarize_upstream_rescoring.py WORK_DIR OUT.json
"""
import json, os, re, sys

SAMPLES = ['wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb', 'wcl1116-aurora-nuecc', 'wcl1116-fg-beamoff-train']
MODES = ['dv2_split_move', 'dv2_snap']


def main():
    w, out = sys.argv[1], sys.argv[2]
    rep = dict(work=w, modes={})
    for m in MODES:
        R = {}
        for s in SAMPLES:
            mg = json.load(open(os.path.join(w, 'tables', m, 'merge_%s.json' % s)))
            eq = json.load(open(os.path.join(w, 'equiv', m, 'equiv_%s.json' % s)))
            rs = json.load(open(os.path.join(w, 'rescore', m, 'rescore_%s.json' % s)))
            cp = json.load(open(os.path.join(w, 'official', m, 'compare_%s.json' % s)))
            R[s] = dict(
                files=mg['files'], file_errors=mg['errors'], wct_versions=mg['wct_versions'], candidates=rs['candidates'],
                objects={x['kind'][5:]: x['rows'] for x in mg['slices'] if x['kind'].startswith('objs_')},
                builder_equivalence=dict(verdict=eq['verdict'], files=eq.get('xning_files'), candidates=eq['cands']['ours'], compared_columns=eq['cands']['compared_columns']),
                kind=rs['kind'], sim_scale_applied=rs['sim_scale_applied'], key_unique=rs['key_unique'],
                closure_shipped_final_models={c['score']: dict(exact=c['exact'], n=c['n'], max_abs=c['max_abs']) for c in rs['closure_shipped_final_models']},
                nan_objects=dict(numu=rs['nan_objects_r3af'], nue=rs['nan_objects_nueA2']),
                numu_cc_flag_bdt_turned_off=rs['numu_cc_flag_bdt_turned_off'],
                official_vs_emulation=dict(numu_rows=cp['numu_rows'], numu_level1={k: cp['numu_' + k] for k in ('numu_1', 'numu_2', 'cosmict_10')},
                                           numu_score=cp['numu_score'], nue_rows=cp['nue_rows'], nue_level1_worst=cp['nue_l1_worst'], nue_score=cp.get('nue_score')),
                weights=rs['weights'])
        corr = {}
        p = os.path.join(w, 'logs', 'official_correct_%s.log' % m)
        if os.path.exists(p):
            for l in open(p):
                mm = re.match(r'(\S+)\s+(\S+)\s+corrected\s+(\d+)\s+median factor (\S+)', l)
                if mm:
                    corr['%s:%s' % (mm.group(1), mm.group(2))] = dict(corrected=int(mm.group(3)), median_factor=mm.group(4))
                mm = re.match(r'cands_(\S+)\.parquet\s+numu_cc_flag off on (\d+) candidates \(flag_1 lost on (\d+)\)', l)
                if mm:
                    corr['numu_cc_flag_off:' + mm.group(1)] = dict(candidates=int(mm.group(2)), flag1_lost=int(mm.group(3)))
        rep['modes'][m] = dict(samples=R, official_correction=corr)
    ok = all(v['builder_equivalence']['verdict'] == 'IDENTICAL' and v['file_errors'] == 0 and v['key_unique'] and
             all(c['exact'] == c['n'] for c in v['closure_shipped_final_models'].values())
             for mm in rep['modes'].values() for v in mm['samples'].values())
    rep['verdict'] = 'OFFLINE_INPUTS_SUFFICIENT_AND_CLOSED' if ok else 'CHECK_FAILED'
    json.dump(rep, open(out, 'w'), indent=1)
    print(rep['verdict'])
    for m in MODES:
        for s in SAMPLES:
            v = rep['modes'][m]['samples'][s]; o = v['official_vs_emulation']
            print(m, s, v['candidates'], v['builder_equivalence']['verdict'], 'flagoff', v['numu_cc_flag_bdt_turned_off'],
                  'numu dis', o['numu_score']['pass_disagree'], 'max %.3g' % o['numu_score']['max_abs'],
                  'nueL1 %.2g' % o['nue_level1_worst'], 'nue dis', (o['nue_score'] or {}).get('pass_disagree'))


if __name__ == '__main__':
    main()
