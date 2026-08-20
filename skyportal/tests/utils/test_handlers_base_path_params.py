"""Unit tests for path-parameter typing on ``BaseHandler``.

``BaseHandler.prepare`` coerces the strings tornado captures from the URL to
the types the handler method annotates, and ``path_parameters_from`` documents
those same annotations in the OpenAPI spec. Most of these tests borrow the real
``coerce_path_args`` onto a minimal handler stand-in; the last few drive it
through a real tornado request, where the ordering against the handler method
matters.
"""

import json
import typing
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import Field
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, Finish

from baselayer.app.handlers.base import BaseHandler as BaselayerHandler
from skyportal.handlers.base import BaseHandler
from skyportal.utils.api_validate import path_adapters_for, path_parameters_from


class FakeHandler:
    """Stand-in exposing what ``coerce_path_args`` touches: the captured
    arguments, the request method, and ``error``."""

    coerce_path_args = BaseHandler.coerce_path_args

    def __init__(self, path_args, method="GET"):
        self.path_args = list(path_args)
        self.request = SimpleNamespace(method=method)
        self.errors = []

    def error(self, message, *args, **kwargs):
        self.errors.append(message)


def coerce(handler):
    """Run the coercion, reporting whether the request was aborted."""
    try:
        handler.coerce_path_args()
    except Finish:
        return False
    return True


# ----------------------------------------------------------------------------
# Coercion: happy path.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "annotation, captured, expected",
    [
        (int, "42", 42),
        (int, "0", 0),
        (float, "3.14", 3.14),
        (str, "ZTF24abc", "ZTF24abc"),
        # Both `Optional[T]` and `T | None` resolve identically; the legacy
        # `typing.Optional` form is covered explicitly so the suite catches
        # breakage if it stops being handled.
        (typing.Optional[int], "7", 7),  # noqa: UP007, UP045
        (int | None, "9", 9),
        # Unmatched optional captures arrive as None and must reach the
        # method untouched so its own default applies.
        (int | None, None, None),
        (typing.Literal["results", "plot"], "plot", "plot"),
        (typing.Annotated[int, Field(description="Photometry ID")], "5", 5),
    ],
)
def test_coerce_success(annotation, captured, expected):
    class H(FakeHandler):
        def get(self, x: annotation):
            pass

    handler = H([captured])
    assert coerce(handler) is True
    assert handler.path_args == [expected]
    assert handler.errors == []


# ----------------------------------------------------------------------------
# Coercion: error path, 400 and abort without invoking the handler method.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "annotation, captured, expected_msg",
    [
        (int, "abc", "Invalid x: abc"),
        (int, "1.5", "Invalid x: 1.5"),
        (float, "not-a-float", "Invalid x: not-a-float"),
        (typing.Literal["results", "plot"], "corner", "Invalid x: corner"),
        (typing.Annotated[int, Field(gt=0)], "-3", "Invalid x: -3"),
    ],
)
def test_coerce_failure(annotation, captured, expected_msg):
    class H(FakeHandler):
        def get(self, x: annotation):
            pass

    handler = H([captured])
    assert coerce(handler) is False
    assert handler.errors == [expected_msg]


# ----------------------------------------------------------------------------
# Signature handling.
# ----------------------------------------------------------------------------


def test_mixed_and_unannotated_params():
    class H(FakeHandler):
        def get(self, obj_id: str, filter_id: int, anything):
            pass

    handler = H(["ZTF24abc", "5", "untouched"])
    assert coerce(handler) is True
    assert handler.path_args == ["ZTF24abc", 5, "untouched"]


def test_keyword_only_params_are_not_path_params():
    """Pydantic body/query models are keyword-only, so they must not consume a
    positional slot and shift the coercion indices."""

    class H(FakeHandler):
        def post(self, obj_id: str, *, body: int = None):
            pass

    assert [name for _, name, _ in path_adapters_for(H, "post")] == ["obj_id"]
    # signatures are fixed at import time, so the lookup is cached per class
    assert path_adapters_for(H, "post") is path_adapters_for(H, "post")


def test_method_is_selected_by_request_method():
    class H(FakeHandler):
        def get(self, x: int):
            pass

        def post(self, x: str):
            pass

    handler = H(["7"], method="POST")
    assert coerce(handler) is True
    assert handler.path_args == ["7"]


def test_fewer_captures_than_params():
    class H(FakeHandler):
        def get(self, x: int, y: int = None):
            pass

    handler = H(["3"])
    assert coerce(handler) is True
    assert handler.path_args == [3]


# ----------------------------------------------------------------------------
# The same annotations drive the OpenAPI `in: path` entries.
# ----------------------------------------------------------------------------


def test_path_parameters_from_signature():
    class H(FakeHandler):
        def get(
            self,
            obj_id: typing.Annotated[str, Field(description="ID of the object")],
            filter_id: int,
            plot_number: int | None = None,
            anything=None,
        ):
            pass

    parameters = path_parameters_from(
        H.get, "/api/sources/{obj_id}/filters/{filter_id}/{plot_number}/{anything}"
    )
    assert parameters == [
        {
            "in": "path",
            "name": "obj_id",
            "required": True,
            "description": "ID of the object",
            "schema": {"type": "string"},
        },
        {
            "in": "path",
            "name": "filter_id",
            "required": True,
            "schema": {"type": "integer"},
        },
        # `T | None` is an optional trailing capture, not a nullable parameter
        {
            "in": "path",
            "name": "plot_number",
            "required": True,
            "schema": {"type": "integer"},
        },
        # unannotated captures document as strings
        {
            "in": "path",
            "name": "anything",
            "required": True,
            "schema": {"type": "string"},
        },
    ]


def test_path_parameters_track_the_rendered_path():
    """Only the placeholders a path actually has get documented, so the
    `multiple` variant of a route cannot document its trailing ID."""

    class H(FakeHandler):
        def get(self, obj_id: str, comment_id: int = None):
            pass

    assert [
        p["name"] for p in path_parameters_from(H.get, "/api/sources/{obj_id}")
    ] == ["obj_id"]


# ----------------------------------------------------------------------------
# End to end through tornado: `prepare` runs before the method, so the method
# receives typed arguments and a bad capture never reaches it.
# ----------------------------------------------------------------------------


class EchoHandler(BaseHandler):
    def get(self, obj_id: str, filter_id: int, plot_number: int | None = None):
        self.write(
            {"types": [type(a).__name__ for a in (obj_id, filter_id, plot_number)]}
        )


class TornadoPathArgTest(AsyncHTTPTestCase):
    """The coercion has to land between tornado capturing the URL and calling
    the method, which only a real request exercises."""

    def get_app(self):
        return Application(
            [(r"/api/sources/([^/]+)/filters/([^/]+)(?:/([0-9]+))?", EchoHandler)]
        )

    def setUp(self):
        # This handler touches no database, so stub baselayer's per-request
        # session hooks. Both have to go together: prepare() is what gives a
        # request its own `session_context_id`, and without that on_finish()
        # would DBSession.remove() the session the test fixtures are using and
        # strand their transaction.
        for name in ("prepare", "on_finish"):
            patcher = patch.object(BaselayerHandler, name, lambda self: None)
            patcher.start()
            self.addCleanup(patcher.stop)
        super().setUp()

    def test_method_receives_coerced_arguments(self):
        response = self.fetch("/api/sources/ZTF24abc/filters/5/2")
        assert response.code == 200
        assert json.loads(response.body)["types"] == ["str", "int", "int"]

    def test_unmatched_optional_capture_stays_none(self):
        response = self.fetch("/api/sources/ZTF24abc/filters/5")
        assert response.code == 200
        assert json.loads(response.body)["types"] == ["str", "int", "NoneType"]

    def test_bad_capture_400s_before_the_method_runs(self):
        response = self.fetch("/api/sources/ZTF24abc/filters/abc")
        assert response.code == 400
        assert "Invalid filter_id: abc" in json.loads(response.body)["message"]
