# Beam-on / beam-off / BNB CV shapes (SHAPE ONLY — NOT EXPOSURE NORMALIZED)

Plots: `plots/baseline_shapes/shapes_valid_candidates.png` (all candidates of `wc.valid` events) and `shapes_final_selected.png` (candidates passing the frozen chain; small statistics: beam-on 77, beam-off 6, CV 649). Counts per panel: `plots/baseline_shapes/shape_counts.json`. Script: `scripts/shape_plots.py`. Every panel is area-normalised and carries the banner **SHAPE ONLY — NOT EXPOSURE NORMALIZED**. Only branches present in the older beam-on schema are used. nueCC is not overlaid.

**Not done, deliberately:** no "beam-on vs MC + scaled beam-off" stack, no scale factor. The beam-off scale needs the beam-on gate count, livetime and run matching (`DATA_EXPOSURE_NORMALIZATION.md`); the beam-off subset has no file in run 18255 and 4 in run 18259.

Observations (descriptive; nothing corrected or tuned):
- The multiplicity-type variables (n 20 MeV showers, n 20br1 showers) and the BDT scores of beam-on and CV look alike; beam-off differs in the scores (few candidates, 822 evaluable).
- **Flash time:** the CV MC beam plateau spans ≈0.2–1.7 µs while open beam-on spans ≈0.5–2.0 µs (hard window edges 0.2/2.2 µs); beam-off is broad as expected for cosmics. A data/MC offset of ≈ +0.3 µs is visible; audited in `FLASH_TIME_CONVENTION_AUDIT.md` (unresolved).
- **Vertex coordinates:** a large spike at (x, y, z) = (0, 0, 0) in all samples (`has_vertex == 0` default; candidates without a reconstructed vertex: 41.6 % of beam-off candidates, 3.9 % beam-on, 1.9 % CV; see `VERTEX_SENTINEL_AUDIT.md`) and a y ≈ 200 cm pile-up in beam-off. Any vertex-based cut must treat the (0,0,0) sentinel explicitly.
- Reco proton count: beam-on and CV have similar 0p/1p shares; beam-off is mostly 0p.
