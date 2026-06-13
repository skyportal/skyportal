"""SkyPortal ASGI BaseHandler + handler re-basing (issue #381).

SkyPortal's ~211 handlers extend the Tornado ``BaseHandler`` chain. Rather than
edit each one, ``rebase(HandlerCls)`` produces an equivalent class whose base is
the baselayer compat shim ``Handler`` (plus SkyPortal's ``BaseHandler``
additions) instead of ``tornado.web.RequestHandler`` -- by copying the handler's
own methods onto the shim base. This lets handlers be mounted on the ASGI app
incrementally and verifies the shim's surface matches what they use.

(The eventual production migration just switches the base of
``skyportal.handlers.base.BaseHandler`` itself; this re-basing is the
non-destructive, incremental path that keeps the Tornado server working too.)
"""

from baselayer.app.handlers.asgi_compat import Handler as ShimHandler
from skyportal import __version__
from skyportal.handlers.base import install_path_param_validation

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


class ASGIBaseHandler(ShimHandler):
    """SkyPortal's ``BaseHandler`` additions, on the shim instead of Tornado."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        install_path_param_validation(cls)

    @property
    def associated_user_object(self):
        if hasattr(self.current_user, "username"):
            return self.current_user
        return self.current_user.created_by

    def success(self, *args, **kwargs):
        super().success(*args, **kwargs, extra={"version": __version__})

    def error(self, message, *args, **kwargs):
        super().error(message, *args, **kwargs, extra={"version": __version__})


def rebase(handler_cls):
    """Return a shim-based equivalent of a Tornado-based SkyPortal handler.

    Copies the handler's own HTTP methods (and any class-level attributes) onto
    ``ASGIBaseHandler``. ``__init_subclass__`` then runs the path-param
    validation against the copied methods, exactly as under Tornado.
    """
    own = {k: v for k, v in handler_cls.__dict__.items() if not k.startswith("__")}
    return type(handler_cls.__name__, (ASGIBaseHandler,), own)
