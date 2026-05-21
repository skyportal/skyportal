"""Unit tests for skyportal.utils.handlers."""

from skyportal.utils.handlers import validate_path_params


class FakeHandler:
    """Minimal stand-in for a Tornado handler.

    Captures ``self.error(...)`` calls in ``self.errors`` so tests can assert
    on the message without needing a running server.
    """

    def __init__(self):
        self.errors = []

    def error(self, message, *args, **kwargs):
        self.errors.append(message)
        return ("error", message)


def test_coerces_int():
    class H(FakeHandler):
        @validate_path_params(filter_id=int)
        def get(self, filter_id):
            return filter_id

    h = H()
    assert h.get("42") == 42
    assert h.errors == []


def test_invalid_int_returns_error():
    class H(FakeHandler):
        @validate_path_params(filter_id=int)
        def get(self, filter_id):
            return filter_id

    h = H()
    result = h.get("not-a-number")
    assert result == ("error", "Invalid filter_id: not-a-number")
    assert h.errors == ["Invalid filter_id: not-a-number"]


def test_none_value_with_default():
    class H(FakeHandler):
        @validate_path_params(filter_id=(int, None))
        def get(self, filter_id=None):
            return filter_id

    h = H()
    assert h.get(None) is None
    assert h.get("7") == 7
    assert h.errors == []


def test_empty_string_with_default():
    class H(FakeHandler):
        @validate_path_params(filter_id=(int, None))
        def get(self, filter_id=None):
            return filter_id

    h = H()
    assert h.get("") is None


def test_none_value_required_passes_through():
    """If no default is set, None passes through unchanged (the handler decides)."""

    class H(FakeHandler):
        @validate_path_params(filter_id=int)
        def get(self, filter_id):
            return filter_id

    h = H()
    assert h.get(None) is None
    assert h.errors == []


def test_multiple_params():
    class H(FakeHandler):
        @validate_path_params(obj_id=str, filter_id=int)
        def get(self, obj_id, filter_id):
            return (obj_id, filter_id)

    h = H()
    assert h.get("ZTF24abc", "5") == ("ZTF24abc", 5)


def test_kwargs_supported():
    class H(FakeHandler):
        @validate_path_params(filter_id=int)
        def get(self, filter_id=None):
            return filter_id

    h = H()
    assert h.get(filter_id="9") == 9


def test_only_named_params_touched():
    """Params not listed in the decorator are passed through unchanged."""

    class H(FakeHandler):
        @validate_path_params(filter_id=int)
        def get(self, filter_id, other):
            return (filter_id, other)

    h = H()
    assert h.get("3", "untouched") == (3, "untouched")


def test_works_with_float():
    class H(FakeHandler):
        @validate_path_params(value=float)
        def get(self, value):
            return value

    h = H()
    assert h.get("3.14") == 3.14
    h.get("bad")
    assert h.errors == ["Invalid value: bad"]


def test_works_on_async_method():
    """The wrapped method may be async; the wrapper returns its coroutine for Tornado to await."""
    import asyncio

    class H(FakeHandler):
        @validate_path_params(filter_id=int)
        async def get(self, filter_id):
            return filter_id

    h = H()
    coro = h.get("11")
    assert asyncio.iscoroutine(coro)
    assert asyncio.run(coro) == 11


def test_async_method_error_short_circuits():
    """When validation fails, the async method is not even called — error returned synchronously."""

    class H(FakeHandler):
        @validate_path_params(filter_id=int)
        async def get(self, filter_id):
            raise AssertionError("should not be called")

    h = H()
    result = h.get("oops")
    assert result == ("error", "Invalid filter_id: oops")
