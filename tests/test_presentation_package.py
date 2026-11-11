"""Presentation prep: every slide number is traceable, no stale / forbidden wording, assets exist and equal their sources.  No analysis is touched."""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; DOC = ROOT / "docs" / "presentation"; AS = ROOT / "presentation_assets" / "ncdelta_baseline"
S = json.load(open(ROOT / "tables" / "baseline_consolidation" / "summary.json")); rows = json.load(open(DOC / "NCDELTA_BASELINE_SLIDE_NUMBERS.json"))
OUT = (DOC / "NCDELTA_BASELINE_PRESENTATION_OUTLINE.md").read_text(); NUMS = (DOC / "NCDELTA_BASELINE_SLIDE_NUMBERS.md").read_text()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def resolve(key):
    v = S
    for tok in re.findall(r"\[(?:'([^']+)'|(\d+))\]", key):
        v = v[int(tok[1])] if tok[1] else v[tok[0]]
    return v


def numbers_in(text):
    return [float(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*\.?\d*", text)]


def test_every_json_number_resolves_and_matches_the_displayed_value():
    n = 0
    for r in rows:
        if r["kind"] == "json":
            v = resolve(r["key"]); assert str(v) == str(r["value"]) or abs(float(v) - float(r["value"])) < 1e-9, r
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                shown = numbers_in(r["displayed"]); cands = [v, 100 * v]
                assert any(abs(s - c) <= 0.006 * max(1, abs(c)) / (1 if c > 100 else 1) + 0.0051 for s in shown for c in cands), (r["displayed"], v)
            n += 1
        elif r["kind"] == "sum":
            assert r["value"] == [sum(S["migration_final"][t][i] for t in S["migration_final"]) for i in range(3)] == [527, 556, 70]; n += 1
    assert n >= 60


def test_every_text_number_occurs_in_the_cited_consolidated_document():
    docs = {}
    for r in rows:
        if r["kind"] == "text":
            d = docs.setdefault(r["file"], (ROOT / r["file"]).read_text()); assert r["value"] in d, (r["file"], r["value"])


def test_headline_numbers_of_the_package():
    e = S["signal"]["eff"]; assert e["any|all"][:2] == [1153, 12427] and e["first|all"][:2] == [1101, 12427]
    assert S["migration_final"] == {"truth 0p": [425, 50, 1], "truth 1p": [93, 471, 30], "truth >=2p": [9, 35, 39]}
    assert abs(S["phase18_correction"]["numu_fail_share_corrected"] - 0.2688) < 5e-4 and S["background"]["selected_nonsignal"] == 635
    assert abs(S["signal_rate"]["total_per_1e20"] - 40.6) < 0.05 and S["natural_cv"]["selected_any"] == 13 and S["harmonized"]["B spine_technote_strict = HARMONIZED ALL"][:2] == [947, 8668]


def test_superseded_phase18_share_never_appears_as_a_headline():
    for name, txt in (("outline", OUT), ("numbers", NUMS)):
        for line in txt.splitlines():
            if re.search(r"29\.8", line):
                assert re.search(r"SUPERSEDED|superseded|Never show|NEVER", line), (name, line)
    assert "26.9 %" in OUT and "26.9 %" in NUMS


def test_forbidden_wording_is_always_caveated():
    neg = re.compile(r"\bNOT\b|\bnot\b|\bNo\b|\bno\b|never|Never|NEVER|refus|only after|Only after|deferred|SUPERSEDED|nothing|without", re.I)
    pats = [r"(?<![A-Za-z/_.])S/B(?![A-Za-z])", r"purity", r"optimi[sz]", r"standard FV", r"SPINE is better", r"Wire-Cell is worse", r"approved", r"significance"]
    for f in DOC.glob("*.md"):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            for p in pats:
                if re.search(p, line):
                    assert neg.search(line), (f.name, i, p, line[:160])
    low = OUT.lower()
    for bad in ("spine is better", "wire-cell is worse", "domain shift is established", "final purity", "significance of "):
        assert bad not in low


def test_outline_structure_and_required_caveats():
    heads = re.findall(r"^### Slide (\d+) \| (.+)$", OUT, flags=re.M); assert [int(a) for a, _ in heads] == list(range(1, 13))
    assert len(re.findall(r"^### Slide O\d \|", OUT, flags=re.M)) == 3 and len(re.findall(r"^\| B\d\d \|", OUT, flags=re.M)) == 15
    assert "CHARACTERISATION CONVENTIONS, NOT APPROVED ANALYSIS DEFINITIONS" in OUT and "NOT S/B" in OUT and "NOT A WIRE-CELL VS SPINE PERFORMANCE COMPARISON" in OUT and "No quantitative domain-shift claim possible" in OUT
    assert "Keep slides **1, 2, 4, 6, 8, 9, 11, 12**" in OUT and "Drop from the full outline: 3, 5, 7, 10" in OUT
    for h in ("Phase 6", "Phase 12", "Phase 17"):
        assert h not in " ".join(t for _, t in heads)
    blocks = re.split(r"^### Slide ", OUT, flags=re.M)[1:13]
    for b in blocks:
        for key in ("Central message", "Plot", "Headline numbers", "Speaker note", "Caveat to keep visible", "Callout"):
            assert key in b, (b[:40], key)
        note = re.search(r"Speaker note \((\d+) s\)", b); assert note and 30 <= int(note.group(1)) <= 60


def test_assets_exist_csv_complete_and_copies_equal_their_sources():
    csvf = pd.read_csv(DOC / "NCDELTA_BASELINE_SLIDE_ASSETS.csv"); assert list(csvf.columns) == ["slide", "role", "source_file", "phase", "figure_number", "crop_or_panel", "headline_number", "provenance", "main_or_backup"]
    listed = set()
    for r in csvf.itertuples():
        m = re.search(r"asset: (presentation_assets/\S+?);", r.provenance)
        if m:
            f = ROOT / m.group(1); assert f.exists(), m.group(1); listed.add(f.resolve())
            if r.provenance.endswith("copy"):
                assert sha(f) == sha(ROOT / r.source_file), r.source_file                                   # originals are copied unmodified
        else:
            assert "no asset" in r.provenance
    on_disk = {p.resolve() for p in AS.rglob("*.png")}; assert on_disk == listed, on_disk ^ listed
    main = [p for p in AS.glob("*.png")]; assert len(main) == 18 and len(list((AS / "backup").glob("*.png"))) == 19
    for n in ("02_cutflow", "03_loss_budget", "04_photon_taxonomy", "05_numu_compactness", "06_vertex_provenance", "07_proton_reco_vs_ke", "08_migration_matrix", "09_delta_mass_residual", "10b_backgrounds_clean_redraw", "11_rates"):
        assert (AS / f"{n}.png").exists()
    assert csvf.main_or_backup.isin(["main", "optional main", "backup", "backup (optional main)"]).all()


def test_main_slide_assets_are_referenced_by_the_outline_and_no_frozen_file_changed():
    for p in AS.glob("*.png"):
        assert p.name in OUT, p.name
    assert sha(ROOT / "configs" / "baseline_selection.yaml") == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"
