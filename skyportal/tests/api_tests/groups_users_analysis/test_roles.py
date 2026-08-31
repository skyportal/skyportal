from skyportal.tests import api


def test_list_roles(view_only_token):
    """GET /api/roles returns every role with its associated ACL ids."""
    status, data = api("GET", "roles", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    role_ids = {r["id"] for r in data["data"]}
    # Sanity-check that the built-in roles are present.
    for required in ("Super admin", "Full user", "View only"):
        assert required in role_ids, f"missing role: {required}"
    # Every role exposes its ACL list (may be empty).
    for role in data["data"]:
        assert "acls" in role and isinstance(role["acls"], list)


def test_grant_and_revoke_user_role(super_admin_token, user):
    """POST grants a role; DELETE revokes it. Read-back via /api/user/<id>
    confirms the in-between state.
    """
    role_to_grant = "Group admin"

    status, data = api(
        "POST",
        f"user/{user.id}/roles",
        data={"roleIds": [role_to_grant]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"user/{user.id}", token=super_admin_token)
    assert status == 200
    assert role_to_grant in data["data"]["roles"]

    status, data = api(
        "DELETE", f"user/{user.id}/roles/{role_to_grant}", token=super_admin_token
    )
    assert status == 200

    status, data = api("GET", f"user/{user.id}", token=super_admin_token)
    assert status == 200
    assert role_to_grant not in data["data"]["roles"]


def test_grant_unknown_role_is_rejected(super_admin_token, user):
    """Posting a non-existent role id returns 400 and lists the invalid ids."""
    status, data = api(
        "POST",
        f"user/{user.id}/roles",
        data={"roleIds": ["DefinitelyNotARealRole"]},
        token=super_admin_token,
    )
    assert status == 400
    assert "DefinitelyNotARealRole" in data["message"]


def test_grant_role_requires_array_of_strings(super_admin_token, user):
    """The POST endpoint enforces shape on roleIds."""
    status, data = api(
        "POST",
        f"user/{user.id}/roles",
        data={"roleIds": "Group admin"},  # string, not array
        token=super_admin_token,
    )
    assert status == 400


def test_non_admin_cannot_grant_roles(view_only_token, user):
    """Granting roles requires the Manage users permission."""
    status, data = api(
        "POST",
        f"user/{user.id}/roles",
        data={"roleIds": ["Group admin"]},
        token=view_only_token,
    )
    assert status == 401
