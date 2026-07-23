"""Server-level tests: tool/resource registration, config, auth."""

import pytest

from services.mcp_server import server

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio

EXPECTED_TOOLS = {
    # api
    "get_api_quick_reference",
    "get_tools_quick_reference",
    "call_skyportal_api",
    # astro_utils
    "convert_time",
    "get_survey_urls",
    "search_sources_near_position",
    # filtering
    "get_candidate_filter_reference",
    "filter_candidates",
    "generate_watchlist_filter",
    # source_products
    "get_source_photometry",
    "get_source_spectra",
    "get_source_classifications",
    "get_source_comments_and_annotations",
    "get_source_host_galaxy",
    "get_tns_summary",
    # analysis
    "analyze_light_curve",
    "analyze_color_evolution",
    # observing
    "get_source_observability",
    # bulk_analysis
    "generate_bulk_lightcurve_code",
    "generate_cone_search_code",
    "generate_fritz_bulk_query_code",
    "generate_alert_download_code",
    "generate_field_visualization_code",
}

EXPECTED_RESOURCES = {
    "skyportal://api/quick_reference",
    "skyportal://tools/reference",
    "skyportal://filters/reference",
}


async def test_all_tools_registered(mcp_client):
    async with mcp_client:
        tools = await mcp_client.list_tools()
    assert {t.name for t in tools} == EXPECTED_TOOLS


async def test_all_resources_registered(mcp_client):
    async with mcp_client:
        resources = await mcp_client.list_resources()
    assert {str(r.uri) for r in resources} == EXPECTED_RESOURCES


async def test_resources_readable(mcp_client):
    async with mcp_client:
        for uri in EXPECTED_RESOURCES:
            contents = await mcp_client.read_resource(uri)
            assert contents[0].text.strip()


async def test_quick_reference_tools_return_docs(mcp_client):
    text = await call_tool_text(mcp_client, "get_api_quick_reference")
    assert "/api/" in text


async def test_get_skyportal_token_stdio_mode():
    assert server.get_skyportal_token() == "test-token"


async def test_get_skyportal_token_stdio_mode_missing(no_auth):
    assert server.get_skyportal_token() is None


async def test_oauth_provider_accepts_valid_token(skyportal_api):
    skyportal_api.add(
        "GET",
        "/api/internal/profile",
        json={"status": "success", "data": {"username": "leo", "id": 7}},
    )
    provider = server.SkyPortalOAuthProvider()
    access_token = await provider.load_access_token("some-token")
    assert access_token is not None
    assert access_token.token == "some-token"
    assert access_token.client_id == "leo"
    assert access_token.scopes == ["user_id:7"]
    # The token must be forwarded to SkyPortal for validation
    assert skyportal_api.requests[0].headers["Authorization"] == "token some-token"


async def test_oauth_provider_rejects_invalid_token(skyportal_api):
    skyportal_api.add("GET", "/api/internal/profile", json={}, status_code=401)
    provider = server.SkyPortalOAuthProvider()
    assert await provider.load_access_token("bad-token") is None


async def test_config_defaults_when_no_config_yaml():
    cfg = server._load_skyportal_config()
    assert cfg["ports"]["app"] == 5001
    assert cfg["ports"]["mcp"] == 8000
