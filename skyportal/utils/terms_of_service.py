__all__ = ["has_accepted", "terms_of_service"]

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import DBSession

from ..models import TermsOfServiceAcceptance

_, cfg = load_env()


def terms_of_service():
    # An enabled but blank config would block everyone behind an empty dialog.
    terms = cfg.get("app.terms_of_service") or {}
    text = (terms.get("text") or "").strip()
    if not terms.get("enabled") or not text:
        return None
    return {
        "version": str(terms.get("version", "1")),
        "title": terms.get("title") or "Terms of Service",
        "text": text,
    }


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
