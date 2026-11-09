# Candidate-associated background taxonomy (second taxonomy; the event-level one is kept)

The existing event-level category (`BNB_TRUTH_CATEGORY_AUDIT.md`, `events.t_code`) is **not replaced**. This adds a second taxonomy tied to the **passing reconstructed candidate** through the production candidate association of `PASSING_CANDIDATE_TRUTH_ASSOCIATION.md` (top `wc.T_match` level-3 match). MC evaluation only; frozen baseline, `any`, 35 MeV, no FV. Table: `tables/background_mechanisms/candidate_truth_category.csv` (one row per passing candidate, with the old category, the new category and the match quality).

## 1. Definition (code: `background_truth.classify_candidate`, `background_mechanisms.add_categories`)
In order: **COSMIC_OR_UNMATCHED** (no match, or the top match is a cosmic truth object) → **MULTI_OR_AMBIGUOUS** (overlaps ≥ 2 distinct truth neutrinos) → **SIGNAL_NCDELTA** (matched interaction is a qualifying natural NC Δ → Nγ neutrino; used only to separate signal-like events) → **OUTSIDE_TPC_NU** (matched neutrino vertex outside the *provisional* TPC box |x|,|y| < 200, 0 < z < 500 cm — descriptive, not an FV) → pi0 (matched interaction has ≥ 1 π⁰ among its GENIE G4 primaries: **NC_PI0** / **CC_PI0**) → **NUE_CC** (|PDG| 12, CC) → **NUMU_CC** → **OTHER_NC** → **OTHER_CC**. The pi0 precedence over flavour follows the event-level taxonomy (so a ν_e CC with a π⁰ is CC_PI0). `rec.mc.nu.npizero` is not used (almost always 0); π⁰ comes from the primaries (`TRUTH_PROTON_DEFINITION_AUDIT.md` §1). Nothing in the event outside the matched interaction can change the label.

## 2. Accounting (exact; `tables/background_mechanisms/summary.json`)
649 selected `any` events = **14 signal-like + 635 non-signal + 0 mixed** (reproduces the validated Phase-2 numbers; the 14 signal-like events are exactly the 14 `SIGNAL_NCDELTA` candidates). The 635 split by reco channel 310 / 230 / 95 (1γ0p / 1γ1p / ≥2p diagnostic) and by candidate-associated category:

| category | 1γ0p | 1γ1p | ≥2p diag | total |
|---|---|---|---|---|
| NC_PI0 | 102 | 68 | 22 | 192 |
| NUE_CC | 53 | 86 | 36 | 175 |
| CC_PI0 | 43 | 42 | 21 | 106 |
| OUTSIDE_TPC_NU | 75 | 17 | 3 | 95 |
| NUMU_CC | 11 | 6 | 7 | 24 |
| OTHER_NC | 10 | 7 | 4 | 21 |
| COSMIC_OR_UNMATCHED | 14 | 0 | 1 | 15 |
| MULTI_OR_AMBIGUOUS | 2 | 4 | 1 | 7 |
| **total** | **310** | **230** | **95** | **635** |

No event is dropped; every ambiguous event is in `MULTI_OR_AMBIGUOUS`. (OTHER_CC is empty.)

## 3. Comparison with the event-level category (635 non-signal events; `old_event_vs_candidate_associated_crosstab_635.csv`)
**574 unchanged, 61 change interpretation** under the mapping NC_PI0, CC_PI0, NUE_CC, NUMU_CC, OTHER_NC, OTHER_CC identical; `DIRT_NO_ACTIVE` ↔ OUTSIDE_TPC_NU; `COSMIC_NO_NU` ↔ COSMIC_OR_UNMATCHED; `MULTI_ACTIVE` has no equivalent (the event-level category could not say which interaction produced the candidate). Of the 61, **40 were `MULTI_ACTIVE`** (several in-box interactions: 14 → NC_PI0, 12 → NUE_CC, 5 → CC_PI0, 3 → NUMU_CC, 1 → OTHER_NC, 5 stay ambiguous) and **21 were resolved differently**:

| old event-level → new candidate-associated | n |
|---|---|
| DIRT_NO_ACTIVE → COSMIC_OR_UNMATCHED | 11 |
| NUMU_CC → OUTSIDE_TPC_NU | 4 |
| NUMU_CC → COSMIC_OR_UNMATCHED | 2 |
| DIRT_NO_ACTIVE → MULTI_OR_AMBIGUOUS | 1 |
| NUE_CC → COSMIC_OR_UNMATCHED | 1 |
| NUE_CC → MULTI_OR_AMBIGUOUS | 1 |
| OTHER_NC → COSMIC_OR_UNMATCHED | 1 |

Examples (event key `(file_index, ev)`): (10395, 8) and (15362, 1) old DIRT_NO_ACTIVE → cosmic/unmatched (top-match IoU 0.19 / 0.31, no neutrino); (7808, 10) and (9220, 3) old MULTI_ACTIVE → CC_PI0 (IoU 0.97 / 0.92 to a ν_μ CC π⁰ in the TPC); (1000, 2) old MULTI_ACTIVE → ambiguous (IoU 0.30, overlaps two neutrinos). Takeaways (descriptive): the old DIRT_NO_ACTIVE group (104 events incl. 1 signal and 1 ambiguous) is 91 genuine outside-TPC neutrino candidates plus 11 candidates with no matched neutrino (cosmic or unmatched); the old MULTI_ACTIVE group is resolved to a single interaction for 35 of its 40 non-signal events and stays ambiguous for 5; the 9 ν_μ CC / ν_e CC / NC-labelled events that become outside-TPC, cosmic or ambiguous show that "an interaction of that type exists in the event" was not always the one the selected candidate was built from. The old category of the 14 signal events was 12 OTHER_NC, 1 MULTI_ACTIVE and 1 DIRT_NO_ACTIVE.

## 4. Caveats
* The categories are of the matched *interaction*; the selected single-photon-like shower may still come from a different particle of it (`SELECTED_SHOWER_TRUTH_MATCH_AUDIT.md`).
* The in/out-of-TPC distinction uses the provisional box; OUTSIDE_TPC_NU is not called "dirt" in these tables because the production truth only says the vertex is outside the box (`OUTSIDE_TPC_AND_COSMIC_BACKGROUND_AUDIT.md`).
* The same taxonomy for all 241,845 candidates (cutflow by class) uses the `T_overlap` dominant-charge neutrino instead of `T_match` (see `EXCLUSIVE_BACKGROUND_MECHANISMS.md` §11).
