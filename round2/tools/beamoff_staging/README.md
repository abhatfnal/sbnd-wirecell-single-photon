# Staging the refreshed beam-off TRAINING partition (WCL1116) to Aurora

**Status (2026-11-19): EXECUTED AND VERIFIED.**
- Avinay pushed the 558 files from his gpvm session on 2026-11-18.
- `tools/verify_staged_beamoff.py` verified 558 / 558; record in `round2/manifests/wcl1116_dev_v1/beamoff_train_staging.{json,tsv.gz}`.
- Training list sha256 `8f2ea601…`.

The transfer needs Avinay's own session: a Fermilab gpvm login and the ALCF one-time passcode. Nothing in this
directory can or should run unattended. Evaluation beam-off is never a substitute.

## What is copied

The **558** pairs of the frozen `fg1-beamoff-train` membership, and nothing else:
- the frozen list is Xuyang's `bdt-comm/data/fg1-beam-off-train.list.tsv`, sha256 `acb69100…`: 572 odd-run pairs, split
  by the owner on 2026-11-09;
- Xin's 14 hold-out files are removed;
- the membership is in `round2/manifests/wcl1116_dev_v1/beamoff_train_membership.tsv.gz`;
- per pair, the one WCL1116 merged CAF under `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/beam-off/<pair id>/`
  (both vertex trees);
- about 5 GB in total.

The following are never copied:
- the even-run evaluation half;
- the full 50k beam-off as a whole;
- hold-out files;
- any other `wcl1116-fg-*` sample.

## Route

This is the one Xuyang used for the same partition on 2026-11-10: `bdt-comm/PLAN.md` line 83 and
`bdt-comm/inbox/updates-1828.md` §4.
- `rsync` over ssh, **pushed from the gpvm**, in a session the user opens. One ssh ControlMaster connection means one
  ALCF passcode.
- `--copy-links` through a links directory.
- The dCache ADLER32 of every file is recorded on the gpvm, before the copy.

Rejected routes:
- `xrdcp` / `gfal-copy` pulled from Aurora: they would need a Fermilab token on Aurora.
- Globus: needs a browser login and a dCache endpoint; untested.

## Steps

On a Fermilab SBND gpvm, as Avinay:

```bash
# the frozen membership (558 ids), from this repository
zcat round2/manifests/wcl1116_dev_v1/beamoff_train_membership.tsv.gz | tail -n +2 | cut -f1 > membership_ids.txt
bash round2/tools/beamoff_staging/gpvm_stage_wcl1116_beamoff_train.sh membership_ids.txt abhat
#   -> /exp/sbnd/data/users/$USER/wcl1116_beamoff_train_stage/{source_manifest.tsv,files.txt,missing.txt,links/}
#   -> rsync to Aurora: /lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117/wcl1116_beamoff_train/
```

Then on Aurora (login node: about 5 GB of checksums and a header read):

```bash
cd round2
$PY tools/verify_staged_beamoff.py --staged $SP_WORK/wcl1116_beamoff_train \
    --membership manifests/wcl1116_dev_v1/beamoff_train_membership.tsv.gz \
    --frozen-list /lus/flare/projects/neutrinoGPU/xning/bdt-comm/data/fg1-beam-off-train.list.tsv \
    --source-manifest $SP_WORK/wcl1116_beamoff_train/source_manifest.tsv \
    --out-json manifests/wcl1116_dev_v1/beamoff_train_staging.json \
    --out-tsv manifests/wcl1116_dev_v1/beamoff_train_staging.tsv.gz \
    --write-list $SP_WORK/wcl1116_dev/lists/wcl1116-fg-beamoff-train.txt
```

The verifier writes the list **only if** all of these hold:
- every staged file is one of the 558;
- every file has an odd run, in its name and in its header, equal to the membership run;
- size and ADLER32 equal the gpvm record, and a sha256 is recorded;
- the file is WCL1116:
  - `recTreeWireCell` and `recTreeWireCell_dv2snap` present;
  - `wct_version` exactly `0.38.0` or `HEAD-0.38.0`, the two stamps of toolkit c935e30d
    (`docs/WCL1116_TOOLKIT_PROVENANCE_NOTE.md`), the same in both trees and across the sample;
  - `dl_weights` exactly `<mode>:dv2max/sbnd/aurora_space/bundle.json@sha256:51588842…`;
- `ismc == 0`;
- 0 duplicate, hold-out, unknown or even-run files, and none missing.

A self-test on Xuyang's OLD fg1 copy passes membership, run and dCache ADLER32 on all 6 files read. It rejects every
one of them as not WCL1116 (no `dv2snap` tree, `wct_version …g78f81c64`), so the two reconstructions cannot mix.

After verification:
1. `tools/make_wcl1116_dev_specs.py --census-dir … --only other` turns the SP other specs from
   `BLOCKED_TRANSFER_EXECUTION` into `READY_FOR_DEVELOPMENT_TRAINING` with the verified list hash.
2. Build the EXT tables, one per tree:

   ```bash
   python -m sp_retrain.build_tables wcl1116-fg-beamoff-train $SP_WORK/wcl1116_dev_tables/<mode> \
       --list $SP_WORK/wcl1116_dev/lists/wcl1116-fg-beamoff-train.txt --wc-tree <tree> --tag dev \
       --approved-exceptions-spec specs/single_photon_other_training_spec_dev_wcl1116_<mode>.yaml ...
   ```

   This is 558 small files, so a single node or the login node is enough.
3. Run `tools/sp_other_census.py`, then `tools/train_wcl1116_dev_model.py`, `legacy_control_compare.py`, the export and
   the C++ check, exactly as for SP numu / ncpi0.
