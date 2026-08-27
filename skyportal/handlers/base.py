from math import ceil

from pydantic import ValidationError as PydanticValidationError
from tornado.gen import sleep
from tornado.iostream import StreamClosedError
from tornado.web import Finish

from baselayer.app.handlers.base import BaseHandler as BaselayerHandler

from .. import __version__
from ..utils.api_validate import (
    format_validation_errors,
    path_adapters_for,
    query_dict_from,
)


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
    def prepare(self):
        # baselayer's prepare() normalizes the captured strings (strips the
        # leading slash of patterns like `(/[0-9]+)`); type them afterwards.
        result = super().prepare()
        self.coerce_path_args()
        return result

    def coerce_path_args(self):
        """Coerce captured path arguments to the types annotated by the handler
        method about to run, 400ing on a value that does not fit.

        A parameter left unannotated keeps tornado's string. ``None`` (an
        unmatched optional capture, e.g. the trailing ``(/[0-9]+)?`` in
        ``/api/obj/analysis(/[0-9]+)/corner(/[0-9]+)?``) passes through so the
        method's own default applies; annotate such a parameter ``T | None``.
        """
        adapters = path_adapters_for(type(self), self.request.method.lower())
        for index, name, adapter in adapters:
            if index >= len(self.path_args):
                break
            value = self.path_args[index]
            if value is None:
                continue
            try:
                self.path_args[index] = adapter.validate_python(value)
            except PydanticValidationError:
                self.error(f"Invalid {name}: {value}")
                raise Finish() from None

    @property
    def associated_user_object(self):
        if hasattr(self.current_user, "username"):
            return self.current_user
        return self.current_user.created_by

    def parse_body(self, model):
        """Validate the JSON request body against a pydantic model.

        Returns the parsed model instance; on failure writes the standard 400
        error response and raises tornado.web.Finish to abort the handler.
        """
        try:
            return model.model_validate(self.get_json())
        except PydanticValidationError as e:
            self.error(f"Invalid/missing parameters: {format_validation_errors(e)}")
            raise Finish() from None

    def parse_query(self, model):
        """Validate query-string arguments against a pydantic model.

        Returns the parsed model instance; on failure writes the standard 400
        error response and raises tornado.web.Finish to abort the handler.
        """
        try:
            return model.model_validate(
                query_dict_from(self.request.query_arguments, model)
            )
        except PydanticValidationError as e:
            self.error(f"Invalid/missing parameters: {format_validation_errors(e)}")
            raise Finish() from None

    def success(self, *args, **kwargs):
        super().success(*args, **kwargs, extra={"version": __version__})

    def error(self, message, *args, **kwargs):
        # Tag with handler name so users know which endpoint failed.
        if message and not str(message).startswith("["):
            message = f"[{self.__class__.__name__}] {message}"
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
