import json

import requests

SYSTEM_PROMPT = """You are an assistant inside SkyPortal, a data platform for \
time-domain and multi-messenger astronomy. You are talking with an astronomer \
in a chat panel of the app.

Use the tools to look things up rather than guessing; if the tools do not answer \
the question, say so plainly. When a value came from a circular or another \
record, quote the text it came from so a reader can check it. Be brief: this is a \
chat message, not a report."""

CONTEXT_DESCRIPTIONS = {
    "source": "source {id}",
    "gcn_event": "GCN event {id}",
    "spectrum": "spectrum {id}",
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
    return [
        {"role": "system", "content": system_prompt(context_type, context_id, user)},
        *(
            {
                "role": "assistant" if message["system"] else "user",
                "content": message["text"],
            }
            for message in messages[-max_messages:]
        ),
    ]


def is_enabled(cfg):
    return bool((cfg.get("app.assistant") or {}).get("base_url"))


def post_to_assistant(cfg, message_id, timeout=2):
    url = f"http://{cfg['hosts.assistant']}:{cfg['ports.assistant']}"
    try:
        requests.post(url, json={"message_id": message_id}, timeout=timeout)
    except requests.exceptions.RequestException:
        return False
    return True


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
        note = f"{len(payload) - len(kept)} more of {len(payload)} not shown"
        return json.dumps({"items": kept, "note": note})

    if not isinstance(payload, dict):
        return text[:budget]

    dropped = []
    by_size = sorted(payload, key=lambda k: -len(json.dumps(payload[k], default=str)))
    for key in by_size:
        if len(json.dumps(payload, default=str)) <= budget:
            break
        payload.pop(key)
        dropped.append(key)
    if dropped:
        payload["_dropped"] = f"fields too large to show: {', '.join(dropped)}"
    return json.dumps(payload, default=str)[:budget]
