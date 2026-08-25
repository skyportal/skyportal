from skyportal.tests import api


def test_list_acls(view_only_token):
    """GET /api/acls returns the full ACL catalog to any authenticated user."""
    status, data = api("GET", "acls", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    # Sanity-check that core ACLs are present.
    for required in ("Comment", "Annotate", "Upload data"):
        assert required in data["data"], f"missing ACL: {required}"


def test_grant_and_revoke_user_acl(super_admin_token, user):
    """POST then DELETE a single ACL on a user, verifying both endpoints
    and that the in-between state survives a read-back via /api/user/<id>.
    """
    acl_to_grant = "Annotate"

    # Grant
    status, data = api(
        "POST",
        f"user/{user.id}/acls",
        data={"aclIds": [acl_to_grant]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"user/{user.id}", token=super_admin_token)
    assert status == 200
    assert acl_to_grant in data["data"]["acls"]

    # Revoke
    status, data = api(
        "DELETE", f"user/{user.id}/acls/{acl_to_grant}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"user/{user.id}", token=super_admin_token)
    assert status == 200
    assert acl_to_grant not in data["data"]["acls"]


def test_grant_user_acl_requires_array(super_admin_token, user):
    """The POST endpoint enforces a list-of-strings shape on aclIds."""
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
    status, data = api(
        "POST",
        f"user/{user.id}/acls",
        data={"aclIds": ["DefinitelyNotARealACL"]},
        token=super_admin_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_non_admin_cannot_grant_acls(view_only_token, user):
    """Granting ACLs requires the Manage users permission."""
    status, data = api(
        "POST",
        f"user/{user.id}/acls",
        data={"aclIds": ["Annotate"]},
        token=view_only_token,
    )
    assert status == 401
