# pyright: reportMissingTypeStubs=false
"""Core SkyPortal API tools: generic API caller and quick reference."""

import logging
from pathlib import Path

import httpx

from ..server import SKYPORTAL_URL, get_skyportal_token, mcp

logger = logging.getLogger(__name__)

RESOURCES_DIR = Path(__file__).parent.parent / "resources"


@mcp.resource("skyportal://api/quick_reference")
def get_api_docs() -> str:
    """Quick reference guide for common SkyPortal API endpoints"""
    return (RESOURCES_DIR / "api_info.md").read_text()


@mcp.resource("skyportal://tools/reference")
def get_tools_docs() -> str:
    """Quick reference guide for all available MCP tools"""
    return (RESOURCES_DIR / "tools_reference.md").read_text()


@mcp.tool()
def get_api_quick_reference() -> str:
    """Get the SkyPortal API quick reference guide.

    Returns a reference of available API endpoints, required parameters,
    and usage patterns. Call once to load into context as needed.
    """
    return (RESOURCES_DIR / "api_info.md").read_text()


@mcp.tool()
def get_tools_quick_reference() -> str:
    """Get the MCP tools quick reference guide.

    Returns a comprehensive list of all available MCP tools organized by
    category, with common workflows and usage examples. Call once to load
    into context when needed.
    """
    return (RESOURCES_DIR / "tools_reference.md").read_text()


@mcp.tool()
async def call_skyportal_api(
    endpoint: str,
    method: str = "GET",
    params: dict | None = None,
    data: dict | None = None,
) -> str:
    """
    Make an API call to SkyPortal.

    Args:
        endpoint: API endpoint (e.g., "/api/sources")
        method: HTTP method (GET, POST, PUT, DELETE)
        params: Query parameters
        data: Request body
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    logger.info("API call → %s %s", method, endpoint)
    url = f"{SKYPORTAL_URL}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method=method,
                url=url,
                headers={"Authorization": f"token {token}"},
                params=params,
                json=data,
            )
        response.raise_for_status()
        return str(response.json())
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        logger.exception("API call failed")
        return f"API Error: {str(e)}"
