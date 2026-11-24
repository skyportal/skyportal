import pytest
import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from skyportal.utils.offset import (
    get_finding_chart,
    get_nearby_offset_stars,
    get_ztfref_url,
)


def test_get_ztfref_url():
    url = get_ztfref_url(123.0, 33.3, 2)
    if url == "":
        pytest.skip("IRSA server down")

    assert isinstance(url, str)
    assert url.find("irsa") != -1


def test_get_nearby_offset_stars():
    how_many = 3
    rez = get_nearby_offset_stars(
        123.0, 33.3, "testSource", how_many=how_many, radius_degrees=3 / 60.0
    )
    # expecting 6 parameters:
    #   a list of the source+offset stars,
    #   What query was used against Gaia,
    #   number of queries_issued,
    #   number of offset stars
    #   whether ZTF ref was used for astrometry
    #   whether Gaia was reachable (proper motion could be applied)
    assert len(rez) == 6
    assert isinstance(rez[0], list)
    assert len(rez[0]) == how_many + 1

    with pytest.raises(Exception):
        rez = get_nearby_offset_stars(
            123.0,
            33.3,
            "testSource",
            how_many=how_many,
            radius_degrees=3 / 60.0,
            allowed_queries=1,
            queries_issued=2,
        )


DESI_URL = (
    "http://legacysurvey.org/viewer/fits-cutout/"
    "?ra=123.0&dec=33.0&layer=dr8&pixscale=2.0&bands=r"
)


def test_get_desi_finding_chart():
    try:
        requests.get(DESI_URL, timeout=10).raise_for_status()
    except (HTTPError, Timeout, ConnectionError):
        pytest.skip("DESI server down")

    rez = get_finding_chart(
        123.0, 33.3, "testSource", image_source="desi", output_format="pdf"
    )

    assert isinstance(rez, dict)
    assert rez["success"]
    assert rez["name"].find("testSource") != -1
    assert rez["data"].find(bytes("PDF", encoding="utf8")) != -1
