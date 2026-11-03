#!/usr/bin/env python3
"""Compile the WCLS top-level jsonnet exactly as wcls-img-clus-matching-xin-prod.fcl
hands it to WireCellToolkit (params -> ext-str, structs -> ext-code), using the
given WIRECELL_PATH-style search list, and write (a) the compiled JSON and (b) a
flattened leaf listing "<type>:<name> <data.path> = <json value>".

Usage: compile_cfg.py OUTPREFIX DIR1:DIR2:...   (needs _jsonnet on PYTHONPATH)
"""
import json
import os
import sys

import _jsonnet

PARAMS = {  # physics.producers.sig2img.wcls_main.params (prod fcl)
    "reality": "sim",
    "img_config": "active2view+masked2view",
    "enable_tracking_root": "true",
    "enable_nugraph_h5": "true",
    "pr_operating_point": "sync",
    "opflash0_input_label": "opflashtpc0:",
    "opflash1_input_label": "opflashtpc1:",
}
STRUCTS = {  # physics.producers.sig2img.wcls_main.structs (prod fcl)
    "recobwire_tags": '["simtpc2d:dnnsp", "simtpc2d:dnnsp"]',
    "trace_tags": '["gauss", "wiener"]',
    "summary_tags": '["", "simtpc2d:wienersummary"]',
    "input_mask_tags": '["simtpc2d:badmasks"]',
    "output_mask_tags": '["bad"]',
}
MAIN = "wcls-img-clus-matching-xin.jsonnet"


def find(path, rel):
    for d in path:
        p = os.path.join(d, rel)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(rel)


def import_callback(path):
    def cb(base, rel):
        cands = [os.path.join(base, rel)] + [os.path.join(d, rel) for d in path]
        for c in cands:
            if os.path.isfile(c):
                with open(c, "rb") as f:
                    return c, f.read()
        raise RuntimeError("import not found: %s (from %s)" % (rel, base))
    return cb


def flatten(obj, prefix, out):
    if isinstance(obj, dict):
        if not obj:
            out[prefix] = "{}"
        for k in sorted(obj):
            flatten(obj[k], prefix + "." + k if prefix else k, out)
    elif isinstance(obj, list):
        if not obj:
            out[prefix] = "[]"
        for i, v in enumerate(obj):
            flatten(v, "%s[%d]" % (prefix, i), out)
    else:
        out[prefix] = json.dumps(obj, sort_keys=True)


def main():
    outprefix, spath = sys.argv[1], sys.argv[2]
    path = [d for d in spath.split(":") if d]
    main_file = find(path, MAIN)
    js = _jsonnet.evaluate_file(main_file, ext_vars=PARAMS, ext_codes=STRUCTS,
                                import_callback=import_callback(path))
    cfg = json.loads(js)
    with open(outprefix + ".json", "w") as f:
        json.dump(cfg, f, indent=1, sort_keys=True)
    leaves = {}
    seen = {}
    for comp in cfg:
        key = "%s:%s" % (comp.get("type"), comp.get("name", ""))
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key += "#%d" % seen[key]
        flatten(comp.get("data", {}), key + " ", leaves)
    with open(outprefix + ".leaves.txt", "w") as f:
        for k in sorted(leaves):
            f.write("%s = %s\n" % (k, leaves[k]))
    print("main:", main_file)
    print("components:", len(cfg), "leaves:", len(leaves))


if __name__ == "__main__":
    main()
