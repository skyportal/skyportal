from math import ceil

import sqlalchemy as sa
from pydantic import ValidationError as PydanticValidationError
from tornado.gen import sleep
from tornado.iostream import StreamClosedError
from tornado.web import Finish

from baselayer.app.handlers.base import BaseHandler as BaselayerHandler
from baselayer.app.models import DBSession, Token

from .. import __version__
from ..utils.api_validate import (
    format_validation_errors,
    path_adapters_for,
    query_dict_from,
)
from ..utils.terms_of_service import has_accepted, terms_of_service


def format_doc(**kwargs):
    """Fill the `{name}` placeholders of a handler method's docstring.

    An f-string in the docstring position leaves `__doc__` at None and apispec
    silently drops the endpoint, hence the placeholders plus this decorator.
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
    terms_of_service_exempt = ()

    def prepare(self):
        # baselayer's prepare() normalizes the captured strings (strips the
        # leading slash of patterns like `(/[0-9]+)`); type them afterwards.
        result = super().prepare()
        self.coerce_path_args()
        self.enforce_terms_of_service()
        return result

    def enforce_terms_of_service(self):
        terms = terms_of_service()
        if terms is None or self.request.method in self.terms_of_service_exempt:
            return
        user_id = self.acting_user_id()
        if user_id is None or has_accepted(user_id, terms["version"]):
            return
        self.error(
            f"You must accept the {terms['title']} before using this instance.",
            status=403,
        )
        raise Finish()

    def acting_user_id(self):
        # prepare() runs before auth_or_token, so the token is not resolved yet.
        header = self.request.headers.get("Authorization") or ""
        if header.startswith("token "):
            with DBSession() as session:
                return session.scalar(
                    sa.select(Token.created_by_id).where(
                        Token.id == header.removeprefix("token").strip()
                    )
                )
        if self.current_user is None or getattr(self, "is_anonymous_user", False):
            return None
        return self.current_user.id

    def coerce_path_args(self):
        """Coerce captured path arguments to the types the handler annotates,
        400ing on a value that does not fit.

        Unannotated keeps tornado's string; ``None`` (an unmatched optional
        capture) passes through so the method default applies, so annotate such
        a parameter ``T | None``.
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

    def _validate(self, model, payload):
        """Parse `payload` with `model`, or write a 400 and abort the handler."""
        try:
            return model.model_validate(payload)
        except PydanticValidationError as e:
            self.error(f"Invalid/missing parameters: {format_validation_errors(e)}")
            raise Finish() from None

    def parse_body(self, model):
        try:
            data = self.get_json()
        except Exception as e:
            self.error(f"Error parsing JSON: {e}")
            raise Finish() from None
        return self._validate(model, data)

    def parse_query(self, model):
        return self._validate(
            model, query_dict_from(self.request.query_arguments, model)
        )

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
        if data.getbuffer().nbytes >= max_file_size:
            return self.error(
                f"Refusing to send files larger than {max_file_size / 1024**2:.2f} MB"
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

        for _ in range(ceil(max_file_size / chunk_size)):
            chunk = data.read(chunk_size)
            if not chunk:
                break
            try:
                self.write(chunk)
                await self.flush()
            except StreamClosedError:
                break
            finally:
                # concurrent downloads would otherwise pile chunks up in RAM
                del chunk
                # let other handlers run between chunks
                await sleep(1e-9)
