"""Full generator fPartList decoder for memberwise vector<simb::MCTruth> (art reco1, login node, read-only).

Extends the validated mixed-sample decoder (nugraph-light-h5-v1-20261011/.../decode_generator_truth.py, exec'd verbatim
up to its main()) with the per-interaction particle list: status, trackId, pdg, mother, start position, start
4-momentum.  Layout (simb::MCParticle v18 memberwise inside the fPartList block; verified by exact byte-end asserts):
  per interaction k: [n_k u32] then columns over the n_k particles:
    fstatus[i32] ftrackId[i32] fpdgCode[i32] fmother[i32]
    fprocess   (column bytecount)            fendprocess (column bytecount)
    ftrajectory: n_k objects, each [bc][ver 12][vec bc][0x4000|ver][pair ver(+checksum)][npts][pos TLV x npts][mom TLV x npts]...
    fmass[f64]  fpolarization (n_k TVector3 objects or one column block)  fdaughters (set<int>)  fWeight[f64]
    fGvtx (n_k TLorentzVector objects)  frescatter[i32]
"""
import struct

_SRC = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/nugraph-light-h5-v1-20261011/validation/"
        "mixed_sample_v1_20261012/scripts/decode_generator_truth.py")
_s = open(_SRC).read()
NS = {}
exec(compile(_s[:_s.index("def main():")], "decode_generator_truth.py[..main]", "exec"), NS)
Cur, raw, outer, read_tlv, mcparticle_head = NS["Cur"], NS["raw"], NS["outer"], NS["read_tlv"], NS["mcparticle_head"]
decode_gtruth, decode_flat, active_tpc, EXPECT = NS["decode_gtruth"], NS["decode_flat"], NS["active_tpc"], NS["EXPECT"]
ACTIVE_JSON, MODE, GINT, GSCAT = NS["ACTIVE_JSON"], NS["MODE"], NS["GINT"], NS["GSCAT"]


def _traj(c):
    end = c.obj_start(); assert c.u16() == 12
    vec_end = c.obj_start(); vv = c.u16(); assert vv & 0x4000, hex(vv)
    pv = c.u16()
    if pv == 0:
        c.u32()
    npts = c.u32()
    pos = [read_tlv(c) for _ in range(npts)]
    mom = [read_tlv(c) for _ in range(npts)]
    assert c.p == vec_end, (c.p, vec_end)
    c.p = end
    return (pos[0] if pos else None), (mom[0] if mom else None), npts


def _objcol(c, n):
    """n byte-counted objects, OR one byte-counted column block; returns after skipping."""
    for _ in range(n):
        c.skip_obj()


def _partlist(c, n_k):
    I = lambda: [c.get("i") for _ in range(n_k)]
    st, tid, pdg, mo = I(), I(), I(), I()
    c.skip_obj(); c.skip_obj()  # fprocess, fendprocess columns
    trj = [_traj(c) for _ in range(n_k)]
    mass = [c.get("d") for _ in range(n_k)]
    return st, tid, pdg, mo, trj, mass


def decode_mctruth_full(b):
    """-> list of interaction dicts with 'particles' (status, trackid, pdg, mother, start xyzt, p4 (px,py,pz,E) GeV)."""
    c = Cur(b); end, n = outer(c, "simb::MCTruth")
    d = [dict() for _ in range(n)]
    pl_end = c.obj_start(); vv = c.u16(); assert vv & 0x4000; assert c.u16() == EXPECT["simb::MCParticle"]
    for k in range(n):
        n_k = c.u32()
        st, tid, pdg, mo, trj, mass = _partlist(c, n_k)
        # remaining columns: fpolarization (TVector3 objects), fdaughters (set<int>), fWeight, fGvtx, frescatter
        p0 = c.p
        try:
            for _ in range(n_k):
                c.skip_obj()          # fpolarization: per-object byte counts
        except AssertionError:
            c.p = p0; c.skip_obj()    # one column block
        dpos = c.p
        try:
            c.skip_obj()              # fdaughters: one column block
        except AssertionError:
            raise
        for _ in range(n_k):
            c.get("d")                # fWeight
        g0 = c.p
        try:
            for _ in range(n_k):
                c.skip_obj()          # fGvtx
        except AssertionError:
            c.p = g0; c.skip_obj()
        for _ in range(n_k):
            c.get("i")                # frescatter
        d[k]["particles"] = [dict(status=st[i], trackid=tid[i], pdg=pdg[i], mother=mo[i], start=trj[i][0], p4=trj[i][1],
                                  npts=trj[i][2], mass=mass[i]) for i in range(n_k)]
    assert c.p == pl_end, (c.p, pl_end)
    for k in range(n):
        nu_end = c.obj_start(); assert c.u16() == EXPECT["simb::MCNeutrino"]
        nu, lep = mcparticle_head(c), mcparticle_head(c)
        d[k].update(nu_pdg=nu["pdg"], lepton_pdg=lep["pdg"], nu_start=nu["start"], mode=c.get("i"), interaction_type=c.get("i"),
                    ccnc=c.get("i"), target=c.get("i"), hitnuc=c.get("i"), hitquark=c.get("i"), W=c.get("d"), X=c.get("d"),
                    Y=c.get("d"), Q2=c.get("d"))
        assert c.p == nu_end, (c.p, nu_end)
    for k in range(n): d[k]["origin"] = c.get("i")
    for k in range(n): c.skip_obj()
    for k in range(n): d[k]["neutrino_set"] = c.get("?")
    assert c.p == end == len(b), (c.p, end, len(b))
    return d


def _traj_full(c):
    end = c.obj_start(); assert c.u16() == 12
    vec_end = c.obj_start(); vv = c.u16(); assert vv & 0x4000, hex(vv)
    pv = c.u16()
    if pv == 0:
        c.u32()
    npts = c.u32()
    pos = [read_tlv(c) for _ in range(npts)]
    mom = [read_tlv(c) for _ in range(npts)]
    assert c.p == vec_end, (c.p, vec_end)
    c.p = end
    return (pos[0] if pos else None), (mom[0] if mom else None), npts, (pos[-1] if pos else None)


def decode_mcparticles(b, want=None):
    """top-level art vector<simb::MCParticle> (e.g. 'largeant'): status, trackid, pdg, mother, start, p4, end.
    want(st, tid, pdg, mo) -> bool limits the returned rows (all columns are still walked byte-exactly)."""
    c = Cur(b); end, n = outer(c, "simb::MCParticle")
    I = lambda: [c.get("i") for _ in range(n)]
    st, tid, pdg, mo = I(), I(), I(), I()
    c.skip_obj(); c.skip_obj()
    trj = [_traj_full(c) for _ in range(n)]
    mass = [c.get("d") for _ in range(n)]
    p0 = c.p
    try:
        for _ in range(n):
            c.skip_obj()
    except AssertionError:
        c.p = p0; c.skip_obj()
    c.skip_obj()
    for _ in range(n):
        c.get("d")
    g0 = c.p
    try:
        for _ in range(n):
            c.skip_obj()
    except AssertionError:
        c.p = g0; c.skip_obj()
    for _ in range(n):
        c.get("i")
    assert c.p == end == len(b), (c.p, end, len(b))
    rows = []
    for i in range(n):
        if want is None or want(st[i], tid[i], pdg[i], mo[i]):
            rows.append(dict(status=st[i], trackid=tid[i], pdg=pdg[i], mother=mo[i], start=trj[i][0], p4=trj[i][1],
                             npts=trj[i][2], end=trj[i][3]))
    return rows
