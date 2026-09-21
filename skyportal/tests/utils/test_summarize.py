"""Which model a summary request uses, and what it does with a cut-off answer."""

from types import SimpleNamespace

import pytest

from skyportal.utils.summarize import summarize, user_summarizer


def _user(**openai):
    return SimpleNamespace(preferences={"summary": {"OpenAI": openai}})


def test_no_settings_without_a_key():
    assert user_summarizer(_user(active=True)) is None
    assert user_summarizer(_user(apikey="sk-abc")) is None  # not active
    assert user_summarizer(SimpleNamespace(preferences={})) is None
    assert user_summarizer(SimpleNamespace(preferences=None)) is None


def test_a_personal_key_defaults_to_openai():
    settings = user_summarizer(_user(active=True, apikey="sk-abc"))
    assert settings["api_key"] == "sk-abc"
    assert settings["base_url"] is None


def test_a_personal_key_goes_to_its_own_url():
    settings = user_summarizer(
        _user(active=True, apikey="key", base_url="https://api.anthropic.com/v1")
    )
    assert settings["base_url"] == "https://api.anthropic.com/v1"
    assert settings["api_key"] == "key"


def test_personal_model_parameters_carry_through():
    settings = user_summarizer(_user(active=True, apikey="key", model="gpt-4o-mini"))
    assert settings["model"] == "gpt-4o-mini"
    assert "apikey" not in settings and "active" not in settings


def _stub_openai(monkeypatch, content, finish_reason):
    """Stand in for the OpenAI client, returning one prepared choice."""
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ]
    )

    class _Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kw: response)
            )

    import openai

    monkeypatch.setattr(openai, "OpenAI", _Client)


@pytest.mark.parametrize("finish_reason", ["stop", None])
def test_a_finished_answer_is_kept(monkeypatch, finish_reason):
    _stub_openai(monkeypatch, "A tidy one-paragraph summary.", finish_reason)
    assert summarize("p", "c", settings={"api_key": "k"}) == (
        "A tidy one-paragraph summary."
    )


def test_an_answer_cut_off_at_max_tokens_is_refused(monkeypatch):
    # A reasoning model can spend the budget before the answer starts, leaving
    # a stub that reads like a summary. Better none than half a sentence.
    _stub_openai(monkeypatch, "SVOM\u2019s ECLAIRs instrument (", "length")
    assert summarize("p", "c", settings={"api_key": "k"}) is None


def test_no_key_asks_nothing():
    assert summarize("p", "c", settings={}) is None
