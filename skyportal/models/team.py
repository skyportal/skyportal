__all__ = ["Team", "GroupTeam"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, join_model

from .group import (
    Group,
    accessible_by_group_admins,
    accessible_by_groups_admins,
    accessible_by_groups_members,
)


class Team(Base):
    """A Team is a collaboration-level grouping of one or more `Group`s. It is
    purely an organizational/presentation layer and never widens data
    visibility: a `User` belongs to a team iff they are a member of one of its
    groups, and team-scoped views are always intersected with the user's
    accessible groups.
    """

    # read: member of any of the team's groups; manage: admin of any of them
    read = accessible_by_groups_members
    create = update = delete = accessible_by_groups_admins

    name = sa.Column(
        sa.String, unique=True, nullable=False, index=True, doc="Name of the team."
    )
    nickname = sa.Column(
        sa.String, unique=True, nullable=True, index=True, doc="Short team nickname."
    )
    description = sa.Column(
        sa.Text, nullable=True, doc="Longer description of the team."
    )
    primary_color = sa.Column(
        sa.String,
        nullable=True,
        doc="Hex color used to theme the app banner when this team is active.",
    )
    secondary_color = sa.Column(
        sa.String, nullable=True, doc="Hex accent color for this team's theme."
    )
    logo_url = sa.Column(
        sa.String,
        nullable=True,
        doc="URL of a logo shown in place of the SkyPortal logo when active.",
    )
    background_url = sa.Column(
        sa.String, nullable=True, doc="URL of a background image for this team."
    )
    groups = relationship(
        "Group",
        secondary="group_teams",
        back_populates="teams",
        passive_deletes=True,
        doc="The groups that make up this team.",
    )


GroupTeam = join_model("group_teams", Group, Team)
GroupTeam.__doc__ = "Join table mapping Groups to Teams."
# Only group admins can add/remove their group to/from a team.
GroupTeam.create = GroupTeam.update = GroupTeam.delete = (
    accessible_by_group_admins & GroupTeam.read
)
