"""Config parsing for the terms of service prompt.

The API tests below only cover the disabled default, because the test server
runs in its own process: enabling the terms there would put a blocking modal in
front of every frontend test. The enabled paths are exercised here instead, by
patching the nested config dict the handler module reads.
"""

import pytest

from skyportal.handlers.api import terms_of_service as tos_module
from skyportal.tests import api


@pytest.fixture()
def terms_config(monkeypatch):
    """Patch keys on the live `app.terms_of_service` dict.

    Patching that nested dict in place, rather than reassigning the dotted
    key, is what makes the change visible: `cfg.get("app.terms_of_service")`
    walks the nesting rather than reading a flat key.
    """
    terms = tos_module.cfg["app"]["terms_of_service"]

    def configure(**values):
        for key, value in values.items():
            monkeypatch.setitem(terms, key, value)

    return configure


def test_absent_by_default():
    """Nothing is prompted until a deployer opts in."""
    assert tos_module.terms_of_service() is None


def test_absent_when_disabled_even_with_text(terms_config):
    terms_config(enabled=False, text="Be excellent to each other.")
    assert tos_module.terms_of_service() is None


@pytest.mark.parametrize("text", ["", "   ", None])
def test_absent_when_enabled_without_text(terms_config, text):
    """An enabled but blank config must not block everyone behind an empty
    dialog."""
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
    # stripped, so a YAML block scalar's trailing newline is not rendered as
    # blank space in the dialog
    assert terms["text"] == "Be **excellent** to each other."


def test_version_is_stringified(terms_config):
    """The version is compared against a String column, so an int in the
    config must not produce a varchar = bigint comparison."""
    terms_config(enabled=True, text="Some terms.", version=3)
    assert tos_module.terms_of_service()["version"] == "3"


def test_title_falls_back_when_blank(terms_config):
    terms_config(enabled=True, text="Some terms.", title="")
    assert tos_module.terms_of_service()["title"] == "Terms of Service"


def test_not_required_when_instance_configures_none(view_only_token):
    """The shipped default is off, so nobody is prompted."""
    status, data = api("GET", "terms_of_service", token=view_only_token)
    assert status == 200
    assert data["data"]["required"] is False


def test_accept_rejected_when_instance_configures_none(view_only_token):
    status, data = api("POST", "terms_of_service", token=view_only_token)
    assert status == 400
    assert "no terms of service" in data["message"]
