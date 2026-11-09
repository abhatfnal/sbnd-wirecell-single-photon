# NC π⁰ / CC π⁰ selected backgrounds: why do they look single-photon-like?

MC evaluation only; frozen baseline, `any`; selected non-signal candidates with candidate-associated category NC_PI0 (192) or CC_PI0 (106). Per-candidate table `tables/background_mechanisms/pi0_candidates.csv`; aggregates `summary.json` (`pi0`). Code: `background_truth.pi0_photon_summary`, `photon_fate_labels`, `scripts/background_deep.py`.

## 1. Can the π⁰ decay be traced exactly?
**Yes, from `wc.T_truth_pf`.** For the matched truth neutrino (`nu_row` = truth `nu_idx`) the tree contains the π⁰ (`pdg 111`) and its two daughter photons (`pdg 22`, `parent_trackid` = the π⁰ track) with energy, start/end point and momentum, **even for photons that deposit no charge**. `T_truth_track` (only tracks with charge in blobs) links the shower particles: `ancestor_trackid` = the π⁰ and `prong_trackid` = the photon whose shower they belong to (verified on events; e.g. a selected shower dominated by a 268 MeV π⁰ photon while the other, 69 MeV photon exits the TPC with zero charge). `GenieEvtRecTree` is not needed (the π⁰ is a status-1 GENIE primary, counted from `rec.mc.nu.prim`); the π⁰ *decay* only exists in Geant4/`T_truth_pf`.
Not stored per photon: direction vectors for the daughters in my table (only energies); the **opening angle is derived from the two energies** with m_π⁰² = 2E₁E₂(1−cosθ) (exact for π⁰ → γγ; NaN for 8 candidates whose energies are inconsistent with that relation or whose second daughter is absent).
Number of π⁰ in the matched interaction's `T_truth_pf` (298 candidates): 1 in 286, 2 in 8, 3 in 3, 0 in 1 (a candidate classified by the `rec.mc.nu` primaries whose π⁰ is not in `T_truth_pf`). The π⁰ vertex is inside the provisional TPC box in all 297 candidates that have a π⁰ record (the category already requires the matched vertex to be in the box).

## 2. π⁰ and photon kinematics (medians; reco 0p vs 1p; `n` = selected candidates)
| | n | selected shower is a π⁰ daughter | … the lead photon | lead E (MeV) | sub E (MeV) | asymmetry | opening angle (°) | truth protons 0 / 1 / ≥2 |
|---|---|---|---|---|---|---|---|---|
| NC_PI0, reco 1γ0p | 102 | 99 | 88 | 431 | 71 | 0.62 | 49 | 68 / 28 / 6 |
| NC_PI0, reco 1γ1p | 68 | 64 | 47 | 281 | 84 | 0.44 | 68 | 8 / 50 / 10 |
| CC_PI0, reco 1γ0p | 43 | 39 | 36 | 496 | 83 | 0.57 | 52 | 17 / 20 / 6 |
| CC_PI0, reco 1γ1p | 42 | 41 | 34 | 445 | 98 | 0.51 | 42 | 4 / 29 / 9 |

In **every** channel the selected shower is a daughter photon of the π⁰ (91–98 % of the candidates: 99/102, 64/68, 39/43, 41/42), predominantly the leading photon (selected in 86 %, 69 %, 84 % and 81 % of the four rows). The decay is highly asymmetric (median asymmetry 0.44–0.62; subleading photon median 71–98 MeV): the subleading photon is typically soft but **not** typically below 20 MeV (below 20 MeV in 15/102, 8/68, 3/43, 2/42).

## 3. Fate of the other photon (labels overlap; counts of candidates; the "other" photon is the daughter not matched to the selected shower)
| label | NC π⁰ 0p (102) | NC π⁰ 1p (68) | CC π⁰ 0p (43) | CC π⁰ 1p (42) |
|---|---|---|---|---|
| truth E < 20 MeV | 15 | 8 | 3 | 2 |
| no charge in blobs | 10 | 10 | 1 | 3 |
| exits the provisional TPC (end point outside) | 12 | 12 | 2 | 4 |
| no reco row at all | 10 | 10 | 1 | 3 |
| dominant reco row is in **another** candidate | 28 | 13 | 13 | 8 |
| dominant row in the same candidate, another row | 30 | 33 | 14 | 12 |
| … that row is not a shower / not type 11 (PID failure) | 16 | 21 | 6 | 9 |
| **merged with the selected shower** (same row dominant or charge shared) | 43 | 17 | 17 | 21 |
| selected shower not a π⁰ daughter / other photon absent in the record | 3 + 4 | 4 + 2 | 4 + 0 | 1 + 0 |

Reading (descriptive; no unique cause is claimed): the "single photon" appearance of a π⁰ comes from a **mixture** of mechanisms. In the reco 1γ0p NC π⁰ sample the largest single mechanisms are the other photon being **merged into the selected shower** (43 of 102), **reconstructed as a different object/candidate** (28 in another candidate, 30 in another row of the same candidate), and **lost or invisible** (no row 10, exits 12, no charge 10, < 20 MeV 15). In the 1γ1p NC π⁰ sample "another row of the same candidate" (33, of which 21 non-shower/PID failures) and "other candidate" (13) dominate and merging is rarer (17). CC π⁰ is similar in 0p and 1p (merging 17/43 vs 21/42).

## 4. Does the π⁰ mechanism differ between reco 0p and 1p?
Little in the photon-side mechanisms (the same labels appear in both), but the **proton content differs strongly and is physical**: truth protons of the NC π⁰ interactions are 0p in 68 of 102 reco-1γ0p and 1p in 50 of 68 reco-1γ1p (truth 1p → reco 0p: 28; truth 0p → reco 1p: 8). So for π⁰ backgrounds the split into 1γ0p/1γ1p mostly follows the true proton topology of the interaction, with a minority of migrations (`EXCLUSIVE_BACKGROUND_MECHANISMS.md` §10). The photon-side differences between channels (more "other row/PID failure", fewer merges in 1γ1p NC π⁰; softer lead photon, 281 vs 431 MeV, and wider opening angle, 68° vs 49°) are descriptive and rest on 68–102 candidates.

## 5. Limits
Truth tracks without charge in blobs are invisible to the overlap labels; "no reco row" means no `T_overlap` row for any track of that photon's shower in any candidate. Labels depend on the definitions in `photon_fate_labels`; the 'exits' flag uses the provisional box and the photon end point only. Statistics are one to two hundred candidates per cell.
