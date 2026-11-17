"""Round-2 retraining machinery for the SBND single-photon BDTs (ncpi0, other).

Architecture follows Xuyang Ning's nu_e retraining (bdt-comm @ 2c499b9): merged CAF -> per-candidate parquet tables ->
frozen training spec -> pools -> event-safe split -> XGBoost -> validation -> export. The code here is a fresh
implementation; see round2/ATTRIBUTION_AND_PROVENANCE.md.
"""
__version__ = '0.1.0'
