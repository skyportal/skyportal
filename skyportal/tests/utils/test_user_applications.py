"""Applications are gated by one flag, and issuing an invitation is how a
decision takes effect, so the invitation pipeline gates them too. A second flag
decides who acts on them."""

import pytest

from skyportal.utils import user_applications


@pytest.mark.parametrize(
    "applications,invitations,expected",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_enabled_requires_both_flags(monkeypatch, applications, invitations, expected):
    monkeypatch.setattr(
        user_applications,
        "cfg",
        {"user_applications.enabled": applications, "invitations.enabled": invitations},
    )
    assert user_applications.user_applications_enabled() is expected


def test_enabled_is_false_for_a_config_predating_the_feature(monkeypatch):
    monkeypatch.setattr(user_applications, "cfg", {"invitations.enabled": True})
    assert user_applications.user_applications_enabled() is False


def test_admins_alone_decide_until_peer_endorsement_is_on(monkeypatch):
    monkeypatch.setattr(user_applications, "cfg", {})
    assert user_applications.deciding_acls() == ("Manage users",)

    monkeypatch.setattr(
        user_applications, "cfg", {"user_applications.peer_endorsement": True}
    )
    assert user_applications.deciding_acls() == ("Endorse users", "Manage users")


class FakeUser:
    """`permissions` is the union of direct and role-granted ACLs, which is what
    `may_decide` must read; `acls` alone would miss the role-granted ones."""

    def __init__(self, permissions=(), is_system_admin=False):
        self.acls = []
        self.permissions = list(permissions)
        self.is_system_admin = is_system_admin


ON = {"user_applications.enabled": True, "invitations.enabled": True}


def test_a_role_granted_acl_counts(monkeypatch):
    """Roles, not direct grants, are how these ACLs reach a user."""
    monkeypatch.setattr(
        user_applications, "cfg", {**ON, "user_applications.peer_endorsement": True}
    )
    from_role = FakeUser(permissions=["Endorse users"])
    assert from_role.acls == []
    assert user_applications.may_decide(from_role) is True


def test_endorse_acl_only_counts_under_peer_endorsement(monkeypatch):
    endorser = FakeUser(permissions=["Endorse users"])

    monkeypatch.setattr(user_applications, "cfg", ON)
    assert user_applications.may_decide(endorser) is False

    monkeypatch.setattr(
        user_applications, "cfg", {**ON, "user_applications.peer_endorsement": True}
    )
    assert user_applications.may_decide(endorser) is True


def test_admins_decide_in_either_mode(monkeypatch):
    monkeypatch.setattr(user_applications, "cfg", ON)
    assert user_applications.may_decide(FakeUser(permissions=["Manage users"])) is True
    assert user_applications.may_decide(FakeUser(is_system_admin=True)) is True


def test_nobody_decides_while_the_feature_is_off(monkeypatch):
    monkeypatch.setattr(user_applications, "cfg", {"invitations.enabled": True})
    assert user_applications.may_decide(FakeUser(is_system_admin=True)) is False
