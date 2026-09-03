"""Answers questions asked in a reserved comment channel.

Woken by the app when a comment lands in that channel, it reads the thread, works
through SkyPortal's MCP endpoint with the asking user's own token, and posts the
answer back into the same thread.
"""

import json
import uuid

import requests
import sqlalchemy as sa
import tornado.escape
import tornado.web
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.models import (
    Comment,
    CommentOnEarthquake,
    CommentOnGCN,
    CommentOnShift,
    CommentOnSpectrum,
    DBSession,
    Group,
    Token,
)
from skyportal.utils.assistant import (
    build_messages,
    condense,
    is_addressed_to_assistant,
)

_, cfg = load_env()
log = make_log("assistant")

PROTOCOL_VERSION = "2026-07-28"
META = "io.modelcontextprotocol/"


def _endpoint():
    return f"{cfg['server.url'].rstrip('/')}/mcp"


def _headers(token, method, tool_name=None):
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if tool_name is not None:
        headers["Mcp-Name"] = tool_name
    return headers


def _rpc(token, method, params, timeout, tool_name=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": dict(params)}
    body["params"]["_meta"] = {
        f"{META}protocolVersion": PROTOCOL_VERSION,
        f"{META}clientCapabilities": {},
    }
    response = requests.post(
        _endpoint(),
        headers=_headers(token, method, tool_name),
        json=body,
        timeout=timeout,
    )
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"].get("message", "MCP call failed"))
    return payload["result"]


def list_tools(token, timeout=60):
    """Tool definitions in the shape an OpenAI-compatible chat API expects."""
    tools = _rpc(token, "tools/list", {}, timeout)["tools"]
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {"type": "object"}),
            },
        }
        for tool in tools
    ]


def call_tool(token, name, arguments, timeout=120):
    """Run one tool and return its text content."""
    result = _rpc(
        token,
        "tools/call",
        {"name": name, "arguments": arguments},
        timeout,
        tool_name=name,
    )
    parts = [
        block.get("text", "")
        for block in result.get("content", [])
        if block.get("type", "text") == "text"
    ]
    return "\n".join(parts)


CONFIG = cfg["app.assistant"] or {}
BASE_URL = CONFIG.get("base_url")
MODEL = CONFIG.get("model") or ""
API_KEY = CONFIG.get("api_key") or ""
MAX_TOOL_CALLS = int(CONFIG.get("max_tool_calls", 8))
MAX_CONTEXT = int(CONFIG.get("max_context_comments", 40))
TIMEOUT = float(CONFIG.get("request_timeout", 300))


COMMENT_MODELS = {
    "sources": (Comment, "obj_id"),
    "spectra": (CommentOnSpectrum, "spectrum_id"),
    "gcn_event": (CommentOnGCN, "gcn_id"),
    "earthquake": (CommentOnEarthquake, "earthquake_id"),
    "shift": (CommentOnShift, "shift_id"),
}
RESOURCE_FOR_MODEL = {
    model.__name__: name for name, (model, _) in COMMENT_MODELS.items()
}


def chat(messages, tools):
    """One completion from an OpenAI-compatible endpoint."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    response = requests.post(
        f"{BASE_URL.rstrip('/')}/chat/completions",
        headers=headers,
        json={"model": MODEL, "messages": messages, "tools": tools, "temperature": 0},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def answer(resource_type, resource_id, comments, token):
    """Work the question through the tools and return the reply text."""
    tools = list_tools(token)
    messages = build_messages(resource_type, resource_id, comments, MAX_CONTEXT)

    for _ in range(MAX_TOOL_CALLS):
        message = chat(messages, tools)
        calls = message.get("tool_calls") or []
        if not calls:
            return (message.get("content") or "").strip()
        messages.append(message)
        for call in calls:
            name = call["function"]["name"]
            try:
                arguments = json.loads(call["function"]["arguments"] or "{}")
                result = call_tool(token, name, arguments)
            except Exception as exc:
                result = f"tool {name} failed: {exc}"
                log(result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": condense(result),
                }
            )

    messages.append(
        {
            "role": "user",
            "content": "Answer now from what you have, and say what is still unknown.",
        }
    )
    return (chat(messages, tools).get("content") or "").strip()


def read_only_token(session, user_id):
    """A token carrying the user's group access but no ACLs, so it cannot write."""
    token = Token(created_by_id=user_id, name=f"assistant-{uuid.uuid4().hex[:8]}")
    session.add(token)
    session.commit()
    return token


def thread_for(session, model, resource_id_col, resource_id, channel):
    """The conversation so far, oldest first."""
    comments = (
        session.scalars(
            sa.select(model)
            .where(
                getattr(model, resource_id_col) == resource_id,
                model.channel == channel,
            )
            .order_by(model.created_at)
        )
        .unique()
        .all()
    )
    return [
        {
            "text": comment.text,
            "system": bool(comment.system),
            "channel": comment.channel,
            "author": comment.author.username if comment.author else None,
        }
        for comment in comments
    ]


def respond(comment_class, comment_id):
    """Answer one question and post the reply into the same channel."""
    model_name = comment_class
    resource_type = RESOURCE_FOR_MODEL.get(model_name)
    if resource_type is None:
        return
    model, resource_id_col = COMMENT_MODELS[resource_type]
    channel = CONFIG.get("channel") or "assistant"

    with DBSession() as session:
        comment = session.scalar(sa.select(model).where(model.id == comment_id))
        if comment is None:
            return
        if not is_addressed_to_assistant(
            {"channel": comment.channel, "system": bool(comment.system)}, channel
        ):
            return

        resource_id = getattr(comment, resource_id_col)
        author_id = comment.author_id
        group_ids = [group.id for group in comment.groups]
        comments = thread_for(session, model, resource_id_col, resource_id, channel)
        token = read_only_token(session, author_id)
        token_id = token.id

        try:
            text = answer(resource_type, resource_id, comments, token_id)
        except Exception as exc:
            log(f"assistant failed on {model_name} {comment_id}: {exc}")
            text = None
        finally:
            session.execute(sa.delete(Token).where(Token.id == token_id))
            session.commit()

        if not text:
            return

        reply = model(
            text=text,
            channel=channel,
            system=True,
            bot=True,
            author_id=author_id,
            groups=session.scalars(
                sa.select(Group).where(Group.id.in_(group_ids))
            ).all(),
            **{resource_id_col: resource_id},
        )
        session.add(reply)
        session.commit()
        log(f"answered {model_name} {comment_id} on {resource_type} {resource_id}")


class AssistantHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            return self.write({"status": "error", "message": "Malformed JSON"})

        if not BASE_URL:
            self.set_status(503)
            return self.write(
                {"status": "error", "message": "app.assistant.base_url is not set"}
            )

        # Answer out of band: the caller is a database hook, not a user waiting.
        IOLoop.current().run_in_executor(
            None,
            lambda: respond(data["comment_class"], data["comment_id"]),
        )
        return self.write({"status": "success"})


def make_app():
    return tornado.web.Application([(r"/", AssistantHandler)])


if __name__ == "__main__":
    if not BASE_URL:
        log("app.assistant.base_url is not set; the service will refuse requests")
    port = int(cfg["ports.assistant"])
    make_app().listen(port)
    log(f"listening on port {port}")
    IOLoop.current().start()
