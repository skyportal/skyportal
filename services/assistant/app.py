"""Woken by the app when a message is posted, answers it through the MCP endpoint."""

import json
import uuid

import requests
import sqlalchemy as sa
import tornado.escape
import tornado.web
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import AssistantMessage, DBSession, Token, User
from skyportal.utils.app import get_app_base_url
from skyportal.utils.assistant import build_messages, condense

_, cfg = load_env()
log = make_log("assistant")
init_db(**cfg["database"])

PROTOCOL_VERSION = "2026-07-28"
META = "io.modelcontextprotocol/"

CONFIG = cfg["app.assistant"] or {}
BASE_URL = CONFIG.get("base_url")
MODEL = CONFIG.get("model") or ""
API_KEY = CONFIG.get("api_key") or ""
MAX_TOOL_CALLS = int(CONFIG.get("max_tool_calls", 8))
MAX_CONTEXT = int(CONFIG.get("max_context_messages", 40))
TIMEOUT = float(CONFIG.get("request_timeout", 300))


def _rpc(token, method, params, timeout, tool_name=None):
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if tool_name is not None:
        headers["Mcp-Name"] = tool_name
    response = requests.post(
        f"{get_app_base_url()}/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                **params,
                "_meta": {
                    f"{META}protocolVersion": PROTOCOL_VERSION,
                    f"{META}clientCapabilities": {},
                },
            },
        },
        timeout=timeout,
    )
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"].get("message", "MCP call failed"))
    if "result" not in payload:
        raise RuntimeError(payload.get("message") or "MCP call failed")
    return payload["result"]


def list_tools(token, timeout=60):
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {"type": "object"}),
            },
        }
        for tool in _rpc(token, "tools/list", {}, timeout)["tools"]
    ]


def call_tool(token, name, arguments, timeout=120):
    result = _rpc(
        token,
        "tools/call",
        {"name": name, "arguments": arguments},
        timeout,
        tool_name=name,
    )
    return "\n".join(
        block.get("text", "")
        for block in result.get("content", [])
        if block.get("type", "text") == "text"
    )


def chat(messages, tools):
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


def answer(conversation, context_type, context_id, user, token):
    tools = list_tools(token)
    messages = build_messages(conversation, MAX_CONTEXT, context_type, context_id, user)

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


def conversation_of(session, user_id, channel):
    messages = (
        session.scalars(
            sa.select(AssistantMessage)
            .where(
                AssistantMessage.user_id == user_id,
                AssistantMessage.channel == channel
                if channel
                else AssistantMessage.channel.is_(None),
            )
            .order_by(AssistantMessage.created_at)
        )
        .unique()
        .all()
    )
    return [
        {"text": message.text, "system": bool(message.system)} for message in messages
    ]


def respond(message_id):
    with DBSession() as session:
        message = session.scalar(
            sa.select(AssistantMessage).where(AssistantMessage.id == message_id)
        )
        if message is None or message.system:
            return

        user_id = message.user_id
        channel = message.channel
        context_type, context_id = message.context_type, message.context_id
        conversation = conversation_of(session, user_id, channel)
        user = session.scalar(sa.select(User).where(User.id == user_id))
        profile = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        token_id = read_only_token(session, user_id).id

        try:
            text = answer(conversation, context_type, context_id, profile, token_id)
        except Exception as exc:
            log(f"assistant failed on message {message_id}: {exc}")
            text = "Something went wrong while looking that up."
        finally:
            session.execute(sa.delete(Token).where(Token.id == token_id))
            session.commit()

        session.add(
            AssistantMessage(
                user_id=user_id,
                channel=channel,
                text=text or "I could not find an answer to that.",
                system=True,
            )
        )
        session.commit()
        Flow().push(user_id, "skyportal/REFRESH_ASSISTANT")
        log(f"answered message {message_id} for user {user_id}")


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

        # Answer out of band: the caller is the API, not a user waiting.
        IOLoop.current().run_in_executor(None, lambda: respond(data["message_id"]))
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
