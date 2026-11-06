# EAF quickstart (NC Δ → Nγ baseline framework)

Works on the Fermilab EAF notebook image (AlmaLinux 9). `/pnfs` is NOT mounted; dCache is read over XRootD.
No credentials are stored in this repository.

## 1. Environment

Dedicated conda env (Python 3.11; uproot, awkward, numpy, pandas, scipy, matplotlib, hist, vector, scikit-learn,
xrootd, fsspec, fsspec-xrootd, pyyaml, pytest, pyarrow; lightgbm/xgboost installed for *later* use, no training in the baseline):

```
/exp/sbnd/data/users/abhat/envs/sp-ncdelta
```

> It lives under `/exp/sbnd/data/...`, **not** `/exp/sbnd/app/...` as first planned: the app area has a hard 60 GiB CephFS quota and
> was already full (`getfattr -n ceph.quota.max_bytes /exp/sbnd/app/users/abhat`), so env creation failed there with "Disk quota exceeded".
> The data area has a 16 TiB quota.

Recreate it (only if missing; the package cache MUST be on local disk, extraction on CephFS crashed mamba):

```bash
# exact command used to build it (mamba 2.9.0 from /opt/pixi/.pixi/envs/default/bin)
export CONDA_PKGS_DIRS=/tmp/sp_pkgs CONDA_SSL_VERIFY=true
mamba create -y -p /exp/sbnd/data/users/abhat/envs/sp-ncdelta --override-channels -c conda-forge --strict-channel-priority \
      python=3.11 uproot awkward numpy pandas scipy matplotlib hist vector scikit-learn xrootd fsspec fsspec-xrootd \
      lightgbm xgboost pyyaml pytest pyarrow
# declarative record: env/eaf-environment.yml ; exact solved versions: env/eaf-environment.lock.txt
```

Your `~/.condarc` points `pkgs_dirs`/`envs_dirs` at `/scratch/7DayLifetime/...` and sets `ssl_verify: false`; the command above overrides
those through environment variables and `-p`, and the user config was not modified.

Activate for a shell (sets `PATH`, `PYTHONPATH=src`, `XRD_NETWORKSTACK=IPv4`, scratch and data dirs; checks the token):

```bash
cd ~/Single-photon/sbnd-wirecell-single-photon
source env/setup_eaf.sh
```

HOME is small (32 GB, ~75 % used): keep data, caches and derived files out of it. Scratch: `$SP_SCRATCH` (`/tmp/$USER/sp_cache`, local and
ephemeral). Persistent derived output: `$SP_DATA` (`/exp/sbnd/data/users/abhat/single_photon_ncdelta`).

## 2. Token

```bash
htgettoken -a htvaultprod.fnal.gov -i sbnd      # interactive; writes the bearer token file
echo "$BEARER_TOKEN_FILE"; test -s "$BEARER_TOKEN_FILE" && echo "token present"    # never print the contents
```

The token expires within hours; renew it before long jobs. Read access to `/sbnd` is enough for everything here.

## 3. XRootD

```bash
export XRD_NETWORKSTACK=IPv4                    # done by setup_eaf.sh
xrdfs root://fndcadoor.fnal.gov ls /pnfs/fnal.gov/usr/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/lists
```

The prepared lists store `/pnfs/sbnd/...`; the door needs `/pnfs/fnal.gov/usr/sbnd/...`. `sbnd_single_photon.xrd.to_xrootd_url` does the conversion.
`xroots://fndcadoor.fnal.gov:1094` also works.

## 4. Manifests

```bash
python scripts/make_manifests.py            # re-fetches the 4 lists over XRootD -> manifests/*.tsv.gz (original order)
```

## 5. Smoke test (read-only, ~1000 events per sample, a few minutes)

```bash
python scripts/smoke_test.py --events 1000   # writes tables/smoke/*, plots/smoke/*  (software validation, NOT physics)
```

## 6. Exposure scan (read-only; ~1-2 h for all four samples with 20 workers)

```bash
python scripts/exposure_scan.py beam_off beam_on_open nuecc bnb_cv --workers 20 --out $SP_DATA/exposure_scan
```

Uses `spawn` multiprocessing (XRootD clients are not fork-safe); writes per-file rows to `$SP_DATA/exposure_scan/<sample>.jsonl` and small
summaries to `tables/pot/`.

## 7. Tests

```bash
python -m pytest tests -q                    # includes one tiny remote read; it is skipped without a bearer token
```

## 8. Reading a CAF interactively

```python
from sbnd_single_photon import samples as S, caf as C
reg = S.load_samples()
url = S.manifest_urls(reg["bnb_cv"], 0, 1)[0]
with C.MergedCaf(url) as f:                                     # only requested branches are read
    d = f.read(wc=["wc.T_tagger.shw_sp_n_20mev_showers"], stop=100)
    valid = f.read_valid(stop=100)                              # wc.valid == 1
    pdg = f.read_nested("wc.T_kine.kine_particle_type", 0, 100) # [event][candidate][particle]
```

## 9. Full baseline pipeline (added)

```bash
source env/setup_eaf.sh                                   # needs an UNEXPIRED token (htgettoken -a htvaultprod.fnal.gov -i sbnd)
python scripts/baseline_scan.py bnb_cv --workers 24       # resumable; one npz per file in $SP_DATA/baseline_scan/<sample> (~36 min for CV)
python scripts/baseline_report.py bnb_cv                  # tables/baseline/*  (nueCC: rates suppressed; add --allow-rates only deliberately)
python scripts/truth_match_scan.py bnb_cv --workers 8 --limit 12000   # MC truth matching (evaluation only), $SP_DATA/truth_match
python scripts/truth_audit_report.py bnb_cv               # tables/proton_audit, tables/candidate_policy, plots/proton_audit
python scripts/truth_taxonomy_audit.py bnb_cv
python scripts/bdt_evaluability_report.py bnb_cv nuecc beam_off beam_on_open
python scripts/shape_plots.py                             # SHAPE ONLY plots in plots/baseline_shapes
```

Do not chain a `pkill -f` whose pattern also appears in your own command line (it kills the shell). The `official_gen2_ncdelta` sample: its official reco1/flatCAF files exist, are listed in SAM and are readable from EAF (section 10); only its Wire-Cell merged-CAF production is pending, so the merged-CAF scripts above do not read it.

## 10. SAM (samweb) from EAF — no gpVM needed

`samweb` is the UPS product `sam_web_client` in the SBND CVMFS tree. It does **not** need a gpVM, a pip install, or a change to the conda environment:

```bash
kinit <user>@FNAL.GOV                                                 # Kerberos ticket (once per session)
source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh    # prints a harmless "Product 'mrb' has no current chain"
setup sam_web_client
samweb -e sbnd server-info                                            # -e sbnd is required; shows "Authenticated username"
samweb -e sbnd list-definition-files <definition> --summary
samweb -e sbnd list-file-locations --dim "defname: <definition>"      # one location per file, in one call
samweb -e sbnd get-metadata --json <file> [<file> ...]                # bulk; mc.pot, event_count, parents, fcl, version
samweb -e sbnd file-lineage parents <file>
```

Do this in a **separate subshell** from the conda analysis shell. In a clean shell the `setup` function is not defined until the Fermilab bootstrap is sourced (`source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setups.sh`), so the repository provides a wrapper that does all of it in an `env -i` subshell and touches nothing else:

```bash
env/sam_eaf.sh server-info
env/sam_eaf.sh list-definition-files aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_ncdeltarad_v10_14_02_05_flat_caf_sbnd --summary
```

SAM locations of the official Gen2 samples are under `/pnfs/sbn/data_add/...` (**`sbn`**, not `sbnd`). `/pnfs` need not be mounted: `xrd.to_xrootd_url(path)` maps `/pnfs/sbn/x` to `root://fndcadoor.fnal.gov//pnfs/fnal.gov/usr/sbn/x`, which opens with the same bearer token (`source env/setup_eaf.sh`). SAM is used read-only; never create or modify definitions from here. Large file lists go under `$SP_DATA/sam/`, not into Git.

Official NC-Delta truth census: `python scripts/official_ncdelta_truth_scan.py scan --workers 24` (≈ 18 min, 15,777 files), `... merge`, `python scripts/official_ncdelta_census_report.py` (see `NCDELTA_GENERATOR_FILTER_AUDIT.md` §4-§5).
