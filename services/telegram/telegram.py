import time

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import User, init_db
from baselayer.log import make_log
from skyportal.models import DBSession
from skyportal.utils.services import check_loaded
from skyportal.utils.telegram import (
    TelegramError,
    telegram_api,
    telegram_enabled,
    user_id_from_code,
)

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("telegram")

TITLE = cfg["app.title"]


def reply(chat_id, text):
    telegram_api("sendMessage", chat_id=chat_id, text=text)


def connect(user_id, chat_id):
    with DBSession() as session:
        user = session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            return None
        user.preferences = {
            **(user.preferences or {}),
            "telegram_integration": {"active": True, "chat_id": chat_id},
        }
        session.commit()
        username = user.username
    Flow().push(user_id, "skyportal/FETCH_USER_PROFILE")
    return username


def handle(message):
    chat = message.get("chat") or {}
    if chat.get("type") != "private":
        return
    command, _, code = (message.get("text") or "").partition(" ")
    if command != "/start" or not code.strip():
        reply(
            chat["id"],
            f"This bot sends your {TITLE} notifications. "
            f"Connect it from your notification settings in {TITLE}.",
        )
        return
    user_id = user_id_from_code(code.strip())
    username = connect(user_id, chat["id"]) if user_id is not None else None
    if username is None:
        reply(
            chat["id"],
            f"This link has expired. Open your notification settings in {TITLE} "
            "and connect Telegram again.",
        )
        return
    log(f"Connected Telegram chat for user {user_id}")
    reply(
        chat["id"],
        f"Connected to {TITLE} as @{username}. Your notifications will arrive here. "
        f"Choose which ones in your notification settings.",
    )


@check_loaded(logger=log)
def service(*args, **kwargs):
    offset = None
    while True:
        try:
            updates = telegram_api(
                "getUpdates",
                request_timeout=60,
                offset=offset,
                timeout=50,
                allowed_updates=["message"],
            )
        except TelegramError as e:
            log(f"Error fetching Telegram updates: {e}")
            time.sleep(e.retry_after or 10)
            continue
        except Exception as e:
            log(f"Error fetching Telegram updates: {e}")
            time.sleep(10)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            try:
                handle(update.get("message") or {})
            except Exception as e:
                log(f"Error handling Telegram update {update['update_id']}: {e}")


if __name__ == "__main__":
    if telegram_enabled():
        service()
    else:
        log("No Telegram bot token configured")
