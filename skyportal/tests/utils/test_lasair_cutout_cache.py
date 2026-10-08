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
    assert not lasair.carries_lightcurve(plain)

    with pytest.raises(ValueError, match="lite lightcurve"):
        asyncio.run(lasair._ingest_object(None, "ZTF26aaa", "ZTF", [1], payload=plain))


def test_polling_still_fetches_the_object():
    # Polling learns an objectId and nothing else, so there the REST call is the
    # only way to get the photometry and must not be refused.
    import asyncio

    called = []

    async def fake_save(*a, **k):
        return None

    orig = lasair._object
    lasair._object = lambda b, oid, token=None: called.append(oid) or {}
    try:
        asyncio.run(lasair._ingest_object(None, "ZTF26aaa", "ZTF", [1], payload=None))
    except Exception:
        pass  # the DB write is not under test; the fetch having happened is
    finally:
        lasair._object = orig
    assert called == ["ZTF26aaa"], "polling no longer fetches the object"
