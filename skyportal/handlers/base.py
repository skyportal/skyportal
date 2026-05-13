from math import ceil

from tornado.gen import sleep
from tornado.iostream import StreamClosedError

from baselayer.app.handlers.base import BaseHandler as BaselayerHandler

from .. import __version__


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
