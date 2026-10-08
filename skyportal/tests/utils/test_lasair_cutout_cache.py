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
