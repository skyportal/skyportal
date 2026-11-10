"""Lasair objects are read from BOOM, never fetched from Lasair one by one."""

import types

import pytest

from skyportal.broker_apis import lasair


def test_cutouts_come_from_boom_not_lasair(monkeypatch):
    class Source:
        name = "BOOM"

        class broker_class:
            @staticmethod
            def get_alert(broker, object_id, session, **kwargs):
                assert kwargs["permissions"] == lasair.PUBLIC_PERMISSIONS
                return {"objectId": object_id, "candid": 42, "candidate": {}}

            @staticmethod
            def get_cutouts(broker, candid, session, **kwargs):
                return {"cutoutScience": f"c{candid}"}

    monkeypatch.setattr(lasair, "_alerts_broker", lambda survey: Source())
    monkeypatch.setattr(
        lasair, "_request", lambda *a, **k: pytest.fail("called Lasair")
    )
    broker = types.SimpleNamespace(altdata={"survey": "ZTF"})
    cutouts = lasair.LASAIRBROKER.get_cutouts(broker, "ZTF26aaa", None)
    assert cutouts == {"cutoutScience": "c42"}


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
