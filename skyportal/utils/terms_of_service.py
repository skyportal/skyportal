__all__ = ["has_accepted", "terms_of_service", "tokens_exempt"]

from functools import cache
from pathlib import Path

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import DBSession
from baselayer.log import make_log

from ..models import TermsOfServiceAcceptance

_, cfg = load_env()
log = make_log("terms_of_service")


@cache
def _text_from_file(path):
    """Read the terms from disk once; editing the file needs a restart."""
    try:
        return Path(path).read_text().strip()
    except OSError as e:
        # Same as no terms at all, so say why rather than silently letting
        # everyone past a gate the deployment meant to have.
        log(f"Could not read terms of service from {path}: {e}")
        return ""


def terms_of_service():
    terms = cfg.get("app.terms_of_service") or {}
    text = (terms.get("text") or "").strip()
    if not text and (path := (terms.get("text_file") or "").strip()):
        text = _text_from_file(path)
    if not terms.get("enabled") or not text:
        return None
    return {
        "version": str(terms.get("version", "1")),
        "title": terms.get("title") or "Terms of Service",
        "text": text,
    }


def tokens_exempt():
    """Whether an API token may act before its owner has accepted the terms.

    A token cannot be shown a dialog, so gating it blocks every script and
    service until a human logs in and clicks through.
    """
    return bool((cfg.get("app.terms_of_service") or {}).get("exempt_tokens"))


def has_accepted(user_id, version):
    with DBSession() as session:
        return (
            session.scalar(
                sa.select(TermsOfServiceAcceptance.id).where(
                    TermsOfServiceAcceptance.user_id == user_id,
                    TermsOfServiceAcceptance.version == version,
                )
            )
            is not None
        )
