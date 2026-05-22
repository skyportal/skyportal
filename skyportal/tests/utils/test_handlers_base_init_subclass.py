"""Unit tests for the path-parameter validation hook on ``BaseHandler``.

The production hook lives at
``skyportal.handlers.base.install_path_param_validation`` and is invoked from
``BaseHandler.__init_subclass__``. To exercise it without a running Tornado
server, these tests define a minimal ``FakeBase`` that wires the *same* helper
into its own ``__init_subclass__``.
"""

import asyncio
import functools
import inspect
import typing

import pytest

from skyportal.handlers.base import (
    HANDLER_METHODS,
    install_path_param_validation,
    resolve_cast,
)


class FakeBase:
    """Stand-in mirroring ``BaseHandler``'s subclass hook.

    Uses the same ``install_path_param_validation`` helper as the real base —
    just without the Tornado machinery that requires a running server.
    """

    def __init__(self):
        self.errors = []

    def error(self, message, *args, **kwargs):
        self.errors.append(message)
        return ("error", message)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        install_path_param_validation(cls)


def _run(coro_or_value):
    if inspect.iscoroutine(coro_or_value):
        return asyncio.run(coro_or_value)
    return coro_or_value


# ----------------------------------------------------------------------------
# resolve_cast — exercises the annotation→callable mapping in isolation.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "annotation, expected_cast, expected_allow_none",
    [
        (int, int, False),
        (float, float, False),
        (str, str, False),
        # Both `Optional[T]` and `T | None` should resolve identically. We
        # explicitly cover the legacy ``typing.Optional`` form here so the test
        # suite catches breakage if the resolver stops handling it.
        (typing.Optional[int], int, True),  # noqa: UP007, UP045
        (int | None, int, True),
        (typing.Optional[float], float, True),  # noqa: UP007, UP045
        (int | float | None, None, False),  # ambiguous union — skipped
    ],
)
def test_resolve_cast(annotation, expected_cast, expected_allow_none):
    cast_fn, allow_none = resolve_cast(annotation)
    assert cast_fn is expected_cast
    assert allow_none is expected_allow_none


# ----------------------------------------------------------------------------
# install_path_param_validation — happy path: successful coercions.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "annotation, input_value, expected",
    [
        (int, "42", 42),
        (int, "0", 0),
        (float, "3.14", 3.14),
        (str, "ZTF24abc", "ZTF24abc"),  # str annotation: no-op
        (int | None, "7", 7),
        (int | None, None, None),  # None passes through
        (int | None, "9", 9),
    ],
)
def test_coerce_success(annotation, input_value, expected):
    class H(FakeBase):
        def get(self, x: annotation):
            return x

    h = H()
    assert _run(h.get(input_value)) == expected
    assert h.errors == []


# ----------------------------------------------------------------------------
# install_path_param_validation — error path: bad coercion returns self.error().
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "annotation, bad_value, expected_msg",
    [
        (int, "abc", "Invalid x: abc"),
        (int, "1.5", "Invalid x: 1.5"),
        (float, "not-a-float", "Invalid x: not-a-float"),
    ],
)
def test_coerce_failure(annotation, bad_value, expected_msg):
    class H(FakeBase):
        def get(self, x: annotation):
            return x

    h = H()
    result = _run(h.get(bad_value))
    assert result == ("error", expected_msg)
    assert h.errors == [expected_msg]


# ----------------------------------------------------------------------------
# Mixed annotations, custom validators, decorator stacking, sync/async.
# ----------------------------------------------------------------------------


def test_multiple_params_mixed_types():
    class H(FakeBase):
        def get(self, obj_id: str, filter_id: int):
            return (obj_id, filter_id)

    h = H()
    assert _run(h.get("ZTF24abc", "5")) == ("ZTF24abc", 5)


def test_unannotated_param_passes_through():
    class H(FakeBase):
        def get(self, anything):
            return anything

    h = H()
    assert _run(h.get("untouched")) == "untouched"


def test_custom_validator_callable():
    def positive_int(v):
        n = int(v)
        if n <= 0:
            raise ValueError("must be positive")
        return n

    class H(FakeBase):
        def get(self, id: positive_int):
            return id

    h = H()
    assert _run(h.get("5")) == 5
    _run(h.get("-3"))
    assert h.errors == ["Invalid id: -3"]


def test_async_method_is_wrapped():
    class H(FakeBase):
        async def get(self, filter_id: int):
            return filter_id

    h = H()
    assert _run(h.get("11")) == 11


def test_stacked_outer_decorator_preserves_signature():
    """``functools.wraps`` on an outer decorator preserves the wrapped method's
    signature, so the hook still sees the real annotations.
    """

    def auth_required(method):
        @functools.wraps(method)
        async def wrap(self, *args, **kwargs):
            self.errors.append("auth_check")
            result = method(self, *args, **kwargs)
            if inspect.iscoroutine(result):
                return await result
            return result

        return wrap

    class H(FakeBase):
        @auth_required
        def get(self, filter_id: int):
            return filter_id

    h = H()
    assert _run(h.get("3")) == 3
    assert h.errors == ["auth_check"]


def test_handler_methods_constant_covers_http_verbs():
    """Guard against accidentally narrowing the set of intercepted methods."""
    assert set(HANDLER_METHODS) == {"get", "post", "put", "patch", "delete"}
