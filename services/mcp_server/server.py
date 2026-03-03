# pyright: reportMissingTypeStubs=false
"""SkyPortal MCP server — config, auth, and entrypoint.

Tools are defined in the tools/ package and register themselves on import.
"""

import logging
import os
from pathlib import Path

import httpx
from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, OAuthProvider
from mcp.server.auth.provider import AuthorizationCode, AuthorizationParams
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

logger = logging.getLogger(__name__)


# ─── Configuration ───────────────────────────────────────────────────────────


def _load_skyportal_config() -> dict:
    """Read config.yaml from the SkyPortal root, merging over built-in defaults."""
    import yaml

    defaults: dict = {
        "ports": {"app": 5001, "mcp": 8000},
        "server": {"host": "localhost", "port": None, "ssl": False},
    }
    root = Path(__file__).resolve().parent.parent.parent
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
    _cfg = _load_skyportal_config()
    _ports = _cfg.get("ports", {})
    _server = _cfg.get("server", {})
    _default_skyportal_url = f"http://127.0.0.1:{_ports.get('app', 5001)}"
    _default_mcp_port = int(_ports.get("mcp", 8000))
    _ssl = _server.get("ssl", False)
    _host = _server.get("host", "localhost")
    _port = _server.get("port")
    _standard_port = 443 if _ssl else 80
    _port_str = f":{_port}" if _port and _port != _standard_port else ""
    _default_mcp_base_url = f"{'https' if _ssl else 'http'}://{_host}{_port_str}"
except Exception as _e:
    logging.warning("Could not load SkyPortal config (reason: %s); using defaults", _e)
    _default_skyportal_url = "http://127.0.0.1:5001"
    _default_mcp_port = 8000
    _default_mcp_base_url = None

SKYPORTAL_URL = os.getenv("SKYPORTAL_URL", _default_skyportal_url)
MCP_PORT = int(os.getenv("MCP_PORT", str(_default_mcp_port)))
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_BASE_URL = os.getenv(
    "MCP_BASE_URL", _default_mcp_base_url or f"http://localhost:{MCP_PORT}"
)
SKYPORTAL_TOKEN = os.getenv("SKYPORTAL_TOKEN")  # For stdio mode


# ─── Auth helper for tools ──────────────────────────────────────────────────


def get_skyportal_token() -> str | None:
    """
    Get SkyPortal API token for the current request.

    In HTTP mode: retrieves token from OAuth provider (per-request auth)
    In stdio mode: uses SKYPORTAL_TOKEN environment variable

    Returns:
        API token string, or None if not authenticated
    """
    transport = os.getenv("MCP_TRANSPORT", "http")

    if transport == "stdio":
        # Stdio mode: use env var token
        return SKYPORTAL_TOKEN
    else:
        # HTTP mode: use per-request OAuth token
        from fastmcp.server.dependencies import get_access_token

        access_token = get_access_token()
        return access_token.token if access_token else None


# ─── OAuth provider ──────────────────────────────────────────────────────────


class SkyPortalOAuthProvider(OAuthProvider):
    """
    OAuth provider for bearer-token authentication.

    MCP clients send a SkyPortal API token as a Bearer header on every
    request.  FastMCP's auth layer calls load_access_token() to validate
    it against SkyPortal's /api/internal/profile endpoint.

    The remaining OAuth methods (client registration, authorize, token
    exchange) are required by the OAuthProvider interface but are not
    used in the normal flow — clients pass their token directly.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=MCP_BASE_URL,
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )
        self._clients: dict[str, OAuthClientInformationFull] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if client_info.client_id:
            self._clients[client_info.client_id] = client_info

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        raise NotImplementedError("Direct bearer-token auth is used instead")

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        return None

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        raise NotImplementedError("Direct bearer-token auth is used instead")

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ):
        return None

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        raise NotImplementedError("Refresh tokens are not supported")

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Validate a SkyPortal token against /api/internal/profile."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{SKYPORTAL_URL}/api/internal/profile",
                    headers={"Authorization": f"token {token}"},
                )
            if not resp.is_success:
                logger.warning(
                    "Token validation failed: SkyPortal returned %s", resp.status_code
                )
                return None
            data = resp.json().get("data", {})
            username = data.get("username", "unknown")
            user_id = data.get("id")
            logger.info("Token validated for user: %s (id=%s)", username, user_id)
            return AccessToken(
                token=token,
                client_id=username,
                scopes=[f"user_id:{user_id}"],
            )
        except Exception:
            logger.exception("Token validation error (SKYPORTAL_URL=%s)", SKYPORTAL_URL)
            return None

    async def revoke_token(self, token) -> None:
        pass


# ─── MCP server instance ────────────────────────────────────────────────────

# For stdio mode, use env var auth; for HTTP mode, use OAuth provider
_transport = os.getenv("MCP_TRANSPORT", "http")
if _transport == "stdio":
    # In stdio mode, no multi-user auth - use SKYPORTAL_TOKEN env var
    mcp = FastMCP(
        "SkyPortal",
        instructions=(
            "Use the get_api_quick_reference tool to learn about available "
            "SkyPortal API endpoints and their parameters. Call it once at the "
            "start of a session or when you need to look up endpoint details."
        ),
    )
else:
    # In HTTP mode, use OAuth provider for multi-user bearer token auth
    mcp = FastMCP(
        "SkyPortal",
        instructions=(
            "Use the get_api_quick_reference tool to learn about available "
            "SkyPortal API endpoints and their parameters. Call it once at the "
            "start of a session or when you need to look up endpoint details."
        ),
        auth=SkyPortalOAuthProvider(),
    )

# Import tool modules — their @mcp.tool() decorators register on import.
# This MUST come after mcp is defined.
from . import tools  # noqa: E402, F401

# Entrypoint: run with `python -m services.mcp_server` (see __main__.py)
