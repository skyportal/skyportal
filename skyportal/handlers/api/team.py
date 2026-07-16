import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions
from skyportal.log import make_log

from ...models import Group, GroupUser, Team
from ..base import BaseHandler

log = make_log("api/team")

# Scalar fields a client may set on a Team.
EDITABLE_FIELDS = [
    "name",
    "nickname",
    "description",
    "primary_color",
    "secondary_color",
    "logo_url",
    "background_url",
]


def team_to_dict(team, include_users=True):
    """Serialize a Team plus its groups and (deduplicated) member roster.

    Membership is derived: a user belongs to the team iff they are a member
    of one of its groups.
    """
    out = team.to_dict()
    out["groups"] = [
        {"id": g.id, "name": g.name, "nickname": g.nickname} for g in team.groups
    ]
    # Derived membership count: distinct users across the team's groups. Cheap —
    # the group_users are already eager-loaded, so this adds no query.
    out["num_members"] = len({gu.user_id for g in team.groups for gu in g.group_users})
    if include_users:
        users = {}
        for g in team.groups:
            for gu in g.group_users:
                if gu.user_id not in users:
                    users[gu.user_id] = {
                        "id": gu.user.id,
                        "username": gu.user.username,
                        "first_name": gu.user.first_name,
                        "last_name": gu.user.last_name,
                    }
        out["users"] = list(users.values())
    return out


class TeamHandler(BaseHandler):
    @auth_or_token
    async def get(self, team_id: int | None = None):
        """
        ---
        single:
          summary: Get a team
          description: Retrieve a team, its groups, and its derived member roster
          tags:
            - teams
          parameters:
            - in: path
              name: team_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: Success
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all accessible teams
          description: Retrieve all teams the current user can access
          tags:
            - teams
          responses:
            200:
              content:
                application/json:
                  schema: Success
            400:
              content:
                application/json:
                  schema: Error
        """
        roster_loader = (
            selectinload(Team.groups)
            .selectinload(Group.group_users)
            .selectinload(GroupUser.user)
        )
        # The list needs only member counts, so it skips loading User objects
        # (group_users alone carry the user_id we count).
        count_loader = selectinload(Team.groups).selectinload(Group.group_users)
        async with self.AsyncSession() as session:
            if team_id is not None:
                try:
                    team_id = int(team_id)
                except (TypeError, ValueError):
                    return self.error(f"Invalid team_id: {team_id}")
                team = await session.scalar(
                    Team.select(session.user_or_token)
                    .options(roster_loader)
                    .where(Team.id == team_id)
                )
                if team is None:
                    return self.error(f"Cannot find Team with id {team_id}")
                return self.success(data=team_to_dict(team))

            teams_result = await session.scalars(
                Team.select(session.user_or_token)
                .options(count_loader)
                .order_by(Team.name)
            )
            teams = teams_result.unique().all()
            return self.success(
                data={"teams": [team_to_dict(t, include_users=False) for t in teams]}
            )

    @permissions(["Manage teams"])
    async def post(self):
        """
        ---
        summary: Create a new team
        description: |
          Create a team from a set of existing groups. The current user must be
          an admin of each group added to the team.
        tags:
          - teams
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  group_ids:
                    type: array
                    items:
                      type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        name = data.get("name")
        if name is None or (isinstance(name, str) and name.strip() == ""):
            return self.error("Missing required parameter: `name`")

        try:
            group_ids = [int(gid) for gid in data.get("group_ids", [])]
        except (TypeError, ValueError):
            return self.error("Invalid group_ids field; unable to parse items to int")

        async with self.AsyncSession() as session:
            existing = await session.scalar(
                Team.select(session.user_or_token).where(Team.name == name)
            )
            if existing is not None:
                return self.error(f"Team with name {name} already exists.")

            groups = []
            if group_ids:
                groups_result = await session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                )
                groups = list(groups_result.unique().all())
                found_ids = {g.id for g in groups}
                missing = set(group_ids) - found_ids
                if missing:
                    return self.error(
                        f"Cannot access group(s): {sorted(missing)}", status=403
                    )

            team = Team(
                name=name,
                nickname=data.get("nickname") or None,
                description=data.get("description") or None,
                primary_color=data.get("primary_color") or None,
                secondary_color=data.get("secondary_color") or None,
                logo_url=data.get("logo_url") or None,
                background_url=data.get("background_url") or None,
                groups=groups,
            )
            session.add(team)
            # commit enforces the model access control (admin of the team's groups)
            await session.commit()
            self.push_all(action="skyportal/FETCH_TEAMS")
            return self.success(data={"id": team.id})

    @permissions(["Manage teams"])
    async def put(self, team_id: int):
        """
        ---
        summary: Update a team
        description: |
          Update a team's fields and/or its set of groups. When `group_ids` is
          provided it replaces the team's groups; the user must be an admin of
          each group added or removed.
        tags:
          - teams
        parameters:
          - in: path
            name: team_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            team_id = int(team_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid team_id: {team_id}")
        data = self.get_json()

        async with self.AsyncSession() as session:
            team = await session.scalar(
                Team.select(session.user_or_token, mode="update")
                .options(selectinload(Team.groups))
                .where(Team.id == team_id)
            )
            if team is None:
                return self.error(f"Cannot find Team with id {team_id}", status=403)

            for field in EDITABLE_FIELDS:
                if field in data:
                    value = data[field]
                    if field == "name" and (
                        value is None or (isinstance(value, str) and not value.strip())
                    ):
                        return self.error("`name` cannot be empty")
                    setattr(team, field, value)

            if "group_ids" in data:
                try:
                    group_ids = [int(gid) for gid in data.get("group_ids") or []]
                except (TypeError, ValueError):
                    return self.error("Invalid group_ids field")
                groups = []
                if group_ids:
                    groups_result = await session.scalars(
                        Group.select(session.user_or_token).where(
                            Group.id.in_(group_ids)
                        )
                    )
                    groups = list(groups_result.unique().all())
                    missing = set(group_ids) - {g.id for g in groups}
                    if missing:
                        return self.error(
                            f"Cannot access group(s): {sorted(missing)}", status=403
                        )
                team.groups = groups

            await session.commit()
            self.push_all(action="skyportal/FETCH_TEAMS")
            return self.success(data={"id": team.id})

    @permissions(["Manage teams"])
    async def delete(self, team_id: int):
        """
        ---
        summary: Delete a team
        description: Delete a team (does not affect its groups or their data)
        tags:
          - teams
        parameters:
          - in: path
            name: team_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        try:
            team_id = int(team_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid team_id: {team_id}")
        async with self.AsyncSession() as session:
            team = await session.scalar(
                Team.select(session.user_or_token, mode="delete").where(
                    Team.id == team_id
                )
            )
            if team is None:
                return self.error(f"Cannot find Team with id {team_id}", status=403)
            await session.delete(team)
            await session.commit()
            self.push_all(action="skyportal/FETCH_TEAMS")
            return self.success()
