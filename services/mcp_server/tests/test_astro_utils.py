"""Tests for time conversion, survey links, and cone search."""

import httpx
import pytest

from services.mcp_server.tools import astro_utils

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio


# ─── convert_time ───────────────────────────────────────────────────────────


async def test_convert_mjd_to_iso(mcp_client):
    text = await call_tool_text(
        mcp_client, "convert_time", {"value": "60400.5", "to_format": "iso"}
    )
    assert text.startswith("2024-03-31T12:00:00")


async def test_convert_iso_to_mjd(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "convert_time",
        {"value": "2024-03-31T12:00:00", "to_format": "mjd"},
    )
    assert float(text) == 60400.5


async def test_convert_jd_autodetected(mcp_client):
    # Values above 2.4M are detected as JD; JD 2460401.0 == MJD 60400.5
    text = await call_tool_text(
        mcp_client, "convert_time", {"value": "2460401.0", "to_format": "mjd"}
    )
    assert float(text) == 60400.5


async def test_convert_unix_to_iso(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "convert_time",
        {"value": "1710504000", "from_format": "unix", "to_format": "iso"},
    )
    assert text.startswith("2024-03-15T12:00:00")


async def test_convert_auto_output_shows_all_formats(mcp_client):
    text = await call_tool_text(mcp_client, "convert_time", {"value": "60400.5"})
    for label in ("ISO:", "MJD:", "JD:", "Unix:"):
        assert label in text


async def test_convert_unknown_format_is_reported(mcp_client):
    text = await call_tool_text(
        mcp_client, "convert_time", {"value": "60400.5", "from_format": "parsec"}
    )
    assert "Unknown from_format" in text


async def test_convert_unparseable_value_is_reported(mcp_client):
    text = await call_tool_text(mcp_client, "convert_time", {"value": "not-a-time"})
    assert "Conversion error" in text


# ─── Coordinate formatting helpers ──────────────────────────────────────────


async def test_ra_to_hms():
    assert astro_utils._ra_to_hms(180.0) == "12:00:00.00"
    assert astro_utils._ra_to_hms(0.0) == "00:00:00.00"


async def test_dec_to_dms():
    assert astro_utils._dec_to_dms(-45.5) == "-45:30:00.00"
    assert astro_utils._dec_to_dms(2.0) == "+02:00:00.00"


# ─── get_survey_urls ────────────────────────────────────────────────────────


async def test_survey_urls_from_coordinates(mcp_client):
    text = await call_tool_text(
        mcp_client, "get_survey_urls", {"ra": 10.6847, "dec": 41.2687}
    )
    assert "RA=10.684700, Dec=+41.268700" in text
    for survey in ("Legacy Survey", "SIMBAD", "TNS", "Aladin"):
        assert survey in text


async def test_survey_urls_resolves_source_id(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET",
        "/api/sources/ZTF21abc",
        json={"status": "success", "data": {"id": "ZTF21abc", "ra": 150.0, "dec": 2.0}},
    )
    text = await call_tool_text(
        mcp_client, "get_survey_urls", {"source_id": "ZTF21abc"}
    )
    assert "ZTF21abc" in text
    assert "RA=150.000000" in text


async def test_survey_urls_requires_position(mcp_client):
    text = await call_tool_text(mcp_client, "get_survey_urls", {})
    assert "Provide either source_id or both ra and dec" in text


# ─── search_sources_near_position ───────────────────────────────────────────


async def test_cone_search_sorts_by_separation(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET",
        "/api/sources",
        json={
            "status": "success",
            "data": {
                "sources": [
                    # ~3.6 arcsec away
                    {"id": "far", "ra": 150.001, "dec": 2.0, "groups": []},
                    # ~0.7 arcsec away
                    {
                        "id": "near",
                        "ra": 150.0002,
                        "dec": 2.0,
                        "groups": [{"name": "Science"}],
                    },
                ]
            },
        },
    )
    text = await call_tool_text(
        mcp_client,
        "search_sources_near_position",
        {"ra": 150.0, "dec": 2.0, "radius_arcsec": 10.0},
    )
    assert text.index("near") < text.index("far")
    assert "Science" in text
    assert "Total: 2 source(s)" in text
    # Radius must be converted from arcsec to degrees for the API
    request = skyportal_api.requests[0]
    assert float(httpx.QueryParams(request.url.query)["radius"]) == pytest.approx(
        10.0 / 3600.0
    )


async def test_cone_search_no_matches(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET", "/api/sources", json={"status": "success", "data": {"sources": []}}
    )
    text = await call_tool_text(
        mcp_client,
        "search_sources_near_position",
        {"ra": 150.0, "dec": 2.0, "radius_arcsec": 5.0},
    )
    assert "No sources found within 5.0 arcsec" in text


async def test_cone_search_requires_auth(mcp_client, no_auth):
    text = await call_tool_text(
        mcp_client, "search_sources_near_position", {"ra": 150.0, "dec": 2.0}
    )
    assert "Not authenticated" in text
