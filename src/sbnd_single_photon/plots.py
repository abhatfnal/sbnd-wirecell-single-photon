"""Config-driven control-plot skeleton (configs/control_plots.yaml). SHAPES ONLY - no physical normalisation.

Histograms are accumulated with FIXED bins from the config, so no raw per-event values need be stored.
"""
from __future__ import annotations

import json
from pathlib import Path

import awkward as ak
import numpy as np
import yaml

from . import proton as P
from .samples import REPO_ROOT

DEFAULT_CFG = REPO_ROOT / "configs" / "control_plots.yaml"
BANNER = "SHAPES ONLY: not exposure-normalised; no data/MC prediction"


def load_specs(path=DEFAULT_CFG) -> list[dict]:
    with open(path) as fh:
        return yaml.safe_load(fh)["plots"]


def spec_branches(specs) -> list[str]:
    return sorted({s["branch"] for s in specs if s["kind"] == "cand" and s["branch"].startswith("wc.")})


class HistAccumulator:
    def __init__(self, specs):
        self.specs = {s["name"]: s for s in specs}
        self.edges = {n: np.linspace(*s["range"], s["bins"] + 1) for n, s in self.specs.items()}
        self.counts = {n: np.zeros(s["bins"]) for n, s in self.specs.items()}
        self.entries = {n: 0 for n in self.specs}
        self.missing: set[str] = set()

    def _add(self, name, values):
        v = np.asarray(values, dtype=float)
        v = v[np.isfinite(v)]
        h, _ = np.histogram(v, bins=self.edges[name])
        self.counts[name] += h
        self.entries[name] += int(len(v))

    def fill(self, arrays: dict, valid, proton_pdg=None, proton_ke=None):
        """arrays: [event][candidate] jagged by branch. ``valid``: bool per event (wc.valid==1 only)."""
        valid = np.asarray(valid, dtype=bool)
        for n, s in self.specs.items():
            kind = s["kind"]
            if kind in ("cand", "derived"):
                if s["branch"] not in arrays:
                    self.missing.add(n); continue
                self._add(n, ak.to_numpy(ak.flatten(arrays[s["branch"]][valid], axis=None)))
            elif kind == "proton_mult" and proton_pdg is not None:
                code = P.classify_reco_protons(proton_pdg[valid], proton_ke[valid])
                self._add(n, ak.to_numpy(ak.flatten(code, axis=None)))
            elif kind == "proton_ke" and proton_pdg is not None:
                ke = proton_ke[valid]
                self._add(n, ak.to_numpy(ak.flatten(ke[proton_pdg[valid] == P.PROTON_PDG], axis=None)))

    def to_json(self) -> dict:
        return {n: {"edges": self.edges[n].tolist(), "counts": self.counts[n].tolist(),
                    "entries": self.entries[n]} for n in self.specs} | {"_missing": sorted(self.missing)}


def draw(hists: dict, specs, outdir, *, mc=("bnb_cv", "nuecc"), data=("beam_off", "beam_on_open")):
    """hists: {sample: HistAccumulator.to_json()}. Two panels per variable: MC shapes | data shapes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    for s in specs:
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=False)
        for ax, group, title in ((axs[0], mc, "MC (shape)"), (axs[1], data, "data, shown separately (shape)")):
            for smp in group:
                h = hists.get(smp, {}).get(s["name"])
                if not h or not h["entries"]:
                    continue
                c = np.asarray(h["counts"]); e = np.asarray(h["edges"])
                ax.stairs(c / max(c.sum(), 1), e, label=f"{smp} (n={h['entries']})")
            ax.set_xlabel(s["xlabel"], fontsize=8); ax.set_title(title, fontsize=9)
            ax.set_ylabel("area-normalised"); ax.legend(fontsize=7)
        fig.suptitle(BANNER + (" | " + s["caveat"] if s.get("caveat") else ""), fontsize=7, color="firebrick")
        fig.tight_layout(); fig.savefig(outdir / f"{s['name']}.png", dpi=80); plt.close(fig)
