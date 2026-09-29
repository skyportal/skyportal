"""Translating a source and its photometry into what TROVE accepts.

The risk here is quiet: TROVE upserts on the target name and stores whatever it
is given, so a wrong magnitude or a mislabelled filter lands in their database
rather than coming back as an error.
"""

import pytest
import requests

from skyportal.utils.trove_submission import (
    MJD_TO_JD,
    TroveSubmissionError,
    photometry_point,
    post_targets,
    source_label,
    target_payload,
)

DETECTION = {
    "mjd": 60000.5,
    "mag": 19.71,
    "magerr": 0.08,
    "limiting_mag": 20.5,
    "filter": "ztfr",
    "instrument_id": 1,
    "instrument_name": "ZTF",
}
NON_DETECTION = {
    "mjd": 60001.5,
    "mag": None,
    "magerr": None,
    "limiting_mag": 20.3,
    "filter": "ztfg",
    "instrument_id": 1,
    "instrument_name": "ZTF",
}


def test_a_detection_carries_its_magnitude_and_error():
    row = photometry_point(DETECTION)
    assert row["magnitude"] == 19.71
    assert row["error"] == 0.08
    assert "limit" not in row


def test_a_non_detection_carries_a_limit_and_no_magnitude():
    # Sending the limiting magnitude as a magnitude would draw an upper limit
    # on the light curve as though something had been measured.
    row = photometry_point(NON_DETECTION)
    assert row["limit"] == 20.3
    assert "magnitude" not in row
    assert "error" not in row


def test_a_detection_does_not_also_send_its_limit():
    # The point carries limiting_mag too; only one of the two is meaningful.
    assert "limit" not in photometry_point(DETECTION)


def test_mjd_becomes_jd():
    assert photometry_point(DETECTION)["jd"] == 60000.5 + MJD_TO_JD


def test_the_source_label_joins_the_facility_to_the_instrument():
    assert source_label("P48", "ZTF") == "P48-ZTF"


def test_a_source_label_without_a_facility_is_just_the_instrument():
    # Telescope nickname is non-null in the model, but an unresolved lookup
    # must not produce a leading separator.
    assert source_label(None, "ZTF") == "ZTF"
    assert source_label("  ", "ZTF") == "ZTF"


def test_the_resolved_label_travels_as_telescope():
    row = photometry_point(DETECTION, source_labels={1: "P48-ZTF"})
    assert row["telescope"] == "P48-ZTF"


def test_an_unresolved_instrument_falls_back_to_its_name():
    # Serialized photometry names no telescope, so a missing lookup still has
    # to say something truthful about where the point came from.
    assert photometry_point(DETECTION)["telescope"] == "ZTF"
    assert photometry_point(DETECTION, source_labels={99: "P48-ZTF"})["telescope"] == (
        "ZTF"
    )


def test_the_filter_goes_over_verbatim_by_default():
    # SkyPortal's filters are already sncosmo bandpass names.
    assert photometry_point(DETECTION)["filter"] == "ztfr"


def test_a_filter_map_renames_what_it_covers_and_nothing_else():
    assert photometry_point(DETECTION, {"ztfr": "r"})["filter"] == "r"
    assert photometry_point(DETECTION, {"sdssu": "u"})["filter"] == "ztfr"


def test_a_point_with_neither_a_magnitude_nor_a_limit_is_dropped():
    empty = {"mjd": 60000.5, "mag": None, "limiting_mag": None, "filter": "ztfr"}
    assert photometry_point(empty) is None


def test_a_point_with_no_time_is_dropped():
    assert photometry_point({"mag": 19.0, "filter": "ztfr"}) is None


def test_permissions_are_always_public():
    payload = target_payload("ZTF26abc", 10.0, -20.0)
    assert payload["permissions"] == "PUBLIC"
    assert payload["type"] == "SIDEREAL"
    assert payload["epoch"] == 2000


def test_every_kind_of_photometry_is_sent():
    # Forced photometry and low-significance points are not filtered out here;
    # what to include is the caller's choice.
    payload = target_payload("ZTF26abc", 10.0, -20.0, [DETECTION, NON_DETECTION])
    assert len(payload["photometry"]) == 2


def test_a_target_with_no_usable_photometry_omits_the_key():
    # TROVE treats a missing key as "target only"; an empty list is noise.
    payload = target_payload("ZTF26abc", 10.0, -20.0, [{"mjd": None}])
    assert "photometry" not in payload


def test_a_source_without_a_position_is_refused():
    with pytest.raises(TroveSubmissionError, match="no position"):
        target_payload("ZTF26abc", None, -20.0)


def test_the_endpoint_is_built_from_the_base_url(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["auth"] = kwargs.get("auth")
        captured["json"] = kwargs.get("json")
        return type(
            "R", (), {"status_code": 200, "json": lambda self: {"ok": 1}, "text": "{}"}
        )()

    monkeypatch.setattr(requests, "post", fake_post)
    post_targets(
        "https://trove.example/",
        "user",
        "pass",
        [target_payload("ZTF26abc", 10.0, -20.0)],
    )
    assert captured["url"] == "https://trove.example/api/target/upload"
    assert captured["auth"] == ("user", "pass")
    # The endpoint takes a list even for a single target.
    assert isinstance(captured["json"], list)


def test_missing_credentials_are_refused_before_the_request(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("must not reach the network")

    monkeypatch.setattr(requests, "post", explode)
    with pytest.raises(TroveSubmissionError, match="credentials"):
        post_targets("https://trove.example", "", "", [{"name": "x"}])


def test_an_error_response_carries_troves_reason(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, **k: type("R", (), {"status_code": 422, "text": "bad filter"})(),
    )
    with pytest.raises(TroveSubmissionError, match="422.*bad filter"):
        post_targets("https://trove.example", "u", "p", [{"name": "x"}])


def test_nothing_to_send_is_refused():
    with pytest.raises(TroveSubmissionError, match="nothing to send"):
        post_targets("https://trove.example", "u", "p", [])
