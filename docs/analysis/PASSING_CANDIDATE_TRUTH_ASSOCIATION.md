# Passing-candidate truth association (BNB CV, frozen baseline, policy `any`)

> **Revalidated against the matcher's design document (see `WIRECELL_TRUTH_MATCH_SEMANTICS.md`, 2026-11-09).** The production top partner of a candidate is the FIRST stored partner (largest *point* IoU), not the largest *charge* IoU that Phase 4 used. Rule change affects 2 of the 649 selected candidates' top partner and exactly **1 category**: (file 32366, run 8060, subrun 80, evt 5) OTHER_NC -> COSMIC_OR_UNMATCHED (1γ1p; both IoUs are tiny: 0.096 for the old top neutrino vs 0.054 point-IoU for a cosmic object). All numbers below are the revalidated ones; the Phase-4 tables are preserved on the pushed Phase-4 branch.

MC **evaluation only**. The selection (`wc.valid == 1`, frozen BDT cuts, `any`) is decided from reconstruction alone (the derived analysis table); truth is attached **afterwards** to the candidates that already passed. No threshold is invented, no cut changed. Code: `src/sbnd_single_photon/background_truth.py` (association), `scripts/background_mechanisms_scan.py` / `scripts/background_deep.py` (scan), `src/sbnd_single_photon/background_mechanisms.py` (tables). Data (outside Git): `$SP_DATA/background_mechanisms/bnb_cv/`.

## 1. What each truth source contains (inspected on merged CAFs; the production source is not in this repository, so semantics are *inferred from the stored data* and stated as such)

| source | content | role here |
|---|---|---|
| `wc.T_match` | production **bipartite reco↔truth matching**. Rows are objects (one row = one object, not a pair) with `level` (0 cluster, 1 particle, 2 candidate by `T_kine` segments, 3 candidate by particle-flow-tree segments; source-defined, `WIRECELL_TRUTH_MATCH_SEMANTICS.md`), `side` (0 = reconstructed, 1 = truth), `obj`, `nu_index`/`kine_index`/`cluster_id` (reco side), `truth_nu_idx`/`truth_trackid` (truth side), `size_q`, `truth_q_in_blobs`, `nmatch`, and per object the lists `match_obj`, `match_iou_q`, `match_shared_q` (charge IoU / shared charge with each matched object), `match_iou_n`, `match_shared_n`, plus `mutual`. Verified on events: `level == 3`, `side == 0` is the whole reconstructed neutrino candidate (`nu_index`); `level == 3`, `side == 1` are truth objects: `truth_nu_idx >= 0` a truth neutrino interaction, `truth_nu_idx == -1` with `truth_trackid > 0` a cosmic (non-neutrino) truth object. Levels 0 (clusters), 1 (particles vs prongs) and 2 (candidate by `T_kine` segments) were **not** used. | **primary candidate association** |
| `wc.T_overlap` | per (candidate `nu_index`, reco particle `particle_id`, segment) the shared charge `q` with a truth `trackid` (and its `nu_idx`), with `in_enu`/`in_pf` flags | dominant-charge cross-check association; reco shower row → truth track |
| `wc.T_truth_nu` | the truth neutrino interactions known to Wire-Cell (`nu_idx`, `pdg`, `ccnc` (0 = CC), `mode`, `int_type`, `E`, vertex, `edep`) | matched-interaction properties |
| `wc.T_truth_track` | Geant4 tracks with charge in the blobs: `trackid`, `nu_idx` (−1 = not from a neutrino), `pdg`, `mother_trackid`/`mother_pdg` (0 = G4 primary), `process`, `ancestor_trackid` (top-level G4 primary the track descends from), `prong_trackid` (the shower/prong-initiating particle), `q_in_blobs`, `start_E` (total energy, GeV) | origin of a shower/proton row |
| `wc.T_truth_pf` | truth particle tree per truth neutrino (`nu_row` = `nu_idx`): the G4 primaries **and** decay products (e.g. π⁰ → γγ with `parent_trackid`), `E`, `KE` (GeV), start/end positions, start momentum — present even for particles that leave no charge | π⁰ decay chain, truth primary protons |
| `wc.T_pf` | reconstructed particle-flow nodes (`node_id`, `parent_id`, `pdg`, `ke_mev`, `kine_index`) | **not used** (reco side only; the proton/shower rows are read from `T_kine`) |
| `rec.mc.nu` (+ `prim`) | CAF truth per interaction: flavour, CC/NC, mode, vertex, GENIE primaries (π⁰ count, protons KE) | taxonomy flags and the truth proton category |
| `GenieEvtRecTree` | full GENIE record (reached through `rec.mc.nu.genie_evtrec_idx`) | **signal definition** only (NC Δ → Nγ ancestry; `NATURAL_NCDELTA_CV_CROSSCHECK.md`) |

The Wire-Cell truth neutrino is linked to its `rec.mc.nu` index by vertex (nearest within the event): the largest distance over the 649 passing candidates is 2.7e-5 cm and **0** neutrino matches are unlinked.

## 2. The association rule (exact)

For every passing candidate (event key `(file_index, ev)`, candidate `nu_index`; implemented for any number of passing candidates per event):

1. From `T_match` level 3, take the matched truth objects of the candidate and take the production's own ranking: partners are stored in order of decreasing **point IoU `match_iou_n`** (ties charge IoU, then lower object index; at most 3), so the **top match** is the first stored partner (Phase 4 had used the largest charge IoU; revalidated, banner above). The **top match** gives the matched object: a truth neutrino index (`tm_top_nu`) or a cosmic object (−1) or none (−9, `tm_n == 0`).
2. Match quality retained: `tm_top_iou`, `tm_top_shared`, `tm_second_iou`, `tm_n` (number of matches), `tm_n_distinct_nu` (distinct truth neutrinos among all matches), `tm_n_cosmic`, `tm_mutual`.
3. Candidate class: **cosmic_or_unmatched** (no match or the top match is a cosmic object), **ambiguous/mixed** (the candidate overlaps ≥ 2 *distinct* truth neutrinos: a structural criterion, no IoU threshold), **signal_matched** (top match is a qualifying NC Δ → Nγ neutrino of the natural-signal list), else **neutrino_matched** (the exact truth-neutrino index and its `rec.mc.nu` index `mnu_k` are kept).
4. Event level: an event counts once; if it has several passing candidates with different categories it is labelled `MULTI_OR_AMBIGUOUS` (explicit, never silently resolved); a signal-matched and a non-signal passing candidate would give `mixed` in the signal/background bookkeeping (`natural_signal.classify_selected_events`, vertex-based, evaluation only). Event-level content never overrides the passing candidate's matched interaction.

## 3. Measured on the 649 selected events (`any`; every event has exactly one passing candidate)

| quantity | value |
|---|---|
| passing candidates / events | 649 / 649 (0 events with several) |
| top match is a neutrino / cosmic-or-unmatched | 633 / 16 |
| candidates overlapping ≥ 2 distinct truth neutrinos | 7 |
| top match flagged `mutual` | 628 (21 not mutual; kept as information, not used to alter the label) |
| `match_iou_q` of the top partner, quantiles (0, 5, 25, 50, 75, 95, 100 %) | 0.027, 0.45, 0.68, 0.82, 0.90, 0.97, 1.00 |
| neutrino top match that also overlaps a cosmic object | 98 |
| agreement of the `T_match` top neutrino with the `T_overlap` dominant-charge neutrino (`dom_nu`) | 646 / 649 (99.5 %); the 3 disagreements are listed in `tables/background_mechanisms/association_disagreements_Tmatch_vs_Toverlap.csv` |
| signal-matched by `T_match` | 14; the same 14 events as the vertex-based signal-like classification (14 signal-like + 635 background + 0 mixed) |

Low `match_iou_q` is common for genuinely neutrino-matched candidates (a fraction of the candidate's charge belongs to overlapping cosmics); no threshold is applied on it. The table `tables/background_mechanisms/candidate_truth_category.csv` carries all match-quality fields for every passing candidate.

## 4. Limits
* The meaning of `T_match` levels/flags is inferred from the data; confirming it with the Wire-Cell authors is an open question (added to `QUESTIONS_FOR_HAIWANG_HANYU.md`).
* For all 241,845 candidates the association is the `T_overlap` dominant-charge neutrino (`BACKGROUND_CUTFLOW_BY_CLASS`, `EXCLUSIVE_BACKGROUND_MECHANISMS.md` §11), because `T_match` was evaluated only for the passing candidates and a file subset; the two agree on the subset (see that document).
* The provisional TPC box (|x|,|y| < 200, 0 < z < 500 cm) only separates in-TPC from outside-TPC interactions; it is not a fiducial volume.
