"""Tornado endpoint serving the MCP protocol from the main app.

The MCP Python SDK is ASGI-based; this handler adapts Tornado's request
model to ASGI and dispatches into FastMCP's stateless Streamable-HTTP app.
Stateless mode keeps no server-side session state, so requests can land on
any app worker behind the load balancer.

Authentication reuses SkyPortal API tokens: clients send
`Authorization: Bearer <token>` (MCP convention) or `Authorization: token
<token>` (SkyPortal convention). The token is validated against the Token
table before any MCP traffic is processed, then exposed to tools via
server.current_request_token so their REST API calls run with the caller's
own permissions.
"""

import asyncio
import json

import tornado.web

from .server import current_request_token, mcp

_asgi_app = None
_lifespan = None


def _reset_state():
    """Testing hook: discard the per-process ASGI app and lifespan state.

    The lifespan task is bound to the event loop it started on; tests that
    create a fresh loop per case must reset between cases.
    """
    global _asgi_app, _lifespan
    if _lifespan is not None and _lifespan._task is not None:
        _lifespan._task.cancel()
    _asgi_app = None
    _lifespan = None


def get_asgi_app():
    global _asgi_app
    if _asgi_app is None:
        # Host/Origin validation and auth are handled by nginx and this
        # handler; the inner ASGI app must not second-guess the Host header.
        _asgi_app = mcp.http_app(
            path="/mcp",
            stateless_http=True,
            host_origin_protection=False,
        )
    return _asgi_app


class _LifespanRunner:
    """Drive the ASGI lifespan protocol once per process.

    FastMCP's session manager only accepts requests while the app's
    lifespan context is open, so start it on first use and keep it open
    for the life of the process.
    """

    def __init__(self, app):
        self.app = app
        self.started = asyncio.Event()
        self._task = None
        self._receive_queue = asyncio.Queue()

    async def ensure_started(self):
        if self._task is None:
            self._task = asyncio.ensure_future(self._run())
            await self._receive_queue.put({"type": "lifespan.startup"})
        await self.started.wait()

    async def _run(self):
        async def receive():
            return await self._receive_queue.get()

        async def send(message):
            if message["type"] == "lifespan.startup.complete":
                self.started.set()
            elif message["type"] == "lifespan.startup.failed":
                raise RuntimeError(
                    f"MCP app failed to start: {message.get('message', '')}"
                )

        scope = {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.3"}}
        await self.app(scope, receive, send)


async def validate_token(token_id):
    """Return True if token_id is a valid token of an active user."""
    import sqlalchemy as sa
    from sqlalchemy.orm import joinedload

    from baselayer.app import models

    try:
        async with models.async_plain_session_factory() as session:
            result = await session.scalars(
                sa.select(models.Token)
                .options(joinedload(models.Token.created_by))
                .where(models.Token.id == token_id)
            )
            token = result.first()
        return token is not None and token.created_by.is_active()
    except Exception:
        return False


class MCPHandler(tornado.web.RequestHandler):
    def initialize(self):
        self._disconnected = asyncio.Event()

    def on_connection_close(self):
        self._disconnected.set()

    async def get(self):
        await self._dispatch()

    async def post(self):
        await self._dispatch()

    async def delete(self):
        await self._dispatch()

    def _extract_token(self):
        header = self.request.headers.get("Authorization", "")
        for scheme in ("Bearer ", "token "):
            if header.startswith(scheme):
                return header[len(scheme) :].strip()
        return None

    def _reject(self, status, message):
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.finish(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32001, "message": message},
                }
            )
        )

    async def _dispatch(self):
        global _lifespan

        token = self._extract_token()
        if token is None:
            self._reject(
                401,
                "Missing SkyPortal API token. Send it as an "
                "'Authorization: Bearer <token>' header.",
            )
            return
        if not await validate_token(token):
            self._reject(401, "Invalid or expired SkyPortal API token.")
            return

        app = get_asgi_app()
        if _lifespan is None:
            _lifespan = _LifespanRunner(app)
        await _lifespan.ensure_started()

        # Tools inherit this via contextvar snapshots in spawned tasks
        current_request_token.set(token)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": self.request.method,
            "scheme": "http",
            "path": "/mcp",
            "raw_path": b"/mcp",
            "query_string": self.request.query.encode(),
            "root_path": "",
            "headers": [
                (name.lower().encode(), value.encode())
                for name, value in self.request.headers.get_all()
            ],
            "client": (self.request.remote_ip, 0),
            "server": ("localhost", 0),
        }

        body_delivered = False

        async def receive():
            nonlocal body_delivered
            if not body_delivered:
                body_delivered = True
                return {
                    "type": "http.request",
                    "body": self.request.body or b"",
                    "more_body": False,
                }
            # Block until the client goes away; returning disconnect early
            # would abort streaming responses.
            await self._disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.start":
                self.set_status(message["status"])
                self.clear_header("Content-Type")
                for name, value in message.get("headers", []):
                    header = name.decode()
                    # Tornado computes framing headers itself
                    if header.lower() in ("content-length", "transfer-encoding"):
                        continue
                    self.set_header(header, value.decode())
            elif message["type"] == "http.response.body":
                if message.get("body"):
                    self.write(message["body"])
                if message.get("more_body"):
                    await self.flush()

        await app(scope, receive, send)
