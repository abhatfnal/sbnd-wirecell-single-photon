#!/usr/bin/env python
"""Phase 18 (roadmap Z): why does the frozen ``numu`` BDT preferentially reject compact, few-segment NC-Delta photon objects, and is that consistent with the intended MicroBooNE training-domain discrimination?
CHARACTERISATION ONLY: no threshold, BDT weight, FV, proton policy, candidate policy, reconstruction or training is changed; no threshold scan.

    source env/setup_eaf.sh
    python scripts/numu_compact_shower_audit.py        # reads the Phase 9-17 products; no ROOT scan

Population: official Gen2 NC-Delta, provisional TPC box, frozen chain (policy ``any``), the 8,038 events that reach the numu stage; survival = the validated baseline flag ``A_numu``.  Adjustments are descriptive
(stratified direct standardisation with bootstrap, grouped logistic deviance bookkeeping), not a causal model.  Compactness bins are fixed in advance (``numu_audit.py``).
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import bdt as B, numu_audit as NA, origin_audit as OR, other_audit as OA, plotstyle as PS, remaining_audit as RA
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "numu_training_domain_audit" / "official_ncdelta"; OUT.mkdir(parents=True, exist_ok=True)
P12 = SPD / "remaining_stage_audit" / "official_ncdelta"; P15 = SPD / "particle_pid_audit" / "official_ncdelta"
TAB = REPO / "tables" / "numu_compact_shower_audit"; PLT = REPO / "plots" / "numu_compact_shower_audit"; TAB.mkdir(parents=True, exist_ok=True); PLT.mkdir(parents=True, exist_ok=True)
K = ["file_index", "ev"]; SUMMARY: dict = {}
PROV = "official Gen2 NC-Delta | frozen inherited selection (policy any) | TPC-box signal events reaching numu | threshold 0.4 fixed | descriptive audit"
SEGV = "in_shw_sp_br3_1_n_shower_segments"; LENV = "in_shw_sp_length_total"; MAINV = "in_shw_sp_length_main"; CHGV = "in_shw_sp_lem_e_charge"
TOPO = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}


def wr(df, name, nd=4):
    df.round(nd).to_csv(TAB / name, index=False); return df


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ============================================================================================================================ load and merge
S = pd.read_parquet(P12 / "numu_stage.parquet"); I = pd.read_parquet(P12 / "numu_stage_inputs.parquet")
inc = [c for c in I.columns if c.startswith("in_")]
assert (S.c_nu_index.values == I.c_nu_index.values).all() and (S.file_index.values == I.file_index.values).all() and (S.ev.values == I.ev.values).all()
D = pd.concat([S.reset_index(drop=True), I[inc].reset_index(drop=True)], axis=1)
Pp = pd.read_parquet(P15 / "photon_pid_events.parquet")[K + ["pid_class", "seg_length_cm", "row_n_segments", "dom_ke_row", "dom_type", "vtx_face_cm"]]
assert not Pp.duplicated(K).any()
D = D.merge(Pp, on=K, how="left"); assert len(D) == 8038
D["survive"] = D.A_numu.astype(bool); assert (D.survive == (D.stage_score > 0.4)).all()
D["obj"] = [NA.object_class(x) for x in D.pid_class]
D["topo_l"] = D.truth35.map(TOPO); D["delta"] = D.delta_label.fillna("n/a")
D["n_seg"] = D[SEGV]; D["len_total"] = D[LENV]; D["compact"] = D[LENV] < NA.COMPACT_LENGTH_CM; D["few_seg"] = D[SEGV] < NA.COMPACT_NSEG
D["segb"] = NA.bin_labels(D[SEGV], NA.SEG_EDGES, NA.SEG_LABELS).astype(str); D["lenb"] = NA.bin_labels(D[LENV], NA.LEN_EDGES, NA.LEN_LABELS).astype(str)
D["e_true"] = D.photon_energy_mev; D["e_reco_row"] = D.dom_ke_row; D["e_reco_shw"] = D.shw_sp_energy; D["e_ratio"] = D.dom_ke_row / D.photon_energy_mev
D["Eb"] = NA.bin_labels(D.e_true, [0, 200, 300, 400, 600, np.inf], ["<200", "200-300", "300-400", "400-600", ">=600"]).astype(str)
D["cosb"] = NA.bin_labels(D.cos_theta_beam, [-1.01, -0.5, 0, 0.5, 1.01], ["-1..-0.5", "-0.5..0", "0..0.5", "0.5..1"]).astype(str)
D["convb"] = NA.bin_labels(D.conv_distance_cm, [0, 5, 15, 30, np.inf], ["<5", "5-15", "15-30", ">=30"]).astype(str)
D["Erb"] = NA.bin_labels(D.e_reco_shw, [0, 50, 100, 200, 400, np.inf], ["<50", "50-100", "100-200", "200-400", ">=400"]).astype(str)
D["keyb"] = NA.bin_labels(D.seg_length_cm, [0, 5, 10, 20, 40, np.inf], ["<5", "5-10", "10-20", "20-40", ">=40"]).astype(str)
D["faceb"] = NA.bin_labels(D.vtx_face_cm, [0, 10, 25, 50, np.inf], ["<10", "10-25", "25-50", ">=50"]).astype(str)
D["origin"] = D.proton_origin.fillna("n/a").astype(str); D["anch_l"] = D.anch.astype(str)
D.to_parquet(OUT / "numu_audit_events.parquet", index=False)

# ============================================================================================================================ TASK 2: baseline reproduction
n = len(D); k = int(D.survive.sum())
SUMMARY["baseline"] = dict(n_events=n, n_pass=k, n_fail=n - k, survival=k / n, n_bdt_evaluable=int(D.A_bdt_evaluable.sum()), n_total_signal_box_events=int(pd.read_parquet(SPD / "shower_vertex_audit/official_ncdelta/event_taxonomy.parquet", columns=["tpc_box"]).tpc_box.sum()))
m = B.TmvaBdt("numu", B.DEFAULT_WEIGHT_DIR / "single_photon_numu_bdt_final.xml"); X = D[["in_" + v for v in m.var_names]].to_numpy(float)
sc = OA.scores_tmva_float32(m, X); ok = np.isfinite(sc)
flips = int(((sc[ok] > 0.4) != D.survive.values[ok]).sum()); SUMMARY["reproduction"] = dict(n_finite_inputs=int(ok.sum()), n_nonfinite_inputs=int((~ok).sum()), max_abs_score_diff=float(np.abs(sc[ok] - D.stage_score.values[ok]).max()), decision_flips=flips,
                                                                                    threshold=0.4, n_trees=len(m.trees), n_inputs=len(m.var_names))
rep = []
def add(label, mask):
    sub = D[mask]; p, lo, hi = NA.wilson(int(sub.survive.sum()), len(sub)); rep.append(dict(group=label, n=len(sub), n_pass=int(sub.survive.sum()), survival=p, lo68=lo, hi68=hi))
add("all events reaching numu", D.index == D.index)
for t, l in TOPO.items(): add(l, D.truth35 == t)
add("clean signal-photon shower", D.clean == "clean"); add("non-clean photon object", D.clean == "non_clean")
for o in NA.OBJECT_ORDER: add("object: " + o, D.obj == o)
for a in ("anchored", "not anchored", "no signal-matched candidate"): add("vertex " + a, D.anch == a)
for lab, mk in (("compact (length < 20 cm)", D.compact), ("not compact (length >= 20 cm)", ~D.compact), ("few-segment (< 5 segments)", D.few_seg), ("not few-segment", ~D.few_seg)): add(lab, mk)
wr(pd.DataFrame(rep), "numu_baseline_reproduction.csv")
V = ["in_shw_sp_br1_1_n_segs", "in_shw_sp_br1_1_sg_length", "in_shw_sp_br1_2_n_shower_segs", "in_shw_sp_br1_2_shower_length", "in_shw_sp_br1_2_max_length", "in_shw_sp_br1_3_n_shower_main_segs", SEGV, "in_shw_sp_br3_1_total_length", "in_shw_sp_br3_1_total_main_length", "in_shw_sp_br3_8_n_main_segs",
     "in_shw_sp_lem_shower_main_length", "in_shw_sp_lem_shower_num_main_segs", CHGV, "in_shw_sp_lem_e_dQdx", "in_shw_sp_hol_1_min_length", "in_shw_sp_hol_2_min_angle", MAINV, LENV, "in_shw_sp_stem_length", "in_numu_score", "in_numu_1_score"]
def vstat(a, b, name):
    a = np.asarray(a, float); b = np.asarray(b, float); a = a[np.isfinite(a)]; b = b[np.isfinite(b)]; pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return dict(variable=name.replace("in_", ""), median_pass=np.median(a), q16_pass=np.quantile(a, .16), q84_pass=np.quantile(a, .84), median_fail=np.median(b), q16_fail=np.quantile(b, .16), q84_fail=np.quantile(b, .84), smd_fail_minus_pass=(b.mean() - a.mean()) / pooled if pooled > 0 else 0.0,
                auc_pass_higher=NA.auc(np.r_[a, b], np.r_[np.ones(len(a), bool), np.zeros(len(b), bool)]))
wr(pd.DataFrame([vstat(D.loc[D.survive, v], D.loc[~D.survive, v], v) for v in V]), "numu_input_pass_vs_fail.csv")
# energy independence of the loss vs compactness dependence (Task 2 confirmation)
wr(NA.survival_table(D, ["Eb"]), "numu_survival_vs_true_energy.csv"); wr(NA.survival_table(D, ["segb"]), "numu_survival_vs_n_segments.csv"); wr(NA.survival_table(D, ["lenb"]), "numu_survival_vs_total_length.csv")
SUMMARY["energy_flatness"] = dict(spearman_survive_vs_etrue=float(stats.spearmanr(D.e_true, D.survive).statistic), spearman_survive_vs_nseg=float(stats.spearmanr(D.n_seg, D.survive).statistic), spearman_survive_vs_len=float(stats.spearmanr(D.len_total, D.survive).statistic),
                                  spearman_nseg_vs_etrue=float(stats.spearmanr(D.n_seg, D.e_true).statistic), spearman_len_vs_etrue=float(stats.spearmanr(D.len_total, D.e_true).statistic))

# ============================================================================================================================ TASK 3: controlling photon object
rows = []
for o in NA.OBJECT_ORDER:
    s = D[D.obj == o]
    if len(s) == 0: continue
    p, lo, hi = NA.wilson(int(s.survive.sum()), len(s))
    rows.append(dict(object=o, n=len(s), survival=p, lo68=lo, hi68=hi, median_n_segments_tagger=s.n_seg.median(), median_total_length_cm=s.len_total.median(), frac_compact=s.compact.mean(), frac_few_seg=s.few_seg.mean(), median_row_n_segments=s.row_n_segments.median(),
                     median_key_segment_length_cm=s.seg_length_cm.median(), median_reco_row_energy_mev=s.e_reco_row.median(), median_reco_shower_energy_mev=s.e_reco_shw.median(), median_Ereco_over_Etrue=s.e_ratio.median(), median_conv_distance_cm=s.conv_distance_cm.median(),
                     median_abs_cos=s.cos_theta_beam.abs().median(), frac_anchored=(s.anch == "anchored").mean(), frac_truth0p=(s.truth35 == 0).mean(), frac_truth1p=(s.truth35 == 1).mean(), frac_truth_ge2p=(s.truth35 == 2).mean(), median_true_energy_mev=s.e_true.median()))
wr(pd.DataFrame(rows), "numu_controlling_object_classes.csv")
T = pd.read_parquet(P15 / "truth_matched_pid_objects.parquet")
Tm = T[["file_index", "ev", "cand", "row", "is_signal_photon_row", "is_signal_primary_proton_row", "p1_t_pdg", "p1_t_nu", "origin_top", "type_class"]].drop_duplicates(["file_index", "ev", "cand", "row"])
Dm = D[D.obj.isin(["muon-like", "pion-like"])][K + ["dom_nu", "dom_row", "survive", "obj", "truth35"]].merge(Tm, left_on=K + ["dom_nu", "dom_row"], right_on=K + ["cand", "row"], how="left")
def tcat(r):
    if pd.isna(r.cand): return "no truth-matched row"
    if r.is_signal_photon_row: return "signal-photon piece"
    if r.is_signal_primary_proton_row: return "signal primary proton"
    if r.p1_t_nu not in (0, 0.0) and not pd.isna(r.p1_t_nu): return "other-neutrino / cosmic object"
    return "other signal-interaction object"
Dm["truth_of_row"] = Dm.apply(tcat, axis=1)
mt = NA.survival_table(Dm, ["obj", "truth_of_row"]); wr(mt, "numu_mu_pi_row_truth.csv"); SUMMARY["mu_pi_rows"] = {f"{r.obj}|{r.truth_of_row}": [int(r.n), float(r.survival)] for r in mt.itertuples()}
SUMMARY["ctrl_cand_is_signal_cand"] = float((D.c_nu_index == D.dom_nu).mean())
# does compactness predict rejection after descriptive control?  (standardised compact - not-compact survival difference; object class partly encodes compactness: fragmentation, so this is bookkeeping)
steps = [("raw (no control)", []), ("+ photon object class", ["obj"]), ("+ object class + vertex anchoring", ["obj", "anch_l"]), ("+ object class + anchoring + topology", ["obj", "anch_l", "topo_l"]),
         ("+ all above + true energy and angle bins", ["obj", "anch_l", "topo_l", "Eb", "cosb"]), ("anchoring + topology + true energy and angle (no object class)", ["anch_l", "topo_l", "Eb", "cosb"])]
adj = []
for cname, flag in (("compact (length < 20 cm) vs not", "compact"), ("few-segment (< 5) vs not", "few_seg")):
    for lab, cols in steps:
        r = OR.bootstrap_standardise(D, flag, True, False, "survive", cols, n_boot=300, min_count=5); adj.append(dict(contrast=cname, control=lab, n_compact=r["n_hi"], n_ref=r["n_lo"], raw=r["raw"], raw_on_support=r["raw_on_support"], adjusted=r["adjusted"], adj_lo68=r["adjusted_lo68"], adj_hi68=r["adjusted_hi68"],
                                                                    support_fraction=r["support_fraction"], n_strata=r["n_strata"]))
wr(pd.DataFrame(adj), "numu_compactness_adjusted_difference.csv")
# within the clean electron-shower class only, and within truth class
sub = D[D.obj == "clean e-shower"]; wr(NA.survival_table(sub, ["lenb"]), "numu_clean_eshower_survival_vs_length.csv"); wr(NA.survival_table(sub, ["segb"]), "numu_clean_eshower_survival_vs_n_segments.csv")
wr(NA.survival_table(D, ["obj", "lenb"]), "numu_survival_by_object_and_length.csv")

# ============================================================================================================================ TASK 5: conditional survival
VARS = [("true photon energy (MeV)", "Eb"), ("true photon beam angle (cos)", "cosb"), ("true conversion distance (cm)", "convb"), ("reco shower energy, tagger (MeV)", "Erb"), ("number of shower segments", "segb"), ("total shower length (cm)", "lenb"),
        ("key-segment length of the dominant row (cm)", "keyb"), ("photon object class", "obj"), ("truth proton class", "topo_l"), ("Delta charge", "delta"), ("proton origin (truth-1p)", "origin"), ("vertex anchoring (5 cm)", "anch_l"), ("vertex-to-edge distance (cm)", "faceb")]
pops = {"all": D.index == D.index, "clean e-shower": D.obj == "clean e-shower", "non-clean photon object": D.clean == "non_clean"}
cs = []
for pn, mk in pops.items():
    for vl, col in VARS:
        t = NA.survival_table(D[mk], [col]); t.columns = ["bin"] + list(t.columns[1:]); t.insert(0, "variable", vl); t.insert(0, "population", pn); cs.append(t)
CS = wr(pd.concat(cs, ignore_index=True), "numu_conditional_survival.csv")
groups = {"true kinematics (energy, angle, conversion, edge)": ["Eb", "cosb", "convb", "faceb"], "photon reco state (object class)": ["obj"], "vertex anchoring": ["anch_l"], "compactness / segmentation (segments, length)": ["segb", "lenb"],
          "reco shower energy": ["Erb"], "truth topology (0p/1p/>=2p, Delta charge)": ["topo_l", "delta"]}
G = D.copy(); GT = NA.grouped_deviance_table(G, "survive", groups); wr(GT, "numu_driver_deviance_groups.csv")
G2 = D[D.obj == "clean e-shower"].copy(); GT2 = NA.grouped_deviance_table(G2, "survive", {k_: v for k_, v in groups.items() if k_ != "photon reco state (object class)"}); wr(GT2, "numu_driver_deviance_groups_clean_eshower.csv")
SUMMARY["driver_groups"] = {r.group: [float(r.pseudo_r2_alone), float(r.share_of_full_deviance_drop)] for r in GT.itertuples()}

# ============================================================================================================================ TASK 6: upstream score dependence and TreeSHAP
fam = np.array([RA.family_of(v) for v in m.var_names]); inf = np.isfinite(X).all(axis=1); rng = np.random.default_rng(20261111)
acc = np.where(inf & D.survive.values)[0]; rej = np.where(inf & ~D.survive.values)[0]; allf = np.where(inf)[0]
fg = np.sort(np.r_[rng.choice(acc, 400, replace=False), rng.choice(rej, 400, replace=False)]); bg = np.sort(rng.choice(allf, 300, replace=False))
res = OA.interventional_shap(m, X[fg], X[bg]); phi = res["phi"]; base = res["base"]; margin = OA.tree_contributions(m, X[fg]).sum(axis=1); add_err = float(np.abs(margin - base - phi.sum(axis=1)).max()); assert add_err < 1e-6
g_acc = D.survive.values[fg]; g_cmp = D.compact.values[fg]; g_few = D.few_seg.values[fg]
def grp(mask): return mask
families = [f for f in RA.FAMILIES if (fam == f).any()]; fr = []
for lab, mk in (("accepted", g_acc), ("rejected", ~g_acc), ("accepted & compact", g_acc & g_cmp), ("accepted & not compact", g_acc & ~g_cmp), ("rejected & compact", ~g_acc & g_cmp), ("rejected & not compact", ~g_acc & ~g_cmp)):
    for f in families:
        idx = fam == f; fr.append(dict(group=lab, n=int(mk.sum()), family=f, mean_signed_phi=float(phi[mk][:, idx].sum(axis=1).mean()), share_of_abs_phi=float(np.abs(phi[mk][:, idx]).sum() / np.abs(phi[mk]).sum())))
FR = wr(pd.DataFrame(fr), "numu_shap_families_by_group.csv")
vr = pd.DataFrame(dict(variable=m.var_names, family=fam, mean_phi_accepted=phi[g_acc].mean(axis=0), mean_phi_rejected=phi[~g_acc].mean(axis=0), mean_abs_phi=np.abs(phi).mean(axis=0), mean_phi_rejected_compact=phi[~g_acc & g_cmp].mean(axis=0), mean_phi_rejected_not_compact=phi[~g_acc & ~g_cmp].mean(axis=0))).sort_values("mean_abs_phi", ascending=False)
wr(vr, "numu_shap_variables.csv"); SUMMARY["shap"] = dict(n_fg=len(fg), n_bg=len(bg), base_margin=base, additivity_max_error=add_err, mean_margin_accepted=float(margin[g_acc].mean()), mean_margin_rejected=float(margin[~g_acc].mean()), threshold_margin=float(np.arctanh(0.4)))
# upstream numu_score: survival, correlation with compactness, discriminating power alone
up = []
for v in ("in_numu_score", "in_numu_1_score", SEGV, LENV, MAINV, CHGV, "in_shw_sp_lem_shower_num_main_segs", "in_shw_sp_stem_length"):
    x = D[v].values; up.append(dict(variable=v.replace("in_", ""), auc_survive_higher=NA.auc(x, D.survive.values), spearman_with_stage_score=float(stats.spearmanr(x, D.stage_score, nan_policy="omit").statistic), spearman_with_n_segments=float(stats.spearmanr(x, D[SEGV], nan_policy="omit").statistic),
                                    spearman_with_total_length=float(stats.spearmanr(x, D[LENV], nan_policy="omit").statistic), spearman_with_true_energy=float(stats.spearmanr(x, D.e_true, nan_policy="omit").statistic)))
wr(pd.DataFrame(up), "numu_upstream_score_dependence.csv")
D["upb"] = pd.qcut(D.in_numu_score, 5, duplicates="drop").astype(str); wr(NA.survival_table(D, ["upb"]), "numu_survival_vs_upstream_numu_score_quintile.csv")
wr(pd.crosstab(D.compact, D.in_numu_score > D.in_numu_score.median(), normalize="index").reset_index(), "numu_upstream_score_high_by_compact.csv")

# ============================================================================================================================ TASK 7: natural CV (candidate level; stored inputs only)
N = pd.read_parquet(P12 / "raw" / "natural_candidates.parquet"); N["survive"] = N.numu_score > 0.4; N["lenb"] = NA.bin_labels(N[LENV], NA.LEN_EDGES, NA.LEN_LABELS).astype(str); N["segb"] = NA.bin_labels(N[SEGV], NA.SEG_EDGES, NA.SEG_LABELS).astype(str)
N["compact"] = N[LENV] < NA.COMPACT_LENGTH_CM
nat = []
for pop, df in (("official Gen2 NC-Delta (event-level controlling candidate)", D), ("natural NC-Delta CV (candidates, no truth label stored)", N)):
    for col in ("lenb", "segb"):
        t = NA.survival_table(df, [col]); t.columns = ["bin"] + list(t.columns[1:]); t.insert(0, "binned_by", "total length" if col == "lenb" else "n segments"); t.insert(0, "population", pop); nat.append(t)
wr(pd.concat(nat, ignore_index=True), "numu_natural_cv_vs_official.csv")
SUMMARY["natural_cv"] = dict(n_candidates=len(N), n_events=int(N[["file_index", "ev"]].drop_duplicates().shape[0]), n_pass=int(N.survive.sum()), survival=float(N.survive.mean()), compact_survival=float(N[N.compact].survive.mean()) if N.compact.any() else None, n_compact=int(N.compact.sum()),
                             noncompact_survival=float(N[~N.compact].survive.mean()), official_compact_survival=float(D[D.compact].survive.mean()), official_noncompact_survival=float(D[~D.compact].survive.mean()))

# ============================================================================================================================ share of total frozen-baseline loss
tx = pd.read_parquet(SPD / "shower_vertex_audit/official_ncdelta/event_taxonomy.parquet", columns=K + ["tpc_box", "A_candidate", "A_n20mev", "A_bdt_evaluable", "A_numu", "A_other", "A_ncpi0", "A_nue", "A_n20br1", "A_final", "truth35"]); tx = tx[tx.tpc_box == True]
N0 = len(tx); nfin = int(tx.A_final.sum()); lost = N0 - nfin
SUMMARY["loss_budget"] = dict(n_signal_box_events=N0, n_final=nfin, n_lost=lost, n_reach_numu=int(len(D)), n_fail_numu=int((~D.survive).sum()), numu_fail_share_of_total_loss=float((~D.survive).sum() / lost), numu_fail_share_of_numu_population=float((~D.survive).mean()),
                              n_fail_numu_compact=int(((~D.survive) & D.compact).sum()), n_fail_numu_few_seg=int(((~D.survive) & D.few_seg).sum()), n_fail_numu_compact_or_few=int(((~D.survive) & (D.compact | D.few_seg)).sum()), n_fail_numu_compact_nonclean=int(((~D.survive) & D.compact & (D.clean == "non_clean")).sum()),
                              n_fail_numu_nonclean=int(((~D.survive) & (D.clean == "non_clean")).sum()), n_fail_numu_clean=int(((~D.survive) & (D.clean == "clean")).sum()))
bud = []
for lab, mk in (("fail numu: all", ~D.survive), ("compact (length < 20 cm)", ~D.survive & D.compact), ("few-segment (< 5)", ~D.survive & D.few_seg), ("compact or few-segment", ~D.survive & (D.compact | D.few_seg)), ("non-clean photon object", ~D.survive & (D.clean == "non_clean")),
                ("clean photon shower", ~D.survive & (D.clean == "clean")), ("clean photon shower, not compact", ~D.survive & (D.clean == "clean") & ~D.compact), ("muon/pion-like dominant object", ~D.survive & D.obj.isin(["muon-like", "pion-like"]))):
    bud.append(dict(group=lab, n=int(mk.sum()), share_of_numu_failures=float(mk.sum() / (~D.survive).sum()), share_of_total_baseline_loss=float(mk.sum() / lost), share_of_signal_box_events=float(mk.sum() / N0)))
wr(pd.DataFrame(bud), "numu_loss_budget.csv")
# if every compact object had the survival of the non-compact ones (descriptive bookkeeping, NOT a selection change)
sc_ = D[~D.compact].survive.mean(); extra = (D.compact.sum() * sc_) - D[D.compact].survive.sum(); SUMMARY["bookkeeping"] = dict(extra_numu_survivors_if_compact_matched_noncompact=float(extra), as_fraction_of_final=float(extra / nfin), note="bookkeeping of the association only; not a selection, not an efficiency gain claim")

# ============================================================================================================================ FIGURES
PS.apply_style(); C = {"clean": "#0072B2", "non_clean": "#D55E00", 0: "#0072B2", 1: "#D55E00", 2: "#009E73"}
def eb(ax, x, t, color, label, off=0.0, marker="o"):
    ax.errorbar(x + off, t.survival, yerr=[np.maximum(t.survival - t.lo68, 0), np.maximum(t.hi68 - t.survival, 0)], color=color, marker=marker, ls="-", label=label, ms=4, capsize=2, lw=1)
def tag(fig, extra="", bottom=0.22):
    fig.subplots_adjust(bottom=bottom); PS.annotate(fig, PROV, extra=extra)
# fig1 survival vs n segments / length by photon state
fig, ax = PS.figure(1, 2, size=(9.2, 3.8), sharey=True)
for j, (col, labs, xl) in enumerate((("segb", NA.SEG_LABELS, "tagger shower segments"), ("lenb", NA.LEN_LABELS, "total tagger shower length (cm)"))):
    for st, off in (("clean", -0.08), ("non_clean", 0.08)):
        t = NA.survival_table(D[D.clean == st], [col]).set_index(col).reindex(labs); t = t.dropna(subset=["survival"]); eb(ax[0, j], np.array([labs.index(i) for i in t.index], float), t, C[st], {"clean": "clean photon shower", "non_clean": "non-clean photon object"}[st], off)
    t = NA.survival_table(D, [col]).set_index(col).reindex(labs); eb(ax[0, j], np.arange(len(labs), dtype=float), t, "k", "all", 0.0, "s")
    ax[0, j].set_xticks(range(len(labs))); ax[0, j].set_xticklabels(labs); ax[0, j].set_xlabel(xl); ax[0, j].set_ylim(0, 1); ax[0, j].grid(alpha=.25)
ax[0, 0].set_ylabel("numu survival (Wilson 68 %)"); ax[0, 0].legend(frameon=False, fontsize=8); tag(fig); fig.savefig(PLT / "fig1_survival_vs_segments_length.png", dpi=150, bbox_inches="tight"); plt.close(fig)
# fig2 score distributions clean vs non-clean
fig, ax = PS.figure(1, 2, size=(9.2, 3.6)); bins = np.linspace(-1, 1, 41)
for st in ("clean", "non_clean"):
    s = D[D.clean == st]; ax[0, 0].hist(s.stage_score, bins=bins, histtype="step", density=True, color=C[st], label={"clean": f"clean (n={len(s)})", "non_clean": f"non-clean (n={len(s)})"}[st], lw=1.5)
    ax[0, 1].hist(s.in_numu_score.clip(-8, 8), bins=np.linspace(-8, 8, 41), histtype="step", density=True, color=C[st], lw=1.5)
ax[0, 0].axvline(0.4, color="k", ls=":", lw=1); ax[0, 0].set_xlabel("frozen numu BDT score (cut 0.4)"); ax[0, 0].set_ylabel("density"); ax[0, 0].legend(frameon=False, fontsize=8); ax[0, 0].set_yscale("log"); ax[0, 1].set_xlabel("upstream input numu_score (log-odds, clipped to +-8)")
tag(fig); fig.savefig(PLT / "fig2_score_by_photon_state.png", dpi=150, bbox_inches="tight"); plt.close(fig)
# fig3 conditional survival vs true energy by compactness strata
fig, ax = PS.figure(1, 2, size=(9.2, 3.8), sharey=True); Elabs = ["<200", "200-300", "300-400", "400-600", ">=600"]; cols = ["#D55E00", "#E69F00", "#009E73", "#0072B2"]
for j, (col, labs, ttl) in enumerate((("lenb", NA.LEN_LABELS, "total shower length (cm)"), ("segb", NA.SEG_LABELS, "shower segments"))):
    for ci, l in enumerate(labs):
        s = D[D[col] == l]; t = NA.survival_table(s, ["Eb"]).set_index("Eb").reindex(Elabs); t = t[t.n >= 15]
        if len(t): eb(ax[0, j], np.array([Elabs.index(i) for i in t.index], float), t, cols[ci], f"{l} (n={len(s)})", (ci - 1.5) * 0.06)
    ax[0, j].set_xticks(range(len(Elabs))); ax[0, j].set_xticklabels(Elabs); ax[0, j].set_xlabel("true photon energy (MeV)"); ax[0, j].set_ylim(0, 1); ax[0, j].grid(alpha=.25); ax[0, j].legend(title=ttl, frameon=False, fontsize=7)
ax[0, 0].set_ylabel("numu survival (bins with n >= 15)"); tag(fig); fig.savefig(PLT / "fig3_survival_vs_energy_by_compactness.png", dpi=150, bbox_inches="tight"); plt.close(fig)
# fig4 compactness by photon reco class
fig, ax = PS.figure(1, 2, size=(10, 4.2)); order = [o for o in NA.OBJECT_ORDER if (D.obj == o).sum() >= 10]
ax[0, 0].boxplot([D.loc[D.obj == o, SEGV].values for o in order], tick_labels=[f"{o}\n(n={int((D.obj == o).sum())})" for o in order], showfliers=False, whis=(16, 84)); ax[0, 0].set_ylabel("tagger shower segments")
ax[0, 1].boxplot([D.loc[D.obj == o, LENV].values for o in order], tick_labels=[f"{o}" for o in order], showfliers=False, whis=(16, 84)); ax[0, 1].set_ylabel("total shower length (cm)")
for a in ax[0]: a.tick_params(axis="x", labelrotation=60, labelsize=7); a.grid(alpha=.25, axis="y")
tag(fig, "boxes: 25-75 %, whiskers 16-84 %", bottom=0.4); fig.savefig(PLT / "fig4_compactness_by_photon_class.png", dpi=150, bbox_inches="tight"); plt.close(fig)
# fig5 SHAP families accepted vs rejected, compact vs not
fig, ax = PS.figure(1, 1, size=(8.6, 4.4)); glabs = ["accepted & not compact", "accepted & compact", "rejected & not compact", "rejected & compact"]; gcol = ["#56B4E9", "#0072B2", "#E69F00", "#D55E00"]; w = 0.2
for gi, gl in enumerate(glabs):
    t = FR[FR.group == gl].set_index("family").reindex(families); ax[0, 0].bar(np.arange(len(families)) + (gi - 1.5) * w, t.mean_signed_phi, w, color=gcol[gi], label=f"{gl} (n={int(t.n.iloc[0])})")
ax[0, 0].axhline(0, color="k", lw=.7); ax[0, 0].set_xticks(range(len(families))); ax[0, 0].set_xticklabels([f.replace(" (", "\n(") for f in families], rotation=45, ha="right", fontsize=7); ax[0, 0].set_ylabel("mean TreeSHAP margin contribution\n(vs a mixed signal background)"); ax[0, 0].legend(frameon=False, fontsize=7); ax[0, 0].grid(alpha=.25, axis="y")
tag(fig, "interventional TreeSHAP of the frozen numu margin; additivity checked", bottom=0.4); fig.savefig(PLT / "fig5_shap_families_by_group.png", dpi=150, bbox_inches="tight"); plt.close(fig)
# fig6 truth topology comparison: survival by topology x compactness
fig, ax = PS.figure(1, 2, size=(9.4, 3.8), sharey=True); w = 0.25
for j, (flag, ttl) in enumerate((("compact", "length < 20 cm vs >= 20 cm"), ("few_seg", "< 5 vs >= 5 segments"))):
    for ti, (t_, l) in enumerate(TOPO.items()):
        for ci, (cv, hatch) in enumerate(((True, "//"), (False, None))):
            s = D[(D.truth35 == t_) & (D[flag] == cv)]; p, lo, hi = NA.wilson(int(s.survive.sum()), len(s)); ax[0, j].bar(ti + (ci - .5) * w, p, w, color=C[t_], hatch=hatch, edgecolor="k", lw=.5, yerr=[[max(p - lo, 0)], [max(hi - p, 0)]], capsize=2, label=None)
            ax[0, j].text(ti + (ci - .5) * w, 0.02, f"n={len(s)}", ha="center", fontsize=6, rotation=90)
    ax[0, j].set_xticks(range(3)); ax[0, j].set_xticklabels(list(TOPO.values())); ax[0, j].set_title(f"hatched = compact side ({ttl})", fontsize=8); ax[0, j].set_ylim(0, 1); ax[0, j].grid(alpha=.25, axis="y")
ax[0, 0].set_ylabel("numu survival (Wilson 68 %)"); tag(fig); fig.savefig(PLT / "fig6_topology_by_compactness.png", dpi=150, bbox_inches="tight"); plt.close(fig)
# fig7 natural CV vs official
fig, ax = PS.figure(1, 1, size=(5.6, 3.8))
t1 = NA.survival_table(D, ["lenb"]).set_index("lenb").reindex(NA.LEN_LABELS); t2 = NA.survival_table(N, ["lenb"]).set_index("lenb").reindex(NA.LEN_LABELS)
eb(ax[0, 0], np.arange(4, dtype=float), t1, "#0072B2", f"official Gen2 (n={len(D)} events)", -0.05); t2 = t2.dropna(subset=["survival"]); eb(ax[0, 0], np.array([NA.LEN_LABELS.index(i) for i in t2.index], float), t2, "#D55E00", f"natural CV (n={len(N)} candidates)", 0.05, "s")
ax[0, 0].set_xticks(range(4)); ax[0, 0].set_xticklabels(NA.LEN_LABELS); ax[0, 0].set_xlabel("total tagger shower length (cm)"); ax[0, 0].set_ylabel("numu survival (Wilson 68 %)"); ax[0, 0].set_ylim(0, 1); ax[0, 0].grid(alpha=.25); ax[0, 0].legend(frameon=False, fontsize=7)
tag(fig); fig.savefig(PLT / "fig7_natural_cv_vs_official.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ============================================================================================================================ summary + metadata
def git(*a): return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()
cfg_sha = sha(REPO / "configs" / "baseline_selection.yaml")
meta = dict(git_head_at_run=git("rev-parse", "HEAD"), branch=git("rev-parse", "--abbrev-ref", "HEAD"), baseline_config_sha256=cfg_sha, numu_xml_sha256=sha(B.DEFAULT_WEIGHT_DIR / "single_photon_numu_bdt_final.xml"), thresholds=dict(numu=0.4, other=0.2, ncpi0=-0.05),
            compactness_bins=dict(n_seg_edges=[0, 5, 11, 18, "inf"], length_edges_cm=[0, 20, 40, 80, "inf"], compact_length_cm=NA.COMPACT_LENGTH_CM, few_segment_below=NA.COMPACT_NSEG), seeds=dict(shap=20261111, bootstrap=20261111), inputs={p.name: sha(p) for p in (P12 / "numu_stage.parquet", P12 / "numu_stage_inputs.parquet", P15 / "photon_pid_events.parquet")})
SUMMARY["metadata"] = meta; (TAB / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=float)); (OUT / "metadata.json").write_text(json.dumps(meta, indent=1, default=float))
print(json.dumps({k_: v for k_, v in SUMMARY.items() if k_ != "metadata"}, indent=1, default=float)[:6000])
