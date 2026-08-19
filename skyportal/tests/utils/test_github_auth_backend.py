"""GitHub sign-in, and the `email_verified` claim the pipeline links on.

GitHub verifies addresses but python-social-auth drops the flag, so baselayer
ships a backend that reports it. The claim crosses a repo boundary — emitted in
baselayer, consumed by skyportal.onboarding — so these pin both halves and the
contract between them.
"""

import uuid

from baselayer.app.backends.github import VerifiedEmailGithubOAuth2
from skyportal.models import DBSession
from skyportal.onboarding import resolve_user


def github_response(emails, user_email=None):
    """What the backend hands the pipeline, given GitHub's /user/emails reply."""

    class Stubbed(VerifiedEmailGithubOAuth2):
        def __init__(self):
            pass

        def _user_data(self, access_token, path=None):
            if path == "/emails":
                return emails
            return {"id": 42, "login": "octocat", "email": user_email}

    return Stubbed().user_data("token")


class FakeStorageUser:
    def get_social_auth(self, provider, uid):
        return None


class FakeStrategy:
    def __init__(self):
        self.storage = type("S", (), {"user": FakeStorageUser()})()


class FakeBackend:
    name = "github"


def details_for(email):
    return {"username": "octocat", "email": email, "first_name": "", "last_name": ""}


def test_verified_primary_email_is_reported_as_verified():
    response = github_response(
        [{"email": "octocat@example.com", "primary": True, "verified": True}]
    )

    assert response["email"] == "octocat@example.com"
    assert response["email_verified"] is True


def test_unverified_address_is_still_reported_but_not_claimed():
    """The user still gets an account carrying their email; only the claim,
    and so the ability to match an existing account, is withheld."""
    response = github_response(
        [{"email": "octocat@example.com", "primary": True, "verified": False}]
    )

    assert response["email"] == "octocat@example.com"
    assert "email_verified" not in response


def test_no_readable_emails_falls_back_to_the_public_address():
    response = github_response([], user_email="public@example.com")

    assert response["email"] == "public@example.com"
    assert "email_verified" not in response


def test_a_verified_github_signin_links_to_the_existing_account(user):
    """The end-to-end contract: backend emits the claim, pipeline links on it."""
    user.contact_email = f"gh{uuid.uuid4().hex[:8]}@example.com"
    DBSession().commit()
    response = github_response(
        [{"email": user.contact_email, "primary": True, "verified": True}]
    )

    resolved = resolve_user(
        FakeStrategy(),
        FakeBackend(),
        f"gh-id-{uuid.uuid4().hex[:8]}",
        details_for(user.contact_email),
        response=response,
    )

    assert resolved is not None and resolved.id == user.id


def test_an_unverified_github_signin_does_not_link(user):
    user.contact_email = f"gh{uuid.uuid4().hex[:8]}@example.com"
    DBSession().commit()
    response = github_response(
        [{"email": user.contact_email, "primary": True, "verified": False}]
    )

    resolved = resolve_user(
        FakeStrategy(),
        FakeBackend(),
        f"gh-id-{uuid.uuid4().hex[:8]}",
        details_for(user.contact_email),
        response=response,
    )

    assert resolved is None
