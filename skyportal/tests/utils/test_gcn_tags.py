from skyportal.utils.gcn import get_json_tags, properties_tags_from_meta


def test_get_json_tags():
    assert get_json_tags({"instrument": "WXT"}) == ["Einstein Probe"]
    assert get_json_tags({"instrument": "BAT-GUANO"}) == ["GUANO"]
    assert get_json_tags({"instrument": "ZTF"}) == []
    assert get_json_tags({}) == []


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
