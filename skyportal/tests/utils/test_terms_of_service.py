"""Config parsing for the terms of service prompt.

The API tests only cover the disabled default: the test server runs in its own
process, so enabling the terms there would block every other frontend test.
"""

from types import SimpleNamespace

import pytest
from tornado.web import Finish

from skyportal.handlers import base as base_module
from skyportal.handlers.base import BaseHandler
from skyportal.tests import api
from skyportal.utils import terms_of_service as tos_module


@pytest.fixture(autouse=True)
def _forget_file_reads():
    """The file is read once per path, so drop that cache between tests."""
    tos_module._text_from_file.cache_clear()
    yield
    tos_module._text_from_file.cache_clear()


@pytest.fixture()
def terms_config(monkeypatch):
    terms = tos_module.cfg["app"]["terms_of_service"]

    def configure(**values):
        for key, value in values.items():
            monkeypatch.setitem(terms, key, value)

    return configure


def test_absent_by_default():
    assert tos_module.terms_of_service() is None


def test_absent_when_disabled_even_with_text(terms_config):
    terms_config(enabled=False, text="Be excellent to each other.")
    assert tos_module.terms_of_service() is None


@pytest.mark.parametrize("text", ["", "   ", None])
def test_absent_when_enabled_without_text(terms_config, text):
    terms_config(enabled=True, text=text)
    assert tos_module.terms_of_service() is None


def test_returns_configured_copy(terms_config):
    terms_config(
        enabled=True,
        title="Rules of the Road",
        text="  Be **excellent** to each other.  ",
    )
    terms = tos_module.terms_of_service()
    assert terms is not None
    assert terms["title"] == "Rules of the Road"
    assert terms["text"] == "Be **excellent** to each other."


def test_version_is_stringified(terms_config):
    """An int in the config must not produce a varchar = bigint comparison."""
    terms_config(enabled=True, text="Some terms.", version=3)
    assert tos_module.terms_of_service()["version"] == "3"


def test_title_falls_back_when_blank(terms_config):
    terms_config(enabled=True, text="Some terms.", title="")
    assert tos_module.terms_of_service()["title"] == "Terms of Service"


def test_text_read_from_a_file(terms_config, tmp_path):
    terms_file = tmp_path / "terms.md"
    terms_file.write_text("## Rules\n\nBe **excellent** to each other.\n")
    terms_config(enabled=True, text="", text_file=str(terms_file))
    assert (
        tos_module.terms_of_service()["text"]
        == "## Rules\n\nBe **excellent** to each other."
    )


def test_inline_text_wins_over_the_file(terms_config, tmp_path):
    terms_file = tmp_path / "terms.md"
    terms_file.write_text("From the file.")
    terms_config(enabled=True, text="Inline.", text_file=str(terms_file))
    assert tos_module.terms_of_service()["text"] == "Inline."


def test_absent_when_the_file_is_missing(terms_config, tmp_path):
    """An unreadable file is no terms at all, rather than an empty prompt."""
    terms_config(enabled=True, text="", text_file=str(tmp_path / "nope.md"))
    assert tos_module.terms_of_service() is None


def test_file_is_read_once(terms_config, tmp_path):
    """Read at startup: an edit needs a restart, so a re-read must not happen."""
    terms_file = tmp_path / "terms.md"
    terms_file.write_text("First.")
    terms_config(enabled=True, text="", text_file=str(terms_file))
    assert tos_module.terms_of_service()["text"] == "First."
    terms_file.write_text("Second.")
    assert tos_module.terms_of_service()["text"] == "First."


def test_tokens_are_gated_by_default():
    assert tos_module.tokens_exempt() is False


def test_tokens_exempt_when_configured(terms_config):
    terms_config(exempt_tokens=True)
    assert tos_module.tokens_exempt() is True


class _StubHandler:
    """Enough of a handler to exercise the gate without a running server."""

    terms_of_service_exempt = ()
    token_from_header = BaseHandler.token_from_header

    def __init__(self, authorization):
        headers = {"Authorization": authorization} if authorization else {}
        self.request = SimpleNamespace(headers=headers, method="GET")
        self.errors = []

    def acting_user_id(self):
        return 999

    def error(self, message, status=None):
        self.errors.append((message, status))


def _run_gate(authorization):
    handler = _StubHandler(authorization)
    try:
        BaseHandler.enforce_terms_of_service(handler)
    except Finish:
        pass
    return handler.errors


def test_a_token_is_refused_until_its_owner_accepts(terms_config, monkeypatch):
    terms_config(enabled=True, text="Some terms.", exempt_tokens=False)
    monkeypatch.setattr(base_module, "has_accepted", lambda *_: False)
    errors = _run_gate("token abc123")
    assert [status for _, status in errors] == [403]


def test_an_exempt_token_acts_before_its_owner_accepts(terms_config, monkeypatch):
    terms_config(enabled=True, text="Some terms.", exempt_tokens=True)
    monkeypatch.setattr(base_module, "has_accepted", lambda *_: False)
    assert _run_gate("token abc123") == []


def test_a_browser_session_is_still_gated_when_tokens_are_exempt(
    terms_config, monkeypatch
):
    """The exemption is for tokens only; a signed-in human still sees the dialog."""
    terms_config(enabled=True, text="Some terms.", exempt_tokens=True)
    monkeypatch.setattr(base_module, "has_accepted", lambda *_: False)
    errors = _run_gate(None)
    assert [status for _, status in errors] == [403]


def test_not_required_when_instance_configures_none(view_only_token):
    status, data = api("GET", "terms_of_service", token=view_only_token)
    assert status == 200
    assert data["data"]["required"] is False


def test_accept_rejected_when_instance_configures_none(view_only_token):
    status, data = api("POST", "terms_of_service", token=view_only_token)
    assert status == 400
    assert "no terms of service" in data["message"]


def test_has_accepted_matches_user_and_version(
    user, user2, public_terms_of_service_acceptance
):
    # has_accepted closes the scoped session, detaching the fixtures' users.
    accepted_id, other_id = user.id, user2.id
    assert tos_module.has_accepted(accepted_id, "1")
    assert not tos_module.has_accepted(accepted_id, "2")
    assert not tos_module.has_accepted(other_id, "1")
