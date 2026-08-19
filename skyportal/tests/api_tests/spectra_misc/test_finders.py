import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import api, client


@pytest.mark.xfail(strict=False)
def test_finder(upload_data_token, public_source):
    sp = client(upload_data_token)
    sp.update_source(public_source.id, ra=234.22, dec=-22.33)

    data = sp.fetch_source_finder(public_source.id, imsize=2)
    assert isinstance(data, bytes)
    assert data[0:10].find(b"PDF") != -1

    # try an image source we dont know about
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_source_finder(public_source.id, image_source="whoknows")
    assert err.value.status_code == 400

    # try an image too big
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_source_finder(public_source.id, imsize=30)
    assert err.value.status_code == 400


def test_finder_chart_facilities(upload_data_token):
    facilities = client(upload_data_token).fetch_finder_chart_facilities()
    assert "Keck" in facilities
    for params in facilities.values():
        assert params.mag_min is not None
        assert params.mag_limit is not None
        assert params.mag_min < params.mag_limit


def test_finder_rejects_invalid_parameters(upload_data_token, public_source):
    sp = client(upload_data_token)
    with pytest.raises(SkyPortalError, match="Invalid image source") as err:
        sp.fetch_source_finder(public_source.id, image_source="whoknows")
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_source_finder(public_source.id, imsize=30)
    assert err.value.status_code == 400
    assert "imsize" in str(err.value)
    assert "outside the allowed range" in str(err.value)


def test_finder_offset_star_mag_range(upload_data_token, public_source):
    # An inverted range (bright end fainter than the faint end) is rejected.
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token).fetch_source_finder(
            public_source.id, mag_min=18, mag_limit=12
        )
    assert err.value.status_code == 400
    assert "mag_min" in str(err.value)

    # Non-numeric magnitude bounds are rejected.
    # raw api: intentionally malformed query (non-numeric mag_min) the typed client can't produce
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"mag_min": "bright"},
        token=upload_data_token,
    )
    assert status == 400


@pytest.mark.xfail(strict=False)
def test_unsourced_finder(upload_data_token):
    sp = client(upload_data_token)
    # get a finder by gaia ID
    data = sp.fetch_unsourced_finding_chart(
        location_type="gaia_dr3",
        catalog_id="3905335598144227200",
        image_source="ps1",
        output_type="pdf",
        obstime="2012-02-28",
        use_ztfref=False,
    )
    assert isinstance(data, bytes)
    assert data[0:10].find(b"PDF") != -1

    # get a finder by position
    data = sp.fetch_unsourced_finding_chart(
        location_type="pos",
        ra=234.22,
        dec=-22.33,
        image_source="ps1",
        output_type="pdf",
        obstime="2020-02-28",
        use_ztfref=False,
    )
    assert isinstance(data, bytes)
    assert data[0:10].find(b"PDF") != -1

    # try a bad Gaia ID
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_unsourced_finding_chart(
            location_type="gaia_dr3",
            catalog_id="-1",
            image_source="ps1",
            output_type="pdf",
            obstime="2012-02-28",
            use_ztfref=False,
        )
    assert err.value.status_code == 400
