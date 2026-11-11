#!/usr/bin/env python
"""AUDIT of the remaining FROZEN single-photon stages of the inherited Wire-Cell selection: the ``numu`` and ``ncpi0`` BDTs, the ``nue`` BDT (inactive) and ``shw_sp_n_20br1_showers == 1``
(descriptive; NO retraining, NO threshold scan, NO new cut, NO policy choice).

    source env/setup_eaf.sh
    python scripts/remaining_stage_scan.py official ; python scripts/remaining_stage_scan.py natural
    python scripts/other_bdt_source_table.py --wct-src <production source dir> --model numu|ncpi0|nue --outdir tables/remaining_stage_audit
    python scripts/remaining_stage_audit.py

Populations (official Gen2 NC-Delta, provisional TPC truth box, policy ``any``): numu = events with a BDT-evaluable candidate (8,034); ncpi0 = events that pass numu AND other (2,781); n_20br1 = events that
pass numu, other, ncpi0 and nue (1,313).  The event-level ``any`` logic is kept: the controlling candidate of a stage is the REACHING candidate with the largest frozen score of that stage (ties: lowest nu_index);
the event passes iff that score exceeds the FIXED threshold (checked event by event against the validated baseline flags).  The BDT scores are NOT stored in the CAF: the reference is the validated
derived-table score of the baseline (``candidates.parquet``), reproduced by the frozen scorer and by the independent TMVA-rule float32 evaluator.
Outputs outside Git: $SP_DATA/remaining_stage_audit/official_ncdelta/ ; compact summaries: tables/remaining_stage_audit/ ; figures: plots/remaining_stage_audit/.
"""
from __future__ import annotations
import hashlib, json, math, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import bdt as B, differential as DF, exclusive_signal as X, other_audit as OA, plotstyle as PS, remaining_audit as RA
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "remaining_stage_audit" / "official_ncdelta"; RAW = OUT / "raw"
P8 = SPD / "other_bdt_audit" / "official_ncdelta"; P9 = SPD / "shower_vertex_audit" / "official_ncdelta"; P10 = SPD / "proton_truth_association" / "official_ncdelta"; P11 = SPD / "common_observables" / "official_ncdelta"
PLD = REPO / "plots" / "remaining_stage_audit"; SUMD = REPO / "tables" / "remaining_stage_audit"
for d in (PLD, SUMD, OUT, OUT / "attribution", OUT / "default_fraction_tables", OUT / "stage_cleanliness"):
    d.mkdir(parents=True, exist_ok=True)
KEY = ["file_index", "ev"]; RSE = ["run", "subrun", "evt"]; SUMMARY: dict = {}
THR = RA.FROZEN_THRESHOLDS
PROV = "official Gen2 NC-Delta | frozen inherited selection (policy any) | TPC-box signal events at the stage | thresholds fixed (numu 0.4, ncpi0 -0.05) | descriptive audit"
TOPO = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}; TCOL = {0: "#0072B2", 1: "#D55E00", 2: "#009E73"}
STAGES = ["shower", "evaluable", "numu", "other", "ncpi0", "nue", "n20br1"]
STAGES_FULL = ["candidate"] + STAGES
FLAG = dict(candidate="A_candidate", shower="A_n20mev", evaluable="A_bdt_evaluable", numu="A_numu", other="A_other", ncpi0="A_ncpi0", nue="A_nue", n20br1="A_n20br1")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cp(k, n):
    return X.binom_ci(int(k), int(n)) if n else (np.nan,) * 3


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLD / name, bbox_inches="tight"); plt.close(fig)


def pq(df):
    """DataFrame safe for parquet: category / interval columns as strings, input columns dropped by the caller."""
    d = df.copy()
    for c_ in d.columns:
        if str(d[c_].dtype) == "category":
            d[c_] = d[c_].astype(str)
    return d


def wr(df, name, outside=None):
    df.to_csv(SUMD / name, index=False)
    if outside:
        df.to_csv(OUT / outside / name, index=False)
    return df


# ======================================================================================================================= load and stage populations
def load():
    sc = pd.read_parquet(RAW / "official_candidates.parquet")
    bc = pd.read_parquet(SPD / "analysis_tables" / "official_gen2_ncdelta" / "candidates.parquet", columns=KEY + ["c_nu_index", "c_score_numu", "c_score_other", "c_score_ncpi0", "c_score_nue", "bdt_evaluable", "cum_candidate_in_valid_event", "cum_n_20mev_showers_gt0",
                         "cum_single_photon_numu_score_gt_0p4", "cum_single_photon_other_score_gt_0p2", "cum_single_photon_ncpi0_score_gt_m0p05", "cum_single_photon_nue_score_gt_m1", "cum_n_20br1_showers_eq1", "c_np35", "c_nrows"])
    c = sc.merge(bc, on=KEY + ["c_nu_index"], how="left", validate="one_to_one")
    c["reach_evaluable"] = c.cum_n_20mev_showers_gt0.fillna(False).astype(bool)
    c["reach_numu"] = c.reach_evaluable & c.c_score_numu.notna()      # finite numu inputs (the baseline `bdt_evaluable` flag requires finite inputs for ALL FOUR models; 3 events pass numu with a non-finite input of a later model)
    c["reach_other"] = c.cum_single_photon_numu_score_gt_0p4.fillna(False).astype(bool); c["reach_ncpi0"] = c.cum_single_photon_other_score_gt_0p2.fillna(False).astype(bool)
    c["reach_nue"] = c.cum_single_photon_ncpi0_score_gt_m0p05.fillna(False).astype(bool); c["reach_n20br1"] = c.cum_single_photon_nue_score_gt_m1.fillna(False).astype(bool)
    T = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"); T = T[T.tpc_box & T.file_index.notna()].copy(); T["file_index"] = T.file_index.astype(int)
    tx = pd.read_parquet(P9 / "event_taxonomy.parquet", columns=KEY + ["outcome", "photon_object_state", "dom_is_sig", "pf_state", "dom_nu", "dom_row"]); tx["clean"] = tx.outcome.map(RA.clean_label)
    vg = pd.read_parquet(P9 / "vertex_geometry.parquet", columns=KEY + ["anchored5", "d_vertex", "conv_distance_cm", "photon_end_class"])
    rm = pd.read_parquet(P10 / "row_matches.parquet", columns=["file_index", "ev", "cand", "row", "kine_particle_type", "ke", "in_match", "origin", "kine_particle_is_shower", "p1_t_pdg", "p1_t_nu", "sig_nu", "kine_energy_included"])
    og = pd.read_parquet(P8 / "proton_origin_all_candidate_stage.parquet", columns=RSE + ["origin"]).rename(columns=dict(origin="proton_origin"))
    E = T.merge(tx, on=KEY, how="left").merge(vg, on=KEY, how="left").merge(og, on=RSE, how="left")
    # leading reco proton row of the SIGNAL-MATCHED candidate: true signal primary proton present or not
    p = rm[rm.in_match & (rm.kine_particle_type == 2212) & (rm.ke > 35)].sort_values("ke", ascending=False).drop_duplicates(KEY)[KEY + ["origin"]].rename(columns=dict(origin="lead_proton_class"))
    E = E.merge(p, on=KEY, how="left")
    E["lead_proton_class"] = np.where(E.A_matched.astype(bool), E.lead_proton_class.fillna("absent"), "no signal-matched candidate")
    E["true_proton_present"] = np.where(~E.A_matched.astype(bool), "no signal-matched candidate", np.where(E.lead_proton_class == "true_primary_signal_proton", "true signal proton present", "absent / other"))
    E["anch"] = np.where(E.anchored5.isna(), "no signal-matched candidate", np.where(E.anchored5 == True, "anchored", "not anchored"))
    E["topo"] = E.truth35.map(TOPO); E["clean_l"] = E.clean.fillna("fails_shower_stage")
    return c, E, T, rm


def model_of(m):
    return B.TmvaBdt(m, B.DEFAULT_WEIGHT_DIR / f"single_photon_{m}_bdt_final.xml")


def stage_frame(c, E, stage):
    """Event-level frame of a stage population with the controlling candidate (inputs, score) and the survival flag (asserted equal to the validated baseline flag)."""
    spec = dict(numu=("reach_numu", "numu_score", "A_numu"), other=("reach_other", "c_score_other", "A_other"), ncpi0=("reach_ncpi0", "ncpi0_score", "A_ncpi0"), nue=("reach_nue", "nue_score", "A_nue"))
    reach_col, score_col, flag = spec[stage]
    ctrl = RA.controlling_candidate(c, reach_col, score_col)
    F = E.merge(ctrl, on=KEY, how="inner", validate="one_to_one", suffixes=("", "_c"))
    prev = {"numu": None, "other": "A_numu", "ncpi0": "A_other", "nue": "A_ncpi0"}[stage]
    if prev:
        assert len(F) == int(E[prev].sum()) and F[prev].astype(bool).all(), (stage, len(F))                       # the population is exactly the events that passed the previous stage
    else:
        assert F.A_numu.astype(bool).sum() == int(E.A_numu.sum()), "an event passes numu without a reaching candidate"
    F["stage_score"] = F[score_col]; F["survive"] = F.stage_score > THR[stage]
    assert (F.survive == F[flag].astype(bool)).all(), f"controlling-candidate decision disagrees with the validated flag at {stage}"
    return F


def reproduction_block(c):
    out = {}
    for m in ("numu", "ncpi0", "nue"):
        model = model_of(m); names = model.var_names; inc = ["in_" + n for n in names]; col = f"{m}_score"
        X_ = c[inc].to_numpy(float); fin = np.isfinite(c[col]); s32 = OA.scores_tmva_float32(model, X_); both = fin & np.isfinite(s32)
        stored = c["c_score_" + m]; ok = stored.notna() & fin
        d = np.abs(s32 - c[col])[both]
        rng = np.random.default_rng(1); sub = rng.choice(np.where(both)[0], size=min(200, int(both.sum())), replace=False)
        sc = np.array([OA.scalar_score_tmva(B.DEFAULT_WEIGHT_DIR / f"single_photon_{m}_bdt_final.xml", X_[i]) for i in sub])
        out[m] = dict(n_candidates=len(c), n_compared_to_stored_derived_score=int(ok.sum()), max_abs_diff_vs_stored=float(np.abs(c[col][ok] - stored[ok]).max()), median_abs_diff_vs_stored=float(np.median(np.abs(c[col][ok] - stored[ok]))),
                      n_stored_missing=int(stored.isna().sum()), n_nonfinite_recomputed=int((~fin).sum()), n_independent_tmva_f32=int(both.sum()), max_abs_diff_vs_independent=float(d.max()), median_abs_diff_vs_independent=float(np.median(d)),
                      n_diff_gt_1e6=int((d > 1e-6).sum()), n_decision_flips_at_threshold=int(((c[col] > THR[m]) != (s32 > THR[m]))[both].sum()), n_tie_convention_cases=RA.n_tie_cases(model, X_), scalar_xml_subset_n=len(sub),
                      scalar_vs_vectorised_f32_max=float(np.abs(sc - s32[sub]).max()), n_inputs=len(names), n_trees=len(model.trees), n_leaves=int(sum((t.ivar < 0).sum() for t in model.trees)), weight_sha256=B.sha256(B.DEFAULT_WEIGHT_DIR / f"single_photon_{m}_bdt_final.xml"))
        assert out[m]["max_abs_diff_vs_stored"] == 0.0 and out[m]["n_decision_flips_at_threshold"] == 0, (m, out[m])
        if m in ("numu", "ncpi0"):
            assert out[m]["max_abs_diff_vs_independent"] < 1e-6, (m, out[m])                     # exact float-level agreement is required for the models that are attributed
        else:
            assert out[m]["n_diff_gt_1e6"] <= out[m]["n_tie_convention_cases"], (m, out[m])      # nue: every candidate where the two evaluators differ is a tie-convention case (x exactly on a cut)
    SUMMARY["reproduction"] = out; wr(pd.DataFrame(out).T.reset_index().rename(columns={"index": "model"}), "score_reproduction.csv", "attribution"); return out


# ======================================================================================================================= survival tables, score distributions, topology decomposition
def surv_row(df, mask, label, value, col="survive"):
    n = int(mask.sum()); k = int((mask & df[col].astype(bool)).sum()); f, lo, hi = cp(k, n)
    return dict(group=label, value=value, n=n, k=k, survival=f, lo68=lo, hi68=hi)


def survival_tables(F, stage):
    recs = []
    groups = [("all", pd.Series("all", index=F.index)), ("truth_topology", F.topo), ("delta_charge", F.delta_label), ("vertex_anchoring", F.anch), ("photon_cleanliness", F.clean_l), ("true_reco_proton", F.true_proton_present),
              ("candidate_multiplicity", np.where(F.n_reaching > 1, "2+ reaching candidates", "1 reaching candidate")), ("proton_origin", F.proton_origin.fillna("n/a (not a truth-1p single-proton event)"))]
    for lab, s in groups:
        for v in pd.Series(s).dropna().unique():
            recs.append(surv_row(F, (pd.Series(s, index=F.index) == v).to_numpy(), lab, v))
    # harmonized (SPINE-like) truth definition: signal flag x 0p50 / Np50
    h = F.spine_truth_signal.astype(bool)
    for lab, m in (("harmonized all (spine_truth_signal)", h), ("harmonized 0p50", h & F.spine_truth_0p50.astype(bool)), ("harmonized Np50", h & F.spine_truth_Np50.astype(bool))):
        recs.append(surv_row(F, m.to_numpy(), "harmonized_truth", lab))
    # topology x clean, topology x anchored, topology x true-proton
    for a_lab, a in (("clean", F.clean_l), ("anchored", F.anch), ("true_proton", F.true_proton_present)):
        for t, g in F.groupby("topo"):
            for v in pd.Series(a[g.index]).dropna().unique():
                recs.append(surv_row(F, ((F.topo == t) & (a == v)).to_numpy(), f"topology x {a_lab}", f"{t} | {v}"))
    for t, g in F.groupby("delta_label"):
        for tt, g2 in g.groupby("topo"):
            recs.append(surv_row(F, ((F.delta_label == t) & (F.topo == tt)).to_numpy(), "delta x topology", f"{t} | {tt}"))
    R = pd.DataFrame(recs); R.insert(0, "stage", stage); return R


def decomposition_block(F, stage):
    """Task 18: how much of the 1p-0p and Delta+ - Delta0 survival difference is inherited from the reconstruction state (clean photon, anchored vertex, true proton present, candidate multiplicity)?"""
    Q = F.copy(); Q["truth_cat"] = Q.truth35.astype(int); Q["delta_pdg"] = np.where(Q.delta_label == "Delta0", 2114, 2214)
    Q["f_clean"] = (Q.clean_l == "clean").astype(float); Q["f_anch"] = (Q.anch == "anchored").astype(float); Q["f_prot"] = (Q.true_proton_present == "true signal proton present").astype(float)
    Q["f_nreach"] = (Q.n_reaching > 1).astype(float); Q["f_energy"] = Q.photon_energy_mev.astype(float); Q["f_cosb"] = Q.cos_theta_beam.astype(float)
    sets = {"raw": [], "+ photon cleanliness": ["f_clean"], "+ vertex anchoring": ["f_clean", "f_anch"], "+ true reco proton present": ["f_clean", "f_anch", "f_prot"], "+ candidate multiplicity": ["f_clean", "f_anch", "f_prot", "f_nreach"],
            "+ photon energy and direction": ["f_clean", "f_anch", "f_prot", "f_nreach", "f_energy", "f_cosb"]}
    recs = []
    for pair, (a, b) in {"truth 1p - truth 0p": ("truth_0p", "truth_1p"), "truth >=2p - truth 0p": ("truth_0p", "truth_ge2p"), "Delta+ - Delta0": ("Delta0", "Delta+")}.items():
        for nm, f in sets.items():
            Qf = Q.dropna(subset=f) if f else Q
            if not f:
                gm = DF.group_masks(Q, [a, b]); ya = Q.survive[gm[a]].mean(); yb = Q.survive[gm[b]].mean(); r = dict(raw_difference=float(yb - ya), adjusted_difference=float(yb - ya), adjusted_lo68=np.nan, adjusted_hi68=np.nan, n=int((gm[a] | gm[b]).sum()))
            else:
                r = {k: float(v) for k, v in DF.adjusted_difference(Qf, a, b, f, stage_col="survive", n_boot=100).items() if isinstance(v, (int, float))}
            recs.append(dict(stage=stage, pair=pair, covariates=nm, **{k: r.get(k, np.nan) for k in ("n", "raw_difference", "adjusted_difference", "adjusted_lo68", "adjusted_hi68")}))
    return pd.DataFrame(recs)


# ======================================================================================================================= inputs: distributions, defaults, families
def vstats(a, b, name):
    a = np.asarray(a, float); b = np.asarray(b, float); a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if len(a) < 3 or len(b) < 3:
        return dict(variable=name, n_a=len(a), n_b=len(b))
    pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2); ks = stats.ks_2samp(a, b)
    return dict(variable=name, n_a=len(a), n_b=len(b), median_a=np.median(a), median_b=np.median(b), q16_a=np.quantile(a, .16), q84_a=np.quantile(a, .84), q16_b=np.quantile(b, .16), q84_b=np.quantile(b, .84),
                smd=(b.mean() - a.mean()) / pooled if pooled > 0 else 0.0, ks=ks.statistic, wasserstein=stats.wasserstein_distance(a, b), wasserstein_over_sd=(stats.wasserstein_distance(a, b) / pooled) if pooled > 0 else 0.0)


def source_defaults(model):
    """Declared default of every input: the struct default of `NeutrinoTaggerInfo.h`, EXCEPT the upstream sub-BDT scores, whose operative 'default' is the `default_val` the scorer returns when the sub-BDT has no object to score
    (`SCORER_DEFAULT`; the struct default 0 is only seen if the scorer was not run, MEASURED: it never is) and the log-odds `numu_score` (no default)."""
    t = pd.read_csv(SUMD / f"input_source_table_{model}.csv"); out = {r.bdt_variable: (float(r.declared_default) if str(r.declared_default).strip() not in ("", "nan") else np.nan) for r in t.itertuples()}
    for n in out:
        if RA.family_of(n) == "upstream BDT scores":
            out[n] = SCORER_DEFAULT.get(n, np.nan)
    return out


def input_block(F, model, stage):
    names = model_of(model).var_names; dflt = source_defaults(model); recs = []
    pairs = {"pass vs fail": (~F.survive, F.survive), "truth 0p vs 1p": (F.truth35 == 0, F.truth35 == 1), "clean vs non-clean photon": (F.clean_l == "non_clean", F.clean_l == "clean"), "not anchored vs anchored": (F.anch == "not anchored", F.anch == "anchored")}
    for pn, (ma, mb) in pairs.items():
        for n in names:
            r = vstats(F.loc[ma, "in_" + n], F.loc[mb, "in_" + n], n); d = dflt.get(n, np.nan)
            r.update(pair=pn, family=RA.family_of(n), default=d, frac_default_a=RA.default_fraction(F.loc[ma, "in_" + n], d), frac_default_b=RA.default_fraction(F.loc[mb, "in_" + n], d)); recs.append(r)
    R = pd.DataFrame(recs); R.insert(0, "stage", stage); R.insert(1, "model", model); return R


REASON = {   # family-level reason a value sits at its declared default (from the fill code read in the source; the same reasons as the Phase-8 `other` audit)
    "upstream BDT scores": "the sub-BDT returns its scorer default when its per-segment/per-object input vectors are empty (the candidate has no object of that tagger); `NeutrinoTaggerInfo.h` default 0 if the scorer was not run",
    "cosmic tagger": "the cosmic sub-tagger did not fire / was not filled for this candidate (the `cosmict_*_filled` flags and their vectors stay empty)",
    "numuCC tagger inputs": "the numuCC flag tagger found no qualifying muon candidate (flag 3 branch not filled)",
    "shower quality (br/lem/hol/lol)": "br2/hol_2 are evaluated only when the shower's start segment is attached to the main vertex (`sg_at_main`); br3/br4/lem/lol sub-checks fill only for qualifying shower topologies",
    "calorimetry (dQ/dx, dE/dx)": "the stem dQ/dx vector is padded (value 3) when the stem has fewer than 20 fit points; summaries stay at their struct default for an unfilled shower",
    "track / hadron activity": "no (second) proton or MIP track attached at the main vertex (`shw_sp_proton_*` default -1 / 0)",
    "vertex / gap geometry": "`shw_sp_shw_vtx_dis` is 0 for an attached shower; the other geometry fields keep struct defaults for an unfilled shower",
    "multiplicity": "counters start at 0; a shower set without the corresponding flag stays at 0",
    "pi0 topology": "`shw_sp_pio_1_*` are filled only if the shower belongs to a reconstructed pi0 pair (`map_shower_pio_id`); `kine_pio_*` only if the kinematics tree found a pi0 pair",
}


def defaults_block(F, model, stage):
    names = model_of(model).var_names; dflt = source_defaults(model); splits = {"all": F.index == F.index, "truth 0p": F.truth35 == 0, "truth 1p": F.truth35 == 1, "truth >=2p": F.truth35 == 2, "Delta0": F.delta_label == "Delta0", "Delta+": F.delta_label == "Delta+",
                                                                                "anchored": F.anch == "anchored", "not anchored": F.anch == "not anchored", "true proton present": F.true_proton_present == "true signal proton present", "true proton absent/other": F.true_proton_present == "absent / other",
                                                                                "clean photon": F.clean_l == "clean", "non-clean photon": F.clean_l == "non_clean", "survive": F.survive, "fail": ~F.survive}
    recs = []
    for n in names:
        d = dflt.get(n, np.nan); r = dict(stage=stage, model=model, variable=n, family=RA.family_of(n), declared_default=d, reason=REASON[RA.family_of(n)])
        for sn, m in splits.items():
            r["frac_default_" + sn] = RA.default_fraction(F.loc[np.asarray(m), "in_" + n], d)
        recs.append(r)
    return pd.DataFrame(recs)


# ======================================================================================================================= model-internal attribution (exact interventional TreeSHAP of the margin; accepted signal as the background)
def shap_block(F, model_name, stage, nfg=600, nbg=300, seed=20261111, extra_events=None):
    """Explain the margin of REJECTED signal candidates relative to ACCEPTED signal candidates of the same stage (exact interventional TreeSHAP against an explicit background sample).
    ``extra_events``: boolean mask of events (rows of F) whose individual attributions are also returned."""
    m = model_of(model_name); names = m.var_names; inc = ["in_" + n for n in names]; Xa = F[inc].to_numpy(float); fin = np.isfinite(Xa).all(axis=1)
    rng = np.random.default_rng(seed); fg_all = np.where(fin & ~F.survive.to_numpy())[0]; bg_all = np.where(fin & F.survive.to_numpy())[0]
    fg = np.sort(rng.choice(fg_all, min(nfg, len(fg_all)), replace=False)); bg = np.sort(rng.choice(bg_all, min(nbg, len(bg_all)), replace=False)); paths = OA.leaf_paths(m)
    res = OA.interventional_shap(m, Xa[fg], Xa[bg], paths); phi = res["phi"]; base = res["base"]
    margin = OA.tree_contributions(m, Xa[fg]).sum(axis=1); add_err = float(np.abs(margin - base - phi.sum(axis=1)).max())
    fam = np.array([RA.family_of(n) for n in names]); topo = F.truth35.to_numpy()[fg]
    var = pd.DataFrame(dict(stage=stage, model=model_name, variable=names, family=fam, mean_phi=phi.mean(axis=0), mean_abs_phi=np.abs(phi).mean(axis=0)))
    for t_, lab in ((0, "0p"), (1, "1p")):
        var["mean_phi_rejected_" + lab] = phi[topo == t_].mean(axis=0) if (topo == t_).any() else np.nan
    var = var.sort_values("mean_abs_phi", ascending=False)
    fams = []
    for f_ in RA.FAMILIES:
        idx = fam == f_
        if idx.any():
            fams.append(dict(stage=stage, model=model_name, family=f_, n_inputs=int(idx.sum()), mean_signed_phi=float(phi[:, idx].sum(axis=1).mean()), mean_abs_family_phi=float(np.abs(phi[:, idx].sum(axis=1)).mean()), share_of_abs_phi=float(np.abs(phi[:, idx]).sum() / np.abs(phi).sum()),
                             mean_signed_phi_0p=float(phi[topo == 0][:, idx].sum(axis=1).mean()) if (topo == 0).any() else np.nan, mean_signed_phi_1p=float(phi[topo == 1][:, idx].sum(axis=1).mean()) if (topo == 1).any() else np.nan))
    fam_t = pd.DataFrame(fams); gap = float(margin.mean() - base)
    info = dict(model=model_name, stage=stage, n_fg=len(fg), n_bg=len(bg), n_fg_available=len(fg_all), n_bg_available=len(bg_all), base_margin=base, mean_margin_rejected=float(margin.mean()), margin_gap=gap, additivity_max_error=add_err, threshold_margin=float(np.arctanh(THR[model_name])))
    assert add_err < 1e-6, add_err
    out = dict(var=var, fam=fam_t, info=info, phi=phi, fg=fg, bg=bg, Xa=Xa, names=names, model=m)
    if extra_events is not None:
        ex = np.where(fin & np.asarray(extra_events))[0]; r2 = OA.interventional_shap(m, Xa[ex], Xa[bg], paths); out["extra_idx"] = ex; out["extra_phi"] = r2["phi"]
    return out


# ======================================================================================================================= ncpi0: what does it reject?
def ncpi0_topology_block(F, rm):
    """Exclusive EM-topology class of every event reaching ncpi0, from the controlling candidate's pi0 inputs, the Phase-9 photon-object state and the T_kine shower rows."""
    r = rm[(rm.kine_particle_type == 11) & (rm.kine_particle_is_shower == 1) & (rm.ke > 20)].merge(F[KEY + ["c_nu_index"]].rename(columns=dict(c_nu_index="cand")), on=KEY + ["cand"])
    sigphoton = (r.p1_t_pdg == 22) & (r.p1_t_nu == r.sig_nu); r = r.assign(sigph=sigphoton)
    cnt = r.groupby(KEY).agg(n_energetic_showers=("row", "size"), n_signal_photon_rows=("sigph", "sum")).reset_index()
    G = F.merge(cnt, on=KEY, how="left").fillna({"n_energetic_showers": 0, "n_signal_photon_rows": 0})
    mass = G["in_shw_sp_pio_1_mass"]; flag = G["in_shw_sp_pio_flag_pio"] == 1
    cls = np.select([flag & ((mass - 135).abs() < 60), flag, G["in_kine_pio_flag"] != 0, G.photon_object_state.astype(str).str.contains("fragment", na=False) | (G.n_signal_photon_rows >= 2), G.n_energetic_showers >= 2],
                    ["reco pi0 pair, mass within 60 MeV of 135", "reco pi0 pair, other mass", "kine-tree pi0 pair candidate only", "signal photon split over several shower rows", "other energetic shower in the candidate"], "single energetic shower, no pi0-pair flag")
    G["em_class"] = cls; G["n_true_photons_25"] = G.n_gamma25
    recs = []
    for c_, g in G.groupby("em_class"):
        n = len(g); k = int(g.survive.sum()); f, lo, hi = cp(k, n)
        recs.append(dict(em_class=c_, n=n, rejected=n - k, survive=k, survival=f, lo68=lo, hi68=hi, frac_of_rejected=float((~g.survive).sum() / (~G.survive).sum()), true_photons_ge2_frac=float((g.n_true_photons_25 >= 2).mean()),
                         median_ncpi0_score=float(g.stage_score.median()), n0p=int((g.truth35 == 0).sum()), n1p=int((g.truth35 == 1).sum()), n2p=int((g.truth35 == 2).sum())))
    T = pd.DataFrame(recs).sort_values("n", ascending=False); return G, T


# ======================================================================================================================= n_20br1 == 1
def n20br1_block(c, E, rm):
    reach = c[c.reach_n20br1].copy(); ev_in = E[E.A_nue.astype(bool)]; passes = reach.groupby(KEY).apply(lambda g: bool((g.shw_sp_n_20br1_showers == 1).any())).rename("any_br1_eq1").reset_index()
    G = ev_in.merge(passes, on=KEY, how="left"); assert len(G) == int(E.A_nue.sum()) and (G.any_br1_eq1 == G.A_n20br1.astype(bool)).all(), "n_20br1 any-logic disagrees with the validated flag"
    fail = G[~G.any_br1_eq1]; assert len(fail) == 160, len(fail)
    r = reach.merge(fail[KEY], on=KEY).sort_values(KEY + ["shw_sp_energy", "c_nu_index"], ascending=[True, True, False, True]).drop_duplicates(KEY)       # controlling candidate of a failing event: the largest shower energy
    nreach = reach.merge(fail[KEY], on=KEY).groupby(KEY).size().rename("n_reaching").reset_index()
    F = fail.merge(r[KEY + ["c_nu_index", "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers", "shw_sp_n_br1_showers", "shw_sp_energy"]], on=KEY, validate="one_to_one").merge(nreach, on=KEY)
    sh = rm[(rm.kine_particle_type == 11) & (rm.kine_particle_is_shower == 1) & (rm.ke > 20)].merge(F[KEY + ["c_nu_index", "dom_nu", "dom_row"]].rename(columns=dict(c_nu_index="cand_c")), on=KEY)
    sh = sh[sh.cand == sh.cand_c]; sh = sh[~((sh.cand == sh.dom_nu) & (sh.row == sh.dom_row))]
    sh["kind"] = np.where((sh.p1_t_pdg == 22) & (sh.p1_t_nu == sh.sig_nu), "extra_signal_photon", np.where(sh.p1_t_nu == sh.sig_nu, "extra_other_signal", "extra_other_interaction"))
    cnt = sh.groupby(KEY + ["kind"]).size().unstack(fill_value=0).reset_index(); F = F.merge(cnt, on=KEY, how="left")
    for k in ("extra_signal_photon", "extra_other_signal", "extra_other_interaction"):
        F[k] = F[k].fillna(0).astype(int) if k in F else 0
    F["n_energetic_shower_rows"] = F.merge(sh.groupby(KEY).size().rename("_n").reset_index(), on=KEY, how="left")["_n"].fillna(0).astype(int).to_numpy() + 1
    F["cls_n20br1"] = [RA.classify_n20br1(int(n), cl == "clean", a, b_, d) for n, cl, a, b_, d in zip(F.shw_sp_n_20br1_showers, F.clean_l, F.extra_signal_photon, F.extra_other_signal, F.extra_other_interaction)]
    assert F.cls_n20br1.isin(RA.N20BR1_CLASSES).all() and len(F) == 160
    recs = []
    for k in RA.N20BR1_CLASSES:
        g = F[F.cls_n20br1 == k]; recs.append(dict(cls=k, n=len(g), frac=len(g) / 160, n0p=int((g.truth35 == 0).sum()), n1p=int((g.truth35 == 1).sum()), n2p=int((g.truth35 == 2).sum()), nDelta0=int((g.delta_label == "Delta0").sum()), nDeltaPlus=int((g.delta_label == "Delta+").sum()),
                                                  n_clean=int((g.clean_l == "clean").sum()), median_n20mev=float(g.shw_sp_n_20mev_showers.median()) if len(g) else np.nan, median_n20br1=float(g.shw_sp_n_20br1_showers.median()) if len(g) else np.nan))
    T = pd.DataFrame(recs)
    ctx = G.merge(reach.sort_values(KEY + ["shw_sp_n_20br1_showers"], ascending=[True, True, False]).drop_duplicates(KEY)[KEY + ["shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers"]], on=KEY)
    dist = ctx.assign(passes=ctx.any_br1_eq1).groupby([ctx.shw_sp_n_20mev_showers.clip(upper=4), ctx.shw_sp_n_20br1_showers.clip(upper=4)]).passes.agg(["size", "sum"]).reset_index().rename(columns=dict(size="n_events", sum="n_pass", shw_sp_n_20mev_showers="n_20mev_showers_capped_4", shw_sp_n_20br1_showers="max_n_20br1_over_reaching_cands_capped_4"))
    return F, T, dist, G


# ======================================================================================================================= photon cleanliness through the frozen chain, conditional survival by state, topology and harmonized chains
def nonclean_sub(state, clean):
    if clean == "clean":
        return "clean"
    return {"photon_fragmented": "fragmented", "photon_shower_typed_non_electron": "typed non-electron", "photon_as_track": "track", "photon_particle_row_missing": "row missing"}.get(state, "other non-clean")


def chain_cleanliness(E):
    base = E[E.A_n20mev.astype(bool)].copy(); base["sub"] = [nonclean_sub(s, c) for s, c in zip(base.photon_object_state, base.clean_l)]
    order = ["clean", "fragmented", "typed non-electron", "track", "row missing", "other non-clean"]; recs = []; cond = []; prev = None
    for st in STAGES:
        cur = base[base[FLAG[st]].astype(bool)]
        r = dict(stage=st, n=len(cur), clean_fraction=float((cur["sub"] == "clean").mean()))
        for o in order:
            r["n_" + o.replace(" ", "_").replace("-", "_")] = int((cur["sub"] == o).sum()); r["frac_" + o.replace(" ", "_").replace("-", "_")] = float((cur["sub"] == o).mean())
        recs.append(r)
        if prev is not None:
            for lab, m in (("all", base["sub"] == base["sub"]), ("clean", base["sub"] == "clean"), ("non-clean (all)", base["sub"] != "clean")) + tuple((o, base["sub"] == o) for o in order[1:]):
                den = base[base[FLAG[prev]].astype(bool) & m]; k = int(den[FLAG[st]].astype(bool).sum()); f, lo, hi = cp(k, len(den)); cond.append(dict(stage=st, previous=prev, state=lab, n_in=len(den), n_out=k, conditional_survival=f, lo68=lo, hi68=hi))
        prev = st
    return pd.DataFrame(recs), pd.DataFrame(cond)


def chain_by_group(E, masks: dict):
    recs = []
    for gn, gm in masks.items():
        sub = E[np.asarray(gm)]; prev = None
        for st in STAGES_FULL:
            cur = sub[sub[FLAG[st]].astype(bool)]; r = dict(group=gn, stage=st, n_surviving=len(cur), n_group=len(sub))
            if prev is not None:
                den = sub[sub[FLAG[prev]].astype(bool)]; f, lo, hi = cp(len(cur), len(den)); r.update(n_entering=len(den), conditional=f, lo68=lo, hi68=hi)
            else:
                f, lo, hi = cp(len(cur), len(sub)); r.update(n_entering=len(sub), conditional=f, lo68=lo, hi68=hi)
            recs.append(r); prev = st
    return pd.DataFrame(recs)


# ======================================================================================================================= natural-CV consistency check
def natural_block():
    from sbnd_single_photon import natural_signal as NS, selection as SEL
    T = SPD / "analysis_tables" / "bnb_cv"; events = pd.read_parquet(T / "events.parquet"); cands = pd.read_parquet(T / "candidates.parquet")
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); sig = NS.to_signal_truth_table(sn); sig = sig[sig.in_region].reset_index(drop=True)
    t = X.signal_event_table(sig, events, cands, SEL.load_config(), policy="any")
    c = pd.read_parquet(RAW / "natural_candidates.parquet")
    d = cands[KEY + ["c_nu_index", "bdt_evaluable", "cum_n_20mev_showers_gt0", "cum_single_photon_numu_score_gt_0p4", "cum_single_photon_other_score_gt_0p2", "cum_single_photon_ncpi0_score_gt_m0p05", "cum_single_photon_nue_score_gt_m1"]]
    c = c.merge(d, on=KEY + ["c_nu_index"], how="left")
    c["reach_numu"] = c.cum_n_20mev_showers_gt0.fillna(False).astype(bool) & c.bdt_evaluable.fillna(False).astype(bool); c["reach_ncpi0"] = c.cum_single_photon_other_score_gt_0p2.fillna(False).astype(bool); c["reach_n20br1"] = c.cum_single_photon_nue_score_gt_m1.fillna(False).astype(bool)
    rows = []; out = {}
    for stage, reach, score, thr, popflag, passflag in (("numu", "reach_numu", "numu_score", THR["numu"], "A_bdt_evaluable", "A_numu"), ("ncpi0", "reach_ncpi0", "ncpi0_score", THR["ncpi0"], "A_other", "A_ncpi0")):
        ctrl = RA.controlling_candidate(c, reach, score); P = t[t[popflag].astype(bool)].merge(ctrl[KEY + [score]], on=KEY, how="inner"); P["survive"] = P[score] > thr
        assert len(P) == int(t[popflag].sum()) and (P.survive == P[passflag].astype(bool)).all(), stage
        for k in (0, 1, 2):
            m = P.truth_cat == k; n = int(m.sum()); kk = int(P.survive[m].sum()); f, lo, hi = cp(kk, n) if n else (np.nan,) * 3
            rows.append(dict(stage=stage, truth=TOPO[k], n_entering=n, n_surviving=kk, survival=f, lo68=lo, hi68=hi, median_score=float(P[score][m].median()) if n else np.nan))
        out[stage] = dict(n=len(P), survive=int(P.survive.sum()), median_score_all=float(P[score].median()))
    reach = c[c.reach_n20br1].merge(t[t.A_nue.astype(bool)][KEY], on=KEY); g = reach.groupby(KEY).apply(lambda x: bool((x.shw_sp_n_20br1_showers == 1).any())).rename("ok").reset_index(); P = t[t.A_nue.astype(bool)].merge(g, on=KEY)
    assert (P.ok == P.A_n20br1.astype(bool)).all()
    for k in (0, 1, 2):
        m = P.truth_cat == k; n = int(m.sum()); kk = int(P.ok[m].sum()); f, lo, hi = cp(kk, n) if n else (np.nan,) * 3
        rows.append(dict(stage="n20br1", truth=TOPO[k], n_entering=n, n_surviving=kk, survival=f, lo68=lo, hi68=hi, median_score=np.nan))
    out["n20br1"] = dict(n=len(P), survive=int(P.ok.sum())); out["n_signal_events"] = len(t)
    a = [r for r in rows if r["stage"] == "numu" and r["truth"] in ("truth 0p", "truth 1p")]
    out["fisher_numu_0p_vs_1p_p"] = float(stats.fisher_exact([[a[0]["n_surviving"], a[0]["n_entering"] - a[0]["n_surviving"]], [a[1]["n_surviving"], a[1]["n_entering"] - a[1]["n_surviving"]]])[1]); R = pd.DataFrame(rows); wr(R, "natural_cv_stage_survival.csv"); SUMMARY["natural"] = dict(out, rows=R.to_dict("records")); return R


# ======================================================================================================================= numu: why does it reject so much signal?  (Task 11/12)
def driver_block(F, rm, stage):
    G = F.copy(); r = rm[rm.kine_particle_is_shower.notna()].merge(G[KEY + ["c_nu_index"]].rename(columns=dict(c_nu_index="cand")), on=KEY + ["cand"])
    mu = r[r.kine_particle_type.isin([13, 211])].groupby(KEY).size().rename("n_mu_pi_rows"); tr = r[r.kine_particle_is_shower == 0].groupby(KEY).size().rename("n_track_rows"); pr = r[(r.kine_particle_type == 2212) & (r.ke > 35)].groupby(KEY).size().rename("n_proton_rows")
    G = G.merge(mu.reset_index(), on=KEY, how="left").merge(tr.reset_index(), on=KEY, how="left").merge(pr.reset_index(), on=KEY, how="left").fillna({"n_mu_pi_rows": 0, "n_track_rows": 0, "n_proton_rows": 0})
    dn = [n for n in model_of("numu").var_names]; dflt = source_defaults("numu"); G["n_default_inputs"] = sum((G["in_" + n].astype("float32") == np.float32(dflt[n])).astype(int) if np.isfinite(dflt.get(n, np.nan)) else 0 for n in dn)
    G["e_bin"] = pd.cut(G.photon_energy_mev, [0, 100, 200, 300, 400, 600, 5000], right=False); G["cosb_bin"] = pd.cut(G.cos_theta_beam, [-1, -0.5, 0, 0.5, 0.8, 1.0001], right=False)
    G["mu_like"] = np.where(G.n_mu_pi_rows > 0, "a muon/pion-typed row in the candidate", "no muon/pion-typed row"); G["nproton_bin"] = G.n_proton_rows.clip(upper=3).astype(int).astype(str)
    G["ntrack_bin"] = pd.cut(G.n_track_rows, [-1, 0, 1, 2, 4, 100]); G["ndefault_bin"] = pd.cut(G.n_default_inputs, [-1, 20, 30, 40, 50, 80]); G["ngood_bin"] = G.in_shw_sp_n_good_showers.clip(upper=3).astype(int).astype(str) if "in_shw_sp_n_good_showers" in G else "n/a"
    recs = []
    for sub_lab, sub in (("all events at the stage", G), ("clean photon only", G[G.clean_l == "clean"]), ("non-clean photon only", G[G.clean_l == "non_clean"])):
        for var in ("e_bin", "cosb_bin", "mu_like", "nproton_bin", "ntrack_bin", "ndefault_bin", "ngood_bin", "true_proton_present", "anch", "topo"):
            for b, g in sub.groupby(var, observed=True):
                k = int(g.survive.sum()); f, lo, hi = cp(k, len(g)); recs.append(dict(stage=stage, subset=sub_lab, variable=var, bin=str(b), n=len(g), k=k, survival=f, lo68=lo, hi68=hi))
    return G, pd.DataFrame(recs)


def high_energy_failures(G, S):
    """Deterministic list: true photon E > 400 MeV, reaches numu, fails numu (every such event, sorted by run/subrun/evt); with the dominant rejecting attribution families of each event."""
    m = (G.photon_energy_mev > 400) & ~G.survive; L = G[m].copy().sort_values(RSE)
    idx = np.where(m.to_numpy())[0]; pos = {i: j for j, i in enumerate(S["extra_idx"])}; names = S["names"]; fam = np.array([RA.family_of(n) for n in names]); rows = []
    for ii, (_, r) in zip(idx, G[m].iterrows()):
        if ii not in pos:
            continue
        phi = S["extra_phi"][pos[ii]]; fam_phi = {f: float(phi[fam == f].sum()) for f in RA.FAMILIES if (fam == f).any()}; order = np.argsort(phi)
        rows.append(dict(run=int(r.run), subrun=int(r.subrun), evt=int(r.evt), truth_topology=r.topo, delta=r.delta_label, photon_energy_mev=float(r.photon_energy_mev), photon_clean=r.clean_l, photon_object_state=r.photon_object_state, vertex_anchoring=r.anch,
                         true_reco_proton=r.true_proton_present, proton_origin=r.proton_origin, numu_score=float(r.stage_score), n_reaching=int(r.n_reaching), n_default_inputs=int(r.n_default_inputs), n_mu_pi_rows=int(r.n_mu_pi_rows),
                         numu_score_input=float(r.in_numu_score), numu_1_score_input=float(r.in_numu_1_score), shw_vtx_dis=float(r.in_shw_sp_shw_vtx_dis), n_good_showers=float(r.in_shw_sp_n_good_showers), n_br1_showers=float(r.in_shw_sp_n_br1_showers),
                         dominant_rejecting_family=min(fam_phi, key=fam_phi.get), dominant_family_phi=min(fam_phi.values()), top_rejecting_variable_1=names[order[0]], top_rejecting_variable_2=names[order[1]], top_rejecting_variable_3=names[order[2]]))
    return pd.DataFrame(rows).sort_values(["run", "subrun", "evt"]).reset_index(drop=True)


# ======================================================================================================================= figures
def score_figure(F, model, fname):
    thr = THR[model]; fig, ax = PS.figure(2, 2, size=(12, 8.4)); lo, hi = np.nanpercentile(F.stage_score, [0.5, 99.5]); bins = np.linspace(lo, hi, 41)
    panels = [("truth topology", [(F.truth35 == k, TOPO[k], TCOL[k]) for k in (0, 1, 2)]), ("Delta charge", [(F.delta_label == "Delta0", "Delta0", "#CC79A7"), (F.delta_label == "Delta+", "Delta+", "#56B4E9")]),
              ("photon reconstruction", [(F.clean_l == "clean", "clean signal-photon shower", "#009E73"), (F.clean_l == "non_clean", "non-clean photon object", "#999999")]),
              ("vertex anchoring / true reco proton", [(F.anch == "anchored", "vertex anchored", "#0072B2"), (F.anch == "not anchored", "not anchored", "#E69F00"), (F.true_proton_present == "true signal proton present", "true proton row present", "#000000"), (F.true_proton_present == "absent / other", "true proton row absent", "#D55E00")])]
    for a, (ttl, items) in zip(ax.flatten(), panels):
        for m, lab, col in items:
            x = F.stage_score[m.to_numpy()]
            a.hist(x.clip(lo + 1e-9, hi - 1e-9), bins=bins, density=True, histtype="step", color=col, lw=1.4, label=f"{lab} (n={len(x)}, pass {100 * (x > thr).mean():.0f} %)")
        a.axvline(thr, color="k", ls="--", lw=1); a.set_xlabel(f"frozen {model} score (controlling candidate); dashed = frozen threshold {thr}", fontsize=8); a.set_ylabel("unit area", fontsize=8); a.set_title(ttl, fontsize=9); a.legend(fontsize=6.5)
    save(fig, fname)


def attribution_figure(S, fname, title):
    fam = S["fam"].sort_values("mean_signed_phi"); fig, ax = PS.figure(1, 2, size=(14, 4.8)); a = ax[0][0]; y = np.arange(len(fam))
    a.barh(y - 0.2, fam.mean_signed_phi_0p, 0.4, color="#0072B2", label="rejected truth 0p"); a.barh(y + 0.2, fam.mean_signed_phi_1p, 0.4, color="#D55E00", label="rejected truth 1p"); a.set_yticks(y); a.set_yticklabels(fam.family, fontsize=7); a.axvline(0, color="k", lw=0.6)
    a.set_xlabel("mean TreeSHAP margin contribution (rejected relative to accepted signal)"); a.legend(fontsize=7); a.set_title(title, fontsize=9)
    a = ax[0][1]; v = S["var"].head(15).iloc[::-1]; a.barh(range(len(v)), v.mean_phi, color=["#D55E00" if x < 0 else "#009E73" for x in v.mean_phi]); a.set_yticks(range(len(v))); a.set_yticklabels(v.variable, fontsize=7); a.axvline(0, color="k", lw=0.6)
    a.set_xlabel("mean signed TreeSHAP (top 15 by mean |phi|)"); i = S["info"]; a.set_title(f"margin gap rejected - accepted = {i['margin_gap']:+.2f} (n_fg={i['n_fg']}, n_bg={i['n_bg']})", fontsize=9); save(fig, fname)


def survival_figure(R, stage, fname):
    fig, ax = PS.figure(1, 3, size=(16, 4.6))
    for a, (grp, lab) in zip(ax[0], (("photon_cleanliness", "photon reconstruction state"), ("vertex_anchoring", "vertex anchoring"), ("true_reco_proton", "true reco proton"))):
        d = R[(R.group == grp) & (R.stage == stage)]; d = d[~d.value.astype(str).str.startswith(("no signal", "fails"))]; x = np.arange(len(d))
        a.errorbar(x, d.survival, yerr=[d.survival - d.lo68, d.hi68 - d.survival], fmt="o", color="k", ms=5)
        for xi, (_, r) in zip(x, d.iterrows()):
            a.text(xi, r.hi68 + 0.02, f"n={r.n}", ha="center", fontsize=7)
        a.set_xticks(x); a.set_xticklabels(d.value, fontsize=7, rotation=10); a.set_ylim(0, 1.05); a.set_ylabel(f"{stage} conditional survival (frozen threshold)"); a.set_title(lab, fontsize=9)
    save(fig, fname)


def topology_survival_figure(R, stage, fname):
    fig, ax = PS.figure(1, 2, size=(12, 4.4)); a = ax[0][0]; d = R[(R.group == "truth_topology") & (R.stage == stage)]; x = np.arange(len(d)); a.errorbar(x, d.survival, yerr=[d.survival - d.lo68, d.hi68 - d.survival], fmt="o", color="k"); a.set_xticks(x); a.set_xticklabels(d.value); a.set_ylim(0, 1)
    a.set_ylabel(f"{stage} conditional survival"); a.set_title("by truth topology", fontsize=9)
    a = ax[0][1]; d = R[(R.group == "topology x clean") & (R.stage == stage)]
    for k, col in zip(("truth 0p", "truth 1p", "truth >=2p"), ("#0072B2", "#D55E00", "#009E73")):
        e = d[d.value.str.startswith(k)]
        for j, (_, r) in enumerate(e.iterrows()):
            a.errorbar(j + 0.08 * ["truth 0p", "truth 1p", "truth >=2p"].index(k), r.survival, yerr=[[r.survival - r.lo68], [r.hi68 - r.survival]], fmt="o", color=col, label=k if j == 0 else None)
    a.set_xticks(range(2)); a.set_xticklabels(["clean", "non-clean"]); a.set_ylim(0, 1); a.legend(fontsize=7); a.set_title("topology within photon-cleanliness class", fontsize=9); save(fig, fname)


def ncpi0_class_figure(T, fname):
    fig, ax = PS.figure(1, 2, size=(14, 4.8)); a = ax[0][0]; d = T.sort_values("n"); y = np.arange(len(d)); a.barh(y, d.survive, color="#009E73", label="survive"); a.barh(y, d.rejected, left=d.survive, color="#D55E00", label="rejected"); a.set_yticks(y); a.set_yticklabels(d.em_class, fontsize=7); a.set_xlabel("events reaching ncpi0"); a.legend(fontsize=7)
    a = ax[0][1]; a.errorbar(d.survival, y, xerr=[d.survival - d.lo68, d.hi68 - d.survival], fmt="o", color="k"); a.set_yticks(y); a.set_yticklabels([]); a.set_xlim(0, 1); a.set_xlabel("ncpi0 conditional survival (frozen threshold)"); save(fig, fname)


def n20br1_figure(T, fname):
    fig, ax = PS.figure(1, 1, size=(9, 4.2)); a = ax[0][0]; y = np.arange(len(T)); left = np.zeros(len(T))
    for col, lab, c_ in (("n0p", "truth 0p", "#0072B2"), ("n1p", "truth 1p", "#D55E00"), ("n2p", "truth >=2p", "#009E73")):
        a.barh(y, T[col], left=left, color=c_, label=lab); left += T[col].to_numpy()
    a.set_yticks(y); a.set_yticklabels([s.replace("__", "\n") for s in T.cls], fontsize=6.5); a.invert_yaxis(); a.set_xlabel("events (the 160 removed by n_20br1 == 1)"); a.legend(fontsize=7); save(fig, fname)


def cleanliness_figure(comp, cond, fname):
    fig, ax = PS.figure(1, 2, size=(14, 4.8)); cats = ["clean", "fragmented", "typed non-electron", "track", "row missing", "other non-clean"]; cols = ["#009E73", "#8c564b", "#CC79A7", "#0072B2", "#56B4E9", "#999999"]; a = ax[0][0]; x = np.arange(len(comp)); bottom = np.zeros(len(comp))
    for c_, col in zip(cats, cols):
        v = comp["frac_" + c_.replace(" ", "_").replace("-", "_")].to_numpy(); a.bar(x, v, bottom=bottom, color=col, edgecolor="k", linewidth=0.3, label=c_); bottom += v
    a.set_xticks(x); a.set_xticklabels([f"{s}\n(n={n})" for s, n in zip(comp.stage, comp.n)], fontsize=7); a.set_ylabel("fraction of surviving events"); a.legend(fontsize=6.5, loc="lower right"); a.set_title("signal-photon object state through the frozen chain", fontsize=9)
    a = ax[0][1]
    for lab, col in (("clean", "#009E73"), ("non-clean (all)", "#999999"), ("fragmented", "#8c564b"), ("typed non-electron", "#CC79A7"), ("track", "#0072B2")):
        d = cond[cond.state == lab]; a.errorbar(np.arange(len(d)), d.conditional_survival, yerr=[d.conditional_survival - d.lo68, d.hi68 - d.conditional_survival], fmt="o-", color=col, ms=4, lw=1, label=lab)
    a.set_xticks(np.arange(len(d))); a.set_xticklabels(d.stage, fontsize=7); a.set_ylim(0, 1.05); a.set_ylabel("conditional survival of the stage"); a.legend(fontsize=6.5); a.set_title("stage-by-stage survival by photon state", fontsize=9); save(fig, fname)


# ======================================================================================================================= dependency graph facts and cross-BDT default table
UPSTREAM = {   # downstream frozen BDT -> upstream outputs consumed as inputs (names as in the XML), SOURCE: UbooneNumuBDTScorer.cxx / UbooneNueBDTScorer.cxx at 4b6853d4
    "numu": ["numu_1_score", "numu_score"], "other": ["numu_score", "numu_1_score", "numu_2_score", "cosmict_10_score"],
    "ncpi0": ["tro_5_score", "tro_4_score", "tro_2_score", "tro_1_score", "stw_4_score", "stw_3_score", "stw_2_score", "sig_2_score", "sig_1_score", "pio_2_score", "lol_2_score", "lol_1_score", "br3_6_score", "br3_5_score", "br3_3_score"], "nue": []}
SCORER_DEFAULT = {"numu_1_score": -0.4, "numu_2_score": -0.1, "numu_3_score": -0.2, "cosmict_10_score": 0.7, "br3_3_score": 0.3, "br3_5_score": 0.42, "br3_6_score": 0.75, "pio_2_score": 0.2, "stw_2_score": 0.7, "stw_3_score": 0.5, "stw_4_score": 0.7,
                  "sig_1_score": 0.59, "sig_2_score": 0.55, "lol_1_score": 0.85, "lol_2_score": 0.7, "tro_1_score": 0.28, "tro_2_score": 0.35, "tro_4_score": 0.33, "tro_5_score": 0.5}      # the `default_val` argument of each cal_*_bdt (source)


def upstream_block(Fs):
    recs = []
    for model, names in UPSTREAM.items():
        F = Fs.get(model)
        for n in names:
            col = "in_" + n
            if F is None or col not in F:
                continue
            v = F[col].to_numpy(float); d = SCORER_DEFAULT.get(n, np.nan)
            recs.append(dict(downstream_bdt=model, upstream_input=n, n_events=len(v), frac_exactly_zero=float((v == 0).mean()), scorer_default=d, frac_at_scorer_default=RA.default_fraction(v, d), median=float(np.nanmedian(v)), q16=float(np.nanquantile(v, .16)), q84=float(np.nanquantile(v, .84)),
                             n_distinct=int(len(np.unique(np.round(v, 6)))), frac_pass=float(F.survive.mean()), median_pass=float(np.nanmedian(v[F.survive.to_numpy()])), median_fail=float(np.nanmedian(v[~F.survive.to_numpy()]))))
    return pd.DataFrame(recs)


def cross_bdt_table(Dnumu, Dother, Dncpi0):
    recs = []
    for fam in RA.FAMILIES:
        r = dict(family=fam, reason=REASON[fam])
        for lab, D in (("numu", Dnumu), ("other", Dother), ("ncpi0", Dncpi0)):
            d = D[D.family == fam]
            r[f"{lab}_n_inputs"] = len(d); r[f"{lab}_default_fraction_mean"] = float(d.frac_default_all.mean()) if (len(d) and d.frac_default_all.notna().any()) else np.nan
            for s in ("truth 0p", "truth 1p"):
                r[f"{lab}_default_fraction_{s.replace(' ', '_')}"] = float(d["frac_default_" + s].mean()) if len(d) else np.nan
        recs.append(r)
    return pd.DataFrame(recs)


def other_defaults(Fother):
    """Default fractions of the Phase-8 `other` BDT at its stage, recomputed with the SAME function and population definition (events reaching `other`)."""
    o = pd.read_parquet(P8 / "official_candidates.parquet"); names = model_of("other").var_names; dflt = source_defaults("other") if (SUMD / "input_source_table_other.csv").exists() else None
    if dflt is None:
        t = pd.read_csv(REPO / "tables" / "other_bdt_audit" / "input_source_table.csv"); dflt = {r.bdt_variable: (float(r.declared_default) if str(r.declared_default).strip() not in ("", "nan") else np.nan) for r in t.itertuples()}
    for n in list(dflt):
        if RA.family_of(n) == "upstream BDT scores":
            dflt[n] = SCORER_DEFAULT.get(n, np.nan)
    Fo = Fother[KEY + ["c_nu_index", "truth35", "delta_label", "anch", "true_proton_present", "clean_l", "survive"]].merge(o[KEY + ["c_nu_index"] + ["in_" + n for n in names]], on=KEY + ["c_nu_index"], how="left", validate="one_to_one")
    splits = {"all": Fo.index == Fo.index, "truth 0p": Fo.truth35 == 0, "truth 1p": Fo.truth35 == 1, "truth >=2p": Fo.truth35 == 2}; recs = []
    for n in names:
        d = dflt.get(n, np.nan); r = dict(stage="other", model="other", variable=n, family=RA.family_of(n), declared_default=d)
        for sn, m in splits.items():
            r["frac_default_" + sn] = RA.default_fraction(Fo.loc[np.asarray(m), "in_" + n], d)
        recs.append(r)
    return pd.DataFrame(recs)


# ======================================================================================================================= orchestration
def finish(extra):
    wf = {m: B.sha256(B.DEFAULT_WEIGHT_DIR / f"single_photon_{m}_bdt_final.xml") for m in B.MODELS}
    meta = dict(git_commit_at_run=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), branch=subprocess.run(["git", "-C", str(REPO), "branch", "--show-current"], capture_output=True, text=True).stdout.strip(),
                official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), signal_truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"), baseline_config_sha256=sha(REPO / "configs" / "baseline_selection.yaml"),
                frozen_thresholds=THR, bdt_weight_sha256=wf, bdt_weight_dir=str(B.DEFAULT_WEIGHT_DIR), event_table_sha256=sha(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"),
                baseline_candidates_sha256=sha(SPD / "analysis_tables" / "official_gen2_ncdelta" / "candidates.parquet"), phase8_summary_sha256=sha(REPO / "tables" / "other_bdt_audit" / "summary.json"), phase9_summary_sha256=sha(REPO / "tables" / "shower_vertex_audit" / "summary.json"),
                phase10_summary_sha256=sha(REPO / "tables" / "proton_truth_association" / "summary.json"), phase11_summary_sha256=sha(REPO / "tables" / "common_observables" / "summary.json"), phase9_event_taxonomy_sha256=sha(P9 / "event_taxonomy.parquet"),
                raw_scan_sha256={k: sha(RAW / f"{k}_candidates.parquet") for k in ("official", "natural")}, shap=dict(foreground="rejected signal controlling candidates", background="accepted signal controlling candidates", seed=20261111),
                candidate_policy="any (event-level; controlling candidate = reaching candidate with the largest stage score)", proton_policy="none used by the stage audit (the leading-proton labels come from the Phase-10 association at 35 MeV, the existing convention)", truth_region="provisional TPC box (no approved FV)", **extra)
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else (o.tolist() if hasattr(o, "tolist") else str(o))))


def main():
    c, E, T, rm = load(); reproduction_block(c)
    Fs = {s: stage_frame(c, E, s) for s in ("numu", "other", "ncpi0", "nue")}
    SUMMARY["populations"] = {s: dict(events=len(f), survive=int(f.survive.sum())) for s, f in Fs.items()}; assert SUMMARY["populations"]["numu"] == dict(events=8038, survive=5007) and SUMMARY["populations"]["ncpi0"] == dict(events=2781, survive=1313)
    # ---- survival, decomposition
    surv = pd.concat([survival_tables(Fs[s], s) for s in ("numu", "ncpi0")]); wr(surv, "stage_survival_by_group.csv"); dec = pd.concat([decomposition_block(Fs[s], s) for s in ("numu", "ncpi0")]); wr(dec, "topology_decomposition.csv")
    # ---- inputs and defaults
    inp = pd.concat([input_block(Fs["numu"], "numu", "numu"), input_block(Fs["ncpi0"], "ncpi0", "ncpi0")]); inp.to_csv(OUT / "default_fraction_tables" / "input_distribution_comparisons.csv", index=False)
    top = inp.assign(abs_smd=inp.smd.abs()).sort_values("abs_smd", ascending=False).groupby(["model", "pair"]).head(8).drop(columns="abs_smd"); wr(top, "input_comparison_top8_per_pair.csv")
    Dn = defaults_block(Fs["numu"], "numu", "numu"); Dp = defaults_block(Fs["ncpi0"], "ncpi0", "ncpi0"); Do = other_defaults(Fs["other"]); pd.concat([Dn, Dp]).to_csv(OUT / "default_fraction_tables" / "default_fractions_numu_ncpi0.csv", index=False)
    wr(Dn.drop(columns=["reason"]), "default_fractions_numu.csv"); wr(Dp.drop(columns=["reason"]), "default_fractions_ncpi0.csv"); X_ = cross_bdt_table(Dn, Do, Dp); wr(X_, "default_fractions_cross_bdt.csv")
    Fu = {"numu": Fs["numu"], "ncpi0": Fs["ncpi0"]}; o = pd.read_parquet(P8 / "official_candidates.parquet", columns=KEY + ["c_nu_index", "in_numu_score", "in_numu_1_score", "in_numu_2_score", "in_cosmict_10_score"])
    Fo_ = Fs["other"][KEY + ["c_nu_index", "survive"]].merge(o, on=KEY + ["c_nu_index"], how="left", suffixes=("", "_p8")); Fu["other"] = Fo_
    up = upstream_block(Fu); wr(up, "upstream_bdt_inputs.csv"); SUMMARY["upstream"] = up.to_dict("records")
    # ---- numu: drivers, attribution, high-energy failures
    G, drv = driver_block(Fs["numu"], rm, "numu"); wr(drv, "numu_survival_by_driver.csv")
    hi = (G.photon_energy_mev > 400) & ~G.survive
    Sn = shap_block(G, "numu", "numu", extra_events=hi.to_numpy()); wr(Sn["var"], "numu_attribution_variables.csv", "attribution"); wr(Sn["fam"], "numu_attribution_families.csv", "attribution"); SUMMARY["numu_shap"] = Sn["info"]
    hl = high_energy_failures(G, Sn); wr(hl, "numu_high_energy_failures.csv", "attribution"); SUMMARY["numu_high_energy"] = dict(n=len(hl), by_family=hl.dominant_rejecting_family.value_counts().to_dict(), by_topology=hl.truth_topology.value_counts().to_dict(), by_clean=hl.photon_clean.value_counts().to_dict(),
                                                                                                                        by_anchoring=hl.vertex_anchoring.value_counts().to_dict(), median_numu_score=float(hl.numu_score.median()))
    # ---- ncpi0: topology classes, attribution
    Gp, Tp = ncpi0_topology_block(Fs["ncpi0"], rm); wr(Tp, "ncpi0_em_topology_classes.csv"); Sp = shap_block(Gp, "ncpi0", "ncpi0"); wr(Sp["var"], "ncpi0_attribution_variables.csv", "attribution"); wr(Sp["fam"], "ncpi0_attribution_families.csv", "attribution"); SUMMARY["ncpi0_shap"] = Sp["info"]
    SUMMARY["ncpi0_em"] = Tp.to_dict("records")
    # ---- n20br1 and cleanliness
    F20, T20, dist, G20 = n20br1_block(c, E, rm); wr(T20, "n20br1_failure_taxonomy.csv"); wr(dist, "n20br1_n20mev_vs_n20br1.csv"); pq(F20.drop(columns=[x for x in F20.columns if x.startswith("in_")])).to_parquet(OUT / "n20br1_stage.parquet", index=False); SUMMARY["n20br1"] = T20.to_dict("records")
    comp, cond = chain_cleanliness(E); wr(comp, "chain_cleanliness.csv", "stage_cleanliness"); wr(cond, "chain_conditional_survival_by_photon_state.csv", "stage_cleanliness"); SUMMARY["chain_cleanliness"] = comp.to_dict("records")
    masks = {"all": E.truth35.notna(), "truth 0p": E.truth35 == 0, "truth 1p": E.truth35 == 1, "truth >=2p": E.truth35 == 2, "Delta0": E.delta_label == "Delta0", "Delta+": E.delta_label == "Delta+",
             "harmonized signal (spine_truth_signal)": E.spine_truth_signal.astype(bool), "harmonized 0p50": E.spine_truth_signal.astype(bool) & E.spine_truth_0p50.astype(bool), "harmonized Np50": E.spine_truth_signal.astype(bool) & E.spine_truth_Np50.astype(bool),
             "clean photon at shower stage": E.clean_l == "clean", "non-clean photon at shower stage": E.clean_l == "non_clean"}
    ch = chain_by_group(E, masks); wr(ch, "chain_conditional_survival_by_group.csv"); SUMMARY["chain"] = ch[ch.group == "all"].to_dict("records")
    nat = natural_block()
    # ---- figures
    score_figure(Fs["numu"], "numu", "numu_score_distributions.png"); attribution_figure(Sn, "numu_attribution.png", "numu: rejected vs accepted signal"); survival_figure(surv, "numu", "numu_survival_by_state.png")
    score_figure(Fs["ncpi0"], "ncpi0", "ncpi0_score_distributions.png"); attribution_figure(Sp, "ncpi0_attribution.png", "ncpi0: rejected vs accepted signal"); survival_figure(surv, "ncpi0", "ncpi0_rejection_by_reco_state.png"); ncpi0_class_figure(Tp, "ncpi0_em_topology_classes.png")
    topology_survival_figure(surv, "numu", "numu_survival_by_topology.png"); n20br1_figure(T20, "n20br1_failure_taxonomy.png"); cleanliness_figure(comp, cond, "clean_photon_fraction_through_chain.png")
    # ---- outside Git
    pq(G.drop(columns=[x for x in G.columns if x.startswith("in_")])).to_parquet(OUT / "numu_stage.parquet", index=False); pq(Gp.drop(columns=[x for x in Gp.columns if x.startswith("in_")])).to_parquet(OUT / "ncpi0_stage.parquet", index=False)
    G[KEY + ["c_nu_index", "stage_score", "survive"] + [x for x in G.columns if x.startswith("in_")]].to_parquet(OUT / "numu_stage_inputs.parquet", index=False); Gp[KEY + ["c_nu_index", "stage_score", "survive"] + [x for x in Gp.columns if x.startswith("in_")]].to_parquet(OUT / "ncpi0_stage_inputs.parquet", index=False)
    for nm, S in (("numu", Sn), ("ncpi0", Sp)):
        np.save(OUT / "attribution" / f"{nm}_phi.npy", S["phi"]); pd.DataFrame(dict(file_index=G.file_index.to_numpy()[S["fg"]] if nm == "numu" else Gp.file_index.to_numpy()[S["fg"]], ev=G.ev.to_numpy()[S["fg"]] if nm == "numu" else Gp.ev.to_numpy()[S["fg"]])).to_csv(OUT / "attribution" / f"{nm}_phi_events.csv", index=False)
    finish({}); print("done", list(SUMMARY))


if __name__ == "__main__":
    main()
