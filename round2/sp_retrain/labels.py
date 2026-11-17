"""Training labels for the single-photon BDTs.

There is deliberately no label definition here yet. The positive and negative classes the frozen MicroBooNE models
were trained with (single_photon_ncpi0_bdt_final.xml, single_photon_other_bdt_final.xml) are not recoverable from any
source available on 2026-11-17 (round2/docs/SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md). Until a training spec carries a
recovered definition and status READY_*, every call that would produce a training label raises TargetBlockedError.
The truth INGREDIENTS (primary pi0 count, photon counts and conversion points, partner neutrino) are in the tables,
so a recovered definition becomes a column expression, not a rebuild.
"""
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
        raise TargetBlockedError('%s v%s is %s: %s' % (spec.get('spec_id'), spec.get('spec_version'), status,
                                                       spec.get('status_reason', '').strip().splitlines()[0] if spec.get('status_reason') else ''))
    if not spec.get('label', {}).get('definition'):
        raise TargetBlockedError('%s has no label.definition' % spec.get('spec_id'))


def training_labels(cands, spec, final=False):
    """The 0/1 target per candidate row. Refuses unless the spec is READY_* and carries a definition."""
    require_ready(spec, final=final)
    raise NotImplementedError('label.definition must be implemented from the recovered original target, not invented')
