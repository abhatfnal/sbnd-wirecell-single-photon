#!/usr/bin/env python3
"""Evidence that the nu_mu simulation dQ/dx correction reached EVERY simulation step-2 job and NO data job (final-domain contract,
route R1; docs/SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md).

The patched toolkit (UbooneNumuBDTScorer, numu_sim_dqdx_scale) logs one info line per step-2 job when k != 1:
    UbooneNumuBDTScorer: simulation dQ/dx scale <k> ...
The workflow (swp-wclocal step2.sh) passes the parameter whenever NUMU_SIM_DQDX_SCALE is set, and the toolkit jsonnet
(sbnd/clus.jsonnet) forces 1.0 unless reality == 'sim'; the C++ does not re-check. So the log census is the per-job proof:
  every simulation pass log has the line with the expected k, and every data pass log has none.
A simulation job without the line (a driver or a grid submission that did not forward the variable) is a FAILURE, as is a
data job with it.

Layout read (Aurora run_pair / swp-wclocal): RUNS/<unit>/run_pair.log ('... start <unit> <sim|data> ...') and
RUNS/<unit>/<pass>/all/wct.log[.gz] for every step-2 pass (pr = split-move, pr-dv2snap = snap).

  python tools/verify_sim_dqdx_logs.py --runs RUNS [--runs RUNS2 ...] --expect-k 1.071 --out RECORD.json
"""
import argparse, glob, gzip, hashlib, json, os, re, sys, time

LINE = re.compile(r'UbooneNumuBDTScorer: simulation dQ/dx scale ([0-9.eE+-]+)')
START = re.compile(r'\bstart (\S+) (sim|data)\b')


def reality(unit_dir):
    p = os.path.join(unit_dir, 'run_pair.log')
    if not os.path.exists(p):
        return None
    for l in open(p, errors='replace'):
        m = START.search(l)
        if m:
            return m.group(2)
    return None


def scan(path):
    op = gzip.open if path.endswith('.gz') else open
    ks = []
    with op(path, 'rt', errors='replace') as f:
        for l in f:
            m = LINE.search(l)
            if m:
                ks.append(float(m.group(1)))
    return ks


def verify(runs_dirs, expect_k):
    units, problems = [], []
    for rd in runs_dirs:
        for ud in sorted(d for d in glob.glob(os.path.join(rd, '*')) if os.path.isdir(d)):
            r = reality(ud)
            if r is None:
                continue
            logs = sorted(glob.glob(os.path.join(ud, '*', 'all', 'wct.log.gz')) + glob.glob(os.path.join(ud, '*', 'all', 'wct.log')))
            passes = []
            for lg in logs:
                ks = scan(lg)
                ok = (len(ks) >= 1 and all(abs(k - expect_k) < 1e-9 for k in ks)) if r == 'sim' else (len(ks) == 0)
                passes.append(dict(log=os.path.relpath(lg, rd), lines=len(ks), k=sorted(set(ks)), ok=ok))
                if not ok:
                    problems.append('%s %s: %s' % (r, os.path.relpath(lg, rd), 'no scale line' if r == 'sim' and not ks else 'k=%s' % sorted(set(ks))))
            if not logs:
                problems.append('%s %s: no step-2 log' % (r, os.path.basename(ud)))
            units.append(dict(unit=os.path.basename(ud), runs=rd, reality=r, passes=passes))
    sim = [p for u in units if u['reality'] == 'sim' for p in u['passes']]
    dat = [p for u in units if u['reality'] == 'data' for p in u['passes']]
    rec = dict(tool='verify_sim_dqdx_logs.py', expect_k=expect_k, runs=list(runs_dirs), created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               units=len(units), sim_units=sum(u['reality'] == 'sim' for u in units), data_units=sum(u['reality'] == 'data' for u in units),
               sim_logs_total=len(sim), sim_logs_with_scale=sum(p['lines'] >= 1 for p in sim), data_logs_total=len(dat), data_logs_with_scale=sum(p['lines'] >= 1 for p in dat),
               problems=problems, status='VERIFIED' if units and not problems else 'NOT_VERIFIED',
               verifier_sha256=hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(), detail=units)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--runs', action='append', required=True); ap.add_argument('--expect-k', type=float, required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rec = verify(a.runs, a.expect_k)
    json.dump(rec, open(a.out, 'w'), indent=1)
    print(json.dumps({k: rec[k] for k in ('status', 'units', 'sim_logs_total', 'sim_logs_with_scale', 'data_logs_total', 'data_logs_with_scale')}))
    sys.exit(0 if rec['status'] == 'VERIFIED' else 1)


if __name__ == '__main__':
    main()
