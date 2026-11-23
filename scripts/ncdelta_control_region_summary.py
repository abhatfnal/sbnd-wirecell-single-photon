#!/usr/bin/env python
"""Authoritative control-region summary (open data only; final/signal region stays blocked). One row per (region, production). PRELIMINARY: available neutrino covariance only.

    source env/setup_eaf.sh && python scripts/ncdelta_control_region_summary.py

baseline = flux + GENIE xsec + FSI + beamline-G4 functions WITHOUT reinteractions_neutron_Geant4 (unresolved neutron-G4 tail function, see the event-level audit); 'incl_nG4' = with it. Neither is a final systematic uncertainty.
NOT included in either: detector / proton reconstruction, cosmic-only (beam-off) MC, dirt, POT, imp_weight, NC-Delta signal-model dials, unresolved-owner events.
"""
import pickle
from ncdelta_syst_common import *
TAB = REPO / "tables" / "ncdelta_purity_datamc"; REG = ["preselection", "SB_numu", "SB_other", "SB_ncpi0", "SB_nue"]; TAGS = ["SB_ncpi0-SB_other-SB_nue", "SB_numu-preselection"]


def chi(df, p, r, kind):
    x = df[(df.production == p) & (df.region == r) & df.test.str.startswith(kind + " (energy")]
    return (float(x.chi2.iloc[0]), int(x.ndof.iloc[0]), float(x.p_value.iloc[0])) if len(x) else (np.nan, 0, np.nan)


def main():
    A = pd.concat([pd.read_csv(TAB / f"syst_sideband_datamc_chi2_{t}.csv") for t in TAGS]); X = pd.concat([pd.read_csv(TAB / f"syst_sideband_datamc_chi2_{t}_excl.csv") for t in TAGS])
    N = pd.read_csv(TAB / "np_over_0p_double_ratio_with_covariance.csv"); rows = []
    for p in PRODUCTIONS:
        plan = pickle.load(open(SYST / f"regions_plan_{p}.pkl", "rb")); wS = plan["pot_data"] / POT_SIGNAL; wB = plan["pot_data"] / plan["pot_cv"]
        for r in REG:
            a = A[(A.production == p) & (A.region == r) & A.test.str.startswith("rate_only")].iloc[0]; x = X[(X.production == p) & (X.region == r) & X.test.str.startswith("rate_only")].iloc[0]; n = N[(N.production == p) & (N.region == r)].iloc[0]
            comp = (plan["B"][r].groupby("cat").size() * wB).to_dict(); comp["NC-Delta signal sample (dedicated)"] = len(plan["S"][r]) * wS; tot = sum(comp.values()); top = sorted(comp.items(), key=lambda kv: -kv[1])[:2]
            cr, cn = chi(X, p, r, "rate+shape"), chi(A, p, r, "rate+shape"); sr, sn = chi(X, p, r, "shape-only"), chi(A, p, r, "shape-only")
            weak = []; 
            if a.n_data < 100: weak.append("n_data<100")
            if min(n.data_0p, n.data_Np) < 50: weak.append("Np or 0p bin <50 events")
            rows.append(dict(region=r, production=p, n_data=int(a.n_data), mc_prediction=a.prediction, data_over_mc=a.ratio, rel_data_stat=a.rel_data_stat, rel_mc_stat=a.rel_mc_stat, rel_syst_baseline=x.rel_syst, rel_syst_incl_nG4=a.rel_syst,
                             n_sigma_from_1_baseline=x.n_sigma_from_unity_total, n_sigma_from_1_incl_nG4=a.n_sigma_from_unity_total, np_over_0p_double_ratio=n.double_ratio, double_ratio_rel_unc_stat_mc=n.rel_stat_mc, double_ratio_rel_unc_baseline=n.rel_total_available,
                             double_ratio_rel_unc_incl_nG4=float(np.hypot(n.rel_stat_mc, n.rel_syst_incl_neutron_g4)), double_ratio_n_sigma_baseline=n.n_sigma_with_available_syst, double_ratio_n_sigma_incl_nG4=n.n_sigma_incl_neutron_g4,
                             energy_rate_shape_chi2=cr[0], energy_rate_shape_ndof=cr[1], energy_rate_shape_p=cr[2], energy_rate_shape_chi2_incl_nG4=cn[0], energy_rate_shape_p_incl_nG4=cn[2],
                             energy_shape_only_chi2=sr[0], energy_shape_only_ndof=sr[1], energy_shape_only_p=sr[2], energy_shape_only_chi2_incl_nG4=sn[0], energy_shape_only_p_incl_nG4=sn[2],
                             dominant_mc_truth=f"{top[0][0]} {100 * top[0][1] / tot:.0f}%; {top[1][0]} {100 * top[1][1] / tot:.0f}%", stat_weak=";".join(weak)))
    df = pd.DataFrame(rows); df.to_csv(TAB / "control_region_summary_final.csv", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40); print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
