# TMVA Evaluation Validation

**Date**: 2026-10-05
**Scorer**: `score_microboone_bdts.py` — pure-Python GradBDT tree-walk evaluator
**XML source**: frozen MicroBooNE reference bundle (SHA256 verified, all files PASS)

---

## Evaluation algorithm

The scorer implements the TMVA GradBoost BDT evaluation algorithm exactly, including the
`tanh` normalization applied by `TMVA::Reader::EvaluateMVA()` for `BoostType: Grad`:

1. Parse `<Variables>` block from XML → ordered variable list by `VarIndex`
2. For each `<BinaryTree>`: precompute a nested Python tuple representing the tree
3. For each tree: walk from root to leaf:
   - At each internal node (nType=0): if `input[IVar] <= Cut` → go left (pos='l'), else right
   - At leaf node (nType=-99): return `float(res)`
4. Raw sum = `sum(boostWeight_i * leaf_res_i)` over all 300 trees
5. **Final score = `tanh(raw_sum)`** — matches TMVA C++ exactly

This matches the TMVA C++ implementation in `TMVA/MethodBDT.cxx`:
```cpp
Double_t MethodBDT::GetMvaValue(Double_t* errLower, Double_t* errUpper) {
    // ...accumulate weighted sum...
    if (DoRegression()) return mvaValue;
    if (fBoostType == "Grad") return 2.0/(1.0+exp(-2.0*mvaValue))-1;  // tanh transform
    // ...
}
```

---

## Critical finding: tanh transform (discovered 2026-10-05)

**ROOT/TMVA cross-validation revealed that `TMVA::Reader::EvaluateMVA("BDT")` for GradBoost
applies `tanh(x)` to the raw weighted-leaf sum.** The initial Python scorer returned raw sums only.

Confirmed by: for ALL 132 evaluations (33 events × 4 BDTs):
```
tanh(python_raw_score) = root_tmva_score  to within 5e-7
```

**Impact on cut flow:**

The MicroBooNE cut thresholds (from `cuts.h`) are calibrated in tanh-space:
- `numu_score > 0.4`
- `other_score > 0.2`
- `ncpi0_score > -0.05`
- `nue_score > -1.0`

The nue threshold of `-1.0` is the mathematical minimum of `tanh(x)` as `x → -∞`. No finite
input can produce `tanh(x) ≤ -1.0`, so `nue_score > -1.0` passes **all** events — it is a
no-cut threshold as calibrated in MicroBooNE. With the raw scorer, 7 events with
raw nue < -1.0 were incorrectly rejected.

**Fix applied**: `score_microboone_bdts.py` `TmvaBdt.evaluate()` now returns `math.tanh(raw)`.

---

## ncpi0 kine_pio_flag branch type fix

`kine_pio_flag` in `T_kine` is stored as `Int_t` (ROOT int32), not float32. The C++
cross-validator must read it as `Int_t` then cast: otherwise binary reinterpretation gives
`1 → ~1.4e-45` as float, which misroutes all ncpi0 trees for 28/33 events.

The Python scorer uses `uproot`, which reads the branch with its correct ROOT type, so this
issue does not affect the Python scorer. The standalone C++ validator (`validate_tmva_standalone.cxx`)
includes the fix:
```cpp
if (vname == "kine_pio_flag") {
    Int_t ival = 0;
    b->SetAddress(&ival);
    b->GetEntry(0);
    val = static_cast<float>(ival);
}
```

---

## ROOT/TMVA cross-validation results (final)

### Method: standalone compiled C++ binary (`validate_tmva_standalone.cxx`)

PyROOT on RHEL9 with CentOS7 ROOT v6_28_12 is non-functional (Cling JIT symbol
materialization failure for `TMVA::Reader::Reader(TString const&, bool)`). A standalone C++
program was compiled with GCC 11 using ROOT headers/libs directly, bypassing Cling/PyROOT.

Required library shims on RHEL9:
- `libtinfo.so.5 → /lib64/libtinfo.so.6`
- `libffi.so.6 → sphinx cffi.libs/libffi-806b1a9d.so.6.0.4`
- `libxxhash.so.0 → spack xxhash-0.8.3`
- `libexpat.so.1 → /lib64/libexpat.so.1` (shadows spack expat needing GLIBC_2.38)
- `libstdc++.so.6 → spack gcc-runtime-13.3.1` (provides GLIBCXX_3.4.30 needed by libRIO.so)
- `libssl.so.10` from nsight-systems CUDA spack area
- `libtbb.so.12` from larsoft tbb package

### Results

| Model | Events | PASS | max |diff| | mean |diff| |
|-------|--------|------|------------|-------------|
| numu  | 33/33  | 33   | 4.72e-07   | ~1.5e-07    |
| other | 33/33  | 33   | 4.94e-07   | ~1.5e-07    |
| ncpi0 | 33/33  | 33   | 4.81e-07   | ~1.5e-07    |
| nue   | 33/33  | 33   | 4.89e-07   | ~1.5e-07    |
| **Total** | **132/132** | **132** | **4.94e-07** | — |

**Overall: ALL_PASS.** Maximum absolute difference 4.94e-7 << tolerance 1e-4.

Cross-validation data in: `tables/tmva_python_crosscheck.csv`

Columns: `run, subrun, event, evt_idx, model, python_score, root_tmva_score, absolute_difference, relative_difference, pass`

---

## Reference event: evt_0001 (run=1 subrun=0 event=215)

### Scores (corrected, tanh-transformed)

| BDT | Raw sum | tanh score |
|-----|---------|-----------|
| `single_photon_numu` | 2.9059670... | 0.9940... |
| `single_photon_other` | 0.9536231... | 0.7397... |
| `single_photon_ncpi0` | −1.4731050... | −0.9001... |
| `single_photon_nue` | −0.3768440... | −0.3599... |

`reco_nuvtxY` (other BDT, VarIndex 145) = `T_kine.kine_nu_y_corr` = −9.7551 cm

### Reproducibility

Two consecutive evaluations of numu BDT for evt_0001:
- Run 1: 0.99404... (tanh-transformed)
- Run 2: 0.99404... (tanh-transformed)
- **Identical (bitwise)** ✓

---

## Score conventions (corrected)

All four BDTs use `BoostType: Grad` (gradient boosting). `TMVA::Reader::EvaluateMVA("BDT")`
returns `tanh(raw_sum)` where `raw_sum = Σ(boostWeight_i × leaf_response_i)`.

The MicroBooNE cut thresholds (in `cuts.h`) operate in tanh-space `[-1, 1]`:
- `single_photon_numu_score > 0.4`
- `single_photon_other_score > 0.2`
- `single_photon_ncpi0_score > -0.05`
- `single_photon_nue_score > -1.0` (no-cut: tanh always > -1.0)

Score ranges observed in 59-event NC Delta sample (tanh-transformed, all in [-1, 1]):
- numu:  [−0.999, +0.999], mean = +0.103
- other: [−0.989, +0.988], mean = −0.236
- ncpi0: [−0.985, +0.709], mean = −0.216
- nue:   [−0.997, +0.877], mean = −0.492

---

## Notes

- Variable order is authoritative from XML `VarIndex`. TMVA indexes variables by position.
- `boostWeight = 1.0` for all 300 trees in all four GradBoost models.
- Leaf `res` values incorporate the training shrinkage; no additional factor needed.
- Float precision: XML cuts/responses stored as ~9 significant digits. Python parses as float64.
  Differences at the 7th significant digit are expected and have no effect on tree routing.
- The XGBoost-to-TMVA converter (`bdt_convert.cxx`) used `TMVA::Reader::EvaluateMVA()`,
  meaning all thresholds in `cuts.h` are in tanh-space. This is confirmed by the threshold
  values being within [-1, 1] and the nue threshold = -1.0 (physical minimum of tanh).
