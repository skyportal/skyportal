"""Lasair serves an object's cutouts once; a repeat costs no API call."""

import tempfile

import pytest

from skyportal.broker_apis import lasair


class _Broker:
    id = 7


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch):
    # A cache of its own, so a run neither reads nor leaves real entries.
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setattr(
            lasair, "cutouts_cache", lasair.Cache(cache_dir=d, max_age=3600)
        )
        yield


def _obj(oid="ZTF26aaa"):
    return {"objectId": oid, "candidates": [{"image_urls": {"Science": "http://x/s"}}]}


def test_the_images_are_fetched_once(monkeypatch):
    calls = []

    def fake(obj, alert_id):
        calls.append(alert_id)
        return {"cutoutScience": "YmFzZTY0"}

    monkeypatch.setattr(lasair, "_cutouts_from_object", fake)

    first = lasair._cached_cutouts(_Broker(), _obj(), "ZTF26aaa")
    second = lasair._cached_cutouts(_Broker(), _obj(), "ZTF26aaa")

    assert first == second == {"cutoutScience": "YmFzZTY0"}
    assert calls == ["ZTF26aaa"], "the second call refetched the images"


def test_a_repeat_does_not_fetch_the_object(monkeypatch):
    # The object call is the one Lasair rate-limits, so the cached path must
    # answer before _object is reached.
    monkeypatch.setattr(
        lasair, "_cutouts_from_object", lambda obj, aid: {"cutoutScience": "YmFzZTY0"}
    )
    fetched = []
    monkeypatch.setattr(
        lasair, "_object", lambda b, aid, token=None: fetched.append(aid) or _obj(aid)
    )

    lasair.LASAIRBROKER.get_cutouts(_Broker(), "ZTF26aaa", None)
    assert fetched == ["ZTF26aaa"]
    lasair.LASAIRBROKER.get_cutouts(_Broker(), "ZTF26aaa", None)
    assert fetched == ["ZTF26aaa"], "the repeat called the Lasair object API again"


def test_a_different_object_is_still_fetched(monkeypatch):
    calls = []
    monkeypatch.setattr(
        lasair,
        "_cutouts_from_object",
        lambda obj, aid: calls.append(aid) or {"cutoutScience": "YmFzZTY0"},
    )
    lasair._cached_cutouts(_Broker(), _obj("A"), "A")
    lasair._cached_cutouts(_Broker(), _obj("B"), "B")
    assert calls == ["A", "B"]


def test_an_empty_result_is_not_cached(monkeypatch):
    # Nothing fetched means nothing to remember; a later attempt must retry.
    calls = []
    monkeypatch.setattr(
        lasair, "_cutouts_from_object", lambda obj, aid: calls.append(aid) or {}
    )
    lasair._cached_cutouts(_Broker(), _obj(), "ZTF26aaa")
    lasair._cached_cutouts(_Broker(), _obj(), "ZTF26aaa")
    assert calls == ["ZTF26aaa", "ZTF26aaa"]


def test_a_plain_kafka_message_is_refused_not_completed_by_an_api_call():
    # Lasair's plain stream carries the filter's selected columns only. Fetching
    # the rest would cost a call per alert, at whatever rate the filter fires,
    # so the message is refused and the error names the setting that fixes it.
    import asyncio

    plain = {"objectId": "ZTF26aaa", "ramean": 1.0, "decmean": 2.0, "gmag": 20.1}
    assert lasair.is_plain_stream_message(plain)

    with pytest.raises(ValueError, match="lite lightcurve"):
        asyncio.run(lasair._ingest_object(None, "ZTF26aaa", "ZTF", [1], payload=plain))


def test_an_empty_lightcurve_is_not_blamed_on_the_stream_setting():
    # The setting is wrong only when the alert is absent. One present but quiet
    # is an ordinary object, and must not send the user to change a correct
    # setting.
    assert not lasair.is_plain_stream_message({"alert": {"diaSourcesList": []}})
    assert not lasair.is_plain_stream_message(
        {"objectId": "ZTF26aaa", "candidates": []}
    )


def _real_alerts():
    # Two messages off a live Lasair LSST topic, supplied by Lasair, with the
    # non-finite floats nulled so they are valid JSON. One arrived without its
    # alert, which is what the selected-columns stream looks like.
    import json
    import pathlib

    path = pathlib.Path(__file__).parents[1] / "data" / "lasair_lsst_stream_alerts.json"
    return json.loads(path.read_text())


def test_a_real_lsst_alert_normalizes_to_photometry_we_can_save():
    plain, full = _real_alerts()

    assert lasair.is_plain_stream_message(plain)
    assert not lasair.is_plain_stream_message(full)

    oid = lasair._object_id_from_message(full)
    normalized = lasair._normalize_object(full, oid)
    candidate = normalized["candidate"]
    # Without any one of these the row saves as a detection with no epoch, no
    # band or no position.
    for key in ("candid", "ra", "dec", "jd", "band", "magpsf"):
        assert candidate.get(key) is not None, f"{key} did not survive normalization"
    assert normalized["prv_candidates"], "the lightcurve did not survive"
    assert all(r["jd"] and r["band"] for r in normalized["prv_candidates"])
