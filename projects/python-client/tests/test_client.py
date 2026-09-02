"""Tests for the shared HTTP plumbing."""

from __future__ import annotations

import httpx
import pytest
import respx

from skyportal_py import SkyPortalError, create_client, unwrap

BASE_URL = "https://skyportal.example.com"


@respx.mock
def test_client_sends_token_and_base_url(client: httpx.Client) -> None:
    """The client joins paths onto the base URL and sends the token header."""
    route = respx.get(f"{BASE_URL}/api/internal/profile").mock(
        return_value=httpx.Response(
            200, json={"status": "success", "data": {"username": "leo"}}
        )
    )
    client.get("/api/internal/profile")
    assert route.calls[0].request.headers["Authorization"] == "token abc123"


@respx.mock
def test_anonymous_client_sends_no_auth_header() -> None:
    """Omitting the token creates a client without an Authorization header."""
    route = respx.get(f"{BASE_URL}/api/sources").mock(
        return_value=httpx.Response(
            200, json={"status": "success", "data": {"sources": []}}
        )
    )
    create_client(BASE_URL).get("/api/sources")
    assert "Authorization" not in route.calls[0].request.headers


def test_unwrap_returns_data() -> None:
    """A success envelope unwraps to its data field."""
    response = httpx.Response(
        200, json={"status": "success", "data": {"sources": [], "totalMatches": 0}}
    )
    assert unwrap(response) == {"sources": [], "totalMatches": 0}


def test_unwrap_error_raises() -> None:
    """An error envelope raises SkyPortalError with the server message."""
    response = httpx.Response(
        400, json={"status": "error", "message": "Invalid source ID"}
    )
    with pytest.raises(SkyPortalError, match="Invalid source ID") as excinfo:
        unwrap(response)
    assert excinfo.value.status_code == 400


def test_unwrap_non_json_raises() -> None:
    """A non-JSON response raises SkyPortalError instead of ValueError."""
    response = httpx.Response(502, text="<html>proxy error</html>")
    with pytest.raises(SkyPortalError, match="non-JSON"):
        unwrap(response)
