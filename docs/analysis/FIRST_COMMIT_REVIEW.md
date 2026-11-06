# First-commit review (NOTHING HAS BEEN COMMITTED OR PUSHED)

Branch `analysis/ncdelta-1g0p-1g1p-baseline-20261105` (from `main` @ `615fe56`). No tracked file is modified; everything below is new/untracked.

## 1. Proposed for the first commit

**Code and configuration (commit):**
- `src/sbnd_single_photon/__init__.py`
- `src/sbnd_single_photon/baseline.py`
- `src/sbnd_single_photon/bdt.py`
- `src/sbnd_single_photon/caf.py`
- `src/sbnd_single_photon/exposure.py`
- `src/sbnd_single_photon/plots.py`
- `src/sbnd_single_photon/proton.py`
- `src/sbnd_single_photon/samples.py`
- `src/sbnd_single_photon/scanio.py`
- `src/sbnd_single_photon/selection.py`
- `src/sbnd_single_photon/truth.py`
- `src/sbnd_single_photon/xrd.py`
- `tests/` (all `test_*.py` and `conftest.py`)
- `scripts/baseline_report.py`
- `scripts/baseline_scan.py`
- `scripts/bdt_evaluability_report.py`
- `scripts/exposure_scan.py`
- `scripts/make_manifests.py`
- `scripts/shape_plots.py`
- `scripts/smoke_test.py`
- `scripts/truth_audit_report.py`
- `scripts/truth_match_scan.py`
- `scripts/truth_taxonomy_audit.py`
- `scripts/vertex_sentinel_report.py`
- `configs/baseline_selection.yaml`
- `configs/control_plots.yaml`
- `configs/samples.yaml`
- `env/eaf-environment.lock.txt`
- `env/eaf-environment.yml`
- `env/setup_eaf.sh`

**Documentation (commit):** all 16 files of `docs/analysis/`, including this one.

**Manifests (commit, 1.3 MB):** `manifests/{bnb_cv,nuecc,beam_off,beam_on_open}.tsv.gz`: they pin the exact file lists (source-list sha256, original order) and are the reproducibility anchor; `scripts/make_manifests.py` regenerates them.

**Small tables (commit, ~75 KB):** `tables/baseline/`, `tables/proton_audit/`, `tables/candidate_policy/`, `tables/bdt_evaluability/`, `tables/vertex_sentinel/`, `tables/pot/`: the numbers quoted in the docs, small text files.

**Plots:** commit `plots/baseline_shapes/` (3 files, 320 KB) and `plots/proton_audit/` (1 file, 48 KB): cited by the docs. **Do not commit `plots/smoke/` (17 files, 422 KB) or `tables/smoke/` (48 KB):** software-validation output of the first 1000 events, superseded by the full scans and regenerable with `scripts/smoke_test.py`.

## 2. Must NOT be committed

- Everything under `/exp/sbnd/data/users/abhat/single_photon_ncdelta/`: `baseline_scan/<sample>/*.npz` (per-file candidate tables, four samples), `truth_match/bnb_cv/*.npz`, `exposure_scan/*.jsonl`, scan/report logs. Derived, large, regenerable; none is inside the repository.
- The environment `/exp/sbnd/data/users/abhat/envs/sp-ncdelta` (2.9 GB). `env/eaf-environment.lock.txt` (11 KB, text) is fine to commit.
- Caches: `__pycache__/`, `.pytest_cache/` (already covered by `.gitignore`), any `.ipynb_checkpoints/` (one stray copy of a doc, created by Jupyter, was removed).
- Credentials: none present (grep of `src`, `scripts`, `env`, `tests`, `configs`: only the words "bearer token" in comments, the test that checks token expiry without printing it, and a package name in the lock file). The token file lives in `/tmp` and is never copied.
- `baseline_v0/`, `jobs/`, DV2 material: untouched.

## 3. Review findings acted on in this pass

- Atomic writes (`.tmp.npz`, then rename) and one retry on transient XRootD errors in `baseline_scan.py` and `truth_match_scan.py`; `scanio.load_scan` skips half-written files; `baseline_report.py` records `completeness` (files and events vs the registry) and warns on an incomplete scan (all four scans are complete).
- Per-POT columns renamed `stored_per_1e20_genPOT` and suppressed (empty) for nueCC and for the data samples; the quantity is described as the POT-normalised neutrino-induced rate of the filtered sample (no cosmic-only component).
- Candidate choice uses only reconstructed quantities (`scanio.policy_mask`: `nu_index`, `flash_group`). MC truth is imported only by the audit/report scripts and `truth.py`, never by `selection.py` or `scanio.py`.
- No code reads `official_gen2_ncdelta` or `aurora_ncdelta_training` (`samples.manifest_urls` raises for them).
- Multiprocessing uses `spawn` with per-worker model loading; files are processed by manifest index and results do not depend on completion order.
- Known limits: `env/setup_eaf.sh` defaults point at this user's directories (overridable via `SP_ENV`, `SP_DATA`, `SP_SCRATCH`); `SP_BDT_WEIGHTS` defaults to the read-only MicroBooNE weights on `/exp/uboone`; `truth_audit_report.py`, `vertex_sentinel_report.py`, `shape_plots.py` and `bdt_evaluability_report.py` need `SP_DATA` (KeyError if unset); `truth_match_scan.py` cannot read file 8398 (DeserializationError, persistent).
- Static check: `python -m compileall` passes; no linter (ruff/flake8/pyflakes) is installed and none was added.

## 4. Test status

`python -m pytest tests -q`: **41 passed** (the remote read needs an unexpired bearer token and is skipped otherwise).

## 5. Unresolved (see `QUESTIONS_FOR_HAIWANG_HANYU.md`)

nueCC normalisation (rare-xsec filter/POT convention), beam-off scaling, candidate ordering/dedup in the production build, FV, 35 MeV threshold, leftover-shower proton rows, flash-time convention, and the Wire-Cell merged-CAF production of the (existing) official Gen2 NC-Δ sample.

## 6. Proposed commit message (do not run)

```
Add NC Delta -> N gamma 1g0p/1g1p baseline framework and BNB background baseline

Merged-CAF reader, offline MicroBooNE BDT scorer (no training), frozen
baseline selection (no FV), reco proton categories, first-pass BNB truth
taxonomy, resumable full-sample scans, candidate-policy / proton /
BDT-evaluability / vertex-sentinel / flash-time / FV / POT audits, manifests,
configs, EAF environment record and 41 tests.

Full official BNB CV baseline: 500,000 events, 499,899 wc.valid,
sum(TotalPOT)=2.7194e19, 649 selected (any) / 626 (first), a POT-normalised
neutrino-induced rate of the official filtered Gen2 CV sample (26.5% of
generated events stored, consistent with the 25% expected filter
efficiency); cosmic-only backgrounds must come from beam-off. Signal
evaluation awaits the Wire-Cell merged CAFs of the existing official Gen2
NC-Delta sample; Aurora samples are training/development only.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```
