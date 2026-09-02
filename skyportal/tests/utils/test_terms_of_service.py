"""Config parsing for the terms of service prompt.

The API tests only cover the disabled default: the test server runs in its own
process, so enabling the terms there would block every other frontend test.
"""

import pytest

from skyportal.tests import api
from skyportal.utils import terms_of_service as tos_module


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
