"""Previewing a filter against BOOM.

A preview is the only thing that tells an author whether their cuts pass
anything, so the ways it can silently mislead them matter more than usual.
"""

import json

from skyportal.broker_apis import boom


class _Broker:
    name = "BOOM"
    altdata = {"survey": "ZTF"}


def _capture(monkeypatch):
    """Record the windows BOOM is asked for, and answer each with a count."""
    seen = []

    def fake_request(broker, method, path, json=None, timeout=None):
        seen.append((path, json.get("start_jd"), json.get("end_jd")))
        return {"count": 10, "pipeline": json["pipeline"]}

    monkeypatch.setattr(boom, "_request", fake_request)
    return seen


def test_a_long_window_is_counted_in_slices(monkeypatch):
    # BOOM caps a test at MAX_TEST_WINDOW_DAYS and rejects anything wider with
    # a bare 400, which reads to the author as a filter that cannot preview
    # rather than a window that is too long. The sorted path already sliced;
    # the count did not.
    seen = _capture(monkeypatch)
    result = boom.BOOMBROKER.test_filter(
        _Broker(),
        None,
        survey="ZTF",
        pipeline=[{"$match": {"candidate.drb": {"$gt": 0.5}}}],
        start_jd=2461300.0,
        end_jd=2461316.0,
        permissions={"ZTF": [1]},
    )
    assert len(seen) == 3, seen
    assert all(end - start <= boom.MAX_TEST_WINDOW_DAYS for _, start, end in seen)
    # The slices cover the whole span, and their counts add up.
    assert seen[0][1] == 2461300.0 and seen[-1][2] == 2461316.0
    assert result["count"] == 30


def test_a_short_window_is_one_request(monkeypatch):
    seen = _capture(monkeypatch)
    result = boom.BOOMBROKER.test_filter(
        _Broker(),
        None,
        survey="ZTF",
        pipeline=[{"$match": {}}],
        start_jd=2461307.0,
        end_jd=2461308.0,
        permissions={"ZTF": [1]},
    )
    assert len(seen) == 1
    assert result["count"] == 10


def test_the_slices_leave_no_gap(monkeypatch):
    # A gap would undercount, which is worse than an error: the author tunes a
    # threshold against a number that is quietly too small.
    seen = _capture(monkeypatch)
    boom.BOOMBROKER.test_filter(
        _Broker(),
        None,
        survey="ZTF",
        pipeline=[{"$match": {}}],
        start_jd=2461300.0,
        end_jd=2461320.0,
        permissions={"ZTF": [1]},
    )
    for (_, _, end), (_, start, _) in zip(seen, seen[1:]):
        assert start == end
