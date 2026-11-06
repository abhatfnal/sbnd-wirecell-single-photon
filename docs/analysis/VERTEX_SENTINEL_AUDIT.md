# (0,0,0) reconstructed-vertex audit

Variables: `wc.T_kine.kine_nu_{x,y,z}_corr` per candidate. Script `scripts/vertex_sentinel_report.py`; table `tables/vertex_sentinel/vertex_sentinel_by_sample.json`. No FV is applied or added.

## Meaning (Wire-Cell source)

`KineInfo` (`NeutrinoTaggerInfo.h`) initialises `kine_nu_x/y/z_corr{0}`; `fill_kine_tree` overwrites them with the main vertex (SCE-corrected, or the raw fitted vertex if no geometry helper — the source comment says the `_corr` name is then misleading). A candidate whose KineInfo is never filled keeps the default zeros. So (0,0,0) is the **default-initialised value of a candidate without a reconstructed main vertex**, not an explicit sentinel constant and not a failed correction. The companion flag `wc.T_tagger.has_vertex` (struct default −1) is the explicit indicator: in the first 100 files of every sample, `has_vertex == 0` ⇔ exactly (0,0,0) (100 %) and `has_vertex == 1` ⇒ never (0,0,0) (0 %); only the values 0 and 1 occur.

## Quantification (all candidates of `wc.valid` events, all files)

| sample | candidates | exactly (0,0,0) | fraction | BDT-evaluable among them | `shw_sp_filled == 0` among them | final-selected with (0,0,0) |
|---|---|---|---|---|---|---|
| bnb_cv | 241,845 | 4,566 | 1.9 % | 0 | 100 % | 0 of 649 |
| nuecc | 98,576 | 215 | 0.22 % | 0 | 100 % | 0 of 15,887 |
| beam_off | 4,733 | 1,967 | 41.6 % | 0 | 100 % | 0 of 6 |
| beam_on_open | 42,316 | 1,633 | 3.9 % | 0 | 100 % | 0 of 77 |

No candidate has only some coordinates equal to zero, and no vertex coordinate is non-finite. For comparison the BDT-evaluable fraction among candidates with a vertex is 21.5 % (CV), 82.1 % (nueCC), 29.7 % (beam-off), 20.9 % (beam-on).

## Consequences

- The baseline chain is unaffected: no (0,0,0) candidate is BDT-evaluable or selected.
- **Any future FV logic must reject `has_vertex == 0` (or equivalently the exact (0,0,0) default) explicitly before applying geometric bounds**; otherwise (0,0,0) is a point inside the box in x and y and sits on the z = 0 edge, and a lenient box (e.g. one with z > −10) would accept vertex-less candidates. Vertex-based plots must drop them (the earlier shape plots show the spike).
- Beam-off has 41.6 % vertex-less candidates, so unconditional vertex-position shape comparisons between beam-off and the other samples are dominated by this class.

## Open question

None blocking. (Optional for Haiwang: confirm that `has_vertex == 0` is the intended "no main vertex" flag.)
