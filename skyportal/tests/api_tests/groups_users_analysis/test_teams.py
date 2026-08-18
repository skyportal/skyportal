import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.teams import TeamPost, TeamPut

from skyportal.tests import api, client


def test_manage_teams_create_get_update_delete_team(
    manage_teams_token, group_admin_user, public_group
):
    sp = client(manage_teams_token)
    name = str(uuid.uuid4())
    team_id = sp.post_team(
        TeamPost(
            name=name,
            description="A team",
            primary_color="#123456",
            logo_url="/static/images/team_logos/ZTF.png",
            group_ids=[public_group.id],
        )
    ).id

    # Fetch it back: groups and derived roster are included.
    team = sp.fetch_team(team_id)
    assert team.name == name
    assert team.primary_color == "#123456"
    assert public_group.id in [g.id for g in team.groups]
    assert group_admin_user.id in [u.id for u in team.users]

    # Update name + color.
    new_name = str(uuid.uuid4())
    sp.update_team(team_id, TeamPut(name=new_name, primary_color="#abcdef"))

    team = sp.fetch_team(team_id)
    assert team.name == new_name
    assert team.primary_color == "#abcdef"

    # Delete it.
    sp.delete_team(team_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_team(team_id)
    assert err.value.status_code == 400


def test_team_appears_in_list(manage_teams_token, public_group):
    sp = client(manage_teams_token)
    team_id = sp.post_team(
        TeamPost(name=str(uuid.uuid4()), group_ids=[public_group.id])
    ).id

    assert team_id in [t.id for t in sp.fetch_teams()]


def test_team_list_reports_num_members(
    manage_teams_token, group_admin_user, public_group
):
    sp = client(manage_teams_token)
    team_id = sp.post_team(
        TeamPost(name=str(uuid.uuid4()), group_ids=[public_group.id])
    ).id

    # Detail view exposes the full roster; num_members matches its length.
    detail = sp.fetch_team(team_id)
    member_ids = {u.id for u in detail.users}
    assert group_admin_user.id in member_ids
    assert detail.num_members == len(member_ids)

    # List view omits the roster but still reports the count (regression: it
    # previously rendered 0 members because `users` was absent from the list).
    team = next(t for t in sp.fetch_teams() if t.id == team_id)
    assert team.users is None
    assert team.num_members == len(member_ids)


def test_recent_sources_scoped_to_team(
    super_admin_token, public_group2, public_source, public_source_group2
):
    # public_source is saved only to public_group; public_source_group2 only to
    # public_group2. A team on public_group2 must scope the widget to that group.
    team_id = (
        client(super_admin_token)
        .post_team(TeamPost(name=str(uuid.uuid4()), group_ids=[public_group2.id]))
        .id
    )

    # raw api: internal dashboard-widget endpoint, outside skyportal-py's scope
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
    team_id = (
        client(super_admin_token)
        .post_team(TeamPost(name=str(uuid.uuid4()), group_ids=[public_group2.id]))
        .id
    )

    # raw api: internal dashboard-widget endpoint, outside skyportal-py's scope
    status, data = api(
        "GET",
        "internal/source_counts",
        params={"teamID": team_id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["count"] == 1


def test_cannot_create_team_without_name(manage_teams_token, public_group):
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "teams",
        data={"group_ids": [public_group.id]},
        token=manage_teams_token,
    )
    assert status == 400
    assert "name: Field required" in data["message"]


def test_manage_teams_acl_required_to_create(group_admin_token, public_group):
    # group_admin_token lacks the "Manage teams" ACL.
    with pytest.raises(SkyPortalError) as err:
        client(group_admin_token).post_team(
            TeamPost(name=str(uuid.uuid4()), group_ids=[public_group.id])
        )
    assert err.value.status_code in (401, 403)


def test_newsfeed_accepts_team_scope(manage_teams_token, public_group):
    sp = client(manage_teams_token)
    team_id = sp.post_team(
        TeamPost(name=str(uuid.uuid4()), group_ids=[public_group.id])
    ).id

    assert isinstance(sp.fetch_news_feed(team_id=team_id), list)
