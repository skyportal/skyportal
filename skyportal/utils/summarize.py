"""Ask the model named by `analysis_services.openai_analysis_service.summary`.

Any server speaking the OpenAI chat-completions protocol works, via `base_url`.
Kept apart from the obj analysis service, which cannot carry a GcnEvent.
"""

__all__ = ["summarize", "summarizer_configured", "user_summarizer"]

import copy

from baselayer.app.env import load_env
from baselayer.log import make_log

env, cfg = load_env()
log = make_log("summarize")

SYSTEM_PROMPT = "You are an authoritative expert in astronomical time-domain research."


def _config():
    return copy.deepcopy(cfg["analysis_services.openai_analysis_service.summary"]) or {}


def summarizer_configured():
    """Whether a key is set, so callers can hide an action that cannot work."""
    return bool(_config().get("api_key"))


def user_summarizer(user):
    """A user's own model settings: their key, sent only to their own base_url."""
    preferences = (getattr(user, "preferences", None) or {}).get("summary", {})
    settings = (preferences or {}).get("OpenAI") or {}
    if not settings.get("active") or not settings.get("apikey"):
        return None
    return {
        **{k: v for k, v in settings.items() if k not in ("apikey", "active")},
        "api_key": settings["apikey"],
        "base_url": settings.get("base_url") or None,
    }


def summarize(prompt, context, timeout=60, settings=None):
    """The model's summary of `context`, or None. `settings` overrides the instance's."""
    settings = settings or _config()
    api_key = settings.get("api_key")
    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=settings.get("base_url") or None,
            timeout=timeout,
        )
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{prompt}\n'''\n{context}\n'''"},
            ],
            model=settings.get("model") or "gpt-4o-mini",
            temperature=settings.get("temperature", 0.3),
            max_tokens=settings.get("max_tokens", 350),
            top_p=settings.get("top_p", 1.0),
        )
    except Exception as e:
        log(f"summarization failed: {e}")
        return None

    text = (response.choices[0].message.content or "").strip()
    return text or None
