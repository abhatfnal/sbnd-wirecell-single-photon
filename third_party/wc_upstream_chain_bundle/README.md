# wc_upstream_chain: toolkit-equivalent upstream tagger scoring

**Version 1.0.0 (2026-11-28). DEVELOPMENT ONLY: it selects no model, threshold or vertex mode.**

This package gives the values that the wire-cell-toolkit 0.38.0 chain stores for the upstream SBND Wire-Cell νμ and νe tagger
BDTs. That is 20 values per candidate:
- `numu_1_score`, `numu_2_score`, `cosmict_10_score`, `numu_score`;
- the 15 νe level-1 `<m>_score`;
- `nue_score`.

It computes them offline from the stored tagger inputs, with the shipped weights or with Xuyang's released weights
(`Ningclover/sbnd-wirecell-bdt` @ `0f13988d`: `numu_round3af` with the simulation-only ×1.071 dQ/dx correction, and
`nue_round4_ruleA_v2` main).

It is the **common numerical reference for Aurora and EAF**, as Avinay decided on 2026-11-28. The evidence:
- it equals the patched in-chain test bit for bit;
- it equals the Aurora module `sp_retrain/upstream_chain.py` on all 593,723 development candidates of both trees;
- it closes the shipped final models on every stored score.

The release's standalone xgboost scripts differ from the chain on about 1 % of candidates, by up to about 0.4. Read
[CONVENTIONS.md](CONVENTIONS.md) before using any number.

Requirements: Python ≥ 3.8, numpy, pandas (and pyarrow for parquet). No ROOT, no xgboost. It does not depend on the Aurora
training framework.

## Install or vendor

```bash
pip install ./upstream_chain_bundle          # or: export PYTHONPATH=<path>/upstream_chain_bundle:$PYTHONPATH
python -m pytest upstream_chain_bundle/tests # self-contained, no data needed
```

## Interface

```python
import wc_upstream_chain as wuc

# 1. verify a release clone: 57 canonical files + 8 auxiliary files + manifest invariants
rep = wuc.verify_release('<clone>/releases', head_commit='0f13988db44423a227789e151b0a374e25771abd')
assert rep['ok'] and rep['inventory_fingerprint'] == wuc.release_inventory()['fingerprints']['canonical_inventory']

# 2. score candidates (Xuyang's cands_/objs_ table schema, one vertex tree at a time)
release = wuc.UpstreamChain(['<clone>/releases/nue_round4_ruleA_v2/wirecell/main',
                             '<clone>/releases/numu_round3af/wirecell',
                             '<wire-cell-data 99c6497f>'])            # WIRECELL_PATH order; numu_tagger3 falls back to shipped
scores = release.score(cands, objs, kind='mc')                         # kind='data' for beam-off / beam-on: never corrected
#   cands: key + wuc.spec.candidate_inputs() columns; objs: {model: per-object table} for wuc.spec.L1_ALL
#   scores: key + the 20 outputs under their CAF names + diag_* columns; scores.attrs['provenance'] = files, sha256, k, kind

# 3. shipped closure (stored level-1 values -> shipped final models must reproduce the stored numu_score / nue_score)
shipped = wuc.UpstreamChain(['<wire-cell-data 99c6497f>'])
closure = shipped.score(cands, objs, kind='mc', stored_l1=True)

# 4. SP inputs of a domain (A stored, B nu_mu release, C nu_e release, D both): replaces only the upstream outputs
sp_frame_D = wuc.sp.replace_upstream_inputs(sp_frame, scores, key, 'D')

# 5. identity translation to another site's key (raises on anything unmapped or duplicated)
t = wuc.identity.translate(scores, mapping, wuc.identity.XN_KEY, wuc.identity.EAF_KEY)
```

Input contract:
- `cands`: one row per candidate. It needs the key and every column in `wuc.spec.candidate_inputs()`:
  - the final-model inputs that are not level-1 outputs;
  - `br_filled`, `pio_filled`, `pio_flag_pio`, `numu_cc_flag_3`, `cosmict_{2,3,7}_filled`.
- `objs[model]`: the key plus `wuc.spec.object_inputs(model, sim_correction)`, one row per object. With the correction, `flag` is
  also needed for numu_1 and numu_2. A missing table means that model has no objects.
- Both are exactly what Xuyang's `tables/build_tables.py --objs` writes, and what the Aurora `tools/extract_upstream_inputs.py`
  writes. Aurora proved the two identical on the same files.

## Command line

```bash
python -m wc_upstream_chain verify --releases <clone>/releases --head <commit>
python -m wc_upstream_chain fingerprint --weights-path A:B:C          # chain fingerprints + route (release / shipped / unknown)
python -m wc_upstream_chain score --cands cands_S.parquet --objs 'objs_{model}_S.parquet' --kind mc \
       --weights-path A:B:C --out scores_S.parquet --key sample,file_id,run,subrun,event,cand      # never overwrites
python -m wc_upstream_chain check-fixture <fixture dir> --releases <clone>/releases --shipped <wire-cell-data> [--part mc]
```

## Files

| file | content |
|---|---|
| `wc_upstream_chain/chain.py` | the scorer (`UpstreamChain`, `ChainScorer`, `compare_exact`) |
| `wc_upstream_chain/tmva_grad.py` | numpy TMVA Grad evaluator; byte-identical to Aurora `sp_retrain/tmva_grad.py` |
| `wc_upstream_chain/spec.py`, `data/*.txt`, `data/l1_models.json` | ordered feature lists, level-1 specs, constants |
| `wc_upstream_chain/inventory.py`, `data/release_inventory.json`, `data/shipped_inventory.json` | canonical inventory, verification, fingerprints |
| `wc_upstream_chain/identity.py` | key conventions, checked translation and joins |
| `wc_upstream_chain/sp.py` | which SP inputs are upstream outputs; checked replacement |
| `tests/` | synthetic tests, plus the optional fixture test (`WC_UPSTREAM_FIXTURE`, `WC_UPSTREAM_RELEASES`, `WC_UPSTREAM_SHIPPED`) |

The data files are regenerated by Aurora's `round2/tools/build_upstream_chain_bundle_data.py`, from the release clone, the
committed spec copies and the shipped files.

## Rules that travel with the bundle

- Score simulation with `kind='mc'` and data with `kind='data'`. Never correct beam-on or beam-off data, never correct the νe
  classifier, and never correct SP input features.
- An SP model trained in one upstream domain must never score inputs of another domain. A model manifest must carry the chain
  fingerprints, and a scorer must refuse a mismatch.
- Xuyang's operating cuts (`nue_score` 3.06, `numu_score` 0.985) are informational only. They are not SP thresholds.
- Every SP model trained on these scores is **DEV_DO_NOT_DEPLOY** until a freeze is approved.
