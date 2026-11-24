import functools
import hashlib
import hmac
import time

import requests

from baselayer.app.env import load_env

_, cfg = load_env()

LINK_LIFETIME_SECONDS = 3600


class TelegramError(Exception):
    def __init__(self, description, retry_after=None):
        super().__init__(description)
        self.retry_after = retry_after


def telegram_enabled():
    return bool(cfg["telegram.bot_token"])


def telegram_api(method, request_timeout=10, **params):
    if "text" in params:
        # Stops Telegram from linking SkyPortal usernames to Telegram accounts
        params["text"] = params["text"].replace("@", "@⁠")
    response = requests.post(
        f"https://api.telegram.org/bot{cfg['telegram.bot_token']}/{method}",
        json=params,
        timeout=request_timeout,
    )
    data = response.json()
    if not data.get("ok"):
        raise TelegramError(
            data.get("description", f"Telegram {method} failed"),
            (data.get("parameters") or {}).get("retry_after"),
        )
    return data["result"]


@functools.cache
def bot_username():
    return telegram_api("getMe")["username"]


def _signature(user_id, expires):
    return hmac.new(
        cfg["app.secret_key"].encode(),
        f"telegram:{user_id}:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()[:32]


def link_url(user_id):
    expires = int(time.time()) + LINK_LIFETIME_SECONDS
    code = f"{user_id}-{expires}-{_signature(user_id, expires)}"
    return f"https://t.me/{bot_username()}?start={code}"


def user_id_from_code(code):
    try:
        user_id, expires, signature = code.split("-")
        user_id, expires = int(user_id), int(expires)
    except ValueError:
        return None
    if expires < time.time():
        return None
    if not hmac.compare_digest(signature, _signature(user_id, expires)):
        return None
    return user_id
