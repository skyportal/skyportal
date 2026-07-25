"""Tests for the Tornado /mcp endpoint (auth + ASGI bridge).

Token validation is stubbed out; everything below it — the ASGI adapter,
FastMCP's Streamable-HTTP app, tool dispatch — runs for real.
"""

import json

import tornado.testing
import tornado.web

from skyportal.handlers.mcp import handler as handler_module
from skyportal.handlers.mcp.handler import MCPHandler

VALID_TOKEN = "valid-test-token"

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {VALID_TOKEN}",
}


def rpc(method, params=None, id=1):
    return json.dumps(
        {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}
    )


def parse_mcp_body(body):
    """Parse a Streamable-HTTP response body (plain JSON or SSE-framed)."""
    text = body.decode()
    if text.lstrip().startswith("{"):
        return json.loads(text)
    messages = [
        json.loads(line[len("data:") :].strip())
        for line in text.splitlines()
        if line.startswith("data:")
    ]
    assert messages, f"no data frames in response: {text!r}"
    return messages[-1]


class MCPHandlerTestCase(tornado.testing.AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        # Each test case runs on a fresh event loop
        handler_module._reset_state()

        async def fake_validate(token_id):
            return token_id == VALID_TOKEN

        self._real_validate = handler_module.validate_token
        handler_module.validate_token = fake_validate

    def tearDown(self):
        handler_module.validate_token = self._real_validate
        handler_module._reset_state()
        super().tearDown()

    def get_app(self):
        return tornado.web.Application([(r"/mcp", MCPHandler)])

    def post_mcp(self, body, headers=None):
        return self.fetch(
            "/mcp", method="POST", body=body, headers=headers or MCP_HEADERS
        )

    def test_missing_auth_header_rejected(self):
        response = self.post_mcp(
            rpc("tools/list"),
            headers={"Content-Type": "application/json"},
        )
        assert response.code == 401
        assert "Missing SkyPortal API token" in response.body.decode()

    def test_invalid_token_rejected(self):
        headers = dict(MCP_HEADERS, Authorization="Bearer wrong-token")
        response = self.post_mcp(rpc("tools/list"), headers=headers)
        assert response.code == 401
        assert "Invalid or expired" in response.body.decode()

    def test_skyportal_token_scheme_accepted(self):
        headers = dict(MCP_HEADERS, Authorization=f"token {VALID_TOKEN}")
        response = self.post_mcp(rpc("tools/list"), headers=headers)
        assert response.code == 200

    def test_initialize(self):
        response = self.post_mcp(
            rpc(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "0.0.0"},
                },
            )
        )
        assert response.code == 200
        message = parse_mcp_body(response.body)
        assert message["result"]["serverInfo"]["name"] == "SkyPortal"

    def test_tools_list(self):
        response = self.post_mcp(rpc("tools/list"))
        assert response.code == 200
        message = parse_mcp_body(response.body)
        tool_names = {t["name"] for t in message["result"]["tools"]}
        assert "convert_time" in tool_names
        assert "get_source_photometry" in tool_names

    def test_tool_call_round_trip(self):
        response = self.post_mcp(
            rpc(
                "tools/call",
                {
                    "name": "convert_time",
                    "arguments": {"value": "60400.5", "to_format": "iso"},
                },
            )
        )
        assert response.code == 200
        message = parse_mcp_body(response.body)
        text = message["result"]["content"][0]["text"]
        assert text.startswith("2024-03-31T12:00:00")
