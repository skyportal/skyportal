from skyportal.utils.gcn import (
    from_igwn_gwalert,
    get_json_tags,
    properties_tags_from_meta,
)


def test_get_json_tags():
    assert get_json_tags({"instrument": "WXT"}) == ["Einstein Probe"]
    assert get_json_tags({"instrument": "BAT-GUANO"}) == ["GUANO"]
    assert get_json_tags({"instrument": "ZTF"}) == []
    assert get_json_tags({}) == []


def test_get_json_tags_igwn_gwalert():
    payload = {
        "superevent_id": "S260101a",
        "alert_type": "PRELIMINARY",
        "event": {
            "significant": True,
            "search": "AllSky",
            "instruments": ["H1", "L1"],
            "pipeline": "gstlal",
            "classification": {"BNS": 0.9, "BBH": 0.05, "Terrestrial": 0.05},
        },
    }
    tags = get_json_tags(payload)
    for expected in ("GW", "BNS", "AllSky", "H1", "L1", "MultiInstrument", "gstlal"):
        assert expected in tags
    assert "Significant" in tags

    # a retraction is just GW + retracted
    assert get_json_tags({"superevent_id": "S260101a", "alert_type": "RETRACTION"}) == [
        "GW",
        "retracted",
    ]


def test_from_igwn_gwalert_normalization():
    payload = {
        "superevent_id": "S260101a",
        "alert_type": "PRELIMINARY",
        "event": {
            "time": "2026-01-01T00:00:00.5Z",
            "far": 1e-9,
            "skymap": "ZmFrZQ==",
            "classification": {"BNS": 0.9},
            "properties": {"HasNS": 1.0},
        },
    }
    out = from_igwn_gwalert(payload)
    assert out["notice_type"] == "LVC_PRELIMINARY"
    assert out["aliases"] == ["LVC#S260101a"]
    assert out["ref_ID"] == "S260101a"
    assert out["trigger_time"] == "2026-01-01T00:00:00.5"
    assert out["healpix_file"].startswith("name=S260101a-PRELIMINARY")
    assert out["properties"]["FAR"] == 1e-9
    assert out["properties"]["BNS"] == 0.9 and out["properties"]["HasNS"] == 1.0

    # retraction: no trigger_time/skymap, flagged for is_retraction
    retr = from_igwn_gwalert({"superevent_id": "S260101a", "alert_type": "RETRACTION"})
    assert retr["notice_type"] == "LVC_RETRACTION"
    assert retr["retraction"] is True
    assert "trigger_time" not in retr and "healpix_file" not in retr


def test_properties_tags_from_meta_near_distance():
    props, tags = properties_tags_from_meta(
        {"log_bci": 1.0, "distmean": 100, "diststd": 20, "ignored": 5}
    )
    assert props == {"log_bci": 1.0, "distmean": 100, "diststd": 20}
    assert tags == ["< 150 Mpc", "< 250 Mpc"]


def test_properties_tags_from_meta_mid_distance():
    props, tags = properties_tags_from_meta({"distmean": 200})
    assert props == {"distmean": 200}
    assert tags == ["< 250 Mpc"]


def test_properties_tags_from_meta_far_and_missing():
    assert properties_tags_from_meta({"distmean": 300}) == ({"distmean": 300}, [])
    assert properties_tags_from_meta({}) == ({}, [])
    # no distmean -> no distance tags even if other properties are present
    assert properties_tags_from_meta({"log_bsn": 2.0}) == ({"log_bsn": 2.0}, [])
