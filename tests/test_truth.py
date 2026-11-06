import awkward as ak
from sbnd_single_photon import truth as T


def _cat(pdg, cc, nc, npi, x, y, z):
    c = T.classify_events(ak.Array([pdg]), ak.Array([cc]), ak.Array([nc]), ak.Array([npi]),
                          ak.Array([x]), ak.Array([y]), ak.Array([z]))
    return T.CATEGORIES[int(c[0])]


IN = ([0.0], [0.0], [250.0])
OUT = ([0.0], [0.0], [900.0])


def test_single_active_categories():
    assert _cat([14], [1], [0], [0], *IN) == "NUMU_CC"
    assert _cat([-14], [1], [0], [0], *IN) == "NUMU_CC"
    assert _cat([12], [1], [0], [0], *IN) == "NUE_CC"
    assert _cat([14], [0], [1], [1], *IN) == "NC_PI0"
    assert _cat([14], [1], [0], [2], *IN) == "CC_PI0"          # pi0 takes precedence over flavour
    assert _cat([14], [0], [1], [0], *IN) == "OTHER_NC"
    assert _cat([16], [1], [0], [0], *IN) == "OTHER_CC"
    assert _cat([14], [0], [0], [0], *IN) == "OTHER"


def test_dirt_multi_and_cosmic():
    assert _cat([14], [1], [0], [0], *OUT) == "DIRT_NO_ACTIVE"
    assert _cat([], [], [], [], [], [], []) == "COSMIC_NO_NU"
    assert _cat([14, 14], [1, 0], [0, 1], [0, 0], [0.0, 10.0], [0.0, 10.0], [250.0, 100.0]) == "MULTI_ACTIVE"
    # one active + one dirt -> the active one decides
    assert _cat([14, 14], [1, 0], [0, 1], [0, 0], [0.0, 900.0], [0.0, 0.0], [250.0, 100.0]) == "NUMU_CC"


def test_nan_position_is_not_active():
    nan = float("nan")
    assert _cat([14], [1], [0], [0], [nan], [nan], [nan]) == "DIRT_NO_ACTIVE"


def test_vectorised_many_events():
    c = T.classify_events(ak.Array([[14], [12]]), ak.Array([[1], [1]]), ak.Array([[0], [0]]), ak.Array([[0], [0]]),
                          ak.Array([[0.0], [0.0]]), ak.Array([[0.0], [0.0]]), ak.Array([[100.0], [100.0]]))
    assert T.category_names(c).tolist() == ["NUMU_CC", "NUE_CC"]


def test_pi0_count_must_come_from_primaries():
    """rec.mc.nu.npizero is 0 in the CAFs; a CC numu event whose primaries contain a pi0 must be CC_PI0 once the count is derived."""
    import awkward as ak
    from sbnd_single_photon import caf as C
    prim_pdg = ak.Array([[13, 2212, 111, 22, 22]])           # one event, one neutrino, 5 primaries
    nprim = ak.Array([[5]])
    n_pi0 = ak.sum(C.per_candidate(prim_pdg, nprim) == 111, axis=-1)
    one = lambda v: ak.Array([[v]])
    code = T.classify_events(one(14), one(1), one(0), n_pi0, one(0.0), one(0.0), one(250.0))
    assert T.CATEGORIES[int(code[0])] == "CC_PI0"
    code0 = T.classify_events(one(14), one(1), one(0), one(0), one(0.0), one(0.0), one(250.0))   # the unfilled field
    assert T.CATEGORIES[int(code0[0])] == "NUMU_CC"
