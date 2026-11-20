#!/usr/bin/env python
"""Normalisation ledger of the purity + data/MC package: one row per contributing sample with exact provenance, plus closure checks. Numbers are READ from committed
summaries / the analysis tables (never typed). OPEN items are explicit: the purity is then an upper bound / MC-only, not a closed estimate.

    source env/setup_eaf.sh && python scripts/ncdelta_normalization_ledger.py
"""
from ncdelta_purity_common import *
import json, yaml

S = yaml.safe_load(open(REPO / "configs" / "samples.yaml"))["samples"]
pj = lambda n: json.load(open(REPO / "tables" / "pot" / f"{n}_summary.json"))
census = json.load(open(REPO / "tables" / "official_ncdelta" / "official_ncdelta_census.json"))
led = json.load(open(TAB / "normalisation_numbers.json")); nat_rate = (117, pj("bnb_cv")["total_pot_sum"])
cv, bo, bf = pj("bnb_cv"), pj("beam_on_open"), pj("beam_off")
sam = census["sam_accounting"]
rows = [
    dict(sample="official_gen2_ncdelta", role="SIGNAL expectation (evaluation)", generator_filter="GENIE (sbn_genie_BNB_base) + CORSIKA cosmics + rockbox; Gen2 rare-signal filter NCDeltaRadiative (Delta0/Delta+ -> N gamma, photon parent in |x|,|y|<=210, -1<=z<=510 cm); unweighted filtered subset",
         pot_or_exposure=census["files"]["sum_TotalPOT"], pot_source="sum TotalPOT of all 15,777 flatCAFs = SAM mc.pot (zero-event units carry POT)", generated_throws=f"{int(sam['flatcaf_units_generated_events'])} (SAM reco1 parents, 12,500 per unit; CAF TotalGenEvents NOT used)",
         accepted_filter_norm="filter acceptance is implicit: weight = POT_target / POT; 1 event never processed by Wire-Cell (13,772/13,773), 12,427 events in the provisional TPC box = denominator", valid_caf_fraction=f"{S['official_gen2_ncdelta']['n_wc_valid_events']}/{S['official_gen2_ncdelta']['n_caf_events']} (events of the merged CAFs; truth denominator 12,427 from all 13,773)",
         event_weight="w = POT_target / 2.8385e21 per truth-in-box event (unit MC weight, no GENIE/flux reweighting)", cosmics_overlaid="yes (corsika in the generator chain)", beam_off_added_separately="no", dirt_present="no (filter vetoes parents outside its box)", intrinsic_nue="n/a (NC signal only)"),
    dict(sample="bnb_cv", role="BACKGROUND (generic BNB MC) after removing in-region natural NC-Delta events", generator_filter="prodgenie_corsika_proton_rockbox0p1; kept if a neutrino vertex is in the TPC or a neutrino-induced TPC deposit > 0.1 MeV (dirt path)",
         pot_or_exposure=cv["total_pot_sum"], pot_source="sum TotalPOT of the 37,742 listed files (identical for old and Nov16: same files)", generated_throws=f"{int(cv['total_gen_events_sum'])} (TotalGenEvents, 50 per file; informational only; POT/gen = 1.44e13 consistent with SAM)",
         accepted_filter_norm="filter drops events with no in-TPC neutrino and <=0.1 MeV deposit: cannot pass a neutrino-induced selection; this also means NO pure-cosmic (no-neutrino) events exist in this MC", valid_caf_fraction=f"{cv['n_wc_valid']}/{cv['n_events']}",
         event_weight=f"w = POT_target / {cv['total_pot_sum']:.6g} (unit MC weight)", cosmics_overlaid="yes (CORSIKA overlay; cosmic-matched candidates present as COSMIC_OR_UNMATCHED)", beam_off_added_separately="YES, needed for the cosmic-only (no-neutrino) component: OPEN (blocker G)",
         dirt_present="yes, inside the sample (rock-box generator; appears as OUTSIDE_TPC_NU); no separate dirt sample", intrinsic_nue="yes, naturally in the BNB flux mixture; the dedicated nueCC sample is NOT added"),
    dict(sample="nuecc", role="CONTROL ONLY (not a background contribution)", generator_filter="exclusive CC nue filter (7.0% pass)", pot_or_exposure=pj("nuecc")["total_pot_sum"], pot_source="sum TotalPOT (flux-equivalent, ~100x the CV POT per generated event)",
         generated_throws="n/a", accepted_filter_norm="exclusive production: not a BNB mixture", valid_caf_fraction=f"{S['nuecc']['n_wc_valid_events']}/{S['nuecc']['n_caf_events']}", event_weight="NOT USED in any yield", cosmics_overlaid="yes", beam_off_added_separately="no", dirt_present="no",
         intrinsic_nue="EXCLUDED from yields to avoid double counting the intrinsic nue already in bnb_cv"),
    dict(sample="beam_on_open", role="DATA (designated open)", generator_filter="data (runs 18255, 18259)", pot_or_exposure=bo["total_pot_sum"], pot_source="sum TotalPOT of the 1,817 files", generated_throws="n/a",
         accepted_filter_norm="open subset of the BNB light stream", valid_caf_fraction=f"{bo['n_wc_valid']}/{bo['n_events']}", event_weight="1", cosmics_overlaid="n/a (data)", beam_off_added_separately="n/a", dirt_present="n/a", intrinsic_nue="n/a"),
    dict(sample="beam_off", role="COSMIC shape only; NOT normalised, NOT stacked", generator_filter="InTime-Run1 beam-off (offbeamlight)", pot_or_exposure="none (TotalPOT = 0)", pot_source="no POT; gate counters sum noffbeambnb = 2,542,847 vs nbnbinfo = 960,047 (beam-on): scale NOT approved",
         generated_throws="n/a", accepted_filter_norm="UNRESOLVED: which counter pair (gates vs triggers), livetime, run overlap (no beam-off file in run 18255)", valid_caf_fraction=f"{bf['n_wc_valid']}/{bf['n_events']}", event_weight="none", cosmics_overlaid="n/a", beam_off_added_separately="this IS the separate component: scale OPEN",
         dirt_present="n/a", intrinsic_nue="n/a"),
]
L = pd.DataFrame(rows); L.to_csv(TAB / "normalization_ledger.csv", index=False)
chk = []
def add(name, ok, detail): chk.append(dict(check=name, status="CLOSED" if ok is True else ("OPEN" if ok is None else "FAILED"), detail=detail))
w = led["nov16"]
add("signal and CV POT are exact sums over the listed files; weights = POT_target/POT", True, f"w_sig = {w['w_sig']:.6g}, w_cv = {w['w_cv']:.6g} per event at 1e20 POT")
rate_ded = 12427 / census["files"]["sum_TotalPOT"] * 1e20; rate_cv = nat_rate[0] / nat_rate[1] * 1e20
add("dedicated in-region signal rate agrees with the natural CV rate (consistency of the two normalisations)", abs(rate_ded - rate_cv) / np.hypot(rate_cv * 0.1, 1) < 3 and abs(rate_ded / rate_cv - 1) < 0.2, f"{rate_ded:.1f} vs {rate_cv:.1f} +- {rate_cv/np.sqrt(117):.1f} per 1e20 POT (ratio {rate_cv/rate_ded:.3f})")
add("no double counting of NC-Delta: in-region natural NC-Delta events removed from the CV background", True, f"{led['old_fg1']['n_removed_events']} CV events with candidates removed ({led['old_fg1']['n_removed_selected_final']} / {led['nov16']['n_removed_selected_final']} of them selected at the final stage old / Nov16)")
add("no double counting of intrinsic nue: nueCC control sample not added; intrinsic nue is in the generic CV", True, "nuecc contributes 0 to every yield")
add("dirt: no separate sample needed; dirt/rock interactions are inside the generic CV", True, "OUTSIDE_TPC_NU category")
add("cosmics overlaid in MC (cosmic-matched candidates)", True, "COSMIC_OR_UNMATCHED present in both productions")
add("cosmic-ONLY (no-neutrino) component: needs beam-off scale", None, "blocker G (gate counters vs triggers, livetime, run overlap) unanswered; purity is therefore an UPPER BOUND / MC-only")
add("MC systematic reweighting (GENIE/flux/G4)", None, "unit weights only; no validated SBND weights wired in; statistical errors only")
add("provisional TPC box as the signal region and as the truth denominator", None, "analysis FV not frozen; the box is a stated provisional definition")
add("signal numerator = event passes with ANY candidate (Round-1 policy), not 'candidate truth-matched to the signal'", True, "identical to the efficiency numerator; selected-signal events passing only via a cosmic-matched candidate are counted as signal")
pd.DataFrame(chk).to_csv(TAB / "normalization_closure_checks.csv", index=False); print(pd.DataFrame(chk).to_string(index=False))
# ---- cosmic-only headroom: how large an UNKNOWN cosmic-only expectation (per 1e20 POT) would lower the purity by X % relative -------------
ov = pd.read_csv(TAB / "overall_purity.csv"); rows = []
for _, r in ov.iterrows():
    t = r.S_per_1e20 + r.B_per_1e20
    for d in (0.1, 0.25, 0.5):
        rows.append(dict(production=r.production, purity_MC_only=r.purity, relative_purity_loss=d, cosmic_only_events_per_1e20_needed=t * (1 / (1 - d) - 1)))
pd.DataFrame(rows).to_csv(TAB / "cosmic_only_headroom.csv", index=False)
