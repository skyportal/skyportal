"""GCN FRB notices (gcn.notices.<mission>.frb) from CHIME and DSA-110."""

from skyportal.utils.gcn import (
    error_radius,
    get_frb_mission,
    get_json_aliases,
    get_json_dateobs,
    get_json_properties,
    get_json_tags,
    get_json_trigger_id,
    get_skymap_cone,
    get_skymap_metadata,
    is_retraction,
)

# Fields as the upstream gcn-schema detection example carries them.
DSA_DETECTION = {
    "notice_type": "dsa110.frb",
    "alert_type": "initial",
    "trigger_time": "2024-09-18T07:19:10.765268Z",
    "id": "240918aaaa",
    "snr": 12.698559761047363,
    "dm": 279.422607421875,
    "event_duration": 1,
    "ra": 346.77850859547,
    "dec": 12.632485229956252,
    "ra_dec_error": [0.016, 0.02],
    "importance": 0.9871308604784662,
}


def test_mission_comes_from_the_topic():
    # The notices carry no mission field, so the topic is the only source.
    assert get_frb_mission(DSA_DETECTION) == "DSA-110"
    assert get_frb_mission({"notice_type": "chime.frb"}) == "CHIME"
    assert get_frb_mission({"notice_type": "einstein_probe.wxt.alert"}) is None
    assert get_frb_mission({}) is None


def test_tags():
    assert get_json_tags(DSA_DETECTION) == ["FRB", "Radio", "DSA-110"]
    assert get_json_tags({"notice_type": "chime.frb"}) == ["FRB", "Radio", "CHIME"]
    assert get_json_tags({"notice_type": "chime.frb", "alert_type": "retraction"}) == [
        "FRB",
        "Radio",
        "CHIME",
        "retracted",
    ]
    # Streams that are not FRB notices keep the tags they had.
    assert get_json_tags({"instrument": "WXT"}) == ["Einstein Probe", "X-ray"]


def test_trigger_id_and_alias():
    assert get_json_trigger_id(DSA_DETECTION) == "240918aaaa"
    assert get_json_aliases(DSA_DETECTION) == ["DSA-110#240918aaaa"]
    assert get_json_aliases({"notice_type": "chime.frb", "id": 1178986771}) == [
        "CHIME#1178986771"
    ]
    assert get_json_aliases({"notice_type": "chime.frb"}) == []
    # The Einstein Probe prefix is unchanged.
    assert get_json_aliases({"instrument": "WXT", "id": ["01709319528"]}) == [
        "EP#01709319528"
    ]


def test_retraction_is_announced_by_alert_type():
    assert is_retraction({"notice_type": "chime.frb", "alert_type": "retraction"})
    assert is_retraction({"alert_type": "RETRACTION"})
    assert not is_retraction(DSA_DETECTION)
    # The older JSON convention still holds.
    assert is_retraction({"retraction": 1})


def test_error_radius_takes_the_semi_major_axis():
    assert error_radius(0.5) == 0.5
    assert error_radius([0.016, 0.012, 87.0]) == 0.016
    assert error_radius([]) is None
    assert error_radius(None) is None


def test_cone_from_an_elliptical_localization():
    # FRB notices give ra_dec_error as an ellipse; a cone needs one radius.
    ra, dec, error = get_skymap_cone(DSA_DETECTION)
    assert (ra, dec) == (346.77850859547, 12.632485229956252)
    assert error == 0.016
    assert get_skymap_metadata(DSA_DETECTION, "dsa110.frb")[0] == "cone"


def test_a_notice_without_a_position_has_no_cone():
    update = {
        "notice_type": "dsa110.frb",
        "alert_type": "update",
        "id": "240918aaaa",
        "trigger_time": "2024-09-18T07:19:10.765268Z",
    }
    assert get_skymap_cone(update) == (None, None, None)
    assert get_skymap_metadata(update, "dsa110.frb")[0] == "missing"
    assert (
        get_skymap_metadata({**update, "alert_type": "retraction"}, "dsa110.frb")[0]
        == "retraction"
    )


def test_properties_carry_the_observables():
    assert get_json_properties(DSA_DETECTION) == {
        "dm": 279.422607421875,
        "snr": 12.698559761047363,
        "importance": 0.9871308604784662,
        "event_duration": 1,
    }
    # A notice with nothing measured stores no properties.
    assert get_json_properties({"notice_type": "dsa110.frb", "id": "x"}) is None
    # A payload that brings its own properties keeps them.
    assert get_json_properties(
        {"notice_type": "dsa110.frb", "dm": 1.0, "properties": {"far": 0.1}}
    ) == {"far": 0.1}
    assert get_json_properties({"instrument": "WXT"}) is None


def test_dateobs_accepts_both_timestamp_forms():
    # CHIME sends a bare timestamp, DSA-110's examples end in Z.
    assert str(get_json_dateobs({"trigger_time": "2026-09-29T17:01:44.388687"})) == (
        "2026-09-29 17:01:44"
    )
    assert str(get_json_dateobs(DSA_DETECTION)) == "2024-09-18 07:19:11"
    assert get_json_dateobs({}) is None
