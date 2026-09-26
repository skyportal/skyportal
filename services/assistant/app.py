"""Woken by the app when a message is posted, answers it through the MCP endpoint."""

import json
import re
import time
import uuid

import requests
import sqlalchemy as sa
import tornado.escape
import tornado.web
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import ACL, init_db, session_context_id
from baselayer.log import make_log
from skyportal.models import (
    AssistantMessage,
    Comment,
    DBSession,
    Group,
    GroupUser,
    Token,
    User,
    UserNotification,
)
from skyportal.utils.app import get_app_base_url
from skyportal.utils.assistant import (
    SERVICE_TOKEN_PREFIX,
    build_messages,
    chat_payload,
    condense,
    offered_tools,
    proposal,
    record_call,
)

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
# request_timeout bounds one call; a question is many, so bound those too.
ANSWER_TIMEOUT = float(CONFIG.get("answer_timeout", 180))
# A reasoning model spends most of its tokens thinking, which a chat answer
# drawn from tool results does not need.
THINKING = bool(CONFIG.get("thinking", False))
MAX_CONTEXT = int(CONFIG.get("max_context_messages", 40))
# How much of one tool result the model gets to see. Prompt processing is cheap
# next to generation, so this buys breadth for very little time.
RESULT_BUDGET = int(CONFIG.get("result_budget", 20000))
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


def list_tools(token, context_type=None):
    """The tools to offer, as the chat API wants them."""
    tools = offered_tools(_rpc(token, "tools/list", {}, 60)["tools"], context_type)
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


def call_tool(token, name, arguments, offered):
    """Run one tool, refusing any that was not offered.

    The token carries the user's own permissions, so this is what stops a model
    talked into it by the text of a circular from writing anything.
    """
    if name not in offered:
        raise PermissionError(f"{name} was not offered for this question")
    result = _rpc(
        token,
        "tools/call",
        {"name": name, "arguments": arguments},
        120,
        tool_name=name,
    )
    return "\n".join(
        block.get("text", "")
        for block in result.get("content", [])
        if block.get("type", "text") == "text"
    )


def chat(messages, tools, timeout=None):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    response = requests.post(
        f"{BASE_URL.rstrip('/')}/chat/completions",
        headers=headers,
        json=chat_payload(MODEL, messages, tools, THINKING),
        timeout=timeout or TIMEOUT,
    )
    if response.status_code >= 400:
        # The status alone says nothing: a refused request looks identical
        # whether the context was too long, a tool schema was rejected or the
        # model was unavailable, and the answer the user sees is the same
        # sentence either way. The server's own words are the only thing that
        # tells them apart, so they go in the log.
        log(
            f"model refused the request: {response.status_code} "
            f"{response.text[:600]} "
            f"(messages={len(messages)}, tools={len(tools)}, "
            f"payload={len(json.dumps(messages)) + len(json.dumps(tools))} chars)"
        )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def remaining(deadline, floor=5.0):
    """Seconds left before the answer is due, or None when too few to be useful."""
    left = deadline - time.monotonic()
    return left if left >= floor else None


def answer(conversation, context_type, context_id, user, token):
    """The answer, the tools it took to get there, and any filter it built."""
    tools = list_tools(token, context_type)
    offered = {tool["function"]["name"] for tool in tools}
    messages = build_messages(conversation, MAX_CONTEXT, context_type, context_id, user)
    trace = []

    deadline = time.monotonic() + ANSWER_TIMEOUT
    # One round-trip can ask for several tools at once, so count the calls
    # themselves. Counting round-trips lets a paging model run four times over.
    calls_made = 0
    while calls_made < MAX_TOOL_CALLS:
        if (left := remaining(deadline)) is None:
            log("out of time before the model finished; answering from what it has")
            break
        message = chat(messages, tools, timeout=left)
        calls = message.get("tool_calls") or []
        if not calls:
            return (message.get("content") or "").strip(), trace, proposal(trace)
        messages.append(message)
        calls_made += len(calls)
        for call in calls:
            name = call["function"]["name"]
            arguments, ok = {}, True
            try:
                arguments = json.loads(call["function"]["arguments"] or "{}")
                result = call_tool(token, name, arguments, offered)
            except Exception as exc:
                ok = False
                result = f"tool {name} failed: {exc}"
                log(result)
            trace.append(record_call(name, arguments, result, ok))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": condense(result, RESULT_BUDGET),
                }
            )

    messages.append(
        {
            "role": "user",
            "content": "Answer now from what you have, and say what is still unknown.",
        }
    )
    if (left := remaining(deadline)) is None:
        return (
            "I ran out of time working that out. Please ask again, or narrow the question.",
            trace,
            proposal(trace),
        )
    # No tools on the last word, or the model asks for another instead of
    # answering and the reply comes back empty.
    text = (chat(messages, [], timeout=left).get("content") or "").strip()
    return text, trace, proposal(trace)


def service_token(session, user_id):
    """A short-lived token carrying the user's own access.

    An admin sees things through an ACL rather than through group membership, so
    a token without their ACLs would leave the assistant insisting a filter they
    are looking at does not exist. Writing is refused in `call_tool` instead.
    """
    user = session.scalar(sa.select(User).where(User.id == user_id))
    token = Token(
        created_by_id=user_id, name=f"{SERVICE_TOKEN_PREFIX}{uuid.uuid4().hex}"
    )
    # permissions, not acls: most of a user's ACLs reach them through a role.
    token.acls = session.scalars(
        sa.select(ACL).where(ACL.id.in_(user.permissions))
    ).all()
    session.add(token)
    session.commit()
    return token


def clear_service_tokens():
    """Drop the tokens a previous run left behind by dying mid-answer."""
    session_context_id.set(uuid.uuid4().hex)
    try:
        with DBSession() as session:
            cleared = session.execute(
                sa.delete(Token).where(Token.name.like(f"{SERVICE_TOKEN_PREFIX}%"))
            ).rowcount
            session.commit()
    except Exception as exc:
        log(f"could not clear the tokens of a previous run: {exc}")
        return
    finally:
        DBSession.remove()
    if cleared:
        log(f"cleared {cleared} token(s) left by a previous run")


def misconfigured(exc):
    """Whether the endpoint refused the credentials, the model or the URL, which
    asking again will not fix."""
    response = getattr(exc, "response", None)
    return response is not None and response.status_code in (401, 403, 404)


def already_answered(session, message):
    """Whether a reply to this message has already been written."""
    return (
        session.scalar(
            sa.select(AssistantMessage.id)
            .where(
                AssistantMessage.user_id == message.user_id,
                AssistantMessage.channel == message.channel
                if message.channel
                else AssistantMessage.channel.is_(None),
                AssistantMessage.system.is_(True),
                AssistantMessage.id > message.id,
            )
            .limit(1)
        )
        is not None
    )


def conversation_of(session, user_id, channel, up_to_id=None):
    """The conversation as it stood when `up_to_id` was asked.

    Anything written afterwards, including an earlier failure's apology, is not
    context for this answer.
    """
    query = sa.select(AssistantMessage).where(
        AssistantMessage.user_id == user_id,
        AssistantMessage.channel == channel
        if channel
        else AssistantMessage.channel.is_(None),
    )
    if up_to_id is not None:
        query = query.where(AssistantMessage.id <= up_to_id)
    messages = (
        session.scalars(query.order_by(AssistantMessage.created_at)).unique().all()
    )
    return [
        {"text": message.text, "system": bool(message.system)} for message in messages
    ]


def _parse_urgency(answer):
    """Pull a trailing ``NOTIFY: yes/no`` marker off a triage answer.

    Returns (is_urgent, text_without_the_marker). A missing marker is treated as
    not urgent, so a model that forgets it never spams notifications.
    """
    text = answer or ""
    match = None
    for m in re.finditer(r"(?im)^[ \t>*_-]*NOTIFY:\s*(yes|no)\b.*$", text):
        match = m
    if match is None:
        return False, text.strip()
    is_urgent = match.group(1).lower() == "yes"
    return is_urgent, (text[: match.start()] + text[match.end() :]).strip()


def post_triage_comment(session, author_id, notify, context_type, context_id, answer):
    """Post the full triage as a bot comment on the source, visible to the query's
    group(s). Only for source-scoped query runs, whose notify carries
    ``comment_groups``; interactive chats (no comment_groups) never post.
    """
    if not isinstance(notify, dict):
        return
    group_ids = notify.get("comment_groups") or []
    text = (answer or "").strip()
    if not (group_ids and context_type == "source" and context_id and text):
        return
    groups = session.scalars(sa.select(Group).where(Group.id.in_(group_ids))).all()
    if not groups:
        return
    session.add(
        Comment(
            text=text,
            obj_id=context_id,
            author_id=author_id,
            groups=list(groups),
            bot=True,
            origin="skybot",
        )
    )


def deliver_notifications(session, author_id, notify, context_type, context_id, answer):
    """Notify the recipients a task run named, with its answer.

    Groups expand to their members; a named user must share a group with the
    author, so a run cannot notify people outside the author's groups.
    """
    if not isinstance(notify, dict):
        return
    wanted = {int(u) for u in (notify.get("users") or [])}
    for gid in notify.get("groups") or []:
        wanted.update(
            session.scalars(
                sa.select(GroupUser.user_id).where(GroupUser.group_id == int(gid))
            ).all()
        )
    wanted.discard(author_id)
    if not wanted:
        return
    author = session.scalar(sa.select(User).where(User.id == author_id))
    if author is not None and author.is_bot:
        # A bot's recipients were resolved and authorised by the triggering query
        # (its subscribers, in its group), so deliver to them directly.
        allowed = wanted
    else:
        # A person's run may only notify people they share a group with.
        author_groups = set(
            session.scalars(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == author_id)
            ).all()
        )
        allowed = set(
            session.scalars(
                sa.select(GroupUser.user_id).where(
                    GroupUser.user_id.in_(wanted),
                    GroupUser.group_id.in_(author_groups or {-1}),
                )
            ).all()
        )
    if not allowed:
        return
    snippet = " ".join((answer or "").split())
    if len(snippet) > 300:
        snippet = snippet[:297] + "..."
    where = f" on {context_type} {context_id}" if context_id else ""
    text = (
        f"Assistant triage{where}: {snippet}"
        if snippet
        else f"An assistant run{where} produced no answer."
    )
    url = f"/source/{context_id}" if context_type == "source" and context_id else None
    for uid in allowed:
        session.add(
            UserNotification(
                user_id=uid, text=text, notification_type="assistant", url=url
            )
        )


def respond(message_id):
    session_context_id.set(uuid.uuid4().hex)
    try:
        with DBSession() as session:
            message = session.scalar(
                sa.select(AssistantMessage).where(AssistantMessage.id == message_id)
            )
            if message is None or message.system:
                return

            user_id = message.user_id
            channel = message.channel
            context_type, context_id = message.context_type, message.context_id
            notify = message.notify
            if already_answered(session, message):
                log(f"message {message_id} already has an answer; not answering twice")
                return
            conversation = conversation_of(
                session, user_id, channel, up_to_id=message.id
            )
            user = session.scalar(sa.select(User).where(User.id == user_id))
            profile = {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            token_id = service_token(session, user_id).id

        # Answering takes minutes, so no connection is held while it runs.
        trace, built = [], None
        try:
            text, trace, built = answer(
                conversation, context_type, context_id, profile, token_id
            )
        except Exception as exc:
            log(f"assistant failed on message {message_id}: {exc}")
            text = (
                "The assistant is not set up correctly; tell an administrator."
                if misconfigured(exc)
                else "Something went wrong while looking that up."
            )

        # A query run ends with a NOTIFY: yes/no marker deciding whether it is
        # worth a notification; the comment is posted either way.
        is_urgent, text = _parse_urgency(text)

        with DBSession() as session:
            session.execute(sa.delete(Token).where(Token.id == token_id))
            asked = session.execute(
                sa.select(AssistantMessage.channel).where(
                    AssistantMessage.id == message_id
                )
            ).one_or_none()
            if asked is not None:
                session.add(
                    AssistantMessage(
                        user_id=user_id,
                        channel=asked[0],
                        text=text or "I could not find an answer to that.",
                        system=True,
                        tool_calls=trace or None,
                        proposal=built,
                    )
                )
                if notify:
                    # The bot comment is the durable record; a notification only
                    # fires when the triage flagged itself urgent, to avoid spam.
                    post_triage_comment(
                        session, user_id, notify, context_type, context_id, text
                    )
                    if is_urgent:
                        deliver_notifications(
                            session, user_id, notify, context_type, context_id, text
                        )
            session.commit()

        if asked is None:
            log(f"message {message_id} is gone; dropping the answer")
            return

        Flow().push(user_id, "skyportal/REFRESH_ASSISTANT")
        log(f"answered message {message_id} for user {user_id}")
    finally:
        DBSession.remove()


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
    clear_service_tokens()
    port = int(cfg["ports.assistant"])
    make_app().listen(port)
    log(f"listening on port {port}")
    IOLoop.current().start()
