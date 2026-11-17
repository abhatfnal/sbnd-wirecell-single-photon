# Aurora umbrella-model training and FermiGrid evaluation: statistical policy for the SP BDTs

Date: 2026-11-17. Applies to every single-photon (SP) BDT development and final training in Round 2.

## The framing

The collaboration separates statistics by **site**, not by model:
- **Aurora** holds all model development and training: Snehadri's DL vertex, the upstream Wire-Cell BDTs (νμ, νe),
  energy estimators, NuGraph, and the downstream SP BDTs.
- **FermiGrid** holds the independent evaluation.

Every model trained on Aurora can therefore be viewed as one part of a single composite ("umbrella") model. That
composite is trained on Aurora as a whole and evaluated once, on FermiGrid. (Paraphrase of the framing given by
Haiwang Yu, 2026-11-17.)

## Policy

1. **Shared Aurora events are allowed.** Upstream reconstruction models and downstream BDTs may use the same Aurora
   events. Snehadri's DV2-MAX `aurora_space` vertex was trained on fold 1 of the aurora-r2 BNB and νe CC events, and the
   SP BDTs train on the same production's events. This is permitted.
2. **The even/odd split is a DEVELOPMENT HOLDOUT.** The SP split keeps even subruns for training and holds out odd
   subruns. The held-out rows test the **downstream** BDT **conditional on** an upstream model that has already seen the
   Aurora domain, and may have seen those very events.
3. **Holdout numbers are development numbers.** They are right for development: comparing reconstruction modes,
   checking generalization within Aurora, comparing with legacy controls, validating machinery. They are **not**
   independent end-to-end performance. Every table built from them carries the label "DEVELOPMENT HOLDOUT" and never
   "test" or "independent".
4. **FermiGrid is the only independent end-to-end evaluation.** That means the official samples, processed with the
   frozen reconstruction and model chain: WCLocal2026Nov16-FermiGrid (`wcl1116-fg-*`) or its successor, fg1, and any
   official NC Δ sample.
5. **Nothing is decided from FermiGrid before the freeze.** Before the full chain is frozen, no FermiGrid evaluation
   product is used for:
   - training;
   - hyperparameter, feature or model-selection decisions;
   - the snap vs split-move choice;
   - keep-or-retrain decisions;
   - operating-threshold optimisation.
   Its performance numbers are not even inspected in this phase. The products are firewalled: `sp_retrain.firewall`
   refuses `/pnfs/`, `prod-fermigrid`, `wcl1116-fg`, `WCLocal2026Nov16-FermiGrid`, `beam-off`, `run3bnb` and
   `opendata`.
6. **The one pre-designated exception** is the odd-run beam-off training partition (`fg1-beamoff-train`). Its membership
   was frozen on 2026-11-09, before this campaign, by run parity.
   - It may be extracted from the refreshed full beam-off rerun using that membership list only, with Xin's hold-out
     files removed.
   - Avinay approved it on 2026-11-17 for the WCL1116 development campaign only. It is not permission to use the
     even-run evaluation half, the full 50k sample, or hold-out events.
   - Record: `manifests/wcl1116_dev_v1/beamoff_train_membership.json`.

## Consequences for reporting

| quantity | what it is | allowed use now |
|---|---|---|
| train-fold metrics | fit quality | diagnostics |
| development-holdout metrics (Aurora odd subruns; beam-off run % 4 == 1) | downstream generalization within the umbrella-trained Aurora domain | development decisions, labelled DEVELOPMENT HOLDOUT |
| legacy-XML control on the same rows | inherited response in the new SBND domain | diagnostics; no threshold tuning |
| FermiGrid official samples | independent end-to-end performance of the frozen chain | **after** the freeze only |
