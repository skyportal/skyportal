import datetime
import uuid

import pytest
import sqlalchemy as sa

from skyportal.models import DBSession, GroupUser, StreamUser, User
from skyportal.onboarding import (
    cfg,
    create_user,
    get_username,
    setup_invited_user_permissions,
    user_details,
)
from skyportal.tests.fixtures import InvitationFactory


class FakeStorageUser:
    """The slice of PSA's user storage that onboarding touches."""

    def __init__(self):
        self.changed_users = []

    def get_username(self, user):
        return user.username

    def changed(self, user):
        self.changed_users.append(user)


class FakeStorage:
    def __init__(self):
        self.user = FakeStorageUser()


class FakeStrategy:
    def __init__(self, session_values=None, settings=None):
        self.storage = FakeStorage()
        self.session_values = session_values or {}
        self.settings = settings or {}
        self.created_users = []

    def session_get(self, name, default=None):
        return self.session_values.get(name, default)

    def setting(self, name, default=None, backend=None):
        return self.settings.get(name, default)

    def create_user(self, **kwargs):
        user = User(**kwargs)
        DBSession().add(user)
        DBSession().flush()
        self.created_users.append(user)
        return user


class FakeBackend:
    def __init__(self, settings=None):
        self.settings = settings or {}

    def setting(self, name, default=None):
        return self.settings.get(name, default)


@pytest.fixture()
def invitations_enabled():
    previous = cfg["invitations"]["enabled"]
    cfg["invitations"]["enabled"] = True
    yield
    cfg["invitations"]["enabled"] = previous


@pytest.fixture()
def invitations_disabled():
    previous = cfg["invitations"]["enabled"]
    cfg["invitations"]["enabled"] = False
    yield
    cfg["invitations"]["enabled"] = previous


@pytest.fixture()
def pipeline_invitation(user):
    previous = cfg["invitations"].get("disable_emailing", False)
    cfg["invitations"]["disable_emailing"] = True
    invitation = InvitationFactory(invited_by=user)
    DBSession().commit()
    yield invitation
    InvitationFactory.teardown(invitation)
    cfg["invitations"]["disable_emailing"] = previous


@pytest.fixture()
def cleanup_users():
    created = []
    yield created
    for user in created:
        obj = DBSession().get(User, user.id) if user.id is not None else None
        if obj is not None:
            DBSession().delete(obj)
    DBSession().commit()


def details_for(username, email=None):
    return {
        "username": username,
        "email": email or f"{username}@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }


def test_create_user_returns_existing_user_by_oauth_uid(invitations_disabled, user):
    user.oauth_uid = f"uid-{uuid.uuid4().hex[:8]}"
    DBSession().commit()

    result = create_user(
        FakeStrategy(), details_for(user.username), FakeBackend(), user.oauth_uid
    )

    assert result["is_new"] is False
    assert result["user"].id == user.id


def test_create_user_requires_invite_token_when_invitations_enabled(
    invitations_enabled,
):
    with pytest.raises(Exception, match="Missing invite token"):
        create_user(
            FakeStrategy(),
            details_for(f"invitee{uuid.uuid4().hex[:8]}"),
            FakeBackend(),
            f"uid-{uuid.uuid4().hex[:8]}",
        )


def test_create_user_rejects_unknown_invite_token(invitations_enabled):
    strategy = FakeStrategy(session_values={"invite_token": uuid.uuid4().hex})
    with pytest.raises(Exception, match="Invalid invite token"):
        create_user(
            strategy,
            details_for(f"invitee{uuid.uuid4().hex[:8]}"),
            FakeBackend(),
            f"uid-{uuid.uuid4().hex[:8]}",
        )


def test_create_user_rejects_used_invitation(invitations_enabled, pipeline_invitation):
    pipeline_invitation.used = True
    DBSession().commit()

    strategy = FakeStrategy(session_values={"invite_token": pipeline_invitation.token})
    with pytest.raises(Exception, match="already been used"):
        create_user(
            strategy,
            details_for(f"invitee{uuid.uuid4().hex[:8]}"),
            FakeBackend(),
            f"uid-{uuid.uuid4().hex[:8]}",
        )


def test_create_user_rejects_expired_invitation(
    invitations_enabled, pipeline_invitation
):
    n_days = int(cfg["invitations.days_until_expiry"])
    pipeline_invitation.created_at = datetime.datetime.now() - datetime.timedelta(
        days=n_days + 1
    )
    DBSession().commit()

    strategy = FakeStrategy(session_values={"invite_token": pipeline_invitation.token})
    with pytest.raises(Exception, match="expired"):
        create_user(
            strategy,
            details_for(f"invitee{uuid.uuid4().hex[:8]}"),
            FakeBackend(),
            f"uid-{uuid.uuid4().hex[:8]}",
        )


def test_create_user_rejects_taken_username(
    invitations_enabled, pipeline_invitation, user
):
    strategy = FakeStrategy(session_values={"invite_token": pipeline_invitation.token})
    with pytest.raises(Exception, match="Username already in use"):
        create_user(
            strategy,
            details_for(user.username),
            FakeBackend(),
            f"uid-{uuid.uuid4().hex[:8]}",
        )


def test_create_user_accepts_valid_invitation(
    invitations_enabled, pipeline_invitation, cleanup_users
):
    username = f"invitee{uuid.uuid4().hex[:8]}"
    strategy = FakeStrategy(session_values={"invite_token": pipeline_invitation.token})

    result = create_user(
        strategy, details_for(username), FakeBackend(), f"uid-{uuid.uuid4().hex[:8]}"
    )
    cleanup_users.append(result["user"])

    assert result["is_new"] is True
    assert result["user"].username == username
    assert pipeline_invitation.role in result["user"].roles


def test_get_username_uses_full_email_when_configured(user):
    strategy = FakeStrategy(settings={"USERNAME_IS_FULL_EMAIL": True})
    details = details_for(f"nobody{uuid.uuid4().hex[:8]}")

    result = get_username(
        strategy, details, FakeBackend(), f"uid-{uuid.uuid4().hex[:8]}"
    )

    assert result["username"] == details["email"]


def test_get_username_builds_from_first_and_last_name():
    strategy = FakeStrategy()
    details = details_for(f"nobody{uuid.uuid4().hex[:8]}")

    result = get_username(
        strategy, details, FakeBackend(), f"uid-{uuid.uuid4().hex[:8]}"
    )

    assert result["username"] == "alovelace" or result["username"].startswith(
        "alovelace"
    )


def test_get_username_returns_existing_username(user):
    user.oauth_uid = f"uid-{uuid.uuid4().hex[:8]}"
    DBSession().commit()

    result = get_username(
        FakeStrategy(), details_for("ignored"), FakeBackend(), user.oauth_uid
    )

    assert result["username"] == user.username


def test_setup_invited_user_permissions_grants_groups_and_streams(
    invitations_enabled,
    user,
    public_group,
    public_stream,
    pipeline_invitation,
    cleanup_users,
):
    invitee = User(
        username=f"invitee{uuid.uuid4().hex[:8]}",
        oauth_uid=f"uid-{uuid.uuid4().hex[:8]}",
    )
    DBSession().add(invitee)
    DBSession().commit()
    cleanup_users.append(invitee)

    pipeline_invitation.groups = [public_group]
    pipeline_invitation.streams = [public_stream]
    pipeline_invitation.admin_for_groups = [False]
    pipeline_invitation.can_save_to_groups = [True]
    DBSession().commit()

    strategy = FakeStrategy(session_values={"invite_token": pipeline_invitation.token})
    setup_invited_user_permissions(strategy, invitee.oauth_uid, {}, invitee)
    DBSession().commit()

    group_ids = set(
        DBSession().scalars(
            sa.select(GroupUser.group_id).where(GroupUser.user_id == invitee.id)
        )
    )
    stream_ids = set(
        DBSession().scalars(
            sa.select(StreamUser.stream_id).where(StreamUser.user_id == invitee.id)
        )
    )
    assert public_group.id in group_ids
    assert public_stream.id in stream_ids
    assert pipeline_invitation.used is True


def test_setup_invited_user_permissions_is_idempotent_for_existing_members(
    invitations_enabled,
    user,
    public_group,
    public_stream,
    pipeline_invitation,
    cleanup_users,
):
    invitee = User(
        username=f"invitee{uuid.uuid4().hex[:8]}",
        oauth_uid=f"uid-{uuid.uuid4().hex[:8]}",
    )
    DBSession().add(invitee)
    DBSession().commit()
    cleanup_users.append(invitee)

    DBSession().add(GroupUser(user_id=invitee.id, group_id=public_group.id))
    DBSession().add(StreamUser(user_id=invitee.id, stream_id=public_stream.id))
    DBSession().commit()

    pipeline_invitation.groups = [public_group]
    pipeline_invitation.streams = [public_stream]
    pipeline_invitation.admin_for_groups = [False]
    pipeline_invitation.can_save_to_groups = [True]
    DBSession().commit()

    strategy = FakeStrategy(session_values={"invite_token": pipeline_invitation.token})
    setup_invited_user_permissions(strategy, invitee.oauth_uid, {}, invitee)
    DBSession().commit()

    group_rows = DBSession().scalars(
        sa.select(GroupUser.id).where(
            GroupUser.user_id == invitee.id, GroupUser.group_id == public_group.id
        )
    )
    stream_rows = DBSession().scalars(
        sa.select(StreamUser.id).where(
            StreamUser.user_id == invitee.id, StreamUser.stream_id == public_stream.id
        )
    )
    assert len(list(group_rows)) == 1
    assert len(list(stream_rows)) == 1
    assert pipeline_invitation.used is True


def test_user_details_skips_users_that_already_have_details(user):
    strategy = FakeStrategy()
    user.contact_email = "already@example.com"
    DBSession().commit()

    user_details(
        strategy,
        {"first_name": "Changed"},
        FakeBackend(),
        user.oauth_uid,
        user=user,
    )

    assert strategy.storage.user.changed_users == []


def test_user_details_does_not_overwrite_protected_fields(user, cleanup_users):
    blank = User(
        username=f"blank{uuid.uuid4().hex[:8]}", oauth_uid=f"uid-{uuid.uuid4().hex[:8]}"
    )
    DBSession().add(blank)
    DBSession().commit()
    cleanup_users.append(blank)

    original_username = blank.username
    strategy = FakeStrategy()
    user_details(
        strategy,
        {"username": "hijacked", "first_name": "Ada"},
        FakeBackend(),
        blank.oauth_uid,
        user=blank,
    )

    assert blank.username == original_username
    assert blank.first_name == "Ada"
