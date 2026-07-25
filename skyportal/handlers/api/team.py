import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

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


class TeamPostBody(BaseModel):
    """Request body for creating a team."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Team name.")
    nickname: str | None = Field(default=None, description="Team nickname.")
    description: str | None = Field(default=None, description="Team description.")
    primary_color: str | None = Field(default=None, description="Primary color.")
    secondary_color: str | None = Field(default=None, description="Secondary color.")
    logo_url: str | None = Field(default=None, description="Logo URL or data URI.")
    background_url: str | None = Field(
        default=None, description="Background image URL or data URI."
    )
    group_ids: list[int] = Field(
        default_factory=list,
        description="IDs of the groups making up the team. The current user "
        "must be an admin of each group added to the team.",
    )


class TeamPostResponse(BaseModel):
    """Data payload returned when creating a team."""

    id: int = Field(description="New team ID")


class TeamPutBody(BaseModel):
    """Request body for updating a team."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Team name.")
    nickname: str | None = Field(default=None, description="Team nickname.")
    description: str | None = Field(default=None, description="Team description.")
    primary_color: str | None = Field(default=None, description="Primary color.")
    secondary_color: str | None = Field(default=None, description="Secondary color.")
    logo_url: str | None = Field(default=None, description="Logo URL or data URI.")
    background_url: str | None = Field(
        default=None, description="Background image URL or data URI."
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="When provided, replaces the team's groups; the user must "
        "be an admin of each group added or removed.",
    )


class TeamPutResponse(BaseModel):
    """Data payload returned when updating a team."""

    id: int = Field(description="Updated team ID")


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
    async def post(self, *, body: TeamPostBody = None) -> TeamPostResponse:
        """
        ---
        summary: Create a new team
        description: |
          Create a team from a set of existing groups. The current user must be
          an admin of each group added to the team.
        tags:
          - teams
        """
        body = self.parse_body(TeamPostBody)
        name = body.name
        if name.strip() == "":
            return self.error("Missing required parameter: `name`")

        group_ids = body.group_ids

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
                nickname=body.nickname or None,
                description=body.description or None,
                primary_color=body.primary_color or None,
                secondary_color=body.secondary_color or None,
                logo_url=body.logo_url or None,
                background_url=body.background_url or None,
                groups=groups,
            )
            session.add(team)
            # commit enforces the model access control (admin of the team's groups)
            await session.commit()
            self.push_all(action="skyportal/FETCH_TEAMS")
            return self.success(data={"id": team.id})

    @permissions(["Manage teams"])
    async def put(self, team_id: int, *, body: TeamPutBody = None) -> TeamPutResponse:
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
        """
        body = self.parse_body(TeamPutBody)
        try:
            team_id = int(team_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid team_id: {team_id}")

        async with self.AsyncSession() as session:
            team = await session.scalar(
                Team.select(session.user_or_token, mode="update")
                .options(selectinload(Team.groups))
                .where(Team.id == team_id)
            )
            if team is None:
                return self.error(f"Cannot find Team with id {team_id}", status=403)

            for field in EDITABLE_FIELDS:
                if field in body.model_fields_set:
                    value = getattr(body, field)
                    if field == "name" and (value is None or not value.strip()):
                        return self.error("`name` cannot be empty")
                    setattr(team, field, value)

            if "group_ids" in body.model_fields_set:
                group_ids = body.group_ids or []
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
