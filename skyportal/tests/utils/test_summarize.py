"""Which model a summary request uses: the instance's, or the user's own."""

from types import SimpleNamespace

from skyportal.utils.summarize import user_summarizer


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
