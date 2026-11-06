"""Vectorised scorer for the four ORIGINAL MicroBooNE single-photon TMVA GradBDT models (NO training).

Same tree walk as ``analysis/microboone_1gamma_v0/score_microboone_bdts.py`` (validated 132/132 against ROOT/TMVA):
go left if ``x[IVar] <= Cut``, response ``tanh(sum_t boostWeight_t * leaf_res_t)``. That script runs on import and
hard-codes Eagle paths, so it cannot be imported; this module re-implements the evaluation for numpy matrices and
is cross-checked against a scalar copy of that tree walk in tests/test_bdt.py.

The XML files are NOT in the repo. Default location (read-only, sha256 identical to the frozen reference bundle,
see provenance/microboone_reference_SHA256SUMS.txt):
    /exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/single_photon_<model>_bdt_final.xml
"""
from __future__ import annotations

import hashlib
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DEFAULT_WEIGHT_DIR = Path(os.environ.get(
    "SP_BDT_WEIGHTS", "/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights"))
MODELS = ("numu", "other", "ncpi0", "nue")
EXPECTED_NVARS = {"numu": 73, "other": 146, "ncpi0": 45, "nue": 56}
# BDT input names that do NOT live in wc.T_tagger:
KINE_INPUTS_NCPI0 = {
    "kine_pio_mass", "kine_pio_flag", "kine_pio_vtx_dis", "kine_pio_energy_1", "kine_pio_energy_2",
    "kine_pio_theta_1", "kine_pio_theta_2", "kine_pio_phi_1", "kine_pio_phi_2",
    "kine_pio_dis_1", "kine_pio_dis_2", "kine_pio_angle",
}
RENAMED = {"reco_nuvtxY": ("T_kine", "kine_nu_y_corr")}


def input_branch(model: str, varname: str) -> str:
    """CAF branch (``wc.<tree>.<branch>``) that feeds BDT input ``varname`` of ``model``."""
    if varname in RENAMED:
        tree, br = RENAMED[varname]
        return f"wc.{tree}.{br}"
    if model == "ncpi0" and varname in KINE_INPUTS_NCPI0:
        return f"wc.T_kine.{varname}"
    return f"wc.T_tagger.{varname}"


@dataclass
class _Tree:
    ivar: np.ndarray    # -1 for leaf
    cut: np.ndarray
    left: np.ndarray
    right: np.ndarray
    res: np.ndarray


class TmvaBdt:
    def __init__(self, name: str, xml_path: str | Path, *, check_nvars: bool = True):
        self.name = name
        self.xml_path = Path(xml_path)
        root = ET.parse(self.xml_path).getroot()
        vs = root.find("Variables").findall("Variable")
        self.var_list = sorted(((int(v.get("VarIndex")), v.get("Expression")) for v in vs))
        if check_nvars and name in EXPECTED_NVARS and len(self.var_list) != EXPECTED_NVARS[name]:
            raise ValueError(f"{name}: expected {EXPECTED_NVARS[name]} vars, got {len(self.var_list)}")
        self.boost, self.trees = [], []
        for bt in root.find("Weights").findall("BinaryTree"):
            self.boost.append(float(bt.get("boostWeight")))
            self.trees.append(self._flatten(bt.find("Node")))
        self.boost = np.asarray(self.boost)

    @staticmethod
    def _flatten(root) -> _Tree:
        ivar, cut, left, right, res = [], [], [], [], []

        def add(node):
            i = len(ivar)
            ivar.append(-1); cut.append(0.0); left.append(-1); right.append(-1); res.append(0.0)
            kids = [c for c in node if c.tag == "Node"]
            if not kids:
                res[i] = float(node.get("res"))
            else:
                l = next(c for c in kids if c.get("pos") == "l")
                r = next(c for c in kids if c.get("pos") == "r")
                ivar[i] = int(node.get("IVar")); cut[i] = float(node.get("Cut"))
                left[i] = add(l); right[i] = add(r)
            return i

        add(root)
        return _Tree(np.array(ivar), np.array(cut), np.array(left), np.array(right), np.array(res))

    @property
    def var_names(self) -> list[str]:
        return [n for _, n in self.var_list]

    def decision(self, X: np.ndarray) -> np.ndarray:
        """X: (n_events, n_vars) in XML VarIndex order. Rows with any non-finite value return NaN."""
        X = np.asarray(X, dtype=np.float64)
        ok = np.isfinite(X).all(axis=1)
        raw = np.zeros(len(X))
        rows = np.where(ok)[0]
        Xo = X[rows]
        for bw, t in zip(self.boost, self.trees):
            node = np.zeros(len(rows), dtype=np.int64)
            for _ in range(256):
                iv = t.ivar[node]
                internal = iv >= 0
                if not internal.any():
                    break
                go_left = Xo[np.arange(len(rows)), np.where(internal, iv, 0)] <= t.cut[node]
                nxt = np.where(go_left, t.left[node], t.right[node])
                node = np.where(internal, nxt, node)
            raw[rows] += bw * t.res[node]
        out = np.full(len(X), np.nan)
        out[rows] = np.tanh(raw[rows])
        return out


def load_models(weight_dir: str | Path = DEFAULT_WEIGHT_DIR) -> dict[str, TmvaBdt]:
    d = Path(weight_dir)
    return {m: TmvaBdt(m, d / f"single_photon_{m}_bdt_final.xml") for m in MODELS}


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
