# Multi-candidate event policy audit (RECOMMENDATION, not a final decision)

Sample: official BNB CV, all 37,742 files (500,000 events, 499,899 `wc.valid`), frozen baseline chain, **no FV**. Truth diagnostics use the first 11,999 files (`scripts/truth_match_scan.py`) and are used **only to evaluate** policies in MC, never to choose a candidate. Tables: `tables/candidate_policy/`. Scripts: `scripts/baseline_scan.py`, `scripts/truth_audit_report.py`, `src/sbnd_single_photon/scanio.py`.

## 1. Production semantics (Wire-Cell source)

Source: `/exp/sbnd/app/users/yuhw/wct-pr543/clus/src/TaggerCheckNeutrino.cxx` (PR #543 tree; **not necessarily the production build 4b6853d4**, so the data were used to cross-check).
- A candidate is one **in-beam flash bundle** (flash gid → main cluster + companions), "doc pr/94": one `T_tagger`/`T_kine` row per bundle; `nu_index` is the row position.
- **Ordering carries a rule, not a physics score:** candidates are stable-sorted by the *selected activity's length, longest first* (ties by gid). Comment in source: "candidate 0 keeps the unnamed TrackFitting slot ... slot 0 now holds the same candidate the pre-pr/94 chain would have chosen, and nu_index 0 means 'primary'". So `nu_index == 0` = the legacy selector's choice (longest), deterministic and data-applicable.
- **Independent candidates are possible by design:** each in-beam flash can make its own bundle. One physical flash seen by both drift volumes arrives as two opflash gids and would make two candidates; WCT has a knob `nu_dedup_flash_group` that keeps the longest candidate of each flash group, **default OFF**.
- `T_bundle` has one row per examined bundle (including dropped ones, with a rejection reason), `T_flash` the flashes (`in_window`, `flash_group`, `nu_index`).

## 2. Frequencies (full sample, `wc.valid` events)

| candidates per event | events | fraction |
|---|---|---|
| 0 | 262,439 | 52.50 % |
| 1 | 233,089 | 46.63 % |
| 2 | 4,357 | 0.87 % |
| 3 | 14 | 0.003 % |

Among the 4,371 multi-candidate events: **65 (1.5 %)** have all candidates in the same `flash_group` (two TPC copies of one flash, one per `flash_tpc`, times differing by 0.1–25 ns in the examples inspected); the other 4,306 have different flash groups (median Δ flash time 0.6 µs). So WCT's flash-group dedup would remove at most 65 events.

## 3. Truth diagnostics (MC only; 1,343 multi-candidate events with a truth match in the first 12k files)

Candidate kind: dominant truth neutrino of the candidate's charge (`T_overlap` ↔ `T_truth_track`), "nu_active" if ≥50 % of charge is from a neutrino whose vertex is inside the *provisional taxonomy box*, "nu_dirt" if outside it, else "cosmic". Pair = the first two candidates.

| class | events | share |
|---|---|---|
| two different active-volume neutrinos | 936 | 70 % |
| active-volume ν + dirt ν | 200 | 15 % |
| active-volume ν + cosmic | 108 | 8 % |
| same interaction split over two candidates (active) | 63 | 5 % |
| dirt/dirt, cosmic+dirt, same-interaction dirt, cosmic/cosmic | 12 + 12 + 8 + 4 | 3 % |

Reading: most multi-candidate events are **genuinely independent interactions** in the same spill window (consistent with 8,164 CV events having two active-volume neutrinos), not duplicates of one interaction. The 65 same-flash-group events do not appear in this truth-matched table (their second candidates have no truth overlap in this scan), so the "same interaction split across TPCs" case is not measured by it. When the pair is ν + cosmic (120 events, ν = active or dirt), `nu_index 0` is the neutrino-dominated candidate in 78 and the cosmic-dominated one in 42: the length ordering favours the neutrino but is not a reliable discriminator (`multicand_kind_of_index0_vs_index1.csv`).

## 4. Consequences for the baseline cut-flow (full CV)

| policy | selected events | note |
|---|---|---|
| `first` (nu_index == 0) | 626 | |
| `any` | **649** | +23 events whose passing candidate has nu_index > 0 |
| `dedup_any` (WCT flash-group rule, then any) | 649 | identical to `any` |

- **No event has more than one candidate passing the full chain** (0 events), so candidate-level and event-level counts are both 649 under `any`; `first` loses 3.5 %.
- Beam-on (open): 77 selected under every policy; beam-off: 6; nueCC: 15,886 (`any`), 15,531 (`first`), one event with two passing candidates.
- Purity of the *selected candidate* (MC evaluation): neutrino-dominated 98.4 % for both `first` and `any`; active-volume-neutrino-dominated 81.4 % for both. `any` adds candidates of the same quality, it does not dilute the sample.
- Reco proton category of the selected event is that of the chosen candidate (`first`: 307/226/93 for 0p/1p/≥2p; `any`: 318/236/95).

## 5. Recommendation (provisional)

1. **Use `any` as the working policy, counting the passing candidates (= events here), and always report `first` alongside.** Reasons from the data: candidates are mostly independent interactions; no event has two passing candidates; `any` selects equally pure candidates; it uses only reconstruction information and works identically on data. It is also what the baseline cut-flow already used.
2. `first` (WCT's own "primary") is the natural alternative if an analysis needs exactly one candidate per event; the cost is 3.5 % of the CV selection.
3. Do **not** introduce a "best score" policy: no reconstruction rationale was found (the order is by length, not score).
4. `dedup_any` is supported by WCT semantics but changes nothing in this baseline.

**This is a recommendation, not a final decision.** The policy must be re-checked with the official Gen2 NC-Δ sample: a signal event with a second spurious candidate, or whose signal candidate is not `nu_index 0`, can only be evaluated there.

## 6. Questions for Haiwang / Hanyu

- Is the production build's candidate sorting/dedup identical to the PR #543 tree read here, and is `nu_dedup_flash_group` off in production?
- Is more than one in-window flash per spill expected in the BNB CV overlay (the 936 two-neutrino events), and how should it be counted for POT?
- Should an event with two interactions count once or twice for an event-level rate?
- For the 65 same-flash-group events, is the second candidate of a same-flash-group pair (the other `flash_tpc`; the examples inspected had zero >20 MeV showers) a known artefact?
