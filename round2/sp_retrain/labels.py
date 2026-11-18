"""Training classes for the single-photon BDTs, gated by the training spec.

Source: E. H. Yandel, PhD thesis, UCSB 2024, sec. 5.2.2 (printed pp.127-133) and appendix E; class expressions as in
MicroBooNE cuts.h @ 0100d4b6:2849-2856. All four BDTs share one positive class; each has its own background type,
"split up by type and used only on the relevant BDT" (p.127).
  positive (1): the candidate's T_match level-2 partner is a neutrino that fits the inclusive single-photon signal
                definition (sec. 5.1.2; sp_truth.classify sp_signal == 1), any category, out-of-FV signal included
  negative (0): the partner is a neutrino of the classifier's background type (NEGATIVE_BKG):
                single_photon_ncpi0  NC pi0 background: not signal, NC, vertex in the 3 cm FV, >= 1 primary pi0 (p.131)
                single_photon_numu   nu_mu CC background with and without a pi0: not signal, |pdg| 14, CC, vertex in
                                     the 3 cm FV (p.128)
                single_photon_nue    nu_e CC background: not signal, |pdg| 12, CC, vertex in the 3 cm FV (p.133)
  excluded (-1): every other row (other backgrounds, cosmic / no partner, unreadable truth or label)
  rows: candidates after the preselection (not a placeholder; shw_sp_n_20mev_showers > 0; label readable), which
        is where the thesis trains (sec. 5.2.1, 5.2.3: "right after preselection, which is also where BDT training is done")

single_photon_other (development definition, 2026-11-17; thesis pp.129-131, App. E.2; cuts.h SPNCBkg / SPoutFVBkg):
  negative (0): partner neutrino of type NCBkg (NC, no primary pi0, in FV, not signal) or outFVBkg (true vertex outside
                the 3 cm FV, dirt included, not signal); a cosmic-matched or unmatched MC candidate (partner_kind cosmic
                / none); every preselected row of an EXT sample (spec samples.development entries with role ext_beam_off:
                off-beam data, no truth, always background). Signal rows of any component stay positive (p.129).
  Trainable only from a spec whose status allows it; the EXT sample is an approved, named exception of that spec.
"""
import numpy as np
import yaml

READY_STATES = ('READY_FOR_DEVELOPMENT_TRAINING', 'READY_FOR_FINAL_TRAINING')
NEGATIVE_BKG = {
    'single_photon_ncpi0': ('NCpi0Bkg',),
    'single_photon_numu': ('numuCCBkg', 'numuCCpi0Bkg'),
    'single_photon_other': ('NCBkg', 'outFVBkg'),
    # thesis p.133 / Fig. 5.10 caption: "Background includes only nu_e CC background events" (not signal, |pdg| 12, CC,
    # true vertex in the 3 cm FV: out-of-FV belongs to Other, the per-BDT counts sum to 263,120); cuts.h 0100d4b6:2856
    'single_photon_nue': ('nueCCBkg',),
}
NEGATIVE_COSMIC_PARTNER = ('single_photon_other',)     # cosmic-matched / unmatched MC candidates are negatives
EXT_ROLE = 'ext_beam_off'


def ext_sample_ids(spec):
    return tuple(s['id'] for s in spec.get('samples', {}).get('development', []) if s.get('role') == EXT_ROLE)


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


def preselection(cands, x_cut=None, ext_ids=()):
    """Thesis Table 5.2 / cuts.h is_singlephoton_pre, SBND mapping: every non-placeholder SBND candidate already has
    numu_cc_flag >= 0 (the MicroBooNE generic-selection flag); shw_sp_n_20mev_showers > 0; label readable.
    x_cut: optional (inner, outer) |x| bounds on the tagger vertex, an SBND stand-in for MicroBooNE's 5-250 cm cut
    (detector-specific; OPEN in the spec)."""
    readable = cands.label_unreadable.to_numpy() == 0
    if ext_ids:   # off-beam data carry no truth: no label to read
        readable = readable | cands['sample'].astype(str).isin(ext_ids).to_numpy()
    m = (cands.is_placeholder.to_numpy() == 0) & (cands.shw_sp_n_20mev_showers.to_numpy() > 0) & readable
    if x_cut is not None:
        ax = np.abs(cands.nu_x.to_numpy())
        m &= (ax > x_cut[0]) & (ax < x_cut[1])
    return m


def development_classes(cands, spec, x_cut=None):
    """1 / 0 / -1 per candidate row (see module docstring) and the preselection mask."""
    name = spec.get('classifier', {}).get('name')
    if name not in NEGATIVE_BKG:
        raise TargetBlockedError('%s: no implemented label definition' % spec.get('spec_id'))
    require_ready(spec, final=False)
    ext_ids = ext_sample_ids(spec)
    if ext_ids and name not in NEGATIVE_COSMIC_PARTNER:
        raise TargetBlockedError('%s: EXT samples are a class of single_photon_other only' % name)
    pre = preselection(cands, x_cut, ext_ids)
    is_ext = cands['sample'].astype(str).isin(ext_ids).to_numpy() if ext_ids else np.zeros(len(cands), bool)
    pk = cands.partner_kind.astype(str).to_numpy()
    nu = (pk == 'neutrino') & (cands.m_sp_truth_ok.fillna(0).to_numpy() == 1) & ~is_ext
    pos = nu & (cands.m_sp_signal.fillna(0).to_numpy() == 1)
    neg = nu & np.isin(cands.m_sp_bkg.astype(str).to_numpy(), NEGATIVE_BKG[name])
    if name in NEGATIVE_COSMIC_PARTNER:
        neg = neg | (np.isin(pk, ('cosmic', 'none')) & ~is_ext) | is_ext
    cls = np.full(len(cands), -1, dtype=np.int8)
    cls[pos] = 1
    cls[neg] = 0
    cls[~pre] = -1
    return cls, pre


def ncpi0_development_classes(cands, spec, x_cut=None):
    if spec.get('classifier', {}).get('name') != 'single_photon_ncpi0':
        raise ValueError('not the ncpi0 spec')
    return development_classes(cands, spec, x_cut)


def training_labels(cands, spec, final=False):
    """Training target per candidate row. Final labels need READY_FOR_FINAL_TRAINING."""
    require_ready(spec, final=final)
    return development_classes(cands, spec)[0]
