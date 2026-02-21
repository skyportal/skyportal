from skyportal.tests import api


def test_standards(view_only_token):
    status, data = api(
        "GET",
        "internal/standards",
        params={
            "facility": "Keck",
            "standard_type": "ESO",
            "dec_filter_range_str": None,
            "ra_filter_range_str": None,
            "show_first_line": True,
        },
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"]["starlist_info"], list)
    assert len(data["data"]["starlist_info"]) > 0
    # make sure we've got an HD source in here
    assert any(x["str"].find("HD") != -1 for x in data["data"]["starlist_info"])


def test_standards_bad_standard_list(view_only_token):
    status, data = api(
        "GET",
        "internal/standards",
        params={
            "facility": "Keck",
            "standard_type": "SpaceX",
            "dec_filter_range": None,
            "ra_filter_range": None,
            "show_first_line": True,
        },
        token=view_only_token,
    )
    assert status == 400
    assert data["message"].find("Invalid") != -1


def test_standards_bad_range(view_only_token):
    status, data = api(
        "GET",
        "internal/standards",
        params={
            "facility": "Keck",
            "standard_type": "ESO",
            "dec_filter_range": None,
            "ra_filter_range": "(-45, 60)",
            "show_first_line": True,
        },
        token=view_only_token,
    )
    assert status == 400
    assert data["message"].find("Elements out of range") != -1

    status, data = api(
        "GET",
        "internal/standards",
        params={
            "facility": "Keck",
            "standard_type": "ESO",
            "dec_filter_range": "(10, 100)",
            "ra_filter_range": None,
            "show_first_line": True,
        },
        token=view_only_token,
    )
    assert status == 400
    assert data["message"].find("Elements out of range") != -1


def test_standards_filter(view_only_token):
    status, data = api(
        "GET",
        "internal/standards",
        params={
            "facility": "Keck",
            "standard_type": "ESO",
            "dec_filter_range": None,
            "ra_filter_range": None,
            "show_first_line": True,
        },
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    full_list = data["data"]["starlist_info"]

    status, data = api(
        "GET",
        "internal/standards",
        params={
            "facility": "Keck",
            "standard_type": "ESO",
            "dec_filter_range": "(-90, 0)",
            "ra_filter_range": "(0, 60)",
            "show_first_line": True,
        },
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    filter_list = data["data"]["starlist_info"]

    assert len(filter_list) < len(full_list)
