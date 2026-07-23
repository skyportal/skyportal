"""Tests for source data product tools (photometry, ID resolution)."""

import pytest

from services.mcp_server.tools.source_products import resolve_source_id

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio

PHOTOMETRY = [
    # Deliberately unsorted to verify MJD sorting
    {
        "mjd": 60010.0,
        "filter": "ztfr",
        "mag": 18.5,
        "magerr": 0.05,
        "limiting_mag": 20.5,
        "snr": 20.0,
        "instrument_name": "ZTF",
        "origin": None,
    },
    {
        "mjd": 60000.0,
        "filter": "ztfg",
        "mag": 19.0,
        "magerr": 0.1,
        "limiting_mag": 20.5,
        "snr": 10.0,
        "instrument_name": "ZTF",
        "origin": None,
    },
]


def add_source(fake, obj_id="ZTF21abc", ra=150.0, dec=2.0):
    fake.add(
        "GET",
        f"/api/sources/{obj_id}",
        json={"status": "success", "data": {"id": obj_id, "ra": ra, "dec": dec}},
    )


# ─── resolve_source_id ──────────────────────────────────────────────────────


async def test_resolve_direct_obj_id(skyportal_api):
    add_source(skyportal_api)
    assert await resolve_source_id("ZTF21abc") == "ZTF21abc"


async def test_resolve_falls_back_to_search(skyportal_api):
    # Direct lookup 404s (TNS name is not an obj_id), then the search
    # endpoint resolves it.
    skyportal_api.add(
        "GET",
        "/api/sources",
        json={"status": "success", "data": {"sources": [{"id": "ZTF21abc"}]}},
    )
    assert await resolve_source_id("AT2021xyz") == "ZTF21abc"
    search_request = skyportal_api.requests[-1]
    assert "sourceID=AT2021xyz" in str(search_request.url)


async def test_resolve_unknown_source(skyportal_api):
    skyportal_api.add(
        "GET", "/api/sources", json={"status": "success", "data": {"sources": []}}
    )
    assert await resolve_source_id("nope") is None


async def test_resolve_without_auth(no_auth):
    assert await resolve_source_id("ZTF21abc") is None


# ─── get_source_photometry ──────────────────────────────────────────────────


async def test_photometry_csv_sorted_by_mjd(mcp_client, skyportal_api):
    add_source(skyportal_api)
    skyportal_api.add(
        "GET",
        "/api/sources/ZTF21abc/photometry",
        json={"status": "success", "data": PHOTOMETRY},
    )
    text = await call_tool_text(
        mcp_client, "get_source_photometry", {"source_name": "ZTF21abc"}
    )
    lines = text.strip().splitlines()
    assert lines[0] == "# ZTF21abc: 2 points, filters: ztfg, ztfr"
    assert lines[1] == "mjd,filter,mag,magerr,limiting_mag,snr,instrument_name,origin"
    assert lines[2].startswith("60000.0,ztfg,19.0")
    assert lines[3].startswith("60010.0,ztfr,18.5")


async def test_photometry_filter_selection(mcp_client, skyportal_api):
    add_source(skyportal_api)
    skyportal_api.add(
        "GET",
        "/api/sources/ZTF21abc/photometry",
        json={"status": "success", "data": PHOTOMETRY},
    )
    text = await call_tool_text(
        mcp_client,
        "get_source_photometry",
        {"source_name": "ZTF21abc", "filters": "ztfg"},
    )
    assert "ztfg" in text
    assert "ztfr" not in text.split("\n", 1)[1]  # only in the summary line


async def test_photometry_filter_selection_no_match(mcp_client, skyportal_api):
    add_source(skyportal_api)
    skyportal_api.add(
        "GET",
        "/api/sources/ZTF21abc/photometry",
        json={"status": "success", "data": PHOTOMETRY},
    )
    text = await call_tool_text(
        mcp_client,
        "get_source_photometry",
        {"source_name": "ZTF21abc", "filters": "sdssu"},
    )
    assert "No photometry found for source ZTF21abc in filters: sdssu" in text


async def test_photometry_empty(mcp_client, skyportal_api):
    add_source(skyportal_api)
    skyportal_api.add(
        "GET",
        "/api/sources/ZTF21abc/photometry",
        json={"status": "success", "data": []},
    )
    text = await call_tool_text(
        mcp_client, "get_source_photometry", {"source_name": "ZTF21abc"}
    )
    assert "No photometry found" in text


async def test_photometry_unresolvable_source(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET", "/api/sources", json={"status": "success", "data": {"sources": []}}
    )
    text = await call_tool_text(
        mcp_client, "get_source_photometry", {"source_name": "nope"}
    )
    assert "Could not resolve 'nope'" in text
