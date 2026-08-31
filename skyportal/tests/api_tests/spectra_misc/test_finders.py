from skyportal.tests import api


def test_finder_chart_facilities(upload_data_token):
    status, data = api(
        "GET",
        "finder_chart/facilities",
        token=upload_data_token,
    )
    assert status == 200
    facilities = data["data"]
    assert "Keck" in facilities
    for params in facilities.values():
        assert "mag_min" in params
        assert "mag_limit" in params
        assert params["mag_min"] < params["mag_limit"]


def test_finder_rejects_invalid_parameters(upload_data_token, public_source):
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"image_source": "whoknows"},
        token=upload_data_token,
    )
    assert status == 400
    assert "image_source: Input should be" in data["message"]

    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"imsize": "30"},
        token=upload_data_token,
    )
    assert status == 400
    assert "imsize" in data["message"]
    assert "outside the allowed range" in data["message"]


def test_finder_offset_star_mag_range(upload_data_token, public_source):
    # An inverted range (bright end fainter than the faint end) is rejected.
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"mag_min": "18", "mag_limit": "12"},
        token=upload_data_token,
    )
    assert status == 400
    assert "mag_min" in data["message"]

    # Non-numeric magnitude bounds are rejected.
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"mag_min": "bright"},
        token=upload_data_token,
    )
    assert status == 400
