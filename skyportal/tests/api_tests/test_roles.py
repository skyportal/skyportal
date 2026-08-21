import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import api, client


def test_list_roles(view_only_token):
    """GET /api/roles returns every role with its associated ACL ids."""
    roles = client(view_only_token).fetch_roles()
    role_ids = {role.id for role in roles}
    # Sanity-check that the built-in roles are present.
    for required in ("Super admin", "Full user", "View only"):
        assert required in role_ids, f"missing role: {required}"
    # Every role exposes its ACL list (may be empty).
    for role in roles:
        assert isinstance(role.acls, list)


def test_grant_and_revoke_user_role(super_admin_token, user):
    """POST grants a role; DELETE revokes it. Read-back via /api/user/<id>
    confirms the in-between state.
    """
    sp = client(super_admin_token)
    role_to_grant = "Group admin"

    sp.post_user_role(user.id, [role_to_grant])
    assert role_to_grant in sp.fetch_user(user.id).roles

    sp.delete_user_role(user.id, role_to_grant)
    assert role_to_grant not in sp.fetch_user(user.id).roles


def test_grant_unknown_role_is_rejected(super_admin_token, user):
    """Posting a non-existent role id returns 400 and lists the invalid ids."""
    with pytest.raises(SkyPortalError, match="DefinitelyNotARealRole") as err:
        client(super_admin_token).post_user_role(user.id, ["DefinitelyNotARealRole"])
    assert err.value.status_code == 400


def test_grant_role_requires_array_of_strings(super_admin_token, user):
    """The POST endpoint enforces shape on roleIds."""
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        f"user/{user.id}/roles",
        data={"roleIds": "Group admin"},  # string, not array
        token=super_admin_token,
    )
    assert status == 400


def test_non_admin_cannot_grant_roles(view_only_token, user):
    """Granting roles requires the Manage users permission."""
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_user_role(user.id, ["Group admin"])
    assert err.value.status_code == 401
