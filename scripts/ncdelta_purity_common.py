"""Loaders + candidate taxonomy shared by the purity / data-MC scripts (frozen R1 selection, old fg1-era vs Nov16). No selection is ever changed here."""
from wcl1116_replay_common import *          # REPO, SPD, OLD/NEW tables, to_D, read_tables, RSE, FROZEN, load_cfg ...
from sbnd_single_photon import purity as PU, datamc as DM, regions as RG, datapolicy as DP, natural_signal as NS
from sbnd_single_photon.truth import ActiveVolume

TAB = REPO / "tables" / "ncdelta_purity_datamc"; TAB.mkdir(parents=True, exist_ok=True)
PLT = REPO / "plots" / "ncdelta_purity_datamc"; PLT.mkdir(parents=True, exist_ok=True)
SF = REPO / "tables" / "legacy_scorer_correction" / "source_faithful"
KEY = ["file_index", "ev"]
POT_TARGET = 1.0e20
POT_SIGNAL = float(__import__("json").load(open(REPO / "tables" / "official_ncdelta" / "official_ncdelta_census.json"))["files"]["sum_TotalPOT"])     # all 15,777 flatCAFs (zero-event units carry POT)
PRODUCTIONS = ("old_fg1", "nov16")


def load_signal(prod, cfg):
    """Dedicated NC-Delta sample: candidates (source-faithful D) + the 12,427 in-region truth events (same denominator for both productions)."""
    ev = pd.read_parquet(DER / f"signal_event_table_{'old' if prod == 'old_fg1' else 'new'}_any.parquet")
    c = pd.read_parquet(SPC / "official_candidates_D_full.parquet") if prod == "old_fg1" else pd.read_parquet(DER / "signal_candidates_new_D.parquet")
    return ev[ev.in_region].reset_index(drop=True), c


def load_cv(prod, cfg):
    if prod == "old_fg1":
        T = SPD / "analysis_tables" / "bnb_cv"; ev = pd.read_parquet(T / "events.parquet"); c = pd.read_parquet(SPC / "bnb_candidates_D_full.parquet"); files = pd.read_parquet(T / "files.parquet")
    else:
        ev, c_raw, files = read_tables(NEW, "bnb_cv"); c = to_D(c_raw, ev, cfg)
    return ev, c, files


def load_data(prod, sample, cfg):
    root = OLD if prod == "old_fg1" else NEW
    ev, c_raw, files = read_tables(root, sample)
    return ev, to_D(c_raw, ev, cfg), files


def natural_signal_in_region():
    sig = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")
    nat = NS.to_signal_truth_table(sig); return sig, nat[nat.in_region].reset_index(drop=True)


def approx_category(c: pd.DataFrame, ev: pd.DataFrame) -> pd.Series:
    """Dominant-neutrino taxonomy for EVERY candidate from the stored candidate/event truth columns (no CAF access): COSMIC_OR_UNMATCHED (no dominant neutrino),
    OUTSIDE_TPC_NU (dominant-neutrino vertex outside the provisional box), then NC/CC pi0 (event-level pi0 flag of the active neutrino), NUE_CC, NUMU_CC, OTHER_NC, OTHER_CC.
    Validated against the production-matched taxonomy at the final selection (tables/ncdelta_purity_datamc/taxonomy_validation.csv); used for stage-wise composition only."""
    pi0 = c[KEY].merge(ev[KEY + ["t_a_pi0"]], on=KEY, how="left")["t_a_pi0"].fillna(False).to_numpy(bool)
    pdg = c.dom_nu_pdg.to_numpy(float); cc = c.dom_nu_ccnc.to_numpy(float) == 0
    inbox = ActiveVolume().contains(c.dom_nu_vx.to_numpy(float), c.dom_nu_vy.to_numpy(float), c.dom_nu_vz.to_numpy(float))
    inbox = np.asarray(inbox, bool)
    nomatch = ~np.isfinite(pdg) | (c.dom_nu.to_numpy(float) < 0) | ~c.dom_ok.to_numpy(bool)
    cat = np.select([nomatch, ~inbox, pi0 & cc, pi0 & ~cc, cc & (np.abs(pdg) == 12), cc & (np.abs(pdg) == 14), cc],
                    ["COSMIC_OR_UNMATCHED", "OUTSIDE_TPC_NU", "CC_PI0", "NC_PI0", "NUE_CC", "NUMU_CC", "OTHER_CC"], "OTHER_NC")
    return pd.Series(cat, index=c.index)
