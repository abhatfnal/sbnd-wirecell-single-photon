# SBND Wire-Cell Inclusive Single-Photon Selection: Tutorial

This tutorial covers the **current best pipeline** for the SBND Wire-Cell inclusive single-photon (1γ) analysis on Sophia/ALCF:
- how it is built;
- how to run it on one event or many;
- how to score and select the output.

It describes only the pipeline as validated on 2026-11-02. Commands are taken from the scripts that produced the validated results; each block names its source.

> **Check before use.** The reconstruction currently runs from a *temporary integration branch*: Wire-Cell master + the DV2-MAX PR + the single-photon delta. If PR #543 has been merged upstream by the time you read this, see §2.3 before building anything.

---

## 1. The pipeline at a glance

```
SBND Reco1 art file (MC)
   │  recob::Wire simtpc2d:dnnsp, recob::OpFlash opflashtpc0/1, MC truth
   ▼
Wire-Cell (lar + WireCellToolkit module, wcls-img-clus-matching-xin-prod.fcl)
   imaging → clustering → Q/L matching → pattern recognition (PR)
   ├─ main-neutrino-vertex placement: DV2-MAX neutrino vertexer (vertex_method=dv2_split_move)
   ├─ standard downstream clustering / direction / shower / PID reconstruction
   └─ single-photon tagger with Fix2-v2 one-hop shower association
   ▼
Wire-Cell outputs per event: tracking-pr.root (T_tagger, T_kine, ...), mabc.zip (Bee), logs
   ▼
Offline scorer (Python, login node): four MicroBooNE single-photon BDTs
   ▼
Pre-FV inclusive 1γ selection (cut flow)  →  0p / Np categorisation
```

Keep these four layers distinct:

| layer | what it is | where it lives |
|---|---|---|
| reconstruction code | C++/jsonnet in Wire-Cell Toolkit, including DV2-MAX and Fix2-v2 | `abhatfnal/wire-cell-toolkit`, branch `feature/sbnd-singlephoton-dv2-integration-20261102` |
| Wire-Cell output | `tracking-pr.root` per event, written by the lar job | your run area |
| offline BDT scoring | pure-Python TMVA evaluator of the four original MicroBooNE BDTs | `analysis/microboone_1gamma_v0/score_microboone_bdts.py` |
| physics selection | pre-FV cut sequence on BDT scores and shower counts, plus 0p/Np | `selection/microboone_single_photon_selection.yaml`; implemented in the scorer |

**Terminology.**
- **DV2-MAX** is a *neutrino vertexer*: a learned **main-neutrino-vertex placement method**. It decides where the neutrino vertex is, and therefore which cluster is the main cluster.
- It is **not** a clustering algorithm. Everything downstream of the vertex (clustering, shower building, PID) is the standard Wire-Cell code.

---

## 2. Where the code lives

### 2.1 Reconstruction (C++ / configuration)

| item | value |
|---|---|
| fork | `https://github.com/abhatfnal/wire-cell-toolkit` |
| integration branch | `feature/sbnd-singlephoton-dv2-integration-20261102` |
| integration commit | **`03c2d4997917990e0f55be7f5b12b36d99b3701b`**, "sbnd: integrate single-photon one-hop with DV2 vertexer" |
| its parent = DV2-MAX PR head | **`feb3ddeb6fea35f42e13c416d65520f22b5b0cbf`** (WireCell/wire-cell-toolkit PR #543, branch `dsnehadri/dv2-max-vertexer`) |
| DV2 PR commits | `43660339` DV2-MAX engine · `eb7636ae` Python inference + r7_cloud bundle · `b87ae37d` `vertex_method` option · `feb3ddeb` SBND default `dv2_split_move` |
| DV2 base (WCT master) | `b7bd2a1a5ca829c178706675223b3961024cc276` |

Commit `03c2d499` changes 6 files relative to the PR head:
- `clus/src/NeutrinoTaggerSinglePhoton.cxx` (Fix2-v2);
- `clus/inc/WireCellClus/MultiAlgBlobClustering.h`, `clus/src/MultiAlgBlobClustering.cxx`, `clus/src/clustering_switch_scope.cxx`, `clus/test/doctest_matching_bundle_provenance.cxx` (matching-bundle provenance stamp; output metadata only);
- `cfg/pgrapher/experiment/sbnd/clus.jsonnet` (8 lines exposing `stamp_matching_bundle_id`).

All six are byte-identical (sha256) to the sources the validated library was built from (`tables/build_provenance.csv` of the DV2 study).

### 2.2 Analysis, selection, provenance

`https://github.com/abhatfnal/sbnd-wirecell-single-photon`, local checkout `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/repos/sbnd-wirecell-single-photon/`.

It holds the offline scorer, TMVA validation, selection definition, cut flows, study reports, job/build scripts, provenance tables and this tutorial. It contains no reconstruction code, no ROOT/HDF5 event files and no compiled libraries.

### 2.3 Check before use

Conceptually the integration is **WCT master (b7bd2a1a) + DV2-MAX PR #543 + the single-photon delta (Fix2-v2 + provenance stamp)**.
- Once PR #543 is merged, the intended workflow is: **new upstream master (which contains DV2) + only the remaining single-photon delta.**
- Do not permanently depend on the temporary branch.

Before building, check:

```bash
git clone https://github.com/WireCell/wire-cell-toolkit.git wct && cd wct
git remote add avinay https://github.com/abhatfnal/wire-cell-toolkit.git
git remote add dsnehadri https://github.com/dsnehadri/wire-cell-toolkit.git
git fetch --all
git merge-base --is-ancestor feb3ddeb6fea35f42e13c416d65520f22b5b0cbf origin/master && echo "DV2 PR is in master"
git diff feb3ddeb 03c2d499 --stat        # the single-photon delta (6 files)
```

- **If the PR is not yet merged:** use `03c2d499` as is.
- **If it is merged:** apply the 6-file delta on the new master. Then re-run the controls in §11 and the comparison against the validated numbers (§16) before trusting results.

---

## 3. Software stack (validated)

| component | value |
|---|---|
| container | `/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif` (SL7, glibc 2.17) |
| LArSoft image | `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs` |
| SBND image | `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/sbnd-v10_14_02_04_delta.squashfs` |
| environment | `source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env` (inside the container) |
| releases | larsoft v10_14_02, sbndcode v10_14_02_04 |
| Wire-Cell Toolkit | `03c2d499`, built with embedded Python (larsoft python v3_9_15), so `HAVE_PYTHON_INC` is defined and `libWCPPyUtil.so` (`WCPPyUtil::DV2_Vertex`) is built |
| larwirecell | source tree at commit `9295e2a34c32b5f92ad6483b83dd4895a00b4c9b` (same source as before), **rebuilt** against the new WCT headers |
| DV2 Python stack | Python 3.9.15 (larsoft); torch 2.5.1+cpu, numpy 2.0.2, scipy 1.13.1, lightgbm 4.6.0 |
| DV2 model bundle | `cfg/dv2max/r7_cloud/bundle.json` (+ `pass1.pt`, `pass2.pt`, `ranker_fold0.txt`, `isotonic_fold0.json`), resolved through `WIRECELL_PATH` |

Notes on the stack:
- **Why larwirecell is rebuilt:** WCT master between the old baseline and the DV2 base adds a member (`m_dead_region`) to `Facade::Grouping`. A larwirecell binary built against the old headers cannot be assumed ABI-compatible.
- **`/lus/flare` paths:** the env file and the images refer to `/lus/flare/projects/neutrinoGPU/scisoft/...`. Those are paths **inside the squashfs images**. Do **not** bind the host `/lus/flare` on Sophia.

**Validated installation (reusable read-only).** These are the binaries that produced every validated number:

| item | path (DV2 study area `$SIGW` = `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102`) | check |
|---|---|---|
| WCT install | `$SIGW/build/install/wct` | `libWireCellClus.so` md5 `927a1834af1e44dfef3467dcc6e53976`; `libWCPPyUtil.so` md5 `cda46125fb700d4247e647cd1b79ba38` |
| larwirecell install | `$SIGW/build/lwc-install` | sha256 in `$SIGW/tables/build_provenance.csv` |
| Python site | `$SIGW/build/pyenv/site39` | wheel sha256 in `build_provenance.csv` |
| WCT cfg tree (incl. bundle) | `$SIGW/source/wct-int/cfg` | git worktree at `03c2d499` |
| run configuration | `$SIGW/config/{armD,armO,common,sce-override}` | md5 list in the DV2 study; §8 |

---

## 4. The NC-Δ radiative signal sample

**Signal predicate** (filter module `NCDeltaRadiative`):
- neutral-current (`CCNC == 1`), with GENIE restricted to `EventGeneratorList: "NCRES"`;
- a final-state photon (status 1, PDG 22) with Δ ancestry: mother Δ⁰ (2114) or Δ⁺ (2214), or photon-from-photon-from-Δ at depth 2;
- Δ vertex inside the TPC box |x| ≤ 210, |y| ≤ 210, −1 ≤ z ≤ 510 cm.

**Inputs**

| item | path / value |
|---|---|
| generator FCL | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/signal_mc/ncdelta/fcl/prodgenie_ncdelta_sbnd.fcl` (includes `prodgenie_nu_singleinteraction_tpc_sbnd.fcl`; `TopVolume: volTPCActive`; one interaction per event) |
| filter source | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/signal_mc/ncdelta/src/NCDeltaRadiative_module.cc`, sha256 `f8574e5fdf6d3f0d8794143aed31d2167ba592498fc50d61e2ff7e11e3f0c3e6` |
| flux | `/lus/grand/projects/neutrinoGPU/simulation_inputs/FluxFiles/gsimple_april07_baseline_*_redecay_wkaonwgh.root` (BNB, `simple_flux`, `DetectorLocation: MINOS-NearDet`) |
| per-batch FCLs | `.../single_photon/baseline_v0/ncdelta_50evt/jobs/gen/fcl/ncdelta_gen_batch_NN.fcl`: include the generator FCL; `maxEvents 1000`; `firstRun = 10·NN` (distinct RNG seeds and RSEs) |

**Processing chain** (job scripts under `.../single_photon/baseline_v0/ncdelta_50evt/jobs/`, all in the container above):

| stage | FCL | command (from the job scripts) | output |
|---|---|---|---|
| GEN (12 batches × 1000 NCRES) | `ncdelta_gen_batch_NN.fcl` | `lar -c ncdelta_gen_batch_NN.fcl -o gen/batch_NN/ncdelta_gen_batch_NN.root` (`gen/pbs_ncdelta_gen_batch.pbs`; it first compiles the filter with the image's g++ and prepends the build dir to `CET_PLUGIN_PATH`) | 59 accepted events in batches 03–12; batches 01–02 accepted 0 |
| G4 (per batch) | `standard_g4_sbnd.fcl` | `lar -c standard_g4_sbnd.fcl -s gen/batch_NN/... -o g4/batch_NN/ncdelta_g4_batch_NN.root` (`g4/pbs_ncdelta_g4_perbatch_array.pbs`, `qsub -J 3-12`) | — |
| G4 merge | `jobs/g4/fcl/ncdelta_g4_merge.fcl` | `lar -c ncdelta_g4_merge.fcl -s g4/batch_03/... … -s g4/batch_12/... -o g4/ncdelta_g4_merged.root` (`g4/pbs_ncdelta_g4_merge.pbs`) | 59 events |
| DetSim | `standard_detsim_sbnd_bothrois.fcl` | `lar -c standard_detsim_sbnd_bothrois.fcl -s g4/ncdelta_g4_merged.root -o detsim/ncdelta_detsim.root` (`detsim/pbs_ncdelta_detsim.pbs`) | — |
| Reco1 | `reco1_nosupera_sbnd.fcl` (`signal_mc/ncdelta/fcl/`: `standard_reco1_sbnd.fcl` with the supera analyzers removed) | `lar -c reco1_nosupera_sbnd.fcl -s detsim/ncdelta_detsim.root -o reco1/ncdelta_reco1.root` (`reco1/pbs_ncdelta_reco1.pbs`) | **59 events** |

Notes:
- G4 runs per batch: a single file mixing ten generator process names breaks G4 physics registration. Merge after G4.
- `bothrois` DetSim is used because Reco1 `gaushit` reads `simtpc2d:gauss`; Wire-Cell reads `simtpc2d:dnnsp`.
- Exit code 134 (abort in a destructor after the output file is closed) is a known pattern of these GEN/G4 jobs in this release. The scripts accept it when the output file is complete.

**The reference Reco1 file:** `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root`.
- It holds 59 events. The directory name `ncdelta_50evt` is historical.
- Entry *i* (0–58) is processed as `evt_000i`, with `lar --nskip i -n 1`.
- Generator truth per entry, in entry order: `.../single_photon/baseline_v0/ncdelta_50evt/tables/ncdelta_truth.csv`. For example, entry 20 is run 60, subrun 0, event 153.

---

## 5. Starting from an existing Reco1 file

**You do not need to regenerate GEN/G4/DetSim if you already have a compatible Reco1 file.** Compatible means the art file contains what the Wire-Cell job reads (from `wcls-img-clus-matching-xin-prod.fcl`):
- `recob::Wire` with tag `simtpc2d:dnnsp`, plus `simtpc2d:badmasks` and `simtpc2d:wienersummary`;
- `recob::OpFlash` `opflashtpc0` and `opflashtpc1`;
- MC truth for the truth labeler: generator `simb::MCTruth`, `largeant` `simb::MCParticle`, and SimEnergyDeposit(Lite).

The configuration is the **simulation** configuration (`reality: "sim"`). Data needs a different FCL and is out of scope here.

A quick check from the Sophia login node (system python3 has uproot):

```bash
python3 - <<'EOF'
import uproot, sys
t = uproot.open("/path/to/reco1.root")["Events"]
names = t.keys(recursive=False)
for want in ("recob::Wires_simtpc2d_dnnsp", "recob::OpFlashs_opflashtpc0_", "recob::OpFlashs_opflashtpc1_",
             "simb::MCTruths_generator", "simb::MCParticles_largeant"):
    print(want, any(n.startswith(want) for n in names))
print("entries:", t.num_entries)
EOF
```

If a product is missing or carries a different tag, check how the file was produced before you change any configuration.

---

## 6. What the DV2-MAX neutrino vertexer does

DV2-MAX (Snehadri's PR #543) replaces the **main-neutrino-vertex determination** inside Wire-Cell pattern recognition. The code is in `clus/src/NeutrinoVertexFinder.cxx` (`determine_overall_main_vertex_DL`), `clus/src/TaggerCheckNeutrino.cxx`, `pyutil/DV2_Vertex.{h,cxx}` and `pyutil/python/dv2max_vertexer/`.

**How it works:**
1. For each neutrino candidate, Wire-Cell builds a 3D point cloud: every PR-graph vertex, then the segment-interior trajectory-fit points of every cluster.
2. The cloud goes through embedded Python (`WCPPyUtil::DV2_Vertex` → `DV2_Vertex.py` → `dv2max_vertexer`: two torch CPU networks plus a LightGBM ranker).
3. The result is one point **P** (cm) and a calibrated score P(< 1 cm).

**`vertex_method` values** (`TaggerCheckNeutrino`):

| value | placement of the main vertex |
|---|---|
| `original` | the traditional chain (geometric vertex finding, `examine_main_vertices` / `check_switch_main_cluster` / `compare_main_vertices_global`, kink/junction snaps, `improve_vertex`, …) |
| `dv2_snap` | the nearest PR-graph vertex to P |
| `dv2_split` | the nearer of the nearest PR-graph vertex and the nearest segment-interior fit point; a fit point splits its segment there (`break_segment`) |
| **`dv2_split_move`** (current SBND choice) | the nearest PR-graph vertex if it is within **1.5 cm** of P (`kDv2MoveReuseDistCm`); otherwise as `dv2_split`. Then the vertex is **moved onto P** (`MyFCN::UpdateInfo`) and the cluster's trajectories and dQ/dx are refit |

What happens after placement:
- **Other clusters.** If the chosen vertex lies in another cluster, the main cluster is switched (a complete `swap_main_cluster`).
- **Traditional sequence bypassed.** Once DV2 accepts a point, the traditional main-vertex sequence is **not executed**. That covers `examine_main_vertices`, `check_switch_main_cluster`, `compare_main_vertices_global` and the `main_vertex_swap_apply`-gated swap, as well as the kink/junction snap, `improve_vertex`, the main-vertex graph audit and the conn3 stitch. For normal DV2 use you do not need to modify those algorithms.
- **Unchanged downstream.** Everything after the vertex is the standard chain: direction, shower clustering, PID, kinematics, taggers.
- **Fallback.** If DV2 returns no prediction, a WARN is printed and the **traditional vertex** is used, with its original refinement. A Python exception inside the DL step is **caught** by the C++, logged as `DL vertex failed`, and also falls back. That is why §11 is mandatory.

On the validated 59-event signal sample (57 candidates):
- every candidate had a prediction and a placement;
- placements: 53 "graph vertex", 4 "split";
- 43 vertices were moved onto P (median 0.275 cm);
- the main cluster was switched in 24 events.

---

## 7. What the single-photon Fix2-v2 one-hop association does

File: `clus/src/NeutrinoTaggerSinglePhoton.cxx`, function `PatternAlgorithms::singlephoton_tagger` (log prefix `fix2_v2:`).

**The algorithm:**
1. **Direct association first.** Take the showers attached to the selected main vertex (`map_vertex_to_shower[main_vertex]`).
   - If any of them is *usable*, the algorithm continues exactly as before. Usable means: the start segment is PDG 11, the energy is > 20 MeV, and it passes the existing `bad_reconstruction_sp` check.
2. **One-hop fallback, only if no direct shower is usable.**
   - Loop over **all** PR-graph edges incident on the main vertex, track-like or shower-like.
   - For each, take the vertex at the other end of the edge and add the showers mapped to that vertex.
3. **Deduplicate.** Candidates go into a `std::set`, so a shower is counted once.
4. **Unchanged downstream.** The union feeds the existing single-photon logic. The photon/shower criteria, `shw_sp_*` variables and BDT inputs are unchanged.

**What it does NOT do:**
- no radius/proximity search;
- no multi-hop graph traversal;
- no search of arbitrary clusters;
- no lower 20 MeV threshold;
- no relaxed PDG requirement;
- no BDT change.

It is **exactly one graph hop**.

**Why DV2 and Fix2 are complementary.** DV2 fixes *where* the neutrino vertex is and which cluster is main. Fix2 handles *local* photon association from that vertex, for example a conversion gap whose shower starts one graph edge away.
- On the signal sample, Fix2 is still what makes several DV2-corrected events accessible: 5 events are one-hop under DV2.
- DV2 does not make Fix2 obsolete. Keep it on.

---

## 8. Configuration for controlled use

**How the configuration is wired** (from `run_arm_template.sh` and the configs):

```
lar -c wcls-img-clus-matching-xin-prod.fcl
   physics.producers.sig2img (WireCellToolkit):
       configs: ["wcls-img-clus-matching-xin.jsonnet"]
       params:  reality=sim, img_config=active2view+masked2view, enable_tracking_root=true,
                enable_nugraph_h5=true, pr_operating_point=sync, opflash{0,1}_input_label=opflashtpc{0,1}:
       structs: recobwire_tags=["simtpc2d:dnnsp","simtpc2d:dnnsp"], summary_tags, input/output mask tags
   → wcls-img-clus-matching-xin.jsonnet:   local pr_sync = import 'pr-operating-point.jsonnet'
   → pr-operating-point.jsonnet (first match on WIRECELL_PATH = the armD or armO directory)
         clus_maker.pr(..., vertex_method=..., dl_weights='', tcn_knobs={...})
```

FCL `params` and `structs` are passed to jsonnet as external variables. No command-line TLAs are used.

**The two validated operating points:**

| | ARM D (preferred) | ARM O (control) |
|---|---|---|
| directory | `$SIGW/config/armD` | `$SIGW/config/armO` |
| `vertex_method` | `'dv2_split_move'` | `'original'` |
| `dl_weights` | `''` | `''` |
| `main_vertex_swap_apply` | not set (C++ default `false`) | not set |
| shared | `$SIGW/config/common`: the top-level FCL, the main jsonnet and `particle_dataset.jsonnet`; `$SIGW/config/sce-override`: `clus.jsonnet` with only the SCE map path changed from `/cvmfs/...` to the image-internal `/lus/flare/projects/neutrinoGPU/scisoft/larsoft/sbnd_data/v01_42_00/SCEoffsets/` | same |

The two `pr-operating-point.jsonnet` files differ in exactly one line (plus a comment). Compiled-config check (`$SIGW/docs/config_semantic_diff.txt`):
- ARM O vs ARM D differ only in `TaggerCheckNeutrino.vertex_method`, `TaggerCheckNeutrino.dv2_bundle` and the provenance string.

**Why `dl_weights=''`.** The PR's `clus.jsonnet` default is `dl_weights = uboone/scn_vtx/...pth`, the legacy MicroBooNE SCN vertex net.
- The reference (pre-DV2) build had no embedded Python, so that net never executed.
- The new build has Python. Leaving the weights set would make `vertex_method=original` run the SCN net, which is a different algorithm from the reference.
- `dl_weights=''` disables the legacy SCN path in both arms; `dv2_*` methods do not read `dl_weights`.

**Keep this configuration** unless a reviewed update says otherwise:
- `dv2_split_move`;
- `dl_weights=''`;
- no `main_vertex_swap_apply=true`, which is a diagnostic knob of the traditional path and was not adopted.

To verify a configuration before running, compile it with the study's checker (needs `_jsonnet`; a copy is in `$SIGW/build/pyenv/host_tools`). Run from your own scratch directory:

```bash
PYTHONPATH=$SIGW/build/pyenv/host_tools /usr/bin/python3 $SIGW/scripts/compile_cfg.py armD \
  "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data:$SIGW/config/armD:$SIGW/config/common:$SIGW/config/sce-override:$SIGW/source/wct-int/cfg"
grep -n "TaggerCheckNeutrino:pr .vertex_method\|TaggerCheckNeutrino:pr .dv2_bundle\|main_vertex_swap" armD.leaves.txt
```

The compiled `armD.json` must have md5 `9ca6613eb74f3f28d7691dfd22c5ba48`, and `armO.json` `5dd42fbe981f267debeb16a14c2f13e1`.

---

## 9. Building, or reusing, the code

### 9.1 Recommended: reuse the validated installation

To reproduce the validated results, use the read-only installation of §3. You need no build, and every number in §16 came from these binaries. The run scripts (§10) default to these paths.

### 9.2 Rebuilding from source

The validated recipe is `$SIGW/scripts/build_all.pbs`. It runs four steps in the container: `build_lightgbm.sh` → `build_wct.sh` → `build_lwc.sh` → `verify_build.sh`.

The scripts hard-code the study area in their first lines (`W=...`, `WCT_SRC=$W/source/wct-int`). To rebuild elsewhere:
- copy `scripts/` into your area;
- change `W=` and the source path;
- keep everything else.

They also use helper directories of the WCT migration build, read-only: `$CAND/config/clean-pkgconfig`, `clean-bzip2`, `clean-fmt-include`, and the larwirecell source `$CAND/larwirecell-src`, with `CAND=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930`.

1. **Source.**
   ```bash
   git clone https://github.com/abhatfnal/wire-cell-toolkit.git wct-src
   cd wct-src && git checkout 03c2d4997917990e0f55be7f5b12b36d99b3701b
   ```
   - If you build from a *git worktree*, write a `version.txt` first: the container's git 1.8 cannot read worktrees, and the WCT `wscript` falls back to `version.txt` (git-ignored).
2. **Python site for DV2.** The wheels used are kept in `$SIGW/build/pyenv/wheels` (sha256 in `build_provenance.csv`). They were installed on the login node with:
   ```bash
   cd <your>/build/pyenv
   /usr/bin/python3 -m pip install --no-deps --no-index --only-binary=:all: --python-version 39 \
     --platform linux_x86_64 --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 \
     --platform manylinux_2_28_x86_64 --platform any --implementation cp --target site39 wheels/*.whl
   ```
   - TODO: exact invocation not preserved in the inspected artifacts for the `pip download` step that fetched these wheels. Reuse the preserved wheel files, which match the hashes in `build_provenance.csv`.
   - The LightGBM wheel's `lib_lightgbm.so` needs glibc 2.27, so `build_lightgbm.sh` rebuilds it in the container from the 4.6.0 sdist (`$SIGW/build/pyenv/src/lightgbm-4.6.0.tar.gz`). torch 2.5.1 is the newest CPU build that runs on the container's glibc 2.17; DV2 needs torch ≥ 2.1.
3. **WCT** (`build_wct.sh`): `wcb configure` with the larsoft externals plus `--with-python-include="$PYTHON_INCLUDE" --with-python-lib="$PYTHON_LIB" --with-python-libs=python3.9`. The script fails unless `HAVE_PYTHON_INC` appears in `WireCellUtil/BuildConfig.h` and `pyutil` is built.
4. **larwirecell** (`build_lwc.sh`): the same 9295e2a3 source, cmake against the new WCT install.
5. **Gates** (`verify_build.sh`; all six must PASS):
   - G1 `HAVE_PYTHON_INC`;
   - G2 `WCPPyUtil::DV2_Vertex` exported;
   - G3 DV2, Fix2-v2 and provenance strings in `libWireCellClus.so`, and the library links `libWCPPyUtil`;
   - G4 `lib_lightgbm.so` loads under glibc 2.17;
   - G5 pure-Python DV2 inference on a synthetic cloud;
   - G6 the C++ bridge returns a point.

Submit with `qsub -v STEPS="lightgbm wct lwc verify" build_all.pbs`, after editing the paths.

---

## 10. Running one event

### 10.1 The validated command sequence

This is from `$SIGW/scripts/run_arm_batch.pbs` (host side) and `$SIGW/scripts/run_arm_template.sh` (in the container); for many events see *Scaling to Multiple Events*.

**Host side, inside a PBS job** (queue/account of the validated runs: `by-gpu`, `neutrinoGPU::wirecell_2026`):

```bash
module use /soft/modulefiles; module load spack-pe-base; module load apptainer
apptainer exec --fakeroot --bind /lus/eagle --bind /lus/grand \
    --overlay /lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs:ro \
    --overlay /lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/sbnd-v10_14_02_04_delta.squashfs:ro \
    /lus/grand/projects/neutrinoGPU/software/containers/slf7.sif \
    bash -lc "<the container-side commands below>"
```

**Container side:**

```bash
source /lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env
ORIG_PYTHONPATH="${PYTHONPATH:-}"
export LD_LIBRARY_PATH="$WCT/lib:$LWC/lib:$PYTHON_LIB:${LD_LIBRARY_PATH:-}"
# drop larsoft libtorch: LD_LIBRARY_PATH beats the torch wheel's RUNPATH ($ORIGIN)
export LD_LIBRARY_PATH="$(echo "${LD_LIBRARY_PATH:-}" | tr ':' '\n' | grep -v '/scisoft/larsoft/libtorch/' | grep -v '^$' | tr '\n' ':' | sed 's/:$//')"
export CET_PLUGIN_PATH="$LWC/lib:$WCT/lib:${CET_PLUGIN_PATH:-}"
export WIRECELL_PATH="$SNAPSHOT:$CFG/arm$ARM:$CFG/common:$CFG/sce-override:$WCT_CFG"
export FHICL_FILE_PATH="$CFG/common:${FHICL_FILE_PATH:-}"
cd "$OUTDIR"
env LD_PRELOAD="$PYTHON_LIB/libpython3.9.so.1.0" \
    PYTHONPATH="$SITE:$WCT/python:$ORIG_PYTHONPATH" \
    DV2_STRICT=1 DV2_HOOK_LOG="$OUTDIR/dv2_hook.jsonl" \
    lar --nskip "$EVENT" -n 1 \
        -c wcls-img-clus-matching-xin-prod.fcl \
        -s "$INPUT_RECO1" \
        --no-output \
        > "$LOGFILE" 2>&1
```

with

```bash
SIGW=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102
SNAPSHOT=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data   # wire/field/charge data
WCT=$SIGW/build/install/wct          LWC=$SIGW/build/lwc-install       SITE=$SIGW/build/pyenv/site39
WCT_CFG=$SIGW/source/wct-int/cfg     CFG=$SIGW/config
ARM=D        # D = vertex_method=dv2_split_move ; O = vertex_method=original (control)
# --- values YOU change ---
INPUT_RECO1=/abs/path/to/reco1.root  # compatible Reco1 art file (§5)
EVENT=0                              # 0-based entry index -> lar --nskip
OUTDIR=/abs/path/out/evt_0000        # one EMPTY directory per event (outputs are written to the cwd)
LOGFILE=$OUTDIR/lar.log
```

Why each setting is there:

| setting | reason |
|---|---|
| `LD_PRELOAD=…/libpython3.9.so.1.0` | Python extension modules (numpy, torch) need the interpreter's symbols globally visible inside `lar` |
| `PYTHONPATH=$SITE:$WCT/python` | `site39` provides torch/numpy/scipy/lightgbm; `$WCT/python` provides `DV2_Vertex.py` and `dv2max_vertexer` |
| larsoft `libtorch` removed from `LD_LIBRARY_PATH` | otherwise the torch wheel's `libtorch_python.so` binds larsoft's `libtorch_cpu.so` → `undefined symbol` (§18-B). The job never loads larsoft libtorch, so removing it changes nothing else |
| `WIRECELL_PATH` order | the arm directory must supply `pr-operating-point.jsonnet`; `common` supplies the main jsonnet; `sce-override` supplies the SCE map path; `$WCT_CFG` supplies the rest of `cfg/`, including `dv2max/r7_cloud/bundle.json` |
| `DV2_STRICT=1` | makes a Python error raise. The C++ still catches it and falls back, so check the log (§11) |
| `DV2_HOOK_LOG` | one JSON line per DV2 call (prediction, score, timing); used by the §11 gate |
| `-n 1 --nskip EVENT`, one directory per event | `tracking-pr.root` is written per lar process; more than one event per process corrupts it |
| `--no-output` | Wire-Cell writes its own files; no art output is needed |

### 10.2 The same thing as a ready-to-use wrapper

`docs/tutorial_assets/run_one_event_in_container.sh` is the template above with `INPUT_RECO1`, `EVENT`, `OUTDIR` and `VERTEX_METHOD` as variables. `docs/tutorial_assets/launch_one_event.pbs` is the host-side launcher.

```bash
qsub -v INPUT_RECO1=/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root,EVENT=15,OUTDIR=$MYAREA/runs/armD/evt_0015,VERTEX_METHOD=dv2_split_move \
     docs/tutorial_assets/launch_one_event.pbs
```

**Control run with the original vertex method:** the same command with `VERTEX_METHOD=original` and a different `OUTDIR`. It must reproduce the frozen Fix2-v2 reconstruction. On the 59-event sample it did: 57 MATCH plus 2 known run-to-run BDT-noise events.

These wrappers pass the identical environment and lar command, but have not themselves been run as a separate job; the validated runs used `run_arm_template.sh`. Compare your first event with the validated output for the same entry (§16) before scaling.

---

## 11. Validating that DV2 actually ran

**An exit code of 0 does not prove DV2 ran.** For every event with a neutrino candidate, require all of the following (strings as printed by the source):

| evidence | how to check |
|---|---|
| DV2 configured | `grep "TaggerCheckNeutrino: vertex_method dv2_split_move, DV2-MAX bundle" $LOGFILE` |
| inference call and prediction | `$OUTDIR/dv2_hook.jsonl` has one line per call, each with a non-null `"pred"` |
| placement | `grep "vertex_method dv2_split_move: main vertex = " $LOGFILE` (`graph vertex` or `split`, the distance to P, P(<1cm), the cluster) |
| move (when not already at P) | `grep "vertex_method dv2_split_move: main vertex moved" $LOGFILE` |
| no fallback | `grep -c "no DV2-MAX prediction" $LOGFILE` → 0 |
| no caught exception | `grep -c "DL vertex failed" $LOGFILE` → 0 |
| no Python error | `grep -c "Traceback" $LOGFILE` → 0 |

`docs/tutorial_assets/check_dv2_run.sh <lar log> <event dir>` runs all of these. It prints `DV2_GATE_PASS`, or `DV2_GATE_PASS_NO_CALL` for an event without a neutrino candidate, where DV2 is never called. It was checked against the validated logs: evt 18 (snap), evt 3 (split and move), evt 39 (no candidate).

The gate is only meaningful for `dv2_split_move` runs. An `original` run has none of these lines; there the expected marker is `dual_chain: OFF pass skipped ... no DL weights`.

Validated signal result: 57/57 candidate events produced a prediction and a placement, with 0 no-prediction fallbacks and 0 inference failures.

---

## 12. Wire-Cell output products

Each event directory contains:
- `tracking-pr.root` (the analysis input);
- `mabc.zip` (Bee event display, including the neutrino-only truth tree);
- `nugraph.h5`, a side output not used here;
- `dv2_hook.jsonl` (DV2 runs);
- `messages.log`, `errors.log`, `tf-default.root`, `trash-all-apa.tar.gz`, `cputime.db`, `memory.db`.

**`tracking-pr.root` trees used by the analysis:**
- `T_tagger`: one entry per event with a neutrino candidate; absent means no candidate;
- `T_kine`: one entry;
- `Trun`: run/subrun/event.

Also present: `T_cluster`, `T_segment`, `T_bundle`, `T_flash`, `T_rec_charge`, `T_proj`, `T_proj_data`, `T_bad_ch`.

**A. Mandatory BDT inputs.** These are the variables listed in each XML's `<Variables>` block, read by name:

| BDT | n inputs | source |
|---|---|---|
| `single_photon_numu` | 73 | `T_tagger` (`numu_cc_*`, `shw_sp_*`) |
| `single_photon_other` | 146 | `T_tagger` (`cosmict_*`, `shw_sp_*`, `numu_*`, `cosmic_*`) and `reco_nuvtxY` → **`T_kine.kine_nu_y_corr`** |
| `single_photon_ncpi0` | 45 | `T_tagger` (`shw_sp_*`, `shw_sp_pio_*`, `tro_*`, `stw_*`, `br3_*`, …) and the `kine_pio_*` variables from **`T_kine`** |
| `single_photon_nue` | 56 | `T_tagger` (`shw_sp_*`) |

The machine-readable list is in the XMLs (§13) and in `collect_inputs()` of the scorer.

**B. Mandatory selection variables:**
- `T_tagger` present (neutrino candidate);
- `T_tagger.shw_sp_filled` (the single-photon block was filled; evaluability gate);
- `T_tagger.shw_sp_n_20mev_showers`;
- `T_tagger.shw_sp_n_20br1_showers`;
- the four BDT scores;
- for 0p/Np: `T_kine.kine_particle_type` and `T_kine.kine_energy_particle` (per-particle arrays).

**C. Useful diagnostics:**
- `T_tagger.nu_x/nu_y/nu_z` (reconstructed vertex), `cluster_id`, `shw_sp_energy`, `photon_flag`, `br_filled`, `cosmic_filled`, `match_isFC`;
- `T_kine.kine_reco_Enu`, `kine_nu_{x,y,z}_corr`, `kine_pio_*`;
- in the lar log: the `fix2_v2:` lines (direct and neighbour showers, with energy and PDG) and the `A5 hadronic retype` lines.

---

## 13. The four MicroBooNE BDTs

**Models.** These are the original MicroBooNE single-photon TMVA GradBoost BDTs, unchanged. **They are not SBND-trained classifiers.**
- `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/reference/sbnd_single_photon_microboone_reference_20261005/weights/single_photon_{numu,other,ncpi0,nue}_bdt_final.xml`
- XML files are not committed to the analysis repository.

**Evaluator:** `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/analysis/microboone_1gamma_v0/score_microboone_bdts.py`. It is identical (md5 `2508298c…`) to `analysis/microboone_1gamma_v0/score_microboone_bdts.py` in the analysis repo.
- It walks every tree exactly and returns **`score = tanh(Σ boostWeight · leaf response)`**, which is what `TMVA::Reader::EvaluateMVA` returns for GradBoost.
- **Validation against ROOT/TMVA:** 132/132 comparisons (33 events × 4 BDTs), maximum |difference| 4.94 × 10⁻⁷ (`analysis/microboone_1gamma_v0/docs/TMVA_VALIDATION.md`).

**Evaluability.** A BDT is evaluated only if the event has a candidate, **`shw_sp_filled == 1`**, and every input is present and finite. Otherwise the score is empty, with a reason such as `MAIN_VERTEX_SHOWER_INACCESSIBLE` or `branch_missing:…`. No default values are substituted.

**Real usage.** The script has **no command-line options**. It reads `BASEDIR/evt_NNNN/tracking-pr.root` for `NNNN = 0 … N_EVENTS−1`, with `BASEDIR` = the frozen baseline directory and `N_EVENTS = 59`, and writes into `tables/` next to itself:

```bash
cd /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/analysis/microboone_1gamma_v0
python3 score_microboone_bdts.py        # scores the frozen baseline_v0 outputs only
```

To score **your** directory, the studies exec the unchanged source with only `BASEDIR`, `OUTDIR`, `N_EVENTS` and the output file names substituted (`ab_lib.run_scorer` in the DV2 study). The same mechanism is packaged as `docs/tutorial_assets/score_wirecell_dir.py`:

```bash
python3 docs/tutorial_assets/score_wirecell_dir.py <wc_dir> <n_events> <outdir> <label>
# e.g. the validated DV2 outputs (reproduces the 10 selected events of §16):
python3 docs/tutorial_assets/score_wirecell_dir.py $SIGW/runs/main/armD/wirecell 59 $MYAREA/scores armD
```

Outputs:
- `<label>_bdt_scores.csv`: per event, evaluability, the four scores, `shw_sp_*` counts and `proton_category`;
- `<label>_cutflow.csv`;
- `<label>_taxonomy.csv`.

It also prints the selected events with their 0p/Np category. It runs on the Sophia login node; system python3 has uproot 5 and numpy.

---

## 14. The current pre-FV inclusive single-photon selection

Definition: `selection/microboone_single_photon_selection.yaml`. It is implemented in the scorer's `compute_cutflow()`, and identically as `CUTS_PRE_FV` in the study tables.

| step | cut | physics meaning |
|---|---|---|
| 1 | all events | — |
| 2 | `T_tagger` present | a neutrino candidate exists |
| 3 | `shw_sp_n_20mev_showers > 0` | a reconstructable > 20 MeV photon-like shower at the neutrino vertex |
| 4 | all four BDTs evaluable | the single-photon feature block is complete |
| 5 | `single_photon_numu_score > 0.4` | νμ CC rejection |
| 6 | `single_photon_other_score > 0.2` | other backgrounds / cosmic rejection |
| 7 | `single_photon_ncpi0_score > -0.05` | NC π⁰ rejection |
| 8 | `single_photon_nue_score > -1.0` | νe rejection |
| 9 | `shw_sp_n_20br1_showers == 1` | exactly one reconstructable photon-like shower |

Notes:
- Because `score = tanh(·) > −1` always, step 8 passes every evaluable event. It is kept as in the MicroBooNE selection.
- There are no other cuts.

> **Do not apply the MicroBooNE fiducial volume.** The MicroBooNE condition `5 < reco_nuvtxX < 250` cm is **not** an SBND fiducial-volume definition and must not be applied to SBND. All current numbers are **pre-FV**. A proper SBND FV has to be defined separately.

---

## 15. 0p / Np

From `score_microboone_bdts.py::read_event`, applied to `T_kine`:

```python
ptypes  = tk["kine_particle_type"].array(library="np")[0]
penergy = tk["kine_energy_particle"].array(library="np")[0]
n_p = int(sum(1 for pt, pe in zip(ptypes, penergy) if int(pt) == 2212 and float(pe) > 35.0))
proton_category = "UNCLASSIFIABLE_NO_KINE" if no T_kine else ("Np" if n_p > 0 else "0p")
```

- A reconstructed proton counts when `kine_particle_type == 2212` and its energy is > 35 MeV. The scorer and the YAML treat this as proton kinetic energy (`reconstructed_proton_ke_threshold_mev: 35.0`).
- **0p** = no such proton; **Np** = at least one.

---

# Quick Start: From Existing Reco1 to Single-Photon Selection

Prerequisites:
- access to `/lus/eagle/projects/neutrinoGPU` and `/lus/grand/projects/neutrinoGPU`;
- a PBS allocation on Sophia;
- an area of your own, `$MYAREA`.

1. **Get the analysis repository and look at the reconstruction code.**
   ```bash
   git clone https://github.com/abhatfnal/sbnd-wirecell-single-photon.git && cd sbnd-wirecell-single-photon
   git clone https://github.com/abhatfnal/wire-cell-toolkit.git ../wct-src
   git -C ../wct-src checkout 03c2d4997917990e0f55be7f5b12b36d99b3701b   # see §2.3 first
   ```
   To reproduce the validated results you do not need to build: the run wrapper uses the validated installation (§3, §9.1).
2. **Environment.** Nothing to set by hand. `launch_one_event.pbs` starts the container, and `run_one_event_in_container.sh` sources the sbndcode env and sets `LD_LIBRARY_PATH`, `CET_PLUGIN_PATH`, `WIRECELL_PATH`, `FHICL_FILE_PATH`, `LD_PRELOAD`, `PYTHONPATH` and `DV2_STRICT` exactly as in §10.1. Edit the `#PBS -A` / `-q` lines for your allocation.
3. **Select the configuration.** Use `VERTEX_METHOD=dv2_split_move`. The wrapper selects `$SIGW/config/armD` (`dl_weights=''`, no swap knob) and refuses to run if the operating point does not contain that `vertex_method`.
4. **Run one Reco1 event.**
   ```bash
   export INPUT_RECO1=/abs/path/to/reco1.root EVENT=0 OUTDIR=$MYAREA/runs/armD/wirecell/evt_0000
   qsub -v INPUT_RECO1=$INPUT_RECO1,EVENT=$EVENT,OUTDIR=$OUTDIR,VERTEX_METHOD=dv2_split_move docs/tutorial_assets/launch_one_event.pbs
   ```
5. **Check the DV2 log.**
   ```bash
   bash docs/tutorial_assets/check_dv2_run.sh $OUTDIR/lar.log $OUTDIR      # expect DV2_GATE_PASS
   ```
6. **Locate the Wire-Cell output.** `$OUTDIR/tracking-pr.root` (`T_tagger`, `T_kine`, `Trun`).
   ```bash
   python3 -c "import uproot; f=uproot.open('$OUTDIR/tracking-pr.root'); print([k for k in f.keys() if k.startswith(('T_tagger','T_kine','Trun'))])"
   ```
7. **Run the BDT scorer.** The directory must be named `evt_NNNN` under a common parent.
   ```bash
   python3 docs/tutorial_assets/score_wirecell_dir.py $MYAREA/runs/armD/wirecell 1 $MYAREA/scores armD
   ```
8. **Apply the selection.** The script prints the pre-FV cut flow and the selected events. Scores and per-event fields are in `$MYAREA/scores/armD_bdt_scores.csv`, and the cut flow is in `armD_cutflow.csv`.
9. **0p/Np.** The `proton_category` column of `armD_bdt_scores.csv`, also printed next to each selected event.

---

# Scaling to Multiple Events

- **Event indexing.** Process entry *i* of the input file as `--nskip i -n 1` into its own directory `<parent>/evt_<i, 4 digits>`. The scorer, and every analysis table, keys events by this index.
- **Batch pattern** (`$SIGW/scripts/run_arm_batch.pbs`): **one PBS job runs a list of (arm, event) pairs sequentially**, one `apptainer exec` and one lar process per pair, with one container log and one lar log per event. For example, `qsub -v RUNSET=main,JOBS="O:18 D:18 O:0 D:0" run_arm_batch.pbs`. To run it for your own input, copy the two scripts and change the fixed paths (`W`, `INFILE`) at the top.
- **Scale:**
  - the validated signal campaign was 59 events × 2 arms in **three** sequential jobs of 36 runs each;
  - one DV2 event takes about 1 minute of wall time; the first call in a process spends a few seconds importing torch;
  - do not submit hundreds of small jobs.
- **Co-resident jobs.** Several of your `by-gpu` jobs can land on the same node, and when one finishes the others have been killed (SIGTERM, exit 143). Prefer fewer jobs, or run parallel lanes inside a single job.
  - Keep partial outputs and rerun only unfinished events.
  - The template refuses to write into a non-empty event directory, so a rerun goes into a cleared or new directory; move the partial one aside rather than deleting it.

---

# If You Already Have Wire-Cell Output

You need one directory per event, `<parent>/evt_NNNN/tracking-pr.root`, produced with this reconstruction (DV2 + Fix2-v2, `enable_tracking_root: "true"`, one event per lar process). It must contain:
- `T_tagger` for candidate events, with the `shw_sp_*` block;
- `T_kine`;
- `Trun`.

Then:

```bash
python3 docs/tutorial_assets/score_wirecell_dir.py <parent> <n_events> <outdir> <label>
```

This gives the BDT scores, evaluability reasons, the pre-FV cut flow, the selected events and 0p/Np. No reconstruction is rerun.

If the output came from another reconstruction version, the numbers are not comparable to §16. Record which commit and configuration produced it.

---

## 16. What has been validated

The 59-event NC-Δ sample, run through the identical stack in both arms (`$SIGW/docs/DV2MAX_SINGLEPHOTON59_REPORT.md`):

| | original vertex method | DV2-MAX `dv2_split_move` |
|---|---|---|
| neutrino candidate | 57 | 57 |
| `shw_sp_filled` (single-photon block accessible) | 38 | 41 |
| all four BDTs evaluable | 38 | 41 |
| pre-FV cut flow | 59 / 57 / 38 / 38 / 15 / 8 / 5 / 5 / 4 | 59 / 57 / 41 / 41 / 29 / 19 / 10 / 10 / 10 |
| pre-FV selected | 4 (0005, 0015, 0020, 0036) | 10 (0002, 0005, 0015, 0022, 0032, 0035, 0042, 0045, 0049, 0056) |
| median vertex–truth distance | 28.27 cm | 2.67 cm |
| main cluster contains the true vertex (40 events where it lies in a reco cluster) | 11/40 | 30/40 |

Further results:
- The **original** arm reproduces the frozen Fix2-v2 reconstruction: 57 MATCH plus 2 events with known run-to-run BDT noise, and an identical cut flow.
- The seven formerly inaccessible main-cluster cases (0002, 0031, 0032, 0037, 0042, 0056, 0058) are all **DIRECT** and BDT-evaluable under DV2.
- "Selected" here is a **pre-FV development-sample selection count**. It is not a signal efficiency.

---

## 17. What you must NOT assume yet

1. DV2 is substantially better on the tested NC-Δ signal sample, but it is **not perfect event-by-event**. For example, it can choose a wrong cluster, and in the signal sample it lost accessibility for 7 events while gaining 10.
2. Some photons are reconstructed in clusters **detached** from a correctly reconstructed neutrino vertex. Fix2 allows exactly one PR-graph hop and intentionally does not solve arbitrary detached-cluster association.
3. The A5 hadronic retype (PID) is **sensitive to the reconstructed vertex**. It fires on different events with and without DV2.
4. The four BDTs are **inherited from MicroBooNE**.
5. The BDT response **changes substantially** with DV2; for example, the signal νμ-BDT pass count goes from 15 to 29.
6. Background validation is therefore required before a higher signal pass count can be interpreted.
7. Do **not tune** BDT thresholds on the 59-event NC-Δ sample.
8. Do **not** treat the MicroBooNE thresholds as the final SBND selection.
9. Do **not** apply the MicroBooNE FV.
10. Large ROOT/HDF5 files, BDT XMLs and compiled libraries are intentionally **not** in the analysis Git repository. They live on Eagle at the paths below.

### Background-validation status

Background validation of the DV2 reconstruction with the inherited MicroBooNE BDTs is **in progress**: ν_μ CC and NC π⁰ from a BNB+CORSIKA Reco1 sample, run through the same O/D stack. Work area: `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102/`. No finalized background report exists yet; do not draw selection conclusions from the signal sample alone.

---

## 18. Troubleshooting

**A. DV2 apparently not running.**
- Check that the build has Python: `grep HAVE_PYTHON_INC <wct-build>/WireCellUtil/BuildConfig.h`. A `dv2_*` method without it makes `configure()` raise.
- Check the bundle: `ls $WCT_CFG/dv2max/r7_cloud/` should show `bundle.json pass1.pt pass2.pt ranker_fold0.txt isotonic_fold0.json`.
- Check `PYTHONPATH` (`site39` first, then `$WCT/python`) and `LD_PRELOAD` of `libpython3.9.so.1.0`.
- Then run the §11 greps. With no `TaggerCheckNeutrino: vertex_method dv2_split_move` line, the job ran `original`: check that `WIRECELL_PATH` starts with the `armD` directory.

**B. `libtorch_python.so: undefined symbol …`.**
- The larsoft `libtorch/v2_1_1b/lib` directory is on `LD_LIBRARY_PATH` and shadows the torch wheel. Remove it exactly as in §10.1. `verify_build.sh` gates G5/G6 test this.

**C. "needs a DV2-MAX bundle … not found on WIRECELL_PATH".**
- `dv2_bundle` is `dv2max/r7_cloud/bundle.json`, resolved through `WIRECELL_PATH`. The WCT `cfg/` directory of `03c2d499` must be on it.

**D. Exit 0, but DV2 fell back.**
- Look for `no DV2-MAX prediction`, `DL vertex failed` or a `Traceback` in the lar log, and check that `dv2_hook.jsonl` has a non-null `pred`. The exit code alone is never sufficient.

**E. Reco1 incompatible.**
- Check the products and tags (§5) and the producing release before changing any code or configuration. The validated configuration reads `simtpc2d:dnnsp` wires and `opflashtpc0/1`.

**F. The scorer cannot evaluate.**
- Look at `*_failure_reason` in the scores CSV.
- `MAIN_VERTEX_SHOWER_INACCESSIBLE` means `shw_sp_filled == 0`: no usable single-photon shower at the vertex.
- `branch_missing:` / `not_finite:` name the input.
- Do not substitute default values: an unevaluable event is a reconstruction result.

**G. No photon found from a correctly reconstructed vertex.**
- Fix2-v2 is one hop by design. A photon whose shower is not mapped to the main vertex or to one of its direct graph neighbours is not recovered.
- Do not widen Fix2 casually. Any change is a reconstruction change and needs its own controlled study.

---

## 19. Reference: paths, provenance and reports

| what | path |
|---|---|
| project root | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/` |
| DV2 validation study (`$SIGW`) | `.../single_photon/development/dv2max_singlephoton59_20261102/` |
| integrated WCT source (worktree at `03c2d499`) | `$SIGW/source/wct-int` |
| main DV2 report | `$SIGW/docs/DV2MAX_SINGLEPHOTON59_REPORT.md` |
| integration map | `$SIGW/docs/INTEGRATION_MAP.md` |
| compiled-config diff | `$SIGW/docs/config_semantic_diff.txt` |
| build provenance (commits, hashes, wheels) | `$SIGW/tables/build_provenance.csv` |
| build / run / verify scripts | `$SIGW/scripts/` (`build_all.pbs`, `build_wct.sh`, `build_lwc.sh`, `build_lightgbm.sh`, `verify_build.sh`, `run_arm_batch.pbs`, `run_arm_template.sh`, `compile_cfg.py`) |
| run configuration | `$SIGW/config/{armD,armO,common,sce-override}` |
| validated outputs | `$SIGW/runs/main/arm{O,D}/wirecell/evt_NNNN/`; logs `$SIGW/logs/main/arm{O,D}/lar_evt_NNNN.log` |
| validated installation | `$SIGW/build/install/wct`, `$SIGW/build/lwc-install`, `$SIGW/build/pyenv/site39` |
| Wire-Cell data snapshot | `.../single_photon/runtime/wire-cell-data` |
| NC-Δ Reco1 (59 events) | `.../single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root` |
| NC-Δ truth table | `.../single_photon/baseline_v0/ncdelta_50evt/tables/ncdelta_truth.csv` |
| NC-Δ production jobs | `.../single_photon/baseline_v0/ncdelta_50evt/jobs/{gen,g4,detsim,reco1}/` |
| signal generator FCL / filter | `.../single_photon/signal_mc/ncdelta/fcl/prodgenie_ncdelta_sbnd.fcl`, `.../single_photon/signal_mc/ncdelta/src/NCDeltaRadiative_module.cc` |
| BDT scorer | `.../single_photon/analysis/microboone_1gamma_v0/score_microboone_bdts.py` |
| BDT XML models | `.../single_photon/reference/sbnd_single_photon_microboone_reference_20261005/weights/` |
| TMVA validation | `.../single_photon/analysis/microboone_1gamma_v0/docs/TMVA_VALIDATION.md` |
| analysis repository | `.../single_photon/repos/sbnd-wirecell-single-photon/` |
| selection definition | `selection/microboone_single_photon_selection.yaml` (analysis repo) |
| DV2 study mirror | `reconstruction_studies/dv2max_singlephoton59/` (analysis repo) |
| tutorial helpers | `docs/tutorial_assets/` (analysis repo) |
| container / images / env | `/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif`; `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/{larsoft-v10_14_02,sbnd-v10_14_02_04_delta}.squashfs`; `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env` |
| background validation (in progress) | `.../single_photon/development/dv2max_background_validation_20261102/` |

`...` = `/lus/eagle/projects/neutrinoGPU/abhat/sbnd`.
