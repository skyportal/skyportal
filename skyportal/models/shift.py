__all__ = ['Shift', 'ShiftUser']

import sqlalchemy as sa
from sqlalchemy.orm import relationship


from baselayer.app.models import (
    Base,
    join_model,
    User,
    CustomUserAccessControl,
    UserAccessControl,
    DBSession,
    safe_aliased,
    AccessibleIfUserMatches,
)
from baselayer.app.env import load_env

from .group import accessible_by_group_members

_, cfg = load_env()


def manage_shift_access_logic(cls, user_or_token):
    """Users can update and delete a shift that they are the admin of."""
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = DBSession().query(cls).join(ShiftUser)
    if not user_or_token.is_system_admin:
        query = query.filter(ShiftUser.user_id == user_id, ShiftUser.admin.is_(True))
    return query


# shift admins can set the admin status of other shift members
def shiftuser_update_access_logic(cls, user_or_token):
    aliased = safe_aliased(cls)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = DBSession().query(cls).join(aliased, cls.shift_id == aliased.shift_id)
    if not user_or_token.is_system_admin:
        query = query.filter(aliased.user_id == user_id, aliased.admin.is_(True))
    return query


class Shift(Base):
    """A scanning shift. A Shift is associated
    with exactly one Group, and a Group may have multiple operational Shifts.
    Members of a group can create, delete, join and leave these shifts depending on their permissions.
    """

    create = read = accessible_by_group_members
    update = delete = CustomUserAccessControl(manage_shift_access_logic)

    name = sa.Column(sa.String, nullable=True, index=True, doc='Name of the shift.')

    description = sa.Column(
        sa.Text, nullable=True, doc='Longer description of the shift.'
    )

    start_date = sa.Column(
        sa.DateTime, nullable=False, index=True, doc="The start time of this shift."
    )

    end_date = sa.Column(
        sa.DateTime, nullable=False, index=True, doc="The end time of this shift."
    )

    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Shift's Group.",
    )
    group = relationship(
        "Group",
        foreign_keys=[group_id],
        back_populates="shifts",
        doc="The Shift's Group.",
    )

    users = relationship(
        'User',
        secondary='shift_users',
        back_populates='shifts',
        passive_deletes=True,
        doc='The members of this shift.',
    )

    shift_users = relationship(
        'ShiftUser',
        back_populates='shift',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc='Elements of a join table mapping Users to Shifts.',
    )


ShiftUser = join_model('shift_users', Shift, User)
ShiftUser.__doc__ = "Join table mapping `Shift`s to `User`s."
ShiftUser.admin = sa.Column(
    sa.Boolean,
    nullable=False,
    default=False,
    doc="Boolean flag indicating whether the User is an admin of the shift.",
)

ShiftUser.update = CustomUserAccessControl(shiftuser_update_access_logic)
ShiftUser.delete = (
    # TODO: admins can leave a shift ONLY if there is at least one other admin
    # users can remove themselves from a shift
    # admins of a shift can remove users from it
    (AccessibleIfUserMatches('user'))
    & ShiftUser.read
    & CustomUserAccessControl(
        lambda cls, user_or_token: DBSession().query(cls).join(Shift)
    )
)

ShiftUser.create = ShiftUser.read
