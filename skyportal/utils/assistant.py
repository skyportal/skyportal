"""Turning a comment thread into a chat exchange, and back again.

Kept free of I/O so the parts with judgement in them can be tested directly.
"""

import json

SYSTEM_PROMPT = """You are an assistant inside SkyPortal, a data platform for \
time-domain and multi-messenger astronomy. You are answering in a comment thread \
that other astronomers can read.

You are looking at {resource}.

Use the tools to look things up rather than guessing; if the tools do not answer \
the question, say so plainly. When a value came from a circular or another \
record, quote the text it came from so a reader can check it. Be brief: this is a \
comment, not a report."""

RESOURCE_DESCRIPTIONS = {
    "sources": "source {id}",
    "gcn_event": "GCN event {id}",
    "spectra": "spectrum {id}",
    "earthquake": "earthquake {id}",
    "shift": "shift {id}",
}


def describe_resource(resource_type, resource_id):
    """A short phrase naming what the thread is attached to."""
    template = RESOURCE_DESCRIPTIONS.get(resource_type, "{type} {id}")
    return template.format(type=resource_type, id=resource_id)


def system_prompt(resource_type, resource_id):
    return SYSTEM_PROMPT.format(resource=describe_resource(resource_type, resource_id))


def build_messages(resource_type, resource_id, comments, max_comments):
    """The thread as chat messages, oldest first, newest kept when it is long."""
    messages = [
        {"role": "system", "content": system_prompt(resource_type, resource_id)}
    ]
    for comment in comments[-max_comments:]:
        role = "assistant" if comment["system"] else "user"
        text = comment["text"]
        if role == "user" and comment.get("author"):
            text = f"{comment['author']}: {text}"
        messages.append({"role": role, "content": text})
    return messages


def is_addressed_to_assistant(comment, channel):
    """Whether a new comment is a question for the assistant.

    Its own replies carry system=True, which is what stops the reply to a reply.
    """
    return comment.get("channel") == channel and not comment.get("system")


def is_enabled(cfg):
    """Whether the instance has an assistant configured."""
    return bool((cfg.get("app.assistant") or {}).get("base_url"))


def assistant_channel(cfg):
    return (cfg.get("app.assistant") or {}).get("channel") or "assistant"


def post_to_assistant(cfg, comment_class, comment_id, timeout=2):
    """Ask the assistant service to answer a comment. Fire and forget."""
    import requests

    url = f"http://{cfg['hosts.assistant']}:{cfg['ports.assistant']}"
    try:
        requests.post(
            url,
            json={"comment_class": comment_class, "comment_id": comment_id},
            timeout=timeout,
        )
    except requests.exceptions.RequestException:
        # The assistant is optional; a question going unanswered must not break
        # the comment that asked it.
        return False
    return True


def condense(text, budget=6000):
    """Fit a tool result into a context budget without handing back broken JSON.

    A record's bulk usually sits in one or two fields (an event's healpix tiles
    run to megabytes), so those are dropped whole and named, leaving the rest
    readable.
    """
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
