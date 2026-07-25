"""SkyPortal MCP server — FastMCP instance, config, and auth helper.

The server runs inside the main web application: the /mcp Tornado endpoint
(handler.py) validates the caller's SkyPortal token and dispatches requests
into FastMCP's ASGI app. For local development it can also run standalone
over stdio (`python -m skyportal.handlers.mcp`) against any SkyPortal
instance, using SKYPORTAL_TOKEN from the environment.

Tools are defined in the tools/ package and register themselves on import.
"""

import contextvars
import os
from pathlib import Path

from fastmcp import FastMCP

# ─── Configuration ───────────────────────────────────────────────────────────


def _load_skyportal_config() -> dict:
    """Read config.yaml from the SkyPortal root, merging over built-in defaults."""
    import yaml

    defaults: dict = {"ports": {"app": 5000}}
    root = Path(__file__).resolve().parent.parent.parent.parent
    cfg_path = root / "config.yaml"
    if not cfg_path.exists():
        return defaults
    with cfg_path.open() as f:
        user_cfg = yaml.safe_load(f) or {}
    for section, values in user_cfg.items():
        if isinstance(values, dict) and section in defaults:
            defaults[section].update(values)
        else:
            defaults[section] = values
    return defaults


try:
    _app_port = int(_load_skyportal_config().get("ports", {}).get("app", 5000))
except Exception:
    _app_port = 5000

# Tools read data through the REST API so every request goes through the
# same permission checks as any other API client.
SKYPORTAL_URL = os.getenv("SKYPORTAL_URL", f"http://localhost:{_app_port}")
SKYPORTAL_TOKEN = os.getenv("SKYPORTAL_TOKEN")  # For stdio mode


# ─── Per-request auth ───────────────────────────────────────────────────────

# Set by the /mcp Tornado handler after validating the Authorization header;
# inherited by the tasks FastMCP spawns to run tools.
current_request_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "skyportal_mcp_token", default=None
)


def get_skyportal_token() -> str | None:
    """
    Get the SkyPortal API token for the current request.

    In-app (HTTP) mode: the token validated by the /mcp endpoint.
    stdio mode: the SKYPORTAL_TOKEN environment variable.
    """
    if os.getenv("MCP_TRANSPORT") == "stdio":
        return SKYPORTAL_TOKEN
    return current_request_token.get()


# ─── MCP server instance ────────────────────────────────────────────────────

mcp = FastMCP(
    "SkyPortal",
    instructions=(
        "Use the get_api_quick_reference tool to learn about available "
        "SkyPortal API endpoints and their parameters. Call it once at the "
        "start of a session or when you need to look up endpoint details."
    ),
)

# Import tool modules — their @mcp.tool() decorators register on import.
# This MUST come after mcp is defined.
from . import tools  # noqa: E402, F401
