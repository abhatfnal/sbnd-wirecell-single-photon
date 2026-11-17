"""Training / evaluation firewall.

Round-2 architecture (2026-11-17):
  * Aurora samples (Haiwang's aurora-r* merged CAFs of Avinay's gen2 MC) are TRAINING / DEVELOPMENT.
  * Official fg1 / FermiGrid / SAM samples are untouched EVALUATION. They never enter a training manifest. This
    includes the fg1 beam-off "train" half that Xuyang's spec_v1 trains on: here it is refused unless a training spec
    names it under approved_exceptions together with who approved it.
  * Nothing is written into another user's area.

Every check raises FirewallError; nothing is silently dropped.
"""
import os

# Path fragments that only official evaluation samples (or real data) carry.
OFFICIAL_MARKERS = ('/pnfs/', 'prod-fermigrid', '/fg1/', 'fg1-', 'fg1_', 'beam-off', 'beamoff', 'run3bnb', 'open-run1',
                    'opendata', 'bnb-data', 'sbnd2026a', 'data_filtered_decoded', 'strmoffbeam', 'strmbnb', 'onbeam',
                    'offbeam')
FOREIGN_USER_AREAS = ('/lus/flare/projects/neutrinoGPU/xning', '/lus/flare/projects/neutrinoGPU/yuhw')


class FirewallError(RuntimeError):
    pass


def official_marker(path):
    """The first official-sample marker found in a path or sample id, or None."""
    p = str(path).lower()
    for m in OFFICIAL_MARKERS:
        if m in p:
            return m
    return None


def check_training_inputs(paths, allowed_roots, approved_exceptions=()):
    """Every training input must sit under an allowed root and carry no official-sample marker.
    approved_exceptions: path prefixes explicitly approved in a training spec (normally empty)."""
    roots = [os.path.normpath(r) + os.sep for r in allowed_roots]
    exc = [os.path.normpath(e) for e in approved_exceptions]
    bad = []
    for p in paths:
        q = os.path.normpath(str(p))
        if any(q.startswith(e) for e in exc):
            continue
        m = official_marker(q)
        if m is not None:
            bad.append((q, 'official marker %r' % m))
        elif not any(q.startswith(r) for r in roots):
            bad.append((q, 'outside allowed roots'))
    if bad:
        raise FirewallError('%d training input(s) refused, first: %s (%s)' % (len(bad), bad[0][0], bad[0][1]))
    return len(paths)


def check_sample_id(sample_id, approved_exceptions=()):
    if sample_id in approved_exceptions:
        return
    m = official_marker(sample_id)
    if m is not None:
        raise FirewallError('sample id %r carries official marker %r' % (sample_id, m))


def check_output_path(path, allowed_output_roots):
    q = os.path.normpath(os.path.abspath(str(path)))
    for f in FOREIGN_USER_AREAS:
        if q == f or q.startswith(f + os.sep):
            raise FirewallError('refusing to write inside %s: %s' % (f, q))
    if not any(q == os.path.normpath(r) or q.startswith(os.path.normpath(r) + os.sep) for r in allowed_output_roots):
        raise FirewallError('output %s is outside the allowed output roots' % q)
    return q
