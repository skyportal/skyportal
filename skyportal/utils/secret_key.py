"""Give the container its own app.secret_key before the app starts.

The image bakes docker.yaml in as config.yaml, so every container built from
it would otherwise run on the key published in config.yaml.defaults -- which
is the one the app now refuses to start on. The generated key is kept in the
persistentdata volume, so sessions and the credentials encrypted under it
survive a restart; a fresh volume means a fresh key, and old sessions stop
working, which is the right trade for a key nobody chose.

Set app.secret_key yourself for anything beyond a single-container
deployment: replicas each generate their own, and a session is only valid on
the one that issued it.
"""

import pathlib
import re
import secrets
import sys

DEFAULT = "abc01234"
CONFIG = pathlib.Path("config.yaml")
STORE = pathlib.Path("persistentdata/secret_key")
SECRET_KEY_LINE = re.compile(r"^(\s*)secret_key:.*$", re.MULTILINE)


def current(text):
    match = SECRET_KEY_LINE.search(text)
    return match.group(0).split(":", 1)[1].strip() if match else None


def stored_key():
    """The key this volume has already been given, or a new one."""
    if STORE.exists() and (key := STORE.read_text().strip()):
        return key
    key = secrets.token_urlsafe(32)
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(key + "\n")
    STORE.chmod(0o600)
    return key


def ensure_secret_key():
    if not CONFIG.exists():
        return 0
    text = CONFIG.read_text()
    present = current(text)
    if present not in (None, "", DEFAULT):
        return 0  # someone set one; leave it alone

    key = stored_key()
    if present is not None:
        text = SECRET_KEY_LINE.sub(rf"\g<1>secret_key: {key}", text, count=1)
    elif re.search(r"^app:$", text, re.MULTILINE):
        text = re.sub(
            r"^app:$", f"app:\n  secret_key: {key}", text, count=1, flags=re.MULTILINE
        )
    else:
        # No app block to extend; start one rather than write nothing and
        # leave the app on the key it refuses to run with.
        text = text.rstrip("\n") + f"\n\napp:\n  secret_key: {key}\n"
    CONFIG.write_text(text)
    print("generated an app.secret_key for this container", file=sys.stderr)
    return 0
