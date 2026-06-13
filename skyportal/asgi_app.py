"""SkyPortal ASGI factory (issue #381).

Builds SkyPortal on Starlette/uvicorn via the baselayer compat shim. SkyPortal's
~211 handlers are mounted by re-basing them onto the shim (``asgi_base.rebase``)
and routing with a regex router that reuses Tornado's *exact* route patterns --
translating patterns like ``/api/allocation(/.*)?`` to Starlette templates is
brittle, so we match the original regex and pass captured groups positionally,
exactly as Tornado does.

Point ``cfg['app.asgi_factory']`` here (see
``baselayer/services/app/asgi_app.py``).
"""

import re
from inspect import isawaitable  # noqa: F401  (re-exported semantics)

import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.handlers.asgi_baselayer import make_baselayer_asgi_app
from baselayer.app.handlers.asgi_compat import Handler, asgi_endpoint, serve_handler
from baselayer.log import make_log

try:
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse
    from starlette.routing import Mount, Route
except ImportError:  # pragma: no cover
    Request = PlainTextResponse = Mount = Route = None  # type: ignore

log = make_log("asgi_app")


class WhoamiHandler(Handler):
    """Sanity endpoint: token auth + a user-aware DB session through the shim."""

    @auth_or_token
    def get(self):
        from baselayer.app.models import User

        user = self.current_user
        username = getattr(user, "username", None) or user.created_by.username
        with self.Session() as session:
            n_users = session.scalar(sa.select(sa.func.count()).select_from(User))
        self.success({"authenticated_as": username, "n_users": n_users})


def _process_path_args(groups):
    """Tornado's path-arg handling: strip leading slashes, '' -> None, and a lone
    None -> no args."""
    args = [g.lstrip("/") if g is not None else None for g in groups]
    args = [a if a != "" else None for a in args]
    if len(args) == 1 and args[0] is None:
        return []
    return args


class TornadoRegexRouter:
    """ASGI app routing by SkyPortal's Tornado regex patterns (in order)."""

    def __init__(self, routes):
        self.compiled = [(re.compile(rf"^{pat}$"), h) for pat, h in routes]

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)
        path = scope["path"]
        for pattern, handler_cls in self.compiled:
            m = pattern.match(path)
            if m is None:
                continue
            path_args = _process_path_args(m.groups())
            handler = handler_cls(request, app=scope.get("app"), path_args=path_args)
            response = await serve_handler(handler, path_args)
            await response(scope, receive, send)
            return
        await PlainTextResponse("Not Found", status_code=404)(scope, receive, send)


def make_asgi_app(settings, cfg):
    from skyportal.app_server import skyportal_handlers
    from skyportal.asgi_base import rebase

    app = make_baselayer_asgi_app(settings, cfg)
    app.routes.append(
        Route("/api/whoami", asgi_endpoint(WhoamiHandler), methods=["GET"])
    )

    rebased, failed = [], []
    for pattern, handler_cls in skyportal_handlers:
        try:
            rebased.append((pattern, rebase(handler_cls)))
        except Exception as e:  # don't let one handler sink the whole mount
            failed.append((handler_cls.__name__, str(e)))
    log(f"Re-based {len(rebased)}/{len(skyportal_handlers)} SkyPortal handlers")
    if failed:
        log(f"  re-base failed for {len(failed)}: {failed[:5]}")

    app.routes.append(Mount("/", app=TornadoRegexRouter(rebased)))
    return app
