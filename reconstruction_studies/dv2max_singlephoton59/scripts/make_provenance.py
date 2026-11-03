#!/usr/bin/env python3
"""Write W/tables/build_provenance.csv: sources, commits, patch, build recipe, library / bundle / Python hashes."""
import csv, hashlib, os, subprocess, glob

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102"
CAND = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930"
FIX2 = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/fix2_vertex_shower_onehop_20261005"
REPO = f"{W}/repos/wct-dv2"
INT = f"{W}/source/wct-int"


def sh(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True).stdout.strip()


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


rows = []
add = lambda cat, item, value, note="": rows.append({"category": cat, "item": item, "value": value, "note": note})

add("repo", "clone", REPO, "fresh clone in W/repos (git 2.52 on the login node)")
add("repo", "remote origin", sh("git remote get-url origin", REPO))
add("repo", "remote dsnehadri", sh("git remote get-url dsnehadri", REPO), "fetched read-only; never pushed / reset")
add("repo", "PR branch", "dsnehadri/dv2-max-vertexer = origin/pr543")
add("repo", "PR head", sh("git rev-parse dsnehadri/dv2-max-vertexer", REPO))
add("repo", "PR merge-base with master", sh("git merge-base dsnehadri/dv2-max-vertexer origin/master", REPO))
add("repo", "origin/master head at fetch", sh("git rev-parse origin/master", REPO))
add("repo", "PR commits (base..head)", " ".join(sh("git log --format=%h --reverse b7bd2a1a..feb3ddeb", REPO).split()))
add("repo", "SP branch head (read-only ref)", sh("git rev-parse sp/onehop", REPO), "feature/sbnd-singlephoton-onehop-20261005")
add("repo", "SP base on master", sh("git merge-base sp/onehop origin/master", REPO))
add("source", "integration tree", INT, "git worktree, detached at feb3ddeb; NOT committed")
add("source", "integration HEAD", sh("git rev-parse HEAD", INT))
add("source", "integration status", sh("git status --short", INT).replace("\n", " | "))
add("source", "PATCH.diff", f"{W}/source/PATCH.diff", f"sha256 {sha(W + '/source/PATCH.diff')}")
add("source", "version.txt", open(f"{INT}/version.txt").read().strip(),
    "container git 1.8 cannot read a worktree; value = host `git describe --tags` + suffix (build metadata only)")
for f in sh("git diff --name-only feb3ddeb", INT).split() + ["clus/test/doctest_matching_bundle_provenance.cxx"]:
    add("source sha256", f, sha(f"{INT}/{f}"))
add("build", "container", "/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif + larsoft-v10_14_02.squashfs + sbnd-v10_14_02_04_delta.squashfs", "same as frozen Fix2-v2 runs")
add("build", "env", "/lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env", "same as frozen")
add("build", "WCT recipe", f"{W}/scripts/build_wct.sh", "= CAND run_candidate_clean_wct_build.sh + --with-python-include/lib/libs (larsoft python v3_9_15)")
add("build", "larwirecell recipe", f"{W}/scripts/build_lwc.sh", "= CAND run_candidate_clean_lwc_build.sh, paths redirected; 3 logging pipes '|| true'")
add("build", "larwirecell source", f"{CAND}/larwirecell-src", "read-only; HEAD 9295e2a3 per CAND dependency gate (not a git checkout)")
add("build", "lightgbm recipe", f"{W}/scripts/build_lightgbm.sh", "lib_lightgbm.so 4.6.0 rebuilt in-container from the PyPI sdist")
add("build", "PBS jobs", "200899 (lightgbm cp -p fail), 200900 (lightgbm PASS; wct: no version.txt), 200901 (wct PASS; lwc SIGPIPE in a logging pipe), 200903 (lwc PASS; verify G5/G6 FAIL: larsoft libtorch shadowing), 200904 (verify 6/6 PASS)", "scripts/build_all.pbs")
add("build", "BuildConfig.h", sh(f"grep HAVE_PYTHON {W}/build/wct-build/WireCellUtil/BuildConfig.h").replace("\n", " | "))
for p in sorted(glob.glob(f"{W}/build/install/wct/lib/*.so")) + sorted(glob.glob(f"{W}/build/lwc-install/lib/*.so")):
    add("library sha256", p.replace(W + "/", "W/"), sha(p), f"md5 {md5(p)}")
add("reference", "frozen Fix2-v2 libWireCellClus.so", f"{FIX2}/build/libWireCellClus.so", f"md5 {md5(FIX2 + '/build/libWireCellClus.so')} (expected 9cff76d0d81a4b6c45a88908e78e73e4)")
B = f"{INT}/cfg/dv2max/r7_cloud"
for p in sorted(glob.glob(B + "/*")):
    add("DV2 bundle sha256", p.replace(W + "/", "W/"), sha(p))
S = f"{W}/build/pyenv"
for p in sorted(glob.glob(S + "/wheels/*.whl")) + sorted(glob.glob(S + "/src/*.tar.gz")):
    add("python wheel sha256", os.path.basename(p), sha(p))
add("python", "site", f"{S}/site39", "pip --target, cp39; PYTHONPATH first entry in the lar job")
add("python", "lib_lightgbm.so (in use)", sha(f"{S}/site39/lightgbm/lib/lib_lightgbm.so"), "container build (max GLIBC_2.14)")
add("python", "lib_lightgbm.so (wheel, kept)", sha(f"{S}/site39/lightgbm/lib/lib_lightgbm.so.wheel_manylinux_2_28"), "needs logf@GLIBC_2.27 -> unusable in slf7")
add("runtime", "LD_LIBRARY_PATH edit", "larsoft libtorch/v2_1_1b/lib removed (both arms)",
    "LD_LIBRARY_PATH beats the torch wheel RUNPATH $ORIGIN; larsoft libtorch is never initialized by this job (smoke LD_DEBUG: 0 inits)")
add("runtime", "smoke run", "ARM D evt 18, RUNSET=smoke, PBS 200905", "lar exit 0; 1 DV2 call, 1 prediction, placement INFO present, 0 fallback/exception lines")
add("runtime", "sentinel runs", "PBS 200906: events 18 0 2 58 20, arms O and D", "all lar exit 0")
add("runtime", "full runs", "PBS 200907 / 200908 / 200909 (18 events x O,D each) + 200928 (rerun D:53 D:55 O:56 D:56)",
    "200907/200908 got SIGTERM (Exit_status 143) at 19:18 UTC the instant co-resident 200909 (same node sophia-gpu-09) "
    "ended; partial D53/D55 outputs moved to W/scratch/killed_sigterm_200907_200908 (not deleted); 200928 reran the 4 "
    "unfinished runs; final: 59/59 lar exit 0 in both arms")
add("python", "interpreter", "larsoft python v3_9_15 (PYTHONHOME from the sbndcode env); libpython3.9.so.1.0 LD_PRELOADed in both arms")
for k in ("dv2_py_smoke_container.txt", "dv2_cxx_smoke_container.txt"):
    p = f"{W}/build/validation/{k}"
    if os.path.isfile(p):
        add("gate evidence", k, open(p).read().strip().splitlines()[-1][:300])
with open(f"{W}/tables/build_provenance.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["category", "item", "value", "note"])
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows")
