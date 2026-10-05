# MicroBooNE Single-Photon Reference Bundle — Provenance

**Purpose**: Cryptographic verification record for the frozen MicroBooNE single-photon BDT
reference materials used in the SBND `baseline_v0` compatibility audit.

**Date verified**: 2026-10-05

---

## Bundle location (Sophia/Eagle)

```
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/reference/
  sbnd_single_photon_microboone_reference_20261005.tar.gz
```

**Tarball SHA256**: `fcf7666b81e5d11dd7a8c5d56628f4ab48aa4b30e392d2eb5b07ad75e2960386` — **PASS**

**Unpacked to**:
```
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/reference/
  sbnd_single_photon_microboone_reference_20261005/
```

---

## File-level SHA256 verification

SHA256SUMS.txt embedded **absolute Fermilab paths** (`/nashome/a/abhat/...`) which do not
exist on Eagle. Standard `sha256sum -c SHA256SUMS.txt` therefore reports "No such file or
directory" for all 10 entries. Verification was performed manually: each expected hash was
extracted from SHA256SUMS.txt and compared against the Eagle file via `sha256sum <eagle_path>`.

All 10 files **PASS**.

| File | SHA256 (64 hex chars) | Status |
|------|----------------------|--------|
| `src/bdt_convert.cxx` | `5181baf3d6814f08e88661bb144adb3530403febdfecc96cd4d63ff6f8fda1a8` | PASS |
| `src/bdt.h` | `0fee088d8f212df854f6578fda64ea24d2223864e6cb75ad54889230c9a0c3d6` | PASS |
| `src/Configure_Lee.h` | `7bb2e365920d9f76f00ff5388ac25eb242328892bf3e4a0a7abdd90e0185cf4d` | PASS |
| `src/cuts.h` | `ee88e954b6f6177b3c8d0c5ee5553a3ed682774a6e71b35a79576b7ac00746c5` | PASS |
| `src/kine.h` | `964ccc6352f8690101fbf09a51f3f98034ae9ec6e619c8c94f75dbb2eb856f5b` | PASS |
| `src/tagger.h` | `2ecb254b818ae1bc3c9154c1fe5940d978af49a832eb34a68fe3b261a0f00202` | PASS |
| `weights/single_photon_ncpi0_bdt_final.xml` | `983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3` | PASS |
| `weights/single_photon_nue_bdt_final.xml` | `8580ba04b4a9e3c7aefbb4d5da5006cff2a131804a7b594843461a7cd6f3758a` | PASS |
| `weights/single_photon_numu_bdt_final.xml` | `5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961` | PASS |
| `weights/single_photon_other_bdt_final.xml` | `8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16` | PASS |

### Note: ncpi0 hash typo in task specification

The audit task specification listed the ncpi0 XML SHA256 as
`983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3e` (65 characters).
SHA256 hashes are always exactly 64 hexadecimal characters. The trailing `e` is a typo in
the task spec. The actual file and SHA256SUMS.txt both contain the correct 64-char hash
shown in the table above. This is a documentation error only; the file is intact.

---

## Provenance metadata

| Field | Value |
|-------|-------|
| Source system | Fermilab /nashome (bbogart's area) |
| Copied to Eagle | 2026-10-04 |
| Copied by | abhat@uchicago.edu |
| Bundle naming convention | `sbnd_single_photon_microboone_reference_YYYYMMDD.tar.gz` |
| Internal provenance file | `provenance/SHA256SUMS.txt` (embedded absolute FNAL paths) |

---

## BDT model summary

| Model | XML file | Variable count | Variable index range |
|-------|----------|---------------|---------------------|
| `single_photon_numu` | `single_photon_numu_bdt_final.xml` | 73 | VarIndex 0–72 |
| `single_photon_other` | `single_photon_other_bdt_final.xml` | 146 | VarIndex 0–145 |
| `single_photon_ncpi0` | `single_photon_ncpi0_bdt_final.xml` | 45 | VarIndex 0–44 |
| `single_photon_nue` | `single_photon_nue_bdt_final.xml` | 56 | VarIndex 0–55 |
| **Total** | | **320** | |

Variable extraction source: XML `<Variables>` element (authoritative over C++ grep).
`bdt_convert.cxx` contains one commented-out AddVariable line for `kine_pio_flag` in the
ncpi0 reader; the XML confirms a single occurrence at VarIndex 34.

---

## Usage constraints

- Do NOT modify any file in this reference bundle.
- Do NOT retrain or alter the XML BDT models.
- This bundle is used **read-only** for compatibility auditing under `baseline_v0`.
- All analysis scripts that reference this bundle must operate on copies or read-only paths.
