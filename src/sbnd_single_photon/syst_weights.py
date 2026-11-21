"""Systematic-weight metadata and helpers for the SBN CAF `rec.mc.nu.wgt.univ` universes (nothing here applies a weight to a result).

Conventions, all taken from the installed source (cvmfs sbnanaobj v10_26_00 / sbncode v10_26_00), not guessed:
* `caf::ReweightType_t` (SREnums.h): kMultiSim = 0, kPMNSigma = 1, kFixed = 2, kMultiSigma = 3.
* A multisigma set's universe j is the single parameter shifted to `parameter_sigma[j]` (GenieWeightCalc.cxx: multisigma supports ONE parameter, universes = values);
  those values are stored per parameter in `globalTree: global/wgts/wgts.map[].vals` and are read here (uproot cannot decode that vector, so the raw basket is parsed and validated).
* A multisim set's universes are random draws (seeded) of all its parameters together; the covariance is the sample covariance of the universe yields about the NOMINAL (unit-weight) yield.
"""
from __future__ import annotations
import re, struct
import numpy as np

KMULTISIM, KPMNSIGMA, KFIXED, KMULTISIGMA = 0, 1, 2, 3
TYPE_NAME = {0: "multisim", 1: "pm_n_sigma", 2: "fixed", 3: "multisigma"}
_HDR = re.compile(rb"@\x00\x00([\x03-\x40])\x00\t([\x01-\x40])", re.S)


def parse_weight_map(raw: bytes) -> list[dict]:
    """Every validated (name, mean, width, covidx, vals) entry of the `wgts.map` basket, in file order.

    An entry is accepted only if both ROOT byte-count words are consistent with the payload (bytecount = 2 + 4 + 4 n for the values vector) and the name is ASCII."""
    out, pos = [], 0
    while True:
        m = _HDR.search(raw, pos)
        if m is None:
            return out
        bc, ln = m.group(1)[0], m.group(2)[0]
        name_b = raw[m.end(): m.end() + ln]; j = m.end() + ln
        if len(name_b) != ln or not all(32 <= c < 127 for c in name_b) or j + 12 + 10 > len(raw) or bc != 2 + 1 + ln:
            pos = m.start() + 1; continue
        mean, width, covidx = struct.unpack(">ffi", raw[j: j + 12]); k = j + 12
        if raw[k: k + 3] != b"@\x00\x00" or raw[k + 4: k + 6] != b"\x00\t":
            pos = m.start() + 1; continue
        bc2 = raw[k + 3]; n = struct.unpack(">i", raw[k + 6: k + 10])[0]
        if n < 0 or bc2 != 2 + 4 + 4 * n or k + 10 + 4 * n > len(raw):
            pos = m.start() + 1; continue
        vals = np.frombuffer(raw[k + 10: k + 10 + 4 * n], dtype=">f4").astype(float)
        out.append(dict(name=name_b.decode(), mean=float(mean), width=float(width), covidx=int(covidx), vals=vals)); pos = k + 10 + 4 * n


def multisigma_sigmas(psets: list[tuple[str, int, int]], entries: list[dict]) -> dict:
    """Map each multisigma PSet name -> its per-universe sigma values, matched by parameter name (the PSet name ends in `_<param>`); raises unless the match is unique and sized nuniv."""
    by_name: dict[str, list[dict]] = {}
    for e in entries:
        by_name.setdefault(e["name"], []).append(e)
    res = {}
    for name, nuniv, typ in psets:
        if typ != KMULTISIGMA:
            continue
        cands = [p for p in by_name if name.endswith("_" + p)]
        cands = [p for p in cands if any(len(e["vals"]) == nuniv for e in by_name[p])]
        if len(cands) != 1:                                      # ambiguous suffix (e.g. nu_p_CC_1Pi vs p_CC_1Pi): take the longest parameter name that fits
            cands = sorted(cands, key=len)[-1:] if cands else []
        if not cands:
            raise ValueError(f"no sigma entry for {name}")
        ents = [e for e in by_name[cands[0]] if len(e["vals"]) == nuniv]
        if not all(np.array_equal(ents[0]["vals"], e["vals"]) for e in ents):
            raise ValueError(f"inconsistent sigma entries for {name}")
        res[name] = ents[0]["vals"]
    return res


def source_group(name: str, typ: int) -> str:
    """Physics group of a weight function; flux and beamline-G4 are kept apart from cross-section / FSI."""
    if name.endswith("_Flux"):
        return "flux_multisim"
    if name.startswith("reinteractions_"):
        return "beamline_g4_reint_multisim"
    if name.startswith("GENIEReWeight_SBN_v1_multisim_FSI_"):
        return "fsi_genie_multisim"
    if name.startswith("GENIEReWeight_SBN_v1_multisim_"):
        return "xsec_genie_multisim"
    if name.startswith("GENIEReWeight_SBN_v1_multisigma_"):
        return "genie_multisigma_diagnostic"          # duplicates the multisim sets for the same knobs (not added to the band)
    if name.startswith(("MINERvA", "MiscInteraction", "NOvAStyle")):
        return "xsec_extra_multisigma"
    return "other"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# reading the per-interaction weight blocks from a merged CAF
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
def split_blocks(flat: np.ndarray, n_nu: int, nuniv: np.ndarray) -> np.ndarray:
    """(n_nu, total_universes) view of one event's flat `rec.mc.nu.wgt.univ`: neutrino-major, then weight function, then universe. Raises if the size is wrong."""
    tot = int(np.sum(nuniv))
    if len(flat) != n_nu * tot:
        raise ValueError(f"flat size {len(flat)} != n_nu {n_nu} x {tot}")
    return np.asarray(flat, dtype=np.float32).reshape(n_nu, tot)


def layout_ok(univ_lengths: np.ndarray, n_nu: int, nuniv: np.ndarray) -> bool:
    """The per-(neutrino, function) universe counts stored in the file equal the global nuniv list repeated once per neutrino (so the block layout assumption holds)."""
    return len(univ_lengths) == n_nu * len(nuniv) and np.array_equal(np.asarray(univ_lengths), np.tile(np.asarray(nuniv), n_nu))


def map_events_by_id(rec_ids: np.ndarray, want: np.ndarray) -> np.ndarray:
    """Explicit join on (run, subrun, evt): for each wanted id row return the recTree entry (or -1). Raises if the recTree ids are not unique."""
    key = [tuple(r) for r in np.asarray(rec_ids)]
    if len(set(key)) != len(key):
        raise ValueError("duplicate run/subrun/evt in recTree")
    pos = {k: i for i, k in enumerate(key)}
    return np.array([pos.get(tuple(r), -1) for r in np.asarray(want)], dtype=np.int64)


def owner_blocks_worker(job):
    """job = (tag, file_index, url, rows) with rows = list of dicts(run, subrun, evt, ev, k, ex, ey, ez, epdg). Returns a dict of per-file proof counters and per-event blocks.

    Per file (all entries, not only the wanted ones): recTree vs recTreeWireCell run/subrun/event arrays identical and in the same order? recTree ids unique? Then each wanted event is
    joined to its recTree entry BY ID (never by entry number), the table's own entry is compared with the joined entry, the weight layout is verified, and the owner interaction's
    vertex/pdg is compared with the expectation (signal records / Wire-Cell truth vertex)."""
    import awkward as ak, uproot
    tag, fi, url, rows = job
    res = dict(tag=tag, file_index=fi, ok=False, err="", proof={}, ev=[])
    try:
        f = uproot.open(url); t = f["recTree"]; w = f["recTreeWireCell"]
        g = f["globalTree"]; nuniv = np.asarray(g["global/wgts/wgts.nuniv"].array(library="ak")[0].tolist())
        rid = np.stack([t[b].array(library="np").astype(np.int64) for b in ("rec.hdr.run", "rec.hdr.subrun", "rec.hdr.evt")], 1)
        wid = np.stack([w[b].array(library="np").astype(np.int64) for b in ("wc.run", "wc.subrun", "wc.evt")], 1)
        same_len = len(rid) == len(wid)
        res["proof"] = dict(n_rec=len(rid), n_wc=len(wid), same_length=bool(same_len), ids_identical_in_order=bool(same_len and np.array_equal(rid, wid)),
                            rec_ids_unique=bool(len({tuple(r) for r in rid}) == len(rid)), wc_ids_unique=bool(len({tuple(r) for r in wid}) == len(wid)))
        want = np.array([[r["run"], r["subrun"], r["evt"]] for r in rows], dtype=np.int64)
        ent = map_events_by_id(rid, want)
        a = t.arrays(["rec.mc.nu.pdg", "rec.mc.nu.iscc", "rec.mc.nu.position.x", "rec.mc.nu.position.y", "rec.mc.nu.position.z", "rec.mc.nu.imp_weight",
                      "rec.mc.nu.wgt.univ", "rec.mc.nu.wgt.univ..length"], library="ak")
        for r, e in zip(rows, ent):
            o = dict(run=r["run"], subrun=r["subrun"], evt=r["evt"], ev_table=r.get("ev", -1), rec_entry=int(e), found=bool(e >= 0), entry_equal=bool(e == r.get("ev", -2)),
                     wc_id_at_table_entry=bool(0 <= r.get("ev", -1) < len(wid) and tuple(wid[int(r["ev"])]) == (r["run"], r["subrun"], r["evt"])), k=int(r["k"]), n_nu=-1,
                     layout_ok=False, vtx_dist_cm=np.nan, pdg_rec=0, pdg_match=False, iscc=-1, imp_weight=np.nan, W=None)
            if e >= 0:
                n_nu = len(a["rec.mc.nu.pdg"][e]); o["n_nu"] = n_nu
                lay = layout_ok(np.asarray(a["rec.mc.nu.wgt.univ..length"][e]), n_nu, nuniv)
                o["layout_ok"] = bool(lay)
                if lay and 0 <= r["k"] < n_nu:
                    blk = split_blocks(np.asarray(a["rec.mc.nu.wgt.univ"][e]), n_nu, nuniv)[int(r["k"])]
                    px, py, pz = (float(a[f"rec.mc.nu.position.{c}"][e][int(r["k"])]) for c in "xyz")
                    o["vtx_dist_cm"] = float(np.sqrt((px - r["ex"]) ** 2 + (py - r["ey"]) ** 2 + (pz - r["ez"]) ** 2)); o["pdg_rec"] = int(a["rec.mc.nu.pdg"][e][int(r["k"])])
                    o["pdg_match"] = bool(r.get("epdg", 0) == 0 or o["pdg_rec"] == r["epdg"]); o["iscc"] = int(a["rec.mc.nu.iscc"][e][int(r["k"])])
                    o["imp_weight"] = float(a["rec.mc.nu.imp_weight"][e][int(r["k"])]); o["W"] = blk.copy()
            res["ev"].append(o)
        res["ok"] = True
    except Exception as ex:                                  # reported, never silently dropped
        res["err"] = repr(ex)[:300]
    return res


def sample_blocks_worker(job):
    """Every interaction's weight block of one file (for the pathological-weight audit; no selection involved). job = (tag, file_index, url, max_events)."""
    import awkward as ak, uproot
    tag, fi, url, mx = job
    try:
        f = uproot.open(url); t = f["recTree"]; nuniv = np.asarray(f["globalTree"]["global/wgts/wgts.nuniv"].array(library="ak")[0].tolist())
        a = t.arrays(["rec.mc.nu.pdg", "rec.mc.nu.iscc", "rec.mc.nu.wgt.univ", "rec.mc.nu.wgt.univ..length"], library="ak", entry_stop=mx)
        blocks, pdg, cc = [], [], []
        for e in range(len(a)):
            n_nu = len(a["rec.mc.nu.pdg"][e])
            if n_nu == 0 or not layout_ok(np.asarray(a["rec.mc.nu.wgt.univ..length"][e]), n_nu, nuniv):
                continue
            blocks.append(split_blocks(np.asarray(a["rec.mc.nu.wgt.univ"][e]), n_nu, nuniv)); pdg += list(np.asarray(a["rec.mc.nu.pdg"][e])); cc += list(np.asarray(a["rec.mc.nu.iscc"][e]))
        return dict(tag=tag, file_index=fi, ok=True, W=np.concatenate(blocks) if blocks else np.zeros((0, int(nuniv.sum())), np.float32), pdg=np.array(pdg), iscc=np.array(cc), err="")
    except Exception as ex:
        return dict(tag=tag, file_index=fi, ok=False, err=repr(ex)[:300])


# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# function table: type / prescription / whether it enters the band, and why
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
SIGMA_GRID = (-1.0, 1.0, -2.0, 2.0, -3.0, 3.0)
SINGLE_EVENT_RATIO_THRESHOLD = 0.8     # a multisim function is flagged single-event-dominated if removing its single most influential event changes sigma(total yield) by more than 20 %
GROUPS_IN_BAND = ("flux_multisim", "beamline_g4_reint_multisim", "xsec_genie_multisim", "fsi_genie_multisim", "xsec_genie_unisim_extra", "xsec_extra_multisigma")


def function_table(names, nuniv, types, sigmas: dict) -> "pd.DataFrame":
    """One row per weight function with its documented type, the covariance prescription, and whether it enters the band (reasons recorded; nothing is dropped silently)."""
    import pandas as pd
    rows, start = [], 0
    for i, (n, u, t) in enumerate(zip(names, nuniv, types)):
        grp = source_group(n, int(t)); sg = tuple(float(x) for x in sigmas.get(n, ()))
        if n.endswith("multisim_RDecBR1gamma"):
            grp = "signal_radiative_br_outside_band"; presc, used, why = "multisim (computed and shown separately)", False, "Delta -> N gamma radiative branching ratio = the signal model; kept OUTSIDE the band by instruction"
        elif grp in ("flux_multisim", "beamline_g4_reint_multisim", "xsec_genie_multisim", "fsi_genie_multisim"):
            presc, used, why = "multisim: sample covariance of the universe yields about the nominal (1/N sum_u dN dN^T)", True, ""
        elif grp == "genie_multisigma_diagnostic":
            if len(sg) == 1:
                grp = "xsec_genie_unisim_extra"; presc, used, why = "single shifted universe (sigma = +1): one-sided dN = N(+1) - N_nom, independent", True, "knob has no multisim counterpart"
            else:
                presc, used, why = "diagnostic only (+-1 sigma response)", False, "duplicates the GENIE multisim set for the same knob (adding both would double count)"
        elif grp == "xsec_extra_multisigma":
            if sg == SIGMA_GRID:
                presc, used, why = "unisim: dN = (N(+1 sigma) - N(-1 sigma))/2, independent", True, ""
            else:
                presc, used, why = "not applied", False, f"universes are not a +-sigma grid (values {[round(float(x), 3) for x in sg]}); the sigma convention of this dial is not documented in the CAF/source"
        else:
            presc, used, why = "not applied", False, "unclassified"
        rows.append(dict(idx=i, name=n, nuniv=int(u), type_code=int(t), type_name=TYPE_NAME.get(int(t), "?"), group=grp, start=start, stop=start + int(u), sigmas=";".join(f"{x:g}" for x in sg),
                         prescription=presc, in_band=used, reason_if_not=why))
        start += int(u)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# covariance products (all linear algebra on per-universe yields; nothing is clipped)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
def universe_yields(W: np.ndarray, w: float, bin_idx: np.ndarray, nbin: int) -> np.ndarray:
    """(nbin, U) yields: sum over events of w * W[e, u] in bin(e). Events with bin_idx < 0 are excluded. float64 accumulation."""
    ok = bin_idx >= 0
    oh = np.zeros((nbin, int(ok.sum())))
    oh[bin_idx[ok], np.arange(int(ok.sum()))] = w
    return oh @ W[ok].astype(np.float64)


def function_deltas(fn: dict, Qu: np.ndarray, Qnom: np.ndarray, g=None):
    """Deltas of a derived quantity for one weight function. Qu: (nQ, nuniv_f) per-universe quantity vectors, Qnom: (nQ,). ``g`` maps a (nQ,) or (nQ, m) array to the derived quantity (default identity).

    Returns (D, scale) with Cov = scale * D D^T: multisim -> D = g(Q_u) - g(Q_nom), scale = 1/N_u; +-sigma grid -> one delta (g(Q(+1)) - g(Q(-1)))/2, scale 1; single sigma=+1 -> g(Q(+1)) - g(Q_nom)."""
    g = g or (lambda q: q)
    gn = g(Qnom[:, None])[:, 0]
    if fn["type_code"] == KMULTISIM:
        return g(Qu) - gn[:, None], 1.0 / Qu.shape[1]
    sg = [float(x) for x in fn["sigmas"].split(";") if x != ""]
    if tuple(sg) == SIGMA_GRID:
        a, b = sg.index(1.0), sg.index(-1.0)
        return ((g(Qu[:, [a]]) - g(Qu[:, [b]])) / 2.0), 1.0
    if sg == [1.0]:
        return g(Qu[:, [0]]) - gn[:, None], 1.0
    raise ValueError(f"no documented prescription for {fn['name']}")


def audit_weights(W: np.ndarray, nuniv_slices: list) -> "pd.DataFrame":
    """Per-function pathological-weight statistics of an (n_events, U) weight matrix. NO clipping or modification."""
    import pandas as pd
    rows = []
    for name, a, b in nuniv_slices:
        x = np.asarray(W[:, a:b], dtype=np.float64); fin = np.isfinite(x); xf = x[fin]
        allone = np.all(x == 1.0, axis=1) if len(x) else np.zeros(0, bool)
        rows.append(dict(name=name, n_events=int(x.shape[0]), n_universes=int(b - a), n_entries=int(x.size), n_nonfinite=int((~fin).sum()), n_zero=int((xf == 0).sum()), n_negative=int((xf < 0).sum()),
                         min=float(xf.min()) if xf.size else np.nan, max=float(xf.max()) if xf.size else np.nan, p999=float(np.percentile(xf, 99.9)) if xf.size else np.nan,
                         n_gt5=int((xf > 5).sum()), n_gt10=int((xf > 10).sum()), frac_exactly_1=float((xf == 1.0).mean()) if xf.size else np.nan,
                         frac_events_inert=float(allone.mean()) if allone.size else np.nan))
    return pd.DataFrame(rows)
