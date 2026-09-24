import re
import uuid
from pathlib import Path

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.profile import ProfilePatch
from skyportal_py.users import UserPost

from skyportal.handlers.api.user import PUBLIC_PROFILE_FIELDS
from skyportal.model_util import create_token
from skyportal.models import DBSession, Token
from skyportal.tests import api, client


def test_get_user_info(manage_users_token, user):
    assert client(manage_users_token).fetch_user(user.id).id == user.id


def test_delete_user_cascades_to_tokens(super_admin_token, user, public_group):
    token_name = str(uuid.uuid4())
    token_id = create_token(ACLs=[], user_id=user.id, name=token_name)
    assert Token.query.get(token_id)

    # end the transaction on the test-side
    DBSession().commit()

    sp = client(super_admin_token)
    sp.delete_user(user.id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_user(user.id)
    assert err.value.status_code == 400

    assert not Token.query.get(token_id)


def test_delete_user_cascades_to_groupuser(
    super_admin_token, manage_groups_token, user, public_group
):
    orig_num_users = len(client(manage_groups_token).fetch_group(public_group.id).users)

    client(super_admin_token).delete_user(user.id)

    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).fetch_user(user.id)
    assert err.value.status_code == 400

    group = client(manage_groups_token).fetch_group(public_group.id)
    assert len(group.users) == orig_num_users - 1


def test_add_basic_user_info(manage_groups_token, super_admin_token):
    sp = client(super_admin_token)
    username = str(uuid.uuid4())
    new_user_id = sp.post_user(
        UserPost(
            username=username,
            first_name="Fritz",
            last_name="Marshal",
            affiliations=["Caltech"],
        )
    ).id

    fetched = sp.fetch_user(new_user_id)
    assert fetched.first_name == "Fritz"
    assert fetched.last_name == "Marshal"
    assert fetched.affiliations == ["Caltech"]

    sp.delete_user(new_user_id)

    # add a bad phone number, expecting an error
    with pytest.raises(SkyPortalError, match="Could not parse input") as err:
        sp.post_user(UserPost(username=username, contact_phone="blah"))
    assert err.value.status_code == 400


def test_add_delete_user_adds_deletes_single_user_group(
    manage_groups_token, super_admin_user_two_groups, super_admin_token
):
    username = str(uuid.uuid4())
    new_user_id = client(super_admin_token).post_user(UserPost(username=username)).id

    groups = client(manage_groups_token).fetch_groups(include_single_user_groups=True)
    assert any(
        group.single_user_group and group.name == username
        for group in groups.all_groups
    )

    client(super_admin_token).delete_user(new_user_id)

    groups = client(manage_groups_token).fetch_groups(include_single_user_groups=True)
    assert not any(
        group.single_user_group and group.name == username
        for group in groups.all_groups
    )


def test_add_modify_user_adds_modifies_single_user_group(
    manage_groups_token, super_admin_user_two_groups, super_admin_token
):
    username = str(uuid.uuid4())
    token_name = str(uuid.uuid4())
    new_user_id = client(super_admin_token).post_user(UserPost(username=username)).id

    groups = client(manage_groups_token).fetch_groups(include_single_user_groups=True)
    assert any(
        group.single_user_group and group.name == username
        for group in groups.all_groups
    )

    token_id = create_token(ACLs=[], user_id=new_user_id, name=token_name)
    new_username = str(uuid.uuid4())

    client(token_id).update_profile(ProfilePatch(username=new_username))

    groups = client(manage_groups_token).fetch_groups(include_single_user_groups=True)
    assert any(
        group.single_user_group and group.name == new_username
        for group in groups.all_groups
    )


def test_user_list(view_only_token):
    client(view_only_token).fetch_users()


def test_user_list_filtering(view_only_token, user, view_only_user):
    # Try some simple filtering options - other options follow very similar
    # logic so just these should be decent coverage
    sp = client(view_only_token)

    # Username
    page = sp.fetch_users(username=user.username)
    assert len(page.users) == 1
    assert page.users[0].id == user.id

    # Role
    # Make sure the result shows up among all the view_only_users provisioned across tests
    # by returning a huge page
    page = sp.fetch_users(role="View only", num_per_page=300)
    result_user_ids = [u.id for u in page.users]
    assert view_only_user.id in result_user_ids
    assert user.id not in result_user_ids


def test_patch_user_expiration_date(super_admin_token, user):
    sp = client(super_admin_token)
    sp.update_user(user.id, expiration_date="2030-01-02")

    # extra="forbid" also verifies the camelCase key is not assigned verbatim
    # alongside the parsed date (to_dict serializes the instance __dict__).
    fetched = sp.fetch_user(user.id)
    assert fetched.expiration_date.date().isoformat() == "2030-01-02"

    sp.update_user(user.id, expiration_date=None)
    assert sp.fetch_user(user.id).expiration_date is None


def test_patch_user_cannot_rewrite_identity_columns(super_admin_token, user):
    """Identity columns aren't part of the request body model, so they are
    rejected outright rather than assigned onto the User."""
    original_uid = user.oauth_uid

    # raw api: intentionally hostile payload the typed client can't produce
    status, data = api(
        "PATCH",
        f"user/{user.id}",
        data={"id": 999999999, "oauth_uid": "hijacked@example.com"},
        token=super_admin_token,
    )
    assert status == 400, data
    assert "Extra inputs are not permitted" in data["message"]

    fetched = client(super_admin_token).fetch_user(user.id)
    assert fetched.id == user.id
    assert fetched.oauth_uid == original_uid


def test_public_profile(view_only_token, user, super_admin_token):
    client(view_only_token).update_profile(
        ProfilePatch(
            affiliations=["Caltech"],
            bio="An astronomer looking at transients",
            contact_email="public_profile_test@skyportal.com",
        )
    )

    # raw api: which keys the profile payload includes varies with visibility prefs
    status, data = api("GET", f"user/{user.id}/profile", token=super_admin_token)
    assert status == 200, data
    profile = data["data"]
    assert profile["id"] == user.id
    assert profile["username"] == user.username
    assert profile["affiliations"] == ["Caltech"]
    assert profile["bio"].startswith("An astronomer")
    assert "contact_email" not in profile

    client(view_only_token).update_profile(
        ProfilePatch(
            preferences={
                "publicProfile": {
                    "affiliations": False,
                    "contact_email": True,
                    "roles": True,
                }
            }
        )
    )

    # raw api: which keys the profile payload includes varies with visibility prefs
    status, data = api("GET", f"user/{user.id}/profile", token=super_admin_token)
    assert status == 200, data
    profile = data["data"]
    assert "affiliations" not in profile
    assert profile["contact_email"] == "public_profile_test@skyportal.com"
    assert profile["roles"] == sorted(role.id for role in user.roles)

    # raw api: which keys the profile payload includes varies with visibility prefs
    status, data = api("GET", "user/99999999/profile", token=view_only_token)
    assert status == 400, data


def test_public_profile_fields_mirrored_in_frontend():
    source = (
        Path(__file__).parents[4] / "static/js/components/user/UserProfileInfo.tsx"
    ).read_text()
    block = re.search(
        r"const PUBLIC_FIELDS: Record<string, boolean> = \{(.*?)\};", source, re.S
    )
    assert block is not None, "PUBLIC_FIELDS not found in UserProfileInfo.tsx"
    frontend = {
        name: value == "true"
        for name, value in re.findall(r"(\w+): (true|false),", block.group(1))
    }
    assert frontend == PUBLIC_PROFILE_FIELDS


def test_user_info_hides_unshared_fields(view_only_token, user, view_only_token2):
    client(view_only_token).update_profile(
        ProfilePatch(bio="An astronomer looking at transients")
    )

    # raw api: asserts which keys the JSON payload includes
    status, data = api("GET", f"user/{user.id}", token=view_only_token2)
    assert status == 200, data
    assert data["data"]["id"] == user.id
    assert data["data"]["bio"].startswith("An astronomer")
    assert "contact_email" not in data["data"]
    assert "permissions" not in data["data"]

    # raw api: asserts which keys the JSON payload includes
    status, data = api("GET", f"user/{user.id}", token=view_only_token)
    assert status == 200, data
    assert data["data"]["contact_email"] == user.contact_email
    assert "permissions" in data["data"]

    # raw api: asserts which keys the JSON payload includes
    status, data = api(
        "GET", "user", params={"username": user.username}, token=view_only_token2
    )
    assert status == 200, data
    listed = next(u for u in data["data"]["users"] if u["id"] == user.id)
    assert listed["bio"].startswith("An astronomer")
    assert "contact_email" not in listed

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_users(email="@")
    assert err.value.status_code == 400
