import pytest
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError

from skyportal.utils import get_nearby_offset_stars, get_finding_chart, get_ztfref_url

from skyportal.utils.offset import irsa


ztfref_url = irsa['url_search']
run_ztfref_test = True
try:
    r = requests.get(ztfref_url)
    r.raise_for_status()
except (HTTPError, TimeoutError, ConnectionError) as e:
    run_ztfref_test = False
    print(e)


@pytest.mark.skipif(not run_ztfref_test, reason='IRSA server down')
def test_get_ztfref_url():
    url = get_ztfref_url(123.0, 33.3, 2)

    assert isinstance(url, str)
    assert url.find("irsa") != -1


def test_get_nearby_offset_stars():
    how_many = 3
    rez = get_nearby_offset_stars(
        123.0, 33.3, "testSource", how_many=how_many, radius_degrees=3 / 60.0
    )

    assert len(rez) == 4
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


desi_url = (
    "http://legacysurvey.org/viewer/fits-cutout/"
    "?ra=123.0&dec=33.0&layer=dr8&pixscale=2.0&bands=r"
)

# check to see if the DESI server is up. If not, do not run test.
run_desi_test = True
try:
    r = requests.get(desi_url)
    r.raise_for_status()
except (HTTPError, Timeout, ConnectionError) as e:
    run_desi_test = False
    print(e)


@pytest.mark.skipif(not run_desi_test, reason="DESI server down")
def test_get_desi_finding_chart():

    rez = get_finding_chart(
        123.0, 33.3, "testSource", image_source='desi', output_format='pdf'
    )

    assert isinstance(rez, dict)
    assert rez["success"]
    assert rez["name"].find("testSource") != -1
    assert rez["data"].find(bytes("PDF", encoding='utf8')) != -1


# test for failure on a too-small image size
def test_get_finding_chart():
    rez = get_finding_chart(123.0, 33.3, "testSource", imsize=1.0, image_source='dss')
    assert not rez["success"]

    rez = get_finding_chart(123.0, 33.3, "testSource", image_source='zomg_telescope')
    assert isinstance(rez, dict)
    assert not rez["success"]
