import functools
import inspect
import types
import typing
from math import ceil

from tornado.gen import sleep
from tornado.iostream import StreamClosedError

from baselayer.app.handlers.base import BaseHandler as BaselayerHandler

from .. import __version__

HANDLER_METHODS = ("get", "post", "put", "patch", "delete")


def resolve_cast(annotation):
    """Resolve a parameter annotation to a cast callable.

    Handles ``Optional[T]`` / ``T | None`` by unwrapping to the inner type and
    setting ``allow_none=True``. Returns ``(cast_fn, allow_none)``.

    If the annotation is a Union with more than one non-None member, returns
    ``(None, False)`` — the wrapper will skip such parameters rather than guess.
    """
    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        non_none = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0], True
        return None, False
    return annotation, False


def install_path_param_validation(cls):
    """Wrap each ``get``/``post``/``put``/``patch``/``delete`` defined on ``cls``
    so positional path arguments are coerced to the types declared in the
    parameter annotations.

    On ``TypeError``/``ValueError`` the wrapper returns
    ``self.error(f"Invalid {name}: {val}")`` and the handler is not invoked.

    ``Optional[T]`` / ``T | None`` annotations are honored: a ``None`` value
    passes through unchanged. Parameters without an annotation are left alone.

    Designed to be called from ``__init_subclass__`` of a base handler class;
    exposed at module level so tests can exercise the same code path against
    a minimal fake base class.
    """
    for method_name in HANDLER_METHODS:
        method = cls.__dict__.get(method_name)
        if method is None:
            continue

        params = list(inspect.signature(method).parameters.values())[1:]  # skip self
        validators = []
        for i, p in enumerate(params):
            if p.annotation is inspect.Parameter.empty:
                continue
            cast_fn, allow_none = resolve_cast(p.annotation)
            if cast_fn is None or cast_fn is str:
                # str-as-no-op + unsupported unions are skipped.
                continue
            validators.append((i, p.name, cast_fn, allow_none))
        if not validators:
            continue

        @functools.wraps(method)
        async def wrapper(
            self, *args, _method=method, _validators=validators, **kwargs
        ):
            new_args = list(args)
            for i, name, cast_fn, allow_none in _validators:
                if i >= len(new_args):
                    break
                val = new_args[i]
                if val is None and allow_none:
                    continue
                try:
                    new_args[i] = cast_fn(val)
                except (TypeError, ValueError):
                    return self.error(f"Invalid {name}: {val}")
            result = _method(self, *new_args, **kwargs)
            if inspect.iscoroutine(result):
                return await result
            return result

        setattr(cls, method_name, wrapper)


def format_doc(**kwargs):
    """Inject values into a handler method's docstring placeholders.

    The purpose of this wrapper is to avoid using an f-string for the
    docstring, because an f-string in the docstring position is not treated
    as a docstring by Python: `__doc__` stays `None`, and apispec silently
    drops the endpoint from the OpenAPI schema. Instead, the docstring is
    written as a plain string with `{name}` placeholders, and this decorator
    fills them in with the given kwargs after the function is defined.
    """

    def wrap(func):
        if func.__doc__:
            try:
                func.__doc__ = func.__doc__.format(**kwargs)
            except KeyError as e:
                raise KeyError(
                    f"format_doc on {func.__qualname__}: missing placeholder {e} — "
                    f"add it to the decorator kwargs or fix the typo in the docstring"
                ) from e
            except (ValueError, IndexError) as e:
                raise type(e)(
                    f"format_doc on {func.__qualname__}: {e} — "
                    f"escape literal braces as {{{{ and }}}}"
                ) from e
        return func

    return wrap


class BaseHandler(BaselayerHandler):
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

    async def send_file(
        self,
        data,
        filename,
        output_type="pdf",
        chunk_size=1024**2,
        max_file_size=20 * 1024**2,
    ):
        """
        data : bytesIO
            File contents.
        filename : str
            Downloaded filename.
        chunk_size : int
            The stream is sent in chunks of `chunk_size` bytes (default: 1MB).
        max_file_size : int
            Filesize limit in bytes (default: 20MB)
        """
        # Adapted from
        # https://bhch.github.io/posts/2017/12/serving-large-files-with-tornado-safely-without-blocking/
        mb = 1024 * 1024 * 1
        if not (data.getbuffer().nbytes < max_file_size):
            return self.error(
                f"Refusing to send files larger than {max_file_size / mb:.2f} MB"
            )

        # do not send result via `.success`, since that uses content-type JSON
        self.set_status(200)
        if output_type == "pdf":
            self.set_header("Content-type", "application/pdf; charset='utf-8'")
            self.set_header("Content-Disposition", f"attachment; filename={filename}")
        elif output_type in ["txt", "xml", "json", "csv"]:
            self.set_header("Content-type", "text/plain")
            self.set_header("Content-Disposition", f"attachment; filename={filename}")
        else:
            self.set_header("Content-type", f"image/{output_type}")

        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )

        for i in range(ceil(max_file_size / chunk_size)):
            chunk = data.read(chunk_size)
            if not chunk:
                break
            try:
                self.write(chunk)  # write the chunk to response
                await self.flush()  # send the chunk to client
            except StreamClosedError:
                # this means the client has closed the connection
                # so break the loop
                break
            finally:
                # deleting the chunk is very important because
                # if many clients are downloading files at the
                # same time, the chunks in memory will keep
                # increasing and will eat up the RAM
                del chunk

                # pause the coroutine so other handlers can run
                await sleep(1e-9)  # 1 ns
