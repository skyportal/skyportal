"""Unit tests for the path-parameter validation hook on BaseHandler.

The hook lives on ``skyportal.handlers.base.BaseHandler.__init_subclass__`` and
wraps each handler method (``get``/``post``/etc.) to coerce its positional
arguments to the types declared in the parameter annotations.

These tests use a minimal fake handler class (mirroring the
``__init_subclass__`` logic) so that they don't require a running server.
"""

import asyncio
import functools
import inspect
import types
import typing

_HANDLER_METHODS = ("get", "post", "put", "patch", "delete")


def _resolve_cast(annotation):
    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        non_none = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0], True
        return None, False
    return annotation, False


class FakeBase:
    """Stand-in mirroring BaseHandler's __init_subclass__ behaviour."""

    def __init__(self):
        self.errors = []

    def error(self, message, *args, **kwargs):
        self.errors.append(message)
        return ("error", message)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for method_name in _HANDLER_METHODS:
            method = cls.__dict__.get(method_name)
            if method is None:
                continue
            params = list(inspect.signature(method).parameters.values())[1:]
            validators = []
            for i, p in enumerate(params):
                if p.annotation is inspect.Parameter.empty:
                    continue
                cast_fn, allow_none = _resolve_cast(p.annotation)
                if cast_fn is None or cast_fn is str:
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


def _run(coro_or_value):
    if inspect.iscoroutine(coro_or_value):
        return asyncio.run(coro_or_value)
    return coro_or_value


def test_coerces_int():
    class H(FakeBase):
        def get(self, filter_id: int):
            return filter_id

    h = H()
    assert _run(h.get("42")) == 42
    assert h.errors == []


def test_invalid_int_returns_error():
    class H(FakeBase):
        def get(self, filter_id: int):
            return filter_id

    h = H()
    result = _run(h.get("not-a-number"))
    assert result == ("error", "Invalid filter_id: not-a-number")


def test_optional_none_passes_through():
    class H(FakeBase):
        def get(self, filter_id: int | None = None):
            return filter_id

    h = H()
    assert _run(h.get(None)) is None
    assert _run(h.get("7")) == 7


def test_pep604_union_supported():
    class H(FakeBase):
        def get(self, filter_id: int | None = None):
            return filter_id

    h = H()
    assert _run(h.get(None)) is None
    assert _run(h.get("9")) == 9


def test_str_annotation_is_noop():
    class H(FakeBase):
        def get(self, obj_id: str):
            return obj_id

    h = H()
    assert _run(h.get("ZTF24abc")) == "ZTF24abc"


def test_unannotated_param_passes_through():
    class H(FakeBase):
        def get(self, anything):
            return anything

    h = H()
    assert _run(h.get("untouched")) == "untouched"


def test_multiple_params_mixed():
    class H(FakeBase):
        def get(self, obj_id: str, filter_id: int):
            return (obj_id, filter_id)

    h = H()
    assert _run(h.get("ZTF24abc", "5")) == ("ZTF24abc", 5)


def test_works_with_float():
    class H(FakeBase):
        def get(self, value: float):
            return value

    h = H()
    assert _run(h.get("3.14")) == 3.14
    _run(h.get("bad"))
    assert h.errors == ["Invalid value: bad"]


def test_async_method():
    class H(FakeBase):
        async def get(self, filter_id: int):
            return filter_id

    h = H()
    assert _run(h.get("11")) == 11


def test_custom_validator():
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


def test_stacked_with_outer_decorator():
    """Auth-style decorators applied above the method should still see the wrapper."""

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


def test_complex_union_unsupported_skipped():
    """Unions with more than one non-None member are left untouched."""

    class H(FakeBase):
        def get(self, value: int | float | None = None):
            return value

    h = H()
    # Even with weird annotation, behavior falls through unchanged
    assert _run(h.get("42")) == "42"
