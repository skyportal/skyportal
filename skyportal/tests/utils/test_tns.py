import types

import pytest
from bs4 import BeautifulSoup

from skyportal.utils.tns import (
    SURVEYS,
    get_objects_from_soup,
    get_tns_headers,
    get_tns_object_id_and_data_source_id,
    get_tns_url,
)


def _phot(filter_name):
    # get_tns_object_id_and_data_source_id only reads `.filter` off photometry
    return types.SimpleNamespace(filter=filter_name)


def test_object_id_ztf_and_decam_passthrough():
    # ZTF/DECAM ids are returned unchanged with their discovery source id
    obj, src = get_tns_object_id_and_data_source_id("ZTF21aaaaaaa", [])
    assert obj == "ZTF21aaaaaaa"
    assert src == SURVEYS["ZTF"]["discovery_data_source_id"]

    decam_id = "A201234561234567p123456"
    obj, src = get_tns_object_id_and_data_source_id(decam_id, [])
    assert obj == decam_id
    assert src == SURVEYS["DECAM"]["discovery_data_source_id"]


def test_object_id_lsst_variants_normalize():
    lsst_src = SURVEYS["LSST"]["discovery_data_source_id"]
    for variant in (
        "LSST-P-DO-12345",
        "LSST12345",
        "LSST_12345",
        "LSST-12345",
        "lsst-p-do-12345",  # case-insensitive
        "diaObject12345",
        "diaObject_12345",
    ):
        obj, src = get_tns_object_id_and_data_source_id(variant, [])
        assert obj == "LSST-P-DO-12345", variant
        assert src == lsst_src, variant


def test_object_id_raw_diaobjectid_uses_photometry_filters():
    lsst_src = SURVEYS["LSST"]["discovery_data_source_id"]

    # raw digits + an LSST-band photometry point -> treated as LSST
    obj, src = get_tns_object_id_and_data_source_id("12345", [_phot("lsstg")])
    assert obj == "LSST-P-DO-12345"
    assert src == lsst_src

    # raw digits without any LSST-band photometry -> unrecognized
    assert get_tns_object_id_and_data_source_id("12345", [_phot("ztfg")]) == (
        None,
        None,
    )
    assert get_tns_object_id_and_data_source_id("12345", []) == (None, None)


def test_object_id_unrecognized():
    assert get_tns_object_id_and_data_source_id("not-an-id", []) == (None, None)


def test_get_tns_headers():
    headers = get_tns_headers(42, "mybot")
    assert headers == {
        "User-Agent": 'tns_marker{"tns_id":42,"type":"bot", "name":"mybot"}'
    }


def test_get_tns_url(monkeypatch):
    monkeypatch.setattr("skyportal.utils.tns.TNS_URL", "https://sandbox.wis-tns.org/")
    assert get_tns_url("search") == "https://sandbox.wis-tns.org/api/get/search"
    assert get_tns_url("object") == "https://sandbox.wis-tns.org/api/get/object"

    with pytest.raises(ValueError, match="Invalid TNS URL type"):
        get_tns_url("not-a-real-type")

    monkeypatch.setattr("skyportal.utils.tns.TNS_URL", None)
    with pytest.raises(ValueError, match="TNS URL is not configured"):
        get_tns_url("search")


RESULTS_HTML = """
<table class="results-table"><tbody>
  <tr class="row-odd public odd">
    <td class="cell-name"><a href="/object/2024abc">2024abc</a></td>
    <td class="cell-ra">12:34:56.78</td>
    <td class="cell-decl">+12:34:56.7</td>
  </tr>
  <tr class="row-even private even">
    <td class="cell-name"><a href="/object/secret">SECRET</a></td>
    <td class="cell-ra">00:00:00.0</td>
    <td class="cell-decl">-00:00:00.0</td>
  </tr>
</tbody></table>
"""


def test_get_objects_from_soup_parses_public_rows_only():
    soup = BeautifulSoup(RESULTS_HTML, "html.parser")
    objects = get_objects_from_soup(soup)
    # only the public/odd row is returned; the private row is skipped
    assert objects == [{"name": "2024abc", "ra": "12:34:56.78", "dec": "+12:34:56.7"}]


def test_get_objects_from_soup_no_table():
    # a page without a results table yields no objects rather than raising
    soup = BeautifulSoup("<html><body>no results</body></html>", "html.parser")
    assert get_objects_from_soup(soup) == []
