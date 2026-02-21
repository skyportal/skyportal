import pytest

from skyportal.tests import api


@pytest.mark.xfail(strict=False)
def test_finder(upload_data_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={"ra": 234.22, "dec": -22.33},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    response = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"imsize": "2"},
        token=upload_data_token,
        raw_response=True,
    )
    status = response.status_code
    data = response.text
    assert status == 200
    assert isinstance(data, str)
    assert data[0:10].find("PDF") != -1
    assert response.headers.get("Content-Type", "Empty").find("application/pdf") != -1

    # try an image source we dont know about
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"image_source": "whoknows"},
        token=upload_data_token,
    )
    assert status == 400

    # try an image too big
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"imsize": "30"},
        token=upload_data_token,
    )
    assert status == 400


@pytest.mark.xfail(strict=False)
def test_unsourced_finder(upload_data_token):
    # get a finder by gaia ID
    response = api(
        "GET",
        "unsourced_finder",
        params={
            "catalog_id": "3905335598144227200",
            "location_type": "gaia_dr3",
            "image_source": "ps1",
            "output_type": "pdf",
            "obstime": "2012-02-28",
            "use_ztfref": False,
        },
        token=upload_data_token,
        raw_response=True,
    )
    status = response.status_code
    data = response.text
    assert status == 200
    assert isinstance(data, str)
    assert data[0:10].find("PDF") != -1
    assert response.headers.get("Content-Type", "Empty").find("application/pdf") != -1

    # get a finder by position
    response = api(
        "GET",
        "unsourced_finder",
        params={
            "location_type": "pos",
            "ra": 234.22,
            "dec": -22.33,
            "image_source": "ps1",
            "output_type": "pdf",
            "obstime": "2020-02-28",
            "use_ztfref": False,
        },
        token=upload_data_token,
        raw_response=True,
    )
    status = response.status_code
    data = response.text
    assert status == 200
    assert isinstance(data, str)
    assert data[0:10].find("PDF") != -1
    assert response.headers.get("Content-Type", "Empty").find("application/pdf") != -1

    # try a bad Gaia ID
    response = api(
        "GET",
        "unsourced_finder",
        params={
            "catalog_id": "-1",
            "location_type": "gaia_dr3",
            "image_source": "ps1",
            "output_type": "pdf",
            "obstime": "2012-02-28",
            "use_ztfref": False,
        },
        token=upload_data_token,
        raw_response=True,
    )
    assert response.status_code == 400
