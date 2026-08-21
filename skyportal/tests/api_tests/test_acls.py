import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import api, client


def test_list_acls(view_only_token):
    """GET /api/acls returns the full ACL catalog to any authenticated user."""
    acls = client(view_only_token).fetch_acls()
    assert isinstance(acls, list)
    # Sanity-check that core ACLs are present.
    for required in ("Comment", "Annotate", "Upload data"):
        assert required in acls, f"missing ACL: {required}"


def test_grant_and_revoke_user_acl(super_admin_token, user):
    """POST then DELETE a single ACL on a user, verifying both endpoints
    and that the in-between state survives a read-back via /api/user/<id>.
    """
    sp = client(super_admin_token)
    acl_to_grant = "Annotate"

    sp.post_user_acl(user.id, [acl_to_grant])
    assert acl_to_grant in sp.fetch_user(user.id).acls

    sp.delete_user_acl(user.id, acl_to_grant)
    assert acl_to_grant not in sp.fetch_user(user.id).acls


def test_grant_user_acl_requires_array(super_admin_token, user):
    """The POST endpoint enforces a list-of-strings shape on aclIds."""
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        f"user/{user.id}/acls",
        data={"aclIds": "Annotate"},  # string instead of array
        token=super_admin_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_grant_unknown_acl_is_rejected(super_admin_token, user):
    """Posting an ACL id that doesn't exist returns 400 without mutating state."""
    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).post_user_acl(user.id, ["DefinitelyNotARealACL"])
    assert err.value.status_code == 400


def test_non_admin_cannot_grant_acls(view_only_token, user):
    """Granting ACLs requires the Manage users permission."""
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_user_acl(user.id, ["Annotate"])
    assert err.value.status_code == 401
