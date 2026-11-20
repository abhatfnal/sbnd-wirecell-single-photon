"""Campaign-level Wire-Cell toolkit provenance of WCLocal2026Nov16 (development_wcl1116_v1).

A merged CAF stores only a version STRING (wc.Trun.wct_version), not a git SHA. Two builds of the SAME tagged commit
made WCLocal2026Nov16, and they stamp that string differently:

  stored wct_version   build                                                   evidence
  "0.38.0"             Aurora: $Y/opt-0.38.0 from the worktree $Y/wct-0.38.0    production_provenance.json (commit recorded
                       at c935e30d (tag 0.38.0; version.txt "0.38.0")           beside the stamp); git rev-parse of the worktree
  "HEAD-0.38.0"        FermiGrid / gpVM: /exp/sbnd/data/users/yuhw/             TARBALL-PROVENANCE.txt of the WCLocal2026Nov16
                       wclocal-nov16/opt, a detached checkout exactly on tag     tarballs: opt WIRECELL_VERSION "HEAD-0.38.0";
                       0.38.0 (WCT version rule: "<branch>-<git describe>",      cfg "wire-cell-toolkit c935e30d 0.38.0 0 dirty
                       branch "HEAD" when detached)                             cfg files" (checked by Avinay on the gpVM)

Both strings map to toolkit commit c935e30d44a09bf208f6de2c2968171b01efd63d (tag 0.38.0). Avinay approved treating
exactly these two strings as the same build for THIS campaign (2026-11-19). This is a closed list, NOT a version
parser: membership is exact string equality. Anything else -- a post-tag "HEAD-0.38.0-1-g<hash>", a feature-branch
"<branch>-0.38.0", "0.38.1", the old fg1 "...-g78f81c64", an empty or unknown string -- is not WCLocal2026Nov16.
"""

WCL1116_TOOLKIT_COMMIT = 'c935e30d44a09bf208f6de2c2968171b01efd63d'
WCL1116_TAG = '0.38.0'
WCL1116_BUNDLE = 'dv2max/sbnd/aurora_space/bundle.json'
WCL1116_BUNDLE_SHA256 = '51588842984919b5d8146f007287a5e7841be6bbc709263b10cdb39046ff8a74'

WCL1116_STAMPS = {
    '0.38.0': dict(
        build='Aurora WCLocal2026Nov16 (/lus/flare/projects/neutrinoGPU/yuhw/opt-0.38.0; worktree wct-0.38.0 at c935e30d)',
        evidence='round2/manifests/wcl1116_aurora_v0/production_provenance.json (stored_wct_version_stamp "0.38.0", toolkit commit c935e30d)'),
    'HEAD-0.38.0': dict(
        build='FermiGrid / gpVM WCLocal2026Nov16 (/exp/sbnd/data/users/yuhw/wclocal-nov16/opt)',
        evidence=('TARBALL-PROVENANCE.txt: opt /exp/sbnd/data/users/yuhw/wclocal-nov16/opt: wire-cell WIRECELL_VERSION "HEAD-0.38.0"; '
                  'cfg /exp/sbnd/data/users/yuhw/wclocal-nov16/wct/cfg: wire-cell-toolkit c935e30d 0.38.0 0 dirty cfg files. Found in '
                  'p0/emu-ncpi0-s0-7/tar/wc/, emu53a/w-mc-nuecc/tar/wc/ and emu53a/w-opendata/tar/wc/ (inspected by Avinay on the gpVM)')),
}

WCL1116_PROVENANCE = dict(
    campaign='development_wcl1116_v1 (WCLocal2026Nov16)',
    toolkit_commit=WCL1116_TOOLKIT_COMMIT, tag=WCL1116_TAG, dirty_cfg_files=0,
    accepted_wct_version_stamps=sorted(WCL1116_STAMPS),
    stamp_mapping=WCL1116_STAMPS,
    rule='exact string equality against this closed list; no substring, regex, suffix or prefix matching',
    per_file_vs_campaign=('each ROOT file stores only the version string (and the DL bundle sha256 in dl_weights), not the '
                          'toolkit SHA; the SHA comes from the campaign-level build records above, and the mapping is this table'),
    approved_by='Avinay Bhat', approved='2026-11-19')


def wcl1116_stamp_ok(stamp):
    """True only for the exact stored strings of the two WCLocal2026Nov16 builds of c935e30d."""
    return isinstance(stamp, str) and stamp in WCL1116_STAMPS


def wcl1116_dl_weights(mode):
    """The exact wc.Trun.dl_weights string of a WCLocal2026Nov16 tree (mode dv2_split_move or dv2_snap)."""
    return '%s:%s@sha256:%s' % (mode, WCL1116_BUNDLE, WCL1116_BUNDLE_SHA256)


def expected_sample_stamp(sample_entry, manifest_stamp):
    """The stored wct_version a sample's files must carry. Default: the input manifest's stamp (unchanged behaviour for
    every existing sample). A spec sample entry may record its own verified stamp (the staged beam-off half); such an
    override must be one of the WCLocal2026Nov16 strings."""
    if 'wct_version_stamp' not in sample_entry:
        return manifest_stamp
    s = sample_entry['wct_version_stamp']
    if not wcl1116_stamp_ok(s):
        raise ValueError('sample %s: wct_version stamp %r is not a WCLocal2026Nov16 build' % (sample_entry.get('id'), s))
    return s


# ------------------------------------------------------------------ campaign-level provenance from an explicit spec
class Provenance:
    """Exact-match reconstruction provenance: a closed list of stored wct_version strings, a toolkit commit, the DL
    bundle and the Wire-Cell trees with their vertex modes. WCL1116 is the default; the next production supplies its own
    values through a campaign spec (config/campaigns/*.yaml) -- nothing is inferred."""

    def __init__(self, stamps, toolkit_commit, bundle, bundle_sha256, trees, record):
        self.stamps = tuple(stamps); self.toolkit_commit = toolkit_commit
        self.bundle, self.bundle_sha256 = bundle, bundle_sha256
        self.trees = dict(trees); self.record = record

    def stamp_ok(self, stamp):
        return isinstance(stamp, str) and stamp in self.stamps

    def dl_weights(self, mode):
        return '%s:%s@sha256:%s' % (mode, self.bundle, self.bundle_sha256)


WCL1116 = Provenance(sorted(WCL1116_STAMPS), WCL1116_TOOLKIT_COMMIT, WCL1116_BUNDLE, WCL1116_BUNDLE_SHA256,
                     {'recTreeWireCell': 'dv2_split_move', 'recTreeWireCell_dv2snap': 'dv2_snap'}, WCL1116_PROVENANCE)


def from_campaign_spec(spec):
    p = spec['production']
    missing = [k for k in ('toolkit_commit', 'toolkit_version_stamps', 'dl_bundle', 'dl_bundle_sha256', 'wc_trees') if not p.get(k)]
    if missing:
        raise ValueError('campaign spec production block lacks %s' % missing)
    return Provenance(p['toolkit_version_stamps'], p['toolkit_commit'], p['dl_bundle'], p['dl_bundle_sha256'], p['wc_trees'],
                      dict(campaign=spec.get('campaign'), production=p))
