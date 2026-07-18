import uuid

from skyportal.tests import api


def test_manage_teams_create_get_update_delete_team(
    manage_teams_token, group_admin_user, public_group
):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "teams",
        data={
            "name": name,
            "description": "A team",
            "primary_color": "#123456",
            "logo_url": "/static/images/team_logos/ZTF.png",
            "group_ids": [public_group.id],
        },
        token=manage_teams_token,
    )
    assert status == 200
    assert data["status"] == "success"
    team_id = data["data"]["id"]

    # Fetch it back: groups and derived roster are included.
    status, data = api("GET", f"teams/{team_id}", token=manage_teams_token)
    assert status == 200
    assert data["data"]["name"] == name
    assert data["data"]["primary_color"] == "#123456"
    group_ids = [g["id"] for g in data["data"]["groups"]]
    assert public_group.id in group_ids
    member_ids = [u["id"] for u in data["data"]["users"]]
    assert group_admin_user.id in member_ids

    # Update name + color.
    new_name = str(uuid.uuid4())
    status, data = api(
        "PUT",
        f"teams/{team_id}",
        data={"name": new_name, "primary_color": "#abcdef"},
        token=manage_teams_token,
    )
    assert status == 200

    status, data = api("GET", f"teams/{team_id}", token=manage_teams_token)
    assert data["data"]["name"] == new_name
    assert data["data"]["primary_color"] == "#abcdef"

    # Delete it.
    status, data = api("DELETE", f"teams/{team_id}", token=manage_teams_token)
    assert status == 200

    status, data = api("GET", f"teams/{team_id}", token=manage_teams_token)
    assert status == 400


def test_team_appears_in_list(manage_teams_token, public_group):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "teams",
        data={"name": name, "group_ids": [public_group.id]},
        token=manage_teams_token,
    )
    assert status == 200
    team_id = data["data"]["id"]

    status, data = api("GET", "teams", token=manage_teams_token)
    assert status == 200
    ids = [t["id"] for t in data["data"]["teams"]]
    assert team_id in ids


def test_team_list_reports_num_members(
    manage_teams_token, group_admin_user, public_group
):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "teams",
        data={"name": name, "group_ids": [public_group.id]},
        token=manage_teams_token,
    )
    assert status == 200
    team_id = data["data"]["id"]

    # Detail view exposes the full roster; num_members matches its length.
    status, data = api("GET", f"teams/{team_id}", token=manage_teams_token)
    assert status == 200
    member_ids = {u["id"] for u in data["data"]["users"]}
    assert group_admin_user.id in member_ids
    assert data["data"]["num_members"] == len(member_ids)

    # List view omits the roster but still reports the count (regression: it
    # previously rendered 0 members because `users` was absent from the list).
    status, data = api("GET", "teams", token=manage_teams_token)
    assert status == 200
    team = next(t for t in data["data"]["teams"] if t["id"] == team_id)
    assert "users" not in team
    assert team["num_members"] == len(member_ids)


def test_recent_sources_scoped_to_team(
    super_admin_token, public_group2, public_source, public_source_group2
):
    # public_source is saved only to public_group; public_source_group2 only to
    # public_group2. A team on public_group2 must scope the widget to that group.
    status, data = api(
        "POST",
        "teams",
        data={"name": str(uuid.uuid4()), "group_ids": [public_group2.id]},
        token=super_admin_token,
    )
    assert status == 200
    team_id = data["data"]["id"]

    status, data = api(
        "GET",
        "internal/recent_sources",
        params={"teamID": team_id},
        token=super_admin_token,
    )
    assert status == 200
    obj_ids = {s["obj_id"] for s in data["data"]}
    assert public_source_group2.id in obj_ids
    assert public_source.id not in obj_ids

    # A bogus team id is a client error, not a silent no-op.
    status, data = api(
        "GET",
        "internal/recent_sources",
        params={"teamID": 999999999},
        token=super_admin_token,
    )
    assert status == 400


def test_source_counts_scoped_to_team(
    super_admin_token, public_group2, public_source_group2
):
    # public_group2 is a fresh group holding exactly one source, so a team on it
    # should count exactly that one source.
    status, data = api(
        "POST",
        "teams",
        data={"name": str(uuid.uuid4()), "group_ids": [public_group2.id]},
        token=super_admin_token,
    )
    assert status == 200
    team_id = data["data"]["id"]

    status, data = api(
        "GET",
        "internal/source_counts",
        params={"teamID": team_id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["count"] == 1


def test_cannot_create_team_without_name(manage_teams_token, public_group):
    status, data = api(
        "POST",
        "teams",
        data={"group_ids": [public_group.id]},
        token=manage_teams_token,
    )
    assert status == 400
    assert "Missing required parameter" in data["message"]


def test_manage_teams_acl_required_to_create(group_admin_token, public_group):
    # group_admin_token lacks the "Manage teams" ACL.
    status, data = api(
        "POST",
        "teams",
        data={"name": str(uuid.uuid4()), "group_ids": [public_group.id]},
        token=group_admin_token,
    )
    assert status in (401, 403)


def test_newsfeed_accepts_team_scope(manage_teams_token, public_group):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "teams",
        data={"name": name, "group_ids": [public_group.id]},
        token=manage_teams_token,
    )
    assert status == 200
    team_id = data["data"]["id"]

    status, data = api(
        "GET", "newsfeed", params={"teamID": team_id}, token=manage_teams_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
