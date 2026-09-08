import json

import requests

SYSTEM_PROMPT = """You are an assistant inside SkyPortal, a data platform for \
time-domain and multi-messenger astronomy. You are talking with an astronomer \
in a chat panel of the app.

Use the tools to look things up rather than guessing; if the tools do not answer \
the question, say so plainly. Do not work out for yourself where a target sits \
in the sky at a given hour, when it rises or sets, or whether it is observable \
from a telescope tonight: you have no clock and no ephemeris, and the figures \
you produce will be wrong. When a value came from a circular or another \
record, quote the text it came from so a reader can check it. Be brief: this is a \
chat message, not a report."""

# Reserved, so sweeping the service's own tokens cannot hit a user's.
SERVICE_TOKEN_PREFIX = "assistant-service-"

CONTEXT_DESCRIPTIONS = {
    "source": "source {id}",
    "gcn_event": "GCN event {id}",
    "spectrum": "spectrum {id}",
    "filter": "broker filter {id}, written as broker id / filter id",
    "earthquake": "earthquake {id}",
    "shift": "shift {id}",
}


def describe_context(context_type, context_id):
    if not context_type or context_id in (None, ""):
        return None
    template = CONTEXT_DESCRIPTIONS.get(context_type, "{type} {id}")
    return template.format(type=context_type, id=context_id)


def describe_user(user):
    if not user:
        return None
    name = " ".join(
        part for part in (user.get("first_name"), user.get("last_name")) if part
    ).strip()
    username = user.get("username")
    if name and username:
        return f"{name} (@{username})"
    return name or username or None


def system_prompt(context_type=None, context_id=None, user=None):
    lines = [SYSTEM_PROMPT]
    person = describe_user(user)
    if person:
        lines.append(f"The person asking is {person}, from their SkyPortal profile.")
    context = describe_context(context_type, context_id)
    if context:
        lines.append(f"They are looking at {context}.")
    return "\n\n".join(lines)


def build_messages(
    messages, max_messages, context_type=None, context_id=None, user=None
):
    turns = [
        {
            "role": "assistant" if message["system"] else "user",
            "content": message["text"],
        }
        for message in messages[-max_messages:]
    ]
    # A model answers a question, so the last turn has to be one. Trailing
    # assistant turns are refused outright by an OpenAI-compatible server.
    while turns and turns[-1]["role"] == "assistant":
        turns.pop()
    return [
        {"role": "system", "content": system_prompt(context_type, context_id, user)},
        *turns,
    ]


def is_enabled(cfg):
    return bool((cfg.get("app.assistant") or {}).get("base_url"))


def post_to_assistant(cfg, message_id):
    url = f"http://{cfg['hosts.assistant']}:{cfg['ports.assistant']}"
    try:
        requests.post(
            url, json={"message_id": message_id}, timeout=2
        ).raise_for_status()
    except requests.exceptions.RequestException:
        return False
    return True


# Below this a per-item share carries nothing worth reading.
MIN_ITEM_SHARE = 300


def _reparsed(text):
    """A condensed result as JSON where it still parses, else as its own text."""
    try:
        return json.loads(text)
    except ValueError:
        return text


def condense(text, budget=6000):
    """Fit a tool result into a context budget without handing back broken JSON."""
    if len(text) <= budget:
        return text

    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return text[:budget] + f"\n... truncated, {len(text)} characters in total"

    if isinstance(payload, list):
        kept = []
        for item in payload:
            kept.append(item)
            if len(json.dumps(kept)) > budget:
                kept.pop()
                break
        # Two events kept whole answer less than every event cut to its date,
        # so take whichever form names more of them.
        room = max(1, min(len(payload), budget // MIN_ITEM_SHARE))
        if len(kept) >= room:
            note = f"{len(payload) - len(kept)} more of {len(payload)} not shown"
            return json.dumps({"items": kept, "note": note})
        shown = payload[:room]
        share = budget // len(shown)
        items = [
            _reparsed(condense(json.dumps(item, default=str), share)) for item in shown
        ]
        left = len(payload) - len(shown)
        note = "each item cut down to fit; asking for more per page will not add to it"
        if left:
            note = f"{len(shown)} of {len(payload)} shown, " + note
        return json.dumps({"items": items, "note": note})

    if not isinstance(payload, dict):
        return text[:budget]

    for key, value in payload.items():
        smaller = _shrunk(value, budget)
        if smaller is not None:
            payload[key] = smaller

    dropped = []
    by_size = sorted(payload, key=lambda k: -len(json.dumps(payload[k], default=str)))
    for key in by_size:
        current = json.dumps(payload, default=str)
        if len(current) <= budget:
            return current
        payload.pop(key)
        dropped.append(key)
        payload["_dropped"] = f"fields too large to show: {', '.join(dropped)}"
    return json.dumps(payload, default=str)


def _shrunk(value, budget):
    """A smaller stand-in for an oversized value, or None if there isn't one.

    A field is worth shrinking before it is worth dropping: a spectrum reduced
    to its date and instrument still answers a question, and a deleted one
    answers nothing.
    """
    if (
        isinstance(value, list)
        and len(value) >= 20
        and all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in value
        )
    ):
        # An answer can use the range a spectrum covers, never its 214 fluxes.
        return {"n": len(value), "min": min(value), "max": max(value)}
    if not isinstance(value, (list, dict)) or not value:
        return None
    if len(json.dumps(value, default=str)) <= budget:
        return None
    return _reparsed(condense(json.dumps(value, default=str), budget))
