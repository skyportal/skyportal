"""Zooniverse sign-in for volunteers.

The parts that can be checked without Zooniverse: what the instance reports
about a user's link, and that a callback cannot be replayed against a user who
never started a sign-in.
"""

import uuid

import sqlalchemy as sa

from skyportal.models import DBSession, ZooniverseToken
from skyportal.tests import api


def test_auth_status_reports_unlinked_and_offers_a_sign_in_url(super_admin_token):
    status, data = api("GET", "zooniverse/auth", token=super_admin_token)
    if status == 400:
        # Instances without zooniverse.* configured say so rather than 500.
        assert "not configured" in data["message"]
        return
    assert status == 200, data
    assert data["data"]["linked"] is False
    assert "oauth/authorize" in data["data"]["authorize_url"]
    assert "response_type=code" in data["data"]["authorize_url"]


def test_callback_refuses_a_state_that_was_never_issued(super_admin_token):
    """Without this, a link could be forged by sending a victim a callback URL."""
    status, data = api(
        "GET",
        "zooniverse/auth/callback?code=abc&state=not-the-one",
        token=super_admin_token,
    )
    assert status == 400, data
    assert "state" in data["message"].lower()


def test_callback_requires_a_code(super_admin_token):
    status, data = api("GET", "zooniverse/auth/callback", token=super_admin_token)
    assert status == 400, data
    assert "code" in data["message"].lower()


def test_unlinking_forgets_the_token(super_admin_user, super_admin_token):
    record = ZooniverseToken(
        user_id=super_admin_user.id,
        access_token=f"tok-{uuid.uuid4().hex}",
        zooniverse_login="a-volunteer",
    )
    DBSession().add(record)
    DBSession().commit()

    status, data = api("DELETE", "zooniverse/auth", token=super_admin_token)
    assert status == 200, data

    DBSession().expire_all()
    assert (
        DBSession().scalar(
            sa.select(ZooniverseToken).where(
                ZooniverseToken.user_id == super_admin_user.id
            )
        )
        is None
    )
