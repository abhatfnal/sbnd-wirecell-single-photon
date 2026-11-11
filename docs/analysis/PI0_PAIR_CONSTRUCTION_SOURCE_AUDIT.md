# How the two "pi0 pairs" of the frozen ncpi0 BDT are built: source audit of `kine_pio_*` and `shw_sp_pio_*`

Date: 2026-11-11. Branch `analysis/ncdelta-pi0-pair-fragmentation-audit-20261111`. Audit only: nothing is retrained, tuned or re-selected. Tags: **SOURCE** (read in code), **MEASURED** (checked on the official Gen2 NC-Delta products, pair-recovery tables in `tables/pi0_pair_fragmentation_audit/`), **NOT AUDITED** (stated, not assumed).

**Source:** `HaiwangYu/wire-cell-toolkit`, branch `sbnd-wc-flatcaf`, **commit `4b6853d4`** (the producer-declared fg1 pin; files read at that commit with `git show 4b6853d4:...`, not the checked-out review tree `58e99669`). Line numbers below are in `clus/src/NeutrinoShowerClustering.cxx` (`NSC`), `clus/src/NeutrinoKinematics.cxx` (`NK`) and `clus/src/NeutrinoTaggerSinglePhoton.cxx` (`NTSP`) at that commit. **Knob defaults** are those of `clus/inc/WireCellClus/NeutrinoPatternBase.h:2309-2342`; the production job configuration is **not public and not audited** (`WIRECELL_TRUTH_MATCH_SEMANTICS.md` section 1), so every statement "knob X is off" means "off in the source default"; the data are consistent with the defaults (section 6).

## 1. Headline

* **The two pairs are different objects built by the same pair finder.** `kine_pio_*` is the shower pair with the **largest `E1 + E2`** among all pairs the finder considers, with **no mass requirement at all**. `shw_sp_pio_*` is a **mass-window pair** (the pair is accepted only if its mass is within the pi0 window) that must **contain the tagger's selected shower**. Neither output stores the identity of its members.
* So `kine_pio_flag != 0` does **not** mean "the reconstruction found a pi0". It means "the candidate has two showers that can be paired, at least one of them detached". In the official Gen2 NC-Delta events that reach ncpi0 the median `kine_pio_mass` of a kinematics-tree-only pair is **47.7 MeV**; **74.5 %** are below 100 MeV and **6.9 %** inside 100-170 MeV (`NCPI0_PAIR_MEMBER_TRUTH_AUDIT.md` section 8).

## 2. Common machinery: the pair finder `id_pi0_with_vertex` (path 1, NSC:7250-8033)

Called from `shower_clustering_with_nv` (NSC:10230-10275) after the back-projection proposer and the shower splitter; `Pi0KineFeatures pio_kine{}` is **zero-initialised** in `TaggerCheckNeutrino.cxx:3621` / `CheckBeamParticle.cxx:2097` (flag 0 = no pair) and written to `T_kine` in `NK:1267-1283` (angles converted to degrees, lengths to cm, energies to MeV).

**Object collection (SOURCE).** Showers reachable through `map_vertex_to_shower` (`Shower` objects of the candidate's graph), never tracks. For each **candidate vertex** (the main vertex plus every vertex that is not inside a shower or that is some shower's start vertex; NSC:7346-7360) the pool is:

| member kind | rule | direction used |
|---|---|---|
| attached shower | connection type 1 (start vertex = the candidate vertex), `abs(pdg) != 13` | the shower's `init_dir` |
| disconnected shower | connection type **2** (type 3 only with `m_pi0_admit_type3`, **off**); either its own start vertex is the candidate vertex, or the angle between its 15 cm PCA direction and the ray candidate-vertex to shower start is **< 30 deg** (`m_pi0_assoc_angle_deg`) | `init_dir` (own-start) or the vertex-to-start ray |

PID requirement: **only `abs(pdg) != 13`** (muon-typed showers excluded unless `m_pi0_admit_mu_showers`, off). **Electron typing is not required**: pion-, electron- and **proton-typed** shower objects all enter. Re-typed hadronic showers (`m_hadronic_retyped_shower_ids`) are excluded (`m_pi0_readmit_retyped` off). No energy threshold, no same-cluster requirement and no truth are used (NSC:7366-7398, 7483-7559).

**Pairs and mass (SOURCE; NSC:7604-7665).** Every unordered pair `(i < j)` in the pool, **except a pair of two attached showers** (`ct1 == 1 && ct2 == 1` is skipped, NSC:7618), gets `m = sqrt(4 kq1 kq2 sin^2(theta/2))` where `kq = Shower::get_kine_charge()` (the **charge-based** energy, not `kine_best`) and `theta` the opening angle of the two directions above, recorded per candidate vertex.

**Measured confirmation of the "at least one detached member" rule:** of the 1,580 pairs identified by energy alone (both members), **none** violates it.

## 3. `kine_pio_*` (the `T_kine` pair)

**Selection ("BDT feature" block, NSC:7668-7725), flag 1.** Loop over all recorded pairs; keep the pair with the **largest `E1 + E2`** (strictly greater than the running maximum, so a tie keeps the first in the iteration order of the pair map, which is ordered by shower graph index: `shower_pair_cmp`, NSC:7265-7271). A pair is eligible only if one of its recorded vertices is the **start vertex of one of the two members** (`cand_vtx == sv1 || sv2`); among such vertices the one **closest to the main vertex** is used. **No mass cut, no window, no ranking by mass.**

| field | definition (SOURCE) |
|---|---|
| `kine_pio_energy_1/2` | `get_kine_charge()` of the pair's first / second shower (graph-index order), MeV |
| `kine_pio_dis_1/2` | distance from the pair vertex to each shower's start point, cm |
| `kine_pio_vtx_dis` | distance from the pair vertex to the main vertex, cm |
| `kine_pio_theta/phi_1/2` | polar angle `acos(dz/|d|)` and `atan2(dy, dx)` of each member's direction, degrees; direction = `shower_cal_dir_3vector` over 15 cm at the shower's own start vertex if `dis < 3 cm`, else the vertex-to-start ray |
| `kine_pio_angle` | angle between those two directions, degrees |
| `kine_pio_mass` | the **recorded pair mass** (NSC:7639), computed with the earlier directions and charges; **it is not recomputed from the stored angle** (so `sqrt(4 E1 E2 sin^2(angle/2))` need not equal it; measured: within 1 MeV for 1,293 of 1,946 events with a finite angle, median difference 0.004 MeV) |
| `kine_pio_flag` | **0** no pair; **1** the with-vertex pair above; **2** overridden by the without-vertex finder |

**Flag 2 (NSC:8191-8641, `id_pi0_without_vertex`).** Runs only if the main vertex has at most `m_pi0_nv_max_prongs = 2` segments, at least one of them in a shower and none in the long muon (NSC:8212-8246). It builds pairs whose "apex" is the closest approach of the two shower axes (collinearity test at 25 deg) and **overrides all `pio_kine` fields with flag 2 for the pair whose `E1 + E2` is >= the running maximum, which starts at the flag-1 pair's `E1 + E2`** (`if (energy_1 + energy_2 < max_energy) continue`, so **ties override**). Measured: 1,894 events with flag 1, **58 with flag 2**.

**Stored identities: none.** `T_kine` stores the twelve numbers only; `T_pf` / `T_segment` carry no pair id. The pair members must be recovered (`NCPI0_PAIR_MEMBER_TRUTH_AUDIT.md` section 4).

## 4. `shw_sp_pio_*` (the tagger pair)

**Where the pair comes from (SOURCE).** Three producers fill `map_shower_pio_id` (shower -> `pio_id`), `map_pio_id_showers` (`pio_id` -> `[shower_1, shower_2]`) and `map_pio_id_mass` (`pio_id` -> `(mass, pio_type)`):

1. `id_pi0_backproject_vertex` (`pio_type` 2, NSC:6581-7236): only with `m_pi0_bp_miss > 0`, **off**.
2. **`id_pi0_with_vertex` acceptance loop (`pio_type` 1, NSC:7728-8033):** from the same recorded pairs, repeatedly take the pair minimising `|m - 135 MeV + 10 MeV|` over the **window `-25 < m - 135 + 10 < 35` MeV, i.e. 100 < m < 160 MeV**, with a 6 MeV bonus for pairs of two connection-type-2 showers (`tmp_penalty`, NSC:7763-7788). The pair is registered (NSC:7988-7994), both members are **re-seated at the pair vertex with connection type 2** and their kinematics recomputed (NSC:7998-8009), and **every other pair that involves either member is deleted** before the next iteration. So several accepted pairs per candidate are possible.
3. `id_pi0_without_vertex` (`pio_type` 2, NSC:8651-8736): best `|m - 135 + 10|` below `m_pi0_nv_mass_window = 60 MeV`, requires **at least one member in `good_showers`**.

**What reaches the output (SOURCE; NTSP:2056-2182 `pi0_identification_sp`).** The tagger picks **one selected ("max") electron shower** (highest `kine_best` among showers that are > 20 MeV, pass br1/br3/br4; NTSP:2395-2505). If that shower is in `map_shower_pio_id`: `shw_sp_pio_flag_pio = 1` and

* `shw_sp_pio_1_energy_1/2` = `get_kine_charge()` of `tmp_pi0_showers.front()` / `.back()`;
* `shw_sp_pio_1_dis_1/2` = distance of each member's start point from the **tagger's vertex point**;
* `shw_sp_pio_1_mass` and `shw_sp_pio_1_pio_type` = the registered mass and type (1 or 2);
* `shw_sp_pio_1_flag` additionally requires `mass_ok` (type 1: `|m - 135| < 35`; type 2: `< 60` MeV), `min(E1, E2) > 15 MeV` with an energy asymmetry `< 0.87` (or `min > 10 MeV` and `max < 400 MeV`), and two vetoes for very asymmetric, far-apart pairs (NTSP:2098-2124).

If the selected shower is **not** in the map: `shw_sp_pio_flag_pio = 0` and the `pio_2` back-to-back search over other clusters' vertices runs instead (`shw_sp_pio_2_v_*`; not a pair).

**Stored identities: none.** Both shower ids exist in memory (`map_pio_id_showers`) and **neither is written**.

## 5. Are the two algorithms identical, overlapping or different?

**Overlapping inputs, different objects.**

| | `kine_pio_*` | `shw_sp_pio_*` |
|---|---|---|
| shower pool and pair masses | the same recorded pairs | the same recorded pairs (type 1) |
| selection | largest `E1 + E2`, **any mass** | smallest `|m - 125|` inside **100-160 MeV** (type 1; 65-185 for type 2) |
| must contain the tagger's selected shower | **no** | **yes** (measured: 262 of 262 exactly identified pairs) |
| member PID | `abs(pdg) != 13` | `abs(pdg) != 13` (type 1/2), the selected shower is an electron |
| several pairs per candidate | one (the maximum) | possibly several; only the one with the selected shower is output |
| ties | first in graph-index order (flag 1); override (flag 2) | first in map order |
| identities stored | no | no |

They coincide only when the maximum-energy pair also lies in the mass window and contains the selected shower: of the 271 events with a tagger pair and the 1,952 with a kine pair, **125** have the same recovered pair, 57 share one member, 20 have different pairs, 7 are unresolved (`NCPI0_PAIR_MEMBER_TRUTH_AUDIT.md` section 7).

## 6. Source versus data

* **Mass window:** all 168 tagger pairs of `pio_type` 1 have `100.2 < m < 159.4 MeV`, exactly the source window (100, 160); the 103 pairs of type 2 lie in 62.8-181.5 MeV (96 % inside 75-195; type 2 also contains the re-priced back-projection family).
* **One member is the selected shower:** 262 of 262 exactly identified tagger pairs contain a row whose energy equals `shw_sp_energy` (selected electron shower).
* **Defaults:** every checked consequence of the default knob values holds; no evidence of a non-default pi0 knob was found, which is **not a proof** (NOT AUDITED).

## 7. What is not established here

* The production job's value of every `m_pi0_*` knob (default-off assumed, consistent with the data).
* The direction of a shower (`shower_cal_dir_3vector`) and `get_kine_charge` of a row are **not stored** in the flatCAF; only `kine_best` is. This limits the pair recovery (`NCPI0_PAIR_MEMBER_TRUTH_AUDIT.md` section 4).
* The physical reason for the 10 MeV offset and the 100-160 MeV window (inherited from the MicroBooNE prototype; not derived here).
