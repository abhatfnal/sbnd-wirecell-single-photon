#!/usr/bin/env python
"""Structural audit of the four FROZEN single-photon TMVA XMLs (no training, read-only).
Depth convention: root Node has depth="0" (the XML attribute); max depth = max over Node@depth = number of
split levels on the longest path (a stump has depth 1). Leaves carry nType != 0 and are at depth = max split depth + 1 in XML.
Writes tables/sp_bdt_xml_audit/*.csv and summary.json."""
import csv, hashlib, json, os, sys, collections
import xml.etree.ElementTree as ET
from pathlib import Path
W = Path(os.environ.get("SP_BDT_WEIGHTS", "/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights"))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "tables/sp_bdt_xml_audit"); OUT.mkdir(parents=True, exist_ok=True)
EXPECT = {"numu": "5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961",
          "other": "8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16",
          "ncpi0": "983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3",
          "nue": "8580ba04b4a9e3c7aefbb4d5da5006cff2a131804a7b594843461a7cd6f3758a"}
summ = {}
for m, exp in EXPECT.items():
    p = W / f"single_photon_{m}_bdt_final.xml"; sha = hashlib.sha256(p.read_bytes()).hexdigest()
    r = ET.parse(p).getroot()
    vs = [(int(v.get("VarIndex")), v.get("Expression")) for v in r.find("Variables")]
    trees = r.find("Weights").findall("BinaryTree")
    splits = collections.Counter(); gains = collections.Counter(); maxd = []; nleaf = []; leafabs = []
    cover = collections.Counter()
    for t in trees:
        md = 0; nl = 0
        for n in t.iter("Node"):
            d = int(n.get("depth")); 
            if n.get("nType") == "0" and n.get("IVar") not in (None, "-1") and len(list(n.findall("Node"))) == 2:
                splits[int(n.get("IVar"))] += 1; md = max(md, d + 1)
            else:
                nl += 1; leafabs.append(abs(float(n.get("res"))))
        maxd.append(md); nleaf.append(nl)
    dd = collections.Counter(maxd)
    names = dict(vs)
    summ[m] = dict(path=str(p), sha256=sha, recorded=exp, sha_match=sha == exp, n_trees=len(trees),
                   NTrees_attr=int(r.find("Weights").get("NTrees")), n_vars=len(vs), max_depth_splitlevels=max(maxd),
                   depth_dist={int(k): v for k, v in sorted(dd.items())}, total_splits=sum(splits.values()),
                   n_vars_used=len(splits), mean_leaves=sum(nleaf) / len(nleaf),
                   options={o.get("name"): o.get("modified") for o in r.find("Options")},
                   creator=[g.get("value") for g in r.find("GeneralInfo") if g.get("name") == "Creator"],
                   boostweights=sorted({t.get("boostWeight") for t in trees}),
                   max_abs_leaf=max(leafabs))
    with open(OUT / f"{m}_variable_splits.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["var_index", "name", "n_splits", "rank_by_splits"])
        order = sorted(range(len(vs)), key=lambda i: (-splits[i], i)); rk = {i: k + 1 for k, i in enumerate(order)}
        for i, nme in vs: w.writerow([i, nme, splits[i], rk[i] if splits[i] else ""])
(OUT / "summary.json").write_text(json.dumps(summ, indent=1))
for m, s in summ.items(): print(m, {k: s[k] for k in ("sha_match", "n_trees", "n_vars", "max_depth_splitlevels", "depth_dist", "total_splits", "n_vars_used", "options", "boostweights", "max_abs_leaf")})

# ---- upstream-score dependency and kine_pio_flag placement (all from the XML) ----
rows = []; extra = {}
for m in EXPECT:
    r = ET.parse(W / f"single_photon_{m}_bdt_final.xml").getroot()
    names = {int(v.get("VarIndex")): v.get("Expression") for v in r.find("Variables")}
    trees = r.find("Weights").findall("BinaryTree"); tot = 0
    stat = collections.defaultdict(lambda: dict(splits=0, trees=set(), depth=collections.Counter()))
    for k, t in enumerate(trees):
        for n in t.iter("Node"):
            if n.get("nType") == "0" and len(n.findall("Node")) == 2:
                tot += 1; nm = names[int(n.get("IVar"))]
                s = stat[nm]; s["splits"] += 1; s["trees"].add(k); s["depth"][int(n.get("depth"))] += 1
    for nm in names.values():
        if nm.endswith("_score") or nm in ("kine_pio_flag",):
            s = stat[nm]
            rows.append([m, nm, s["splits"], round(100 * s["splits"] / tot, 2), len(s["trees"]), len(trees),
                         json.dumps({int(a): b for a, b in sorted(s["depth"].items())})])
    sc = [nm for nm in names.values() if nm.endswith("_score")]
    extra[m] = dict(n_score_inputs=len(sc), score_inputs=sc,
                    score_split_share_pct=round(100 * sum(stat[n]["splits"] for n in sc) / tot, 2),
                    numu_pair_split_share_pct=round(100 * sum(stat[n]["splits"] for n in ("numu_score", "numu_1_score")) / tot, 2))
    if m == "ncpi0":
        s = stat["kine_pio_flag"]
        extra[m]["kine_pio_flag"] = dict(splits=s["splits"], trees=len(s["trees"]), depth=dict(sorted(s["depth"].items())))
with open(OUT / "upstream_score_and_flag_usage.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "variable", "n_splits", "pct_of_model_splits", "n_trees_using", "n_trees", "split_depth_distribution"]); w.writerows(rows)
summ["_dependency"] = extra
(OUT / "summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(extra, indent=1)[:1800])
