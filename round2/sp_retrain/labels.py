"""Training classes for the single-photon BDTs, gated by the training spec.

single_photon_ncpi0 (spec v0.2.0, READY_FOR_DEVELOPMENT_TRAINING). Source: E. H. Yandel, PhD thesis, UCSB 2024,
sec. 5.2.2 (printed pp.127-132) and appendix E.3 (p.281); class expressions as in MicroBooNE cuts.h @ 0100d4b6:2849-2855.
  positive (1): the candidate's T_match level-2 partner is a neutrino that fits the inclusive single-photon signal
                definition (sec. 5.1.2; sp_truth.classify sp_signal == 1), any category, out-of-FV signal included
  negative (0): the partner is a neutrino in the NC pi0 background (not signal, NC, vertex in the 3 cm FV, >= 1 primary
                pi0; sp_bkg == 'NCpi0Bkg')
  excluded (-1): every other row (other backgrounds, cosmic / no partner, unreadable truth or label)
  rows: candidates after the preselection (not a placeholder; shw_sp_n_20mev_showers > 0; label readable), which
        is where the thesis trains (sec. 5.2.1, 5.2.3: "right after preselection, which is also where BDT training is done")

single_photon_other: not implemented. Its negative class needs in-time cosmic (EXT, off-beam data) events, which no
Aurora training sample holds (round2/docs/YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md).
"""
import numpy as np
import yaml

READY_STATES = ('READY_FOR_DEVELOPMENT_TRAINING', 'READY_FOR_FINAL_TRAINING')


class TargetBlockedError(RuntimeError):
    pass


def load_spec(path):
    with open(path) as f:
        return yaml.safe_load(f)


def require_ready(spec, final=False):
    status = spec.get('status')
    need = ('READY_FOR_FINAL_TRAINING',) if final else READY_STATES
    if status not in need:
        reason = spec.get('status_reason', '') or ''
        raise TargetBlockedError('%s v%s is %s: %s' % (spec.get('spec_id'), spec.get('spec_version'), status,
                                                       reason.strip().splitlines()[0] if reason.strip() else ''))
    if not spec.get('label', {}).get('definition'):
        raise TargetBlockedError('%s has no label.definition' % spec.get('spec_id'))


def preselection(cands, x_cut=None):
    """Thesis Table 5.2 / cuts.h is_singlephoton_pre, SBND mapping: every non-placeholder SBND candidate already has
    numu_cc_flag >= 0 (the MicroBooNE generic-selection flag); shw_sp_n_20mev_showers > 0; label readable.
    x_cut: optional (inner, outer) |x| bounds on the tagger vertex, an SBND stand-in for MicroBooNE's 5-250 cm cut
    (detector-specific; OPEN in the spec)."""
    m = (cands.is_placeholder.to_numpy() == 0) & (cands.shw_sp_n_20mev_showers.to_numpy() > 0) & (cands.label_unreadable.to_numpy() == 0)
    if x_cut is not None:
        ax = np.abs(cands.nu_x.to_numpy())
        m &= (ax > x_cut[0]) & (ax < x_cut[1])
    return m


def ncpi0_development_classes(cands, spec, x_cut=None):
    """1 / 0 / -1 per candidate row (see module docstring) and the preselection mask."""
    if spec.get('classifier', {}).get('name') != 'single_photon_ncpi0':
        raise ValueError('not the ncpi0 spec')
    require_ready(spec, final=False)
    pre = preselection(cands, x_cut)
    nu = (cands.partner_kind.astype(str).to_numpy() == 'neutrino') & (cands.m_sp_truth_ok.fillna(0).to_numpy() == 1)
    pos = nu & (cands.m_sp_signal.fillna(0).to_numpy() == 1)
    neg = nu & (cands.m_sp_bkg.astype(str).to_numpy() == 'NCpi0Bkg')
    cls = np.full(len(cands), -1, dtype=np.int8)
    cls[pos] = 1
    cls[neg] = 0
    cls[~pre] = -1
    return cls, pre


def training_labels(cands, spec, final=False):
    """Training target per candidate row. Final labels need READY_FOR_FINAL_TRAINING; only ncpi0 is implemented."""
    require_ready(spec, final=final)
    if spec.get('classifier', {}).get('name') == 'single_photon_ncpi0':
        return ncpi0_development_classes(cands, spec)[0]
    raise TargetBlockedError('%s: no implemented label definition' % spec.get('spec_id'))
