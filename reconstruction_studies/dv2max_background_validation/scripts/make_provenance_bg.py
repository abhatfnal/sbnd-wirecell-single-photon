#!/usr/bin/env python3
"""Write W/tables/build_provenance.csv for the DV2-MAX x SP background validation.

Re-hashes NOW every file whose sha256 the signal study recorded (SIGW/tables/build_provenance.csv: libraries, DV2
bundle, integration sources, Python wheels, lib_lightgbm) and compares: any DIFFERENT row = binaries differ from the
signal study = STOP condition.  Adds the ARM F (frozen Fix2-v2) control stack, configs, scorer, analysis scripts,
input files and PBS jobs of this study.  Read-only on SIGW / CAND / FIX2.
"""
import csv, hashlib, os, glob, sys

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102"
SIGW = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102"
CAND = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930"
FIX2 = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005"
CFGF = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/"
        "reco-bundle-id-fix-validation-20260916/config-final")
ANA = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/analysis/microboone_1gamma_v0"
REPO_SCORER = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/repos/sbnd-wirecell-single-photon/analysis/microboone_1gamma_v0/score_microboone_bdts.py"
JOBS = sys.argv[1] if len(sys.argv) > 1 else ""


def h(p, algo="sha256"):
    x = hashlib.new(algo)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            x.update(b)
    return x.hexdigest()


rows = []


def add(cat, item, value, signal_value="", status="", note=""):
    rows.append(dict(category=cat, item=item, value=value, signal_value=signal_value, status=status, note=note))


# 1. every hashed signal-study artefact, re-hashed now
sig = list(csv.DictReader(open(f"{SIGW}/tables/build_provenance.csv")))
n_diff = 0
for r in sig:
    cat, item, val = r["category"], r["item"], r["value"]
    if cat in ("library sha256", "DV2 bundle sha256"):
        p = item.replace("W/", SIGW + "/", 1) if item.startswith("W/") else item
    elif cat == "source sha256":
        p = f"{SIGW}/source/wct-int/{item}"
    elif cat == "python wheel sha256":
        c = glob.glob(f"{SIGW}/build/pyenv/wheels/{item}") + glob.glob(f"{SIGW}/build/pyenv/src/{item}")
        p = c[0] if c else ""
    elif cat == "python" and item.startswith("lib_lightgbm.so (in use)"):
        p = f"{SIGW}/build/pyenv/site39/lightgbm/lib/lib_lightgbm.so"
    elif cat == "python" and item.startswith("lib_lightgbm.so (wheel"):
        p = f"{SIGW}/build/pyenv/site39/lightgbm/lib/lib_lightgbm.so.wheel_manylinux_2_28"
    else:
        continue
    now = h(p) if p and os.path.isfile(p) else "MISSING"
    st = "IDENTICAL" if now == val else "DIFFERENT"
    n_diff += st != "IDENTICAL"
    add(cat, item, now, val, st, "ARM O/D stack (used read-only from SIGW)")

md5file = open(f"{SIGW}/build/validation/libWireCellClus.so.md5").read().strip()
now = h(f"{SIGW}/build/install/wct/lib/libWireCellClus.so", "md5")
add("guard", "ARM O/D libWireCellClus.so md5", now, md5file, "IDENTICAL" if now == md5file else "DIFFERENT",
    "run_bg_template.sh refuses to run unless md5 == 927a1834af1e44dfef3467dcc6e53976")
n_diff += now != md5file

# 2. configs (byte-identical copies) and compiled configs
for line in open(f"{W}/configs/signal_config_md5.txt"):
    m, f = line.split()
    a, b = h(f"{W}/configs/{f}", "md5"), h(f"{SIGW}/config/{f}", "md5")
    st = "IDENTICAL" if a == b == m else "DIFFERENT"
    n_diff += st != "IDENTICAL"
    add("config md5", f, a, b, st, "W/configs copy vs SIGW/config")
for f in ("armO.json", "armD.json"):
    a, b = h(f"{W}/configs/compiled/{f}", "md5"), h(f"{W}/configs/signal_compiled/{f}", "md5")
    st = "IDENTICAL" if a == b else "DIFFERENT"
    n_diff += st != "IDENTICAL"
    add("compiled config md5", f, a, b, st, "compiled here vs compiled in the signal study")

# 3. ARM F control stack (frozen Fix2-v2), recorded (no signal-study counterpart except the reference md5)
p = f"{FIX2}/build/libWireCellClus.so"
add("ARM F stack", p, h(p, "md5"), "9cff76d0d81a4b6c45a88908e78e73e4",
    "IDENTICAL" if h(p, "md5") == "9cff76d0d81a4b6c45a88908e78e73e4" else "DIFFERENT", "frozen Fix2-v2 libWireCellClus.so (md5)")
for p in sorted(glob.glob(f"{CAND}/install/wct-clean/lib/*.so")) + sorted(glob.glob(f"{CAND}/build/lwc-install-clean/lib/*.so")):
    add("ARM F stack sha256", p.replace(CAND + "/", "CAND/"), h(p), "", "", "read-only")
add("ARM F stack", "config dir", CFGF, "", "", "WIRECELL_PATH = SNAPSHOT:config-final:CAND/config/sce-override:CAND/wct/cfg")

# 4. scorer / BDT weights / analysis code
a, b = h(f"{ANA}/score_microboone_bdts.py", "md5"), h(REPO_SCORER, "md5")
add("scorer", "score_microboone_bdts.py", a, b, "IDENTICAL" if a == b else "DIFFERENT", "analysis dir vs repo copy; run unchanged except N_EVENTS/BASEDIR/OUTDIR substitution")
_ns = {"__file__": f"{ANA}/score_microboone_bdts.py", "__name__": "scorer_paths"}
_src = open(f"{ANA}/score_microboone_bdts.py").read()
exec(_src[:_src.index("XML_PATHS")] + _src[_src.index("XML_PATHS"):].split("}\n", 1)[0] + "}\n", _ns)
for k, p in _ns["XML_PATHS"].items():
    add("BDT weights sha256", f"{k}: {p}", h(p), "", "", "as read by the scorer (XML_PATHS)")
for p in sorted(glob.glob(f"{W}/scripts/*.py") + glob.glob(f"{W}/scripts/*.sh") + glob.glob(f"{W}/scripts/*.pbs")
                + glob.glob(f"{W}/scripts/analysis/*.py")):
    add("study script sha256", p.replace(W + "/", "W/"), h(p))
for p in (f"{SIGW}/scripts/analysis/run_dv2.py", f"{SIGW}/scripts/analysis/ab_lib.py"):
    add("signal analysis (exec'd read-only)", p.replace(SIGW + "/", "SIGW/"), h(p))

# 5. inputs
for rs in ("numucc", "ncpi0"):
    ev = list(csv.DictReader(open(f"{W}/inputs/{rs}_events.csv")))
    files = sorted({r["source_file"] for r in ev})
    tot = sum(os.path.getsize(f) for f in files)
    add("input", f"{rs}_events.csv", h(f"{W}/inputs/{rs}_events.csv"), "", "",
        f"{len(ev)} events from {len(files)} Reco1 files ({tot / 1e9:.2f} GB); file list sha256 below")
    add("input", f"{rs} Reco1 file list sha256", hashlib.sha256("\n".join(files).encode()).hexdigest())
add("input", "truth census", h(f"{W}/inputs/stageA10k_truth_events.csv"), "", "", "inputs/stageA10k_truth_events.csv (10000 rows)")

# 6. runtime
add("runtime", "container", "/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif + larsoft-v10_14_02.squashfs + sbnd-v10_14_02_04_delta.squashfs", "", "", "same as the signal study")
add("runtime", "env", "/lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env", "", "", "same as the signal study")
add("runtime", "lar command", "lar --nskip NSKIP -n 1 -c wcls-img-clus-matching-xin-prod.fcl -s INFILE --no-output", "", "", "DV2_STRICT=1, LD_PRELOAD libpython3.9 (O/D)")
if JOBS:
    for j in JOBS.split("|"):
        k, v = j.split("=", 1)
        add("PBS job", k, v)

with open(f"{W}/tables/build_provenance.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["category", "item", "value", "signal_value", "status", "note"])
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows;", n_diff, "DIFFERENT")
sys.exit(1 if n_diff else 0)
