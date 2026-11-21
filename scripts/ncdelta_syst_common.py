"""Event-level owner tables for the systematic-weight attachment (frozen selection, final stage, both productions). Nothing here changes a selection.

COUNTING UNIT = the event (any passing candidate; each event once), exactly as in the purity tables.

OWNER RULES (no weight is ever invented):
* Signal (dedicated NC-Delta sample): the owner is the in-region qualifying NC-Delta interaction `signal_nu_index` of the official master records (rec.mc.nu index k).
* Background (generic BNB CV): the owner is the rec.mc.nu interaction `mnu_k` that the truth scan associates with the passing candidate(s). An event has a resolved owner only if
  every passing candidate has a production-matched neutrino interaction (cand_category not COSMIC_OR_UNMATCHED / MULTI_OR_AMBIGUOUS, finite mnu_k, exactly one matched
  interaction) and all passing candidates share the same mnu_k. Everything else is UNRESOLVED with the reason recorded; its neutrino-systematic treatment is open.
"""
from ncdelta_purity_common import *
from sbnd_single_photon import signal_master as SM, background_mechanisms as BM

NU_CATS = {"SIGNAL_NCDELTA", "OUTSIDE_TPC_NU", "NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OTHER_NC", "OTHER_CC"}      # categories that name one production-matched neutrino interaction
RUN = ["run", "subrun", "evt"]


def signal_owners(prod, cfg):
    """Selected (final, any-candidate) in-region signal events with their owner interaction. Returns (table, n_truth)."""
    sev, sc = load_signal(prod, cfg)
    st = sev[KEY].merge(PU.event_stage_table(sc, KEY), on=KEY, how="left")
    for s in PU.STAGES:
        st[s] = st[s].fillna(False).astype(bool)
    st["ch_n20br1"] = st["ch_n20br1"].fillna("")
    # The master records index the ORIGINAL flatCAFs ((file_index, ev) there is NOT the merged-CAF key of the analysis tables), so the owner is joined on run/subrun/event.
    rec = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "signal_records.parquet")
    rr = SM.region_records(rec, SM.load_regions()["active_tpc"])
    assert not rr.duplicated(RUN).any()
    own = rr[RUN + ["signal_nu_index", "vtx_x", "vtx_y", "vtx_z", "nu_pdg", "genie_mode", "n_signal_nu"]]
    base = sev[KEY + RUN].reset_index(drop=True)
    t = base.merge(own, on=RUN, how="left", validate="one_to_one")
    assert len(t) == len(sev) == 12427 and t.signal_nu_index.notna().all()
    t = pd.concat([t, st.drop(columns=KEY).reset_index(drop=True)], axis=1)               # st rows follow sev row order (merge on KEY, left, one-to-one)
    assert len(st) == len(sev)
    t["owner_k"] = t.signal_nu_index.astype(int); t["resolved"] = True; t["reason"] = "dedicated_signal_interaction"
    return t, len(sev)


def background_owners(prod, cfg, sigN, nat_in):
    """All CV events (not just selected) at every stage with the owner determination; use the stage columns to select."""
    cev, cc, cf = load_cv(prod, cfg)
    light = pd.read_parquet(LIGHT[prod]); light = BM.add_categories(light, sigN)
    ck = ["file_index", "ev", "nu_index"]
    j = cc[["file_index", "ev", "c_nu_index", "reco_proton_cat"]].rename(columns={"c_nu_index": "nu_index"}).merge(
        light[ck + ["cand_category", "mnu_k", "tm_n_distinct_nu", "tm_n", "mnu_link_dist_cm", "mnu_pdg", "mnu_ccnc", "mnu_x", "mnu_y", "mnu_z"]], on=ck, how="left", validate="one_to_one")
    assert len(j) == len(cc) and j.cand_category.notna().all()
    j.index = cc.index
    masks = PU.stage_masks(cc)
    st = PU.event_stage_table(cc, KEY)
    rm = PU.remove_in_region_natural_signal(st, nat_in[KEY], KEY)
    st["removed_in_region_natural_signal"] = rm.to_numpy(bool)
    sub = j[masks["n20br1"]].copy()
    sub["cand_ok"] = sub.cand_category.isin(NU_CATS) & sub.mnu_k.notna() & (sub.tm_n_distinct_nu <= 1) & (sub.tm_n >= 1)
    g = sub.groupby(KEY)
    own = g.agg(n_pass=("nu_index", "size"), all_ok=("cand_ok", "all"), nk=("mnu_k", lambda x: x.dropna().nunique()), k=("mnu_k", "min"),
                ncat=("cand_category", "nunique"), cat=("cand_category", "first"), any_cosmic=("cand_category", lambda x: (x == "COSMIC_OR_UNMATCHED").any()),
                any_multi=("cand_category", lambda x: (x == "MULTI_OR_AMBIGUOUS").any()), maxlink=("mnu_link_dist_cm", "max")).reset_index()
    own["resolved"] = own.all_ok & (own.nk == 1)
    own["reason"] = np.select([own.resolved, own.any_cosmic, own.any_multi, own.nk > 1, ~own.all_ok], ["unique_matched_interaction", "cosmic_or_unmatched_candidate", "multi_or_ambiguous_candidate",
                                                                                                         "passing_candidates_disagree_on_interaction", "no_unique_interaction"], "other")
    own["owner_k"] = np.where(own.resolved, own.k, -1).astype(int)
    own["event_category"] = np.where(own.ncat > 1, "MULTI_OR_AMBIGUOUS", own.cat)
    t = st.merge(own.drop(columns=["k", "all_ok"]), on=KEY, how="left")
    run = cev[KEY + RUN]; t = t.merge(run, on=KEY, how="left", validate="one_to_one")
    return t, cc, j, masks, cf


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# assembly of the event-level weight matrices
# ------------------------------------------------------------------------------------------------------------------------------------------------------------
SYST = SPD / "ncdelta_purity_datamc" / "syst"
E_BINS = np.geomspace(20.0, 3000.0, 9)                       # selected-shower energy [MeV], 8 bins, first-pass histogram at the final selection
CH_BINS = ["1g0p", "1g1p", "ge2p"]                           # reconstructed proton-multiplicity channel (event level)
NU_TOT = 22485


def event_variable(c, mask, var="c_shw_sp_energy"):
    """One value per event from the passing candidates. REPRESENTATIVE-CANDIDATE RULE: the passing candidate with the lowest c_nu_index (deterministic; the weight owner does NOT depend on it).
    Also returns, per event, whether the passing candidates would fall in different shower-energy bins (so the rule's effect is quantified, not hidden)."""
    sub = c.loc[mask, KEY + ["c_nu_index", var]].sort_values(KEY + ["c_nu_index"]).copy()
    sub["bin"] = np.digitize(sub[var].to_numpy(float), E_BINS) - 1
    g = sub.groupby(KEY)
    out = g[[var]].first().join(g.size().rename("n_pass_c")).join(g.bin.nunique().rename("n_bins"))
    return out.reset_index()


def assemble(prod, cfg, sigN, nat_in, require_proof=True):
    """Selected-event tables with attached weight matrices for S and B. Returns dict(S=..., B=...) of (events DataFrame, W float32 [n, 22485], nominal weight, diagnostics dict)."""
    out = {}
    cev, cc, cf = load_cv(prod, cfg); pot_cv = float(cf.total_pot.sum())
    sev, sc = load_signal(prod, cfg)
    for tag in ("S", "B"):
        own = pd.read_parquet(SYST / f"owners_{tag}_{prod}.parquet")
        if tag == "S":
            ev = own[own.n20br1 & own.file_index.notna()].copy(); ev["ch"] = ev["ch_n20br1"]; masks = PU.stage_masks(sc)["n20br1"]; ev = ev.merge(event_variable(sc, masks), on=KEY, how="left", validate="one_to_one")
            w = PU.weight(POT_TARGET, POT_SIGNAL)
        else:
            ev = own[own.n20br1 & ~own.removed_in_region_natural_signal].copy(); ev["ch"] = ev["ch_n20br1"]; masks = PU.stage_masks(cc)["n20br1"]; ev = ev.merge(event_variable(cc, masks), on=KEY, how="left", validate="one_to_one")
            w = PU.weight(POT_TARGET, pot_cv)
        ev = ev.reset_index(drop=True); ev["resolved"] = ev.resolved.fillna(False).astype(bool)
        meta = pd.read_parquet(SYST / f"blocks_meta_{tag}_{prod}.parquet"); Wb = np.load(SYST / f"blocks_{tag}_{prod}.npy", mmap_mode="r")
        meta["row"] = np.arange(len(meta))
        j = ev[["file_index", "run", "subrun", "evt", "resolved"]].reset_index().merge(meta[["file_index", "run", "subrun", "evt", "row", "found", "layout_ok", "vtx_dist_cm", "pdg_match", "imp_weight", "rec_entry",
                                                                                           "ev_table", "entry_equal", "wc_id_at_table_entry", "n_nu", "k"]], on=["file_index", "run", "subrun", "evt"], how="left", validate="one_to_one")
        j = j.set_index("index").loc[ev.index]
        W = np.ones((len(ev), NU_TOT), np.float32)
        have = j.row.notna().to_numpy(); rows = j.row[have].astype(int).to_numpy()
        W[have] = np.asarray(Wb[rows])
        ev["has_block"] = have; ev["imp_weight"] = j.imp_weight.to_numpy(); ev["vtx_dist_cm"] = j.vtx_dist_cm.to_numpy(); ev["layout_ok"] = j.layout_ok.to_numpy(); ev["pdg_match"] = j.pdg_match.to_numpy()
        ev["entry_equal"] = j.entry_equal.to_numpy(); ev["wc_id_at_table_entry"] = j.wc_id_at_table_entry.to_numpy()
        if tag == "S":
            assert have.all(), f"{(~have).sum()} selected signal events without a weight block"
        else:
            assert (have == ev.resolved.to_numpy(bool)).all(), "background: blocks exist exactly for the resolved events"
        out[tag] = dict(ev=ev, W=W, w=w)
    return out
