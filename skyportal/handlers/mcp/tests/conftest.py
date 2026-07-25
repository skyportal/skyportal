"""Unit tests for the MCP server.

These run without a live SkyPortal instance: tools are called through
FastMCP's in-memory client transport, and SkyPortal API calls are
intercepted with httpx.MockTransport.

Run from the repo root:  pytest skyportal/handlers/mcp/tests
"""

import os

# Checked at call time by get_skyportal_token()
os.environ["MCP_TRANSPORT"] = "stdio"

import httpx
import pytest
from astropy.utils import iers
from fastmcp import Client

from skyportal.handlers.mcp import server

# The parent package (and thus server) may be imported before this file
# runs, so set the stdio-mode token on the module rather than via env.
server.SKYPORTAL_TOKEN = "test-token"

# Tests use fixed past dates; the bundled IERS table covers them.
iers.conf.auto_download = False


class FakeSkyPortal:
    """Route table for httpx.MockTransport: (METHOD, path) -> JSON response.

    Payloads may be dicts or callables taking the request and returning an
    httpx.Response. Every request is recorded for assertions. Unrouted
    paths return 404.
    """

    def __init__(self):
        self.routes = {}
        self.requests = []

    def add(self, method, path, json=None, status_code=200):
        self.routes[(method.upper(), path)] = (status_code, json)

    def handler(self, request):
        self.requests.append(request)
        route = self.routes.get((request.method, request.url.path))
        if route is None:
            return httpx.Response(404, json={"status": "error", "message": "not found"})
        status_code, payload = route
        if callable(payload):
            return payload(request)
        return httpx.Response(status_code, json=payload)


@pytest.fixture
def skyportal_api(monkeypatch):
    """Intercept all httpx.AsyncClient traffic with a FakeSkyPortal."""
    fake = FakeSkyPortal()
    real_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(fake.handler)
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
    return fake


@pytest.fixture
def no_auth(monkeypatch):
    """Simulate a missing SKYPORTAL_TOKEN."""
    monkeypatch.setattr(server, "SKYPORTAL_TOKEN", None)


@pytest.fixture
def mcp_client():
    """In-memory MCP client connected to the server instance."""
    return Client(server.mcp)


async def call_tool_text(client, name, arguments=None):
    """Call a tool and return its text content."""
    async with client:
        result = await client.call_tool(name, arguments or {})
    return result.content[0].text
