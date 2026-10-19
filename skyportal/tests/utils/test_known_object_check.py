"""Deciding whether a track is already a known minor planet.

The failure that matters is a query that breaks and reads as "undiscovered",
which invites submitting a known object as a discovery. A negative is only
reported when a control observation proves the query path still works.
"""

from datetime import datetime

import pytest

import skyportal.utils.jpl_sbident as sbident
from skyportal.utils.jpl_sbident import JPLSBIdentError, check_known_object

TRACK = [
    {"jd": 2461293.86664, "ra": 8.980389, "dec": 48.596773},
    {"jd": 2461299.80088, "ra": 8.119989, "dec": 49.146170},
    {"jd": 2461306.82705, "ra": 6.855218, "dec": 49.397193},
]
CONTROL = {"jd": 2461299.86532, "ra": 8.108341, "dec": 49.150555, "expect": "Ceres"}


def times(jd):
    return datetime(2026, 9, 10)


def patch_identify(monkeypatch, behaviour):
    monkeypatch.setattr(sbident, "identify", behaviour)


def test_a_match_is_reported_as_known(monkeypatch):
    patch_identify(
        monkeypatch, lambda *a, **k: [{"name": "2026 AB", "offset_arcsec": 3.7}]
    )
    result = check_known_object(TRACK, times, control=CONTROL)
    assert result["known"] is True
    assert result["verified"] is True


def test_a_match_needs_no_control(monkeypatch):
    # JPL naming something at that position is self-verifying.
    patch_identify(
        monkeypatch, lambda *a, **k: [{"name": "2026 AB", "offset_arcsec": 3.7}]
    )
    assert check_known_object(TRACK, times)["verified"] is True


def test_a_clean_negative_needs_the_control_to_pass(monkeypatch):
    calls = []

    def behaviour(ra, dec, *a, **k):
        calls.append(ra)
        return (
            [{"name": "1 Ceres", "offset_arcsec": 3.7}] if ra == CONTROL["ra"] else []
        )

    patch_identify(monkeypatch, behaviour)
    result = check_known_object(TRACK, times, control=CONTROL)
    assert result["known"] is False
    assert result["verified"] is True
    assert CONTROL["ra"] in calls, "the control must actually be queried"


def test_a_negative_without_a_control_is_not_trusted(monkeypatch):
    patch_identify(monkeypatch, lambda *a, **k: [])
    result = check_known_object(TRACK, times)
    assert result["known"] is None
    assert result["verified"] is False
    assert "control" in result["reason"]


def test_a_control_that_finds_nothing_means_the_query_is_broken(monkeypatch):
    # Everything returns empty, including where a known object must be. That is
    # a broken query, not a discovery.
    patch_identify(monkeypatch, lambda *a, **k: [])
    result = check_known_object(TRACK, times, control=CONTROL)
    assert result["known"] is None
    assert result["verified"] is False
    assert "broken query" in result["reason"]


def test_a_control_returning_the_wrong_object_does_not_count(monkeypatch):
    patch_identify(
        monkeypatch,
        lambda ra, *a, **k: (
            [] if ra != CONTROL["ra"] else [{"name": "99 Other", "offset_arcsec": 3.7}]
        ),
    )
    assert check_known_object(TRACK, times, control=CONTROL)["verified"] is False


def test_a_failed_query_is_never_a_negative(monkeypatch):
    def boom(*a, **k):
        raise JPLSBIdentError("JPL did not answer within 30s")

    patch_identify(monkeypatch, boom)
    result = check_known_object(TRACK, times, control=CONTROL)
    assert result["known"] is None
    assert result["verified"] is False
    assert "could not be queried" in result["reason"]


def test_a_long_arc_is_sampled_rather_than_queried_at_every_epoch(monkeypatch):
    calls = []
    patch_identify(monkeypatch, lambda ra, *a, **k: calls.append(ra) or [])
    long_track = [
        {"jd": 2461293 + i, "ra": 9.0 - 0.1 * i, "dec": 48.6} for i in range(19)
    ]
    check_known_object(long_track, times, control=CONTROL)
    assert len(calls) <= 4, "ends and middle, plus the control"


def test_the_ends_and_middle_are_what_get_queried(monkeypatch):
    calls = []
    patch_identify(monkeypatch, lambda ra, *a, **k: calls.append(ra) or [])
    check_known_object(TRACK, times)
    assert calls == [d["ra"] for d in TRACK]


def test_a_control_from_the_same_night_is_what_we_ask_for():
    # The control's value is that it runs the same query the real one does:
    # same epoch, same observing code. A control from another month would test
    # the network and nothing else.
    from skyportal.broker_apis.boom import BOOMBROKER

    captured = {}

    class FakeBroker:
        id = 1
        altdata = {"survey": "ZTF"}

    def fake_request(broker, method, path, json=None, **kwargs):
        captured["filter"] = json["filter"]
        return [
            {
                "candidate": {
                    "jd": 2461293.9,
                    "ra": 10.0,
                    "dec": 48.0,
                    "ssnamenr": "187965",
                }
            }
        ]

    from skyportal.broker_apis import boom

    original = boom._request
    boom._request = fake_request
    try:
        control = BOOMBROKER.find_control_detection(
            FakeBroker(), 2461293.86664, None, survey="ZTF", permissions=None
        )
    finally:
        boom._request = original

    window = captured["filter"]["candidate.jd"]
    assert window["$gte"] < 2461293.86664 < window["$lte"]
    assert control["expect"] == "187965"


def test_a_night_with_no_known_object_yields_no_control():
    # Better to report unverified than to invent a control.
    from skyportal.broker_apis import boom
    from skyportal.broker_apis.boom import BOOMBROKER

    class FakeBroker:
        id = 1
        altdata = {"survey": "ZTF"}

    original = boom._request
    boom._request = lambda *a, **k: []
    try:
        assert (
            BOOMBROKER.find_control_detection(
                FakeBroker(), 2461293.86664, None, survey="ZTF", permissions=None
            )
            is None
        )
    finally:
        boom._request = original


# The two cases that fail in opposite directions, from real BOOM output.
# 2019 SS77 sits 91 arcsec outside its own prediction and IS the object; the
# neighbours of boom_thor_000002 are precisely where predicted and are NOT.
STALE_EPHEMERIS = [
    (
        2461300.81,
        [
            {
                "name": "2019 SS77",
                "offset_arcsec": 91.85,
                "ra_rate": -14.78,
                "dec_rate": -11.47,
            }
        ],
    ),
    (
        2461303.83,
        [
            {
                "name": "2019 SS77",
                "offset_arcsec": 91.46,
                "ra_rate": -14.78,
                "dec_rate": -11.47,
            }
        ],
    ),
]
MOVER = [
    {"jd": 2461300.81, "ra": 5.0, "dec": -4.0},
    {"jd": 2461303.83, "ra": 5.55, "dec": -4.20},
]


def test_a_known_object_outside_its_prediction_is_still_identified():
    # A fixed cone under ~250 arcsec calls this a discovery. It is 2019 SS77.
    from skyportal.utils.jpl_sbident import identify_across_arc

    verdict = identify_across_arc(STALE_EPHEMERIS, MOVER)[0]
    assert verdict["identified"] is True
    assert verdict["nearest_arcsec"] > 90, "far outside any radius we would pick"
    assert "held near" in verdict["reason"]


def test_a_neighbour_that_drifts_apart_is_not_our_object():
    from skyportal.utils.jpl_sbident import identify_across_arc

    drifting = [
        (2461300.81, [{"name": "508260", "offset_arcsec": 120.0}]),
        (2461303.83, [{"name": "508260", "offset_arcsec": 315.4}]),
    ]
    verdict = identify_across_arc(drifting, MOVER)[0]
    assert verdict["identified"] is False
    assert "drifted" in verdict["reason"]


def test_matching_motion_alone_does_not_identify():
    # Asteroids in one field move alike; a neighbour matched ours to
    # 0.2 arcsec/h. The offset test is what separates them.
    from skyportal.utils.jpl_sbident import _track_rates, identify_across_arc

    ra_rate, dec_rate = _track_rates(MOVER)
    same_motion_far_apart = [
        (
            2461300.81,
            [
                {
                    "name": "neighbour",
                    "offset_arcsec": 150.0,
                    "ra_rate": ra_rate,
                    "dec_rate": dec_rate,
                }
            ],
        ),
        (
            2461303.83,
            [
                {
                    "name": "neighbour",
                    "offset_arcsec": 400.0,
                    "ra_rate": ra_rate,
                    "dec_rate": dec_rate,
                }
            ],
        ),
    ]
    verdict = identify_across_arc(same_motion_far_apart, MOVER)[0]
    assert verdict["motion_agrees"] is True
    assert verdict["identified"] is False, "motion agreement must not override drift"


def test_something_right_where_predicted_is_identified_immediately():
    from skyportal.utils.jpl_sbident import identify_across_arc

    close = [(2461300.81, [{"name": "1 Ceres", "offset_arcsec": 3.7}])]
    assert identify_across_arc(close, MOVER)[0]["identified"] is True


def test_a_single_far_hit_is_not_identified_without_a_second_epoch():
    # One epoch says nothing about drift, so proximity is all there is.
    from skyportal.utils.jpl_sbident import identify_across_arc

    one = [(2461300.81, [{"name": "far thing", "offset_arcsec": 200.0}])]
    assert identify_across_arc(one, MOVER)[0]["identified"] is False


# Real SkyBoT hits for two BOOM tracks, captured 2026-09-25 at obs code I41.
# The trap: the two rejects have zero drift because they were seen once, so a
# bare flat-vs-drifting rule would identify them and reject the real recovery.
SS77_TRACK = [
    {"jd": 2461302.8795255, "ra": 5.0, "dec": -4.0},
    {"jd": 2461305.8795255, "ra": 5.0117, "dec": -4.0219},
]
SS77_HITS = [
    (
        2461302.8795255,
        [
            {
                "name": "2019 SS77",
                "offset_arcsec": 91.85,
                "ra_rate": -14.78,
                "dec_rate": -11.47,
            },
            {
                "name": "2003 TO7",
                "offset_arcsec": 261.9,
                "ra_rate": -30.72,
                "dec_rate": -2.87,
            },
        ],
    ),
    (
        2461304.3795255,
        [
            {
                "name": "2019 SS77",
                "offset_arcsec": 93.67,
                "ra_rate": -14.78,
                "dec_rate": -11.47,
            },
            {
                "name": "2001 YN104",
                "offset_arcsec": 273.6,
                "ra_rate": -22.93,
                "dec_rate": -18.19,
            },
        ],
    ),
    (
        2461305.8795255,
        [
            {
                "name": "2019 SS77",
                "offset_arcsec": 91.46,
                "ra_rate": -14.78,
                "dec_rate": -11.47,
            },
        ],
    ),
]


def verdicts_for(hits, track):
    from skyportal.utils.jpl_sbident import identify_across_arc

    return {v["name"]: v for v in identify_across_arc(hits, track)}


def test_the_real_recovery_is_identified():
    verdict = verdicts_for(SS77_HITS, SS77_TRACK)["2019 SS77"]
    assert verdict["identified"] is True
    assert verdict["epochs"] == 3
    # 2.2 arcsec of drift against 470 arcsec/day of motion is flat.
    assert verdict["offset_drift_arcsec"] < 5


def test_a_hit_seen_once_is_not_identified_by_its_zero_drift():
    # These have drift 0.0 only because there is nothing to drift against.
    # Without the two-epoch guard they would outrank the real recovery.
    for name in ("2003 TO7", "2001 YN104"):
        verdict = verdicts_for(SS77_HITS, SS77_TRACK)[name]
        assert verdict["epochs"] == 1
        assert verdict["offset_drift_arcsec"] == 0.0
        assert verdict["identified"] is False, f"{name} must not identify"


def test_the_crowded_field_finds_nothing():
    # boom_thor_000002: one precisely-known neighbour, seen once, 196 arcsec out.
    hits = [
        (
            2461300.8,
            [
                {
                    "name": "2001 QJ256",
                    "offset_arcsec": 196.5,
                    "ra_rate": -1.89,
                    "dec_rate": 8.12,
                }
            ],
        )
    ]
    track = [
        {"jd": 2461300.8, "ra": 5.0, "dec": -4.0},
        {"jd": 2461303.8, "ra": 5.003, "dec": -3.979},
    ]
    assert verdicts_for(hits, track)["2001 QJ256"]["identified"] is False


def test_the_drift_threshold_has_room_above_the_real_case():
    # Calibrated against 2.2 arcsec of real drift, not the 0.4 first quoted.
    from skyportal.utils.jpl_sbident import MAX_OFFSET_DRIFT_ARCSEC

    assert MAX_OFFSET_DRIFT_ARCSEC > 2.21 * 3


def test_the_cone_is_wide_enough_to_hold_the_recovery():
    # At 250 arcsec the middle epoch drops and the recovery looks like a
    # neighbour seen twice.
    from skyportal.utils.jpl_sbident import DEFAULT_HALF_WIDTH_DEG

    assert DEFAULT_HALF_WIDTH_DEG * 3600 >= 360


def test_a_single_epoch_reject_says_why_not_just_how_many():
    # This is the reason a scanner will see most often, so "epochs=1" is not
    # good enough: what matters is that it left the field.
    reason = verdicts_for(SS77_HITS, SS77_TRACK)["2003 TO7"]["reason"]
    assert "drifted out of the cone" in reason
    assert "262 arcsec" in reason
