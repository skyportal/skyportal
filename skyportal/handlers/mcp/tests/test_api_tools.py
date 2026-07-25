"""Tests for the generic API caller tool."""

import pytest

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio


async def test_call_api_success(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET",
        "/api/groups",
        json={"status": "success", "data": {"user_groups": []}},
    )
    text = await call_tool_text(
        mcp_client, "call_skyportal_api", {"endpoint": "/api/groups"}
    )
    assert "success" in text
    request = skyportal_api.requests[0]
    assert request.headers["Authorization"] == "token test-token"


async def test_call_api_forwards_params_and_body(mcp_client, skyportal_api):
    skyportal_api.add(
        "POST", "/api/comment", json={"status": "success", "data": {"id": 1}}
    )
    await call_tool_text(
        mcp_client,
        "call_skyportal_api",
        {
            "endpoint": "/api/comment",
            "method": "POST",
            "params": {"objID": "ZTF21abc"},
            "data": {"text": "hello"},
        },
    )
    request = skyportal_api.requests[0]
    assert request.method == "POST"
    assert "objID=ZTF21abc" in str(request.url)
    assert b'"text"' in request.content


async def test_call_api_http_error_reported(mcp_client, skyportal_api):
    text = await call_tool_text(
        mcp_client, "call_skyportal_api", {"endpoint": "/api/nonexistent"}
    )
    assert "HTTP Error 404" in text


async def test_call_api_requires_auth(mcp_client, no_auth):
    text = await call_tool_text(
        mcp_client, "call_skyportal_api", {"endpoint": "/api/groups"}
    )
    assert "Not authenticated" in text
