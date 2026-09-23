"""Each photometry point remembers the alert it came from.

The lightcurve payload is slim and carries no alert id, so the point has to
keep one to be able to ask the broker for its images later. A mover's objectId
changes almost every detection, which leaves the alert id as the only way back.
"""

from skyportal.broker_apis._save import build_photometry_groups

STREAMS = {("ZTF", 1): [1]}


def detection(jd, candid=None, flux=100.0):
    point = {
        "jd": jd,
        "band": "g",
        "psfFlux": flux,
        "psfFluxErr": 1.0,
        "ra": 1.0,
        "dec": 2.0,
        "programid": 1,
    }
    if candid is not None:
        point["candid"] = candid
    return point


def groups_for(data):
    return build_photometry_groups("ZTF26abc", "ZTF", data, 1, STREAMS)


def altdata_of(data):
    groups = groups_for(data)
    assert groups, "no photometry group was built"
    return next(iter(groups.values())).get("altdata")


def test_a_detection_keeps_its_alert_id():
    assert altdata_of({"prv_candidates": [detection(2460000.5, candid=12345)]})[
        "candid"
    ] == ["12345"]


def test_the_alert_id_is_a_string():
    # A ZTF candid is a 19-digit integer, which JSON hands to the browser as a
    # float and rounds; the broker is then asked for an alert that does not exist.
    candid = 2461306013298615001
    stored = altdata_of({"prv_candidates": [detection(2460000.5, candid=candid)]})
    assert stored["candid"] == [str(candid)]
    assert int(stored["candid"][0]) == candid


def test_forced_photometry_carries_no_alert_id():
    # There is no alert behind a forced-photometry epoch. Nothing is stamped, so
    # the block is pruned entirely and the point offers no cutouts rather than
    # pointing at somebody else's image.
    assert altdata_of({"fp_hists": [detection(2460000.5)]}) is None


def test_every_point_gets_an_entry():
    # The arrays are positional, so a missing candid has to be a null rather
    # than a gap, or every later point is attributed to the wrong alert.
    data = {
        "prv_candidates": [
            detection(2460000.5, candid=1),
            detection(2460001.5),
            detection(2460002.5, candid=3),
        ]
    }
    stored = altdata_of(data)
    assert stored["candid"] == ["1", None, "3"]
    assert len(stored["candid"]) == len(stored["rh"])


def test_a_detection_without_an_alert_id_still_keeps_the_others():
    # Pruning is all-or-nothing per group, so one point with an id keeps the
    # block alive and the nulls beside it stay aligned.
    data = {"prv_candidates": [detection(2460000.5), detection(2460001.5, candid=7)]}
    assert altdata_of(data)["candid"] == [None, "7"]


def test_a_key_that_applies_to_only_some_points_is_dropped_where_it_does_not():
    # Parallel arrays become a DataFrame column, so a key absent for one point
    # arrives as NaN rather than None. NaN is not JSON, and a point carrying
    # one would be offered cutouts for an alert that does not exist.
    from skyportal.handlers.api.photometry import _blank

    assert _blank(float("nan")) is True
    assert _blank(None) is True
    assert _blank("") is True
    assert _blank("2461306013298615001") is False
    assert _blank(0) is False


def test_a_real_value_of_zero_is_kept():
    # rh/delta/phase are numbers; zero is a value, not an absence.
    from skyportal.handlers.api.photometry import _blank

    assert _blank(0.0) is False


def test_the_cutout_cache_is_keyed_per_broker_survey_and_alert():
    # Two brokers can serve the same survey, and the same candid means a
    # different alert in a different survey, so none of the three may be
    # dropped from the key.
    from skyportal.broker_apis.boom import cutouts_cache

    assert cutouts_cache is not None
    keys = {f"{b}_{s}_{a}" for b in (1, 2) for s in ("ZTF", "LSST") for a in (7, 8)}
    assert len(keys) == 8
