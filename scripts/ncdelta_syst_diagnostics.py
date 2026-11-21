#!/usr/bin/env python
"""Diagnostics that must close BEFORE any systematic covariance is built or shown (nothing is applied to a result).

    source env/setup_eaf.sh && export BEARER_TOKEN_FILE=... && python scripts/ncdelta_syst_diagnostics.py

Writes tables/ncdelta_purity_datamc/syst_*.csv :
  syst_function_table            all 134 weight functions: type, sigma values, prescription, in-band flag + reason
  syst_identity_proof            recTree <-> recTreeWireCell identity/order proof (every entry of every file read) + join checks of the weight blocks
  syst_join_diagnostics          fraction of selected S and B (events, yield) with a unique weight owner; unresolved reasons
  syst_unit_weight_reproduction  nominal S, B, P from the attached events with all weights = 1 vs the committed purity tables (must be exact)
  syst_weight_audit              per function: universes, non-finite, zero, negative, max/tails, fraction exactly 1, applicability (selected S, selected B, broad samples)
  syst_imp_weight_distribution   selected-event imp_weight distributions;  syst_imp_weight_hypothetical (HYPOTHETICAL ONLY, not an alternative result)
  syst_source_feasibility        per source group: functions, universes, prescription, feasibility
"""
from ncdelta_syst_common import *
from sbnd_single_photon import samples as S, syst_weights as SW
import uproot, json

TAB = REPO / "tables" / "ncdelta_purity_datamc"
cfg = load_cfg(); sigN, nat_in = natural_signal_in_region()
url0 = S.read_manifest(REPO / "manifests" / "wcl1116" / "bnb_cv.tsv.gz")[0]["url"]
g = uproot.open(url0)["globalTree"]
NAMES = [str(x) for x in g["global/wgts/wgts.name"].array(library="ak")[0]]; NUNIV = g["global/wgts/wgts.nuniv"].array(library="ak")[0].tolist(); TYPES = g["global/wgts/wgts.type"].array(library="ak")[0].tolist()
ents = SW.parse_weight_map(bytes(memoryview(g["global/wgts/wgts.map"].basket(0).data)))
FT = SW.function_table(NAMES, NUNIV, TYPES, SW.multisigma_sigmas(list(zip(NAMES, NUNIV, TYPES)), ents)); FT.to_csv(TAB / "syst_function_table.csv", index=False)
assert FT.nuniv.sum() == NU_TOT and (FT.stop.iloc[-1] == NU_TOT)
SLICES = list(zip(FT.name, FT.start, FT.stop))

# ---- 1. identity proof + block join checks -----------------------------------------------------------------------------------------------------------------------
rows = []
for prod in PRODUCTIONS:
    for tag in ("S", "B"):
        pr = pd.read_parquet(SYST / f"proof_{tag}_{prod}.parquet"); me = pd.read_parquet(SYST / f"blocks_meta_{tag}_{prod}.parquet")
        rows.append(dict(production=prod, sample="signal" if tag == "S" else "bnb_cv", n_files=len(pr), n_entries_checked=int(pr.n_rec.sum()), same_length_all=bool(pr.same_length.all()),
                         files_ids_identical_in_order=int(pr.ids_identical_in_order.sum()), rec_ids_unique_all=bool(pr.rec_ids_unique.all()), wc_ids_unique_all=bool(pr.wc_ids_unique.all()),
                         n_events_joined=len(me), found_by_id=int(me.found.sum()), joined_entry_equals_table_entry=int(me.entry_equal.sum()), wc_id_at_table_entry_matches=int(me.wc_id_at_table_entry.sum()),
                         layout_ok=int(me.layout_ok.sum()), owner_vertex_within_1e3_um=int((me.vtx_dist_cm < 1e-3).sum()), max_vertex_dist_cm=float(me.vtx_dist_cm.max()), owner_pdg_matches=int(me.pdg_match.sum())))
pd.DataFrame(rows).to_csv(TAB / "syst_identity_proof.csv", index=False)

# ---- 2. join diagnostics + unit-weight reproduction ---------------------------------------------------------------------------------------------------------------
ov = pd.read_csv(TAB / "overall_purity.csv").set_index("production"); tp = pd.read_csv(TAB / "topology_purity.csv")
jr, ur, imp_rows, hyp_rows, A = [], [], [], [], {}
for prod in PRODUCTIONS:
    A[prod] = X = assemble(prod, cfg, sigN, nat_in)
    wS, wB = X["S"]["w"], X["B"]["w"]; eS, eB = X["S"]["ev"], X["B"]["ev"]
    nS, nB, nBr = len(eS), len(eB), int(eB.resolved.sum())
    jr.append(dict(production=prod, sample="S", n_events=nS, n_unique_owner=nS, frac_events=1.0, yield_per_1e20=nS * wS, yield_unique_per_1e20=nS * wS, frac_yield=1.0, unresolved_reasons=""))
    rs = eB[~eB.resolved].reason.value_counts().to_dict(); rcat = eB[~eB.resolved].event_category.value_counts().to_dict()
    jr.append(dict(production=prod, sample="B", n_events=nB, n_unique_owner=nBr, frac_events=nBr / nB, yield_per_1e20=nB * wB, yield_unique_per_1e20=nBr * wB, frac_yield=nBr / nB,
                   unresolved_reasons=json.dumps(rs), unresolved_event_categories=json.dumps(rcat), n_events_multiple_passing_candidates=int((eB.n_pass > 1).sum()), n_events_whose_candidates_differ_in_energy_bin=int((eB.n_bins > 1).sum())))
    jr[-2]["n_events_multiple_passing_candidates"] = int((eS.n_pass_c > 1).sum()); jr[-2]["n_events_whose_candidates_differ_in_energy_bin"] = int((eS.n_bins > 1).sum())
    # unit-weight reproduction: all universe weights replaced by 1 (S, B), same event unit as the purity tables
    Sx, Bx = nS * wS, nB * wB; P = Sx / (Sx + Bx)
    ur.append(dict(production=prod, topology="inclusive", S_attached=Sx, S_table=ov.loc[prod, "S_per_1e20"], B_attached=Bx, B_table=ov.loc[prod, "B_per_1e20"], P_attached=P, P_table=ov.loc[prod, "purity"],
                   exact=bool(np.isclose(Sx, ov.loc[prod, "S_per_1e20"], rtol=0, atol=1e-9) and np.isclose(Bx, ov.loc[prod, "B_per_1e20"], rtol=0, atol=1e-9) and np.isclose(P, ov.loc[prod, "purity"], rtol=0, atol=1e-12))))
    for lab, sel in (("1g0p", lambda e: e.ch == "1g0p"), ("1gNp", lambda e: e.ch.isin(["1g1p", "ge2p"]))):
        ns, nb = int(sel(eS).sum()), int(sel(eB).sum()); Sx, Bx = ns * wS, nb * wB; r = tp[(tp.production == prod) & (tp.reco_channel == lab)].iloc[0]
        ur.append(dict(production=prod, topology=lab, S_attached=Sx, S_table=r.S_per_1e20, B_attached=Bx, B_table=r.B_per_1e20, P_attached=Sx / (Sx + Bx), P_table=r.purity,
                       exact=bool(np.isclose(Sx, r.S_per_1e20, rtol=0, atol=1e-9) and np.isclose(Bx, r.B_per_1e20, rtol=0, atol=1e-9) and np.isclose(Sx / (Sx + Bx), r.purity, rtol=0, atol=1e-12))))
    # imp_weight of the owner interaction: distributions of the selected events, and a HYPOTHETICAL purity (not an alternative result)
    for tag, e in (("S", eS), ("B_resolved", eB[eB.resolved])):
        q = e.imp_weight.to_numpy(float); imp_rows.append(dict(production=prod, sample=tag, n=len(q), mean=q.mean(), median=np.median(q), p10=np.percentile(q, 10), p90=np.percentile(q, 90), min=q.min(), max=q.max(), frac_exactly_1=float((q == 1).mean())))
    iS = eS.imp_weight.to_numpy(float).sum() * wS; iBr = eB[eB.resolved].imp_weight.to_numpy(float).sum() * wB; n_un = int((~eB.resolved).sum()); mB = eB[eB.resolved].imp_weight.mean()
    for variant, iB in (("unresolved background events keep weight 1", iBr + n_un * wB), ("unresolved background events get the mean resolved imp_weight", iBr + n_un * wB * mB)):
        hyp_rows.append(dict(production=prod, HYPOTHETICAL_ONLY=True, variant=variant, S_nominal=nS * wS, S_if_imp_weight=iS, B_nominal=nB * wB, B_if_imp_weight=iB, P_nominal=nS * wS / (nS * wS + nB * wB), P_if_imp_weight=iS / (iS + iB),
                            P_ratio=(iS / (iS + iB)) / (nS * wS / (nS * wS + nB * wB)), S_over_B_nominal=nS * wS / (nB * wB), S_over_B_if_imp_weight=iS / iB, S_over_B_ratio=(iS / iB) / (nS * wS / (nB * wB))))
pd.DataFrame(jr).to_csv(TAB / "syst_join_diagnostics.csv", index=False); pd.DataFrame(ur).to_csv(TAB / "syst_unit_weight_reproduction.csv", index=False)
pd.DataFrame(imp_rows).to_csv(TAB / "syst_imp_weight_distribution.csv", index=False); pd.DataFrame(hyp_rows).to_csv(TAB / "syst_imp_weight_hypothetical.csv", index=False)
assert all(r["exact"] for r in ur), "unit-weight reproduction is not exact"

# ---- 3. pathological-weight audit ----------------------------------------------------------------------------------------------------------------------------------
sets = {}
for prod in PRODUCTIONS:
    sets[f"S_selected_{prod}"] = A[prod]["S"]["W"]; sets[f"B_selected_resolved_{prod}"] = A[prod]["B"]["W"][A[prod]["B"]["ev"].resolved.to_numpy(bool)]
for tag in ("S", "B"):
    f = SYST / f"audit_sample_{tag}.npy"
    if f.exists():
        sets[f"{'signal' if tag == 'S' else 'bnb_cv'}_all_interactions_random_files_nov16"] = np.load(f, mmap_mode="r")
au = []
for lab, W in sets.items():
    a = SW.audit_weights(W, SLICES); a.insert(0, "weight_set", lab); au.append(a)
au = pd.concat(au, ignore_index=True).merge(FT[["name", "group", "type_name", "in_band"]], on="name"); au.to_csv(TAB / "syst_weight_audit.csv", index=False)
summ = au.groupby("weight_set").agg(functions=("name", "size"), functions_with_nonfinite=("n_nonfinite", lambda x: int((x > 0).sum())), functions_with_negative=("n_negative", lambda x: int((x > 0).sum())),
                                    functions_with_zero=("n_zero", lambda x: int((x > 0).sum())), functions_max_gt10=("max", lambda x: int((x > 10).sum())), overall_max=("max", "max"),
                                    functions_inert_all_events=("frac_events_inert", lambda x: int((x == 1).sum()))).reset_index(); summ.to_csv(TAB / "syst_weight_audit_summary.csv", index=False)

# ---- 4. source feasibility ----------------------------------------------------------------------------------------------------------------------------------------------
fe = FT.groupby("group").agg(functions=("name", "size"), universes=("nuniv", "sum"), in_band_functions=("in_band", "sum"), type_names=("type_name", lambda x: ",".join(sorted(set(x)))),
                             prescription=("prescription", "first"), reasons_not_in_band=("reason_if_not", lambda x: "; ".join(sorted(set(v for v in x if v))))).reset_index()
fe.to_csv(TAB / "syst_source_feasibility.csv", index=False)
print(pd.DataFrame(jr).to_string()); print(pd.DataFrame(ur).to_string()); print(summ.to_string()); print(fe.to_string())
