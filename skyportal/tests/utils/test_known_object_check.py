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
    patch_identify(monkeypatch, lambda *a, **k: [{"name": "2026 AB", "offset": 3.7}])
    result = check_known_object(TRACK, times, control=CONTROL)
    assert result["known"] is True
    assert result["verified"] is True


def test_a_match_needs_no_control(monkeypatch):
    # JPL naming something at that position is self-verifying.
    patch_identify(monkeypatch, lambda *a, **k: [{"name": "2026 AB"}])
    assert check_known_object(TRACK, times)["verified"] is True


def test_a_clean_negative_needs_the_control_to_pass(monkeypatch):
    calls = []

    def behaviour(ra, dec, *a, **k):
        calls.append(ra)
        return [{"name": "1 Ceres"}] if ra == CONTROL["ra"] else []

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
        lambda ra, *a, **k: [] if ra != CONTROL["ra"] else [{"name": "99 Other"}],
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
