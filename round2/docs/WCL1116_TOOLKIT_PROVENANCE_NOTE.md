# WCLocal2026Nov16 toolkit provenance: `0.38.0` vs `HEAD-0.38.0`

Date: 2026-11-19. Scope: campaign `development_wcl1116_v1` (WCLocal2026Nov16) only. Code: `sp_retrain/provenance.py`.

## 1. What each file stores

A merged CAF stores the toolkit version **string** `wc.Trun.wct_version`. It does **not** store a git SHA.
`wc.Trun.dl_weights` stores the DL bundle path and its sha256.

| sample | stored `wct_version` (both Wire-Cell trees) | stored `dl_weights` |
|---|---|---|
| Aurora WCL1116: `wcl1116-aurora-{ncdr,bnb,nuecc}` | `0.38.0` | `<mode>:dv2max/sbnd/aurora_space/bundle.json@sha256:51588842…` |
| staged beam-off training half (558 files, FermiGrid) | `HEAD-0.38.0` (558 / 558) | the same, exactly (558 / 558, both trees) |

The staged files also carry the same νμ / νe BDT weight files, track-fitting configuration and weights directory as the
Aurora files (`$SP_WORK/beamoff_verify_diagnosis/trun_metadata_558.json`).

## 2. Campaign-level build records

| build | record | toolkit |
|---|---|---|
| Aurora (`/lus/flare/projects/neutrinoGPU/yuhw/opt-0.38.0`) | worktree `wct-0.38.0`: `git rev-parse HEAD` = `c935e30d…`, `git describe --tags` = `0.38.0`; `version.txt` = `0.38.0`; `manifests/wcl1116_aurora_v0/production_provenance.json` | `c935e30d44a09bf208f6de2c2968171b01efd63d` |
| FermiGrid / gpVM (`/exp/sbnd/data/users/yuhw/wclocal-nov16/opt`) | `TARBALL-PROVENANCE.txt`, found in `p0/emu-ncpi0-s0-7/tar/wc/`, `emu53a/w-mc-nuecc/tar/wc/` and `emu53a/w-opendata/tar/wc/`: `opt …/wclocal-nov16/opt: wire-cell WIRECELL_VERSION "HEAD-0.38.0"`; `cfg …/wclocal-nov16/wct/cfg: wire-cell-toolkit c935e30d 0.38.0 0 dirty cfg files`. Inspected by Avinay on the gpVM, 2026-11-19 | `c935e30d` (tag `0.38.0`, 0 dirty cfg files) |

**Why the strings differ.** The toolkit's own rule (`wscript` `determine_version()`, `cmake/WCTVersion.cmake`):
- the version is `git describe --tags`, or `version.txt` if git gives nothing;
- unless the branch is `master` or a numeric release branch, the branch name is prefixed: `<branch>-<describe>`.

A detached checkout exactly on tag `0.38.0` therefore stamps `HEAD-0.38.0`, because `git rev-parse --abbrev-ref HEAD`
is `HEAD`. One commit past the tag would stamp `HEAD-0.38.0-1-g<hash>`. The Aurora build stamped the bare `0.38.0`.

## 3. Mapping and policy (approved by Avinay, 2026-11-19)

| stored string | maps to |
|---|---|
| `0.38.0` | Aurora WCLocal2026Nov16 build of `c935e30d44a09bf208f6de2c2968171b01efd63d` |
| `HEAD-0.38.0` | FermiGrid / gpVM WCLocal2026Nov16 build of `c935e30d44a09bf208f6de2c2968171b01efd63d` |

- This is a **closed list compared by exact string equality**: no substring, regex, suffix or tag-prefix matching. It
  is **not** a version parser.
- Rejected, with tests (`tests/test_wcl1116_dev.py`):
  - post-tag stamps: `HEAD-0.38.0-N-g<hash>`, `0.38.0-N-g<hash>`;
  - branch stamps: `<branch>-0.38.0`, `<branch>-0.38.0-N-g<hash>`;
  - `0.38.1`;
  - the old fg1 stamp `…-g78f81c64`;
  - whitespace or case variants, and unknown or empty strings.
- **Per sample, the expected string is exact.** The Aurora samples are checked against `0.38.0` (the input manifest).
  The staged beam-off sample is checked against the single stamp recorded by its verifier, `HEAD-0.38.0`, which is
  written into the SP other specs as `wct_version_stamp`.
  - A file without its sample's stamp gives no training rows, the same rule as before.
- **Unchanged:** every other verification (membership, odd runs, hold-out, checksums, both trees, `ismc`, the DL bundle).
  - The DL-bundle check is now stricter: an exact per-tree `dl_weights` string instead of a sha substring.
  - Both trees of a file must carry the same stamp, and all files of the staged sample must carry one stamp.
