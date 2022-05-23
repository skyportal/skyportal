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
)
from baselayer.app.env import load_env

from .group import GroupUser, accessible_by_group_members

_, cfg = load_env()


def manage_shift_access_logic(cls, user_or_token):
    # admins of the shift and admins of the group associated with the shift can delete and update a shift
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = DBSession().query(cls).join(GroupUser, cls.group_id == GroupUser.group_id)
    if not user_or_token.is_system_admin:
        admin_query = query.filter(
            GroupUser.user_id == user_id, GroupUser.admin.is_(True)
        )
        if admin_query.count() == 0:
            query = query.join(ShiftUser)
            query = query.filter(
                ShiftUser.user_id == user_id, ShiftUser.admin.is_(True)
            )
        else:
            query = admin_query
    return query


def shiftuser_update_access_logic(cls, user_or_token):
    aliased = safe_aliased(cls)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    user_shift_admin = (
        DBSession()
        .query(Shift)
        .join(GroupUser, GroupUser.group_id == Shift.group_id)
        .filter(sa.and_(GroupUser.user_id == user_id, GroupUser.admin.is_(True)))
    )
    query = DBSession().query(cls).join(aliased, cls.shift_id == aliased.shift_id)
    if not user_or_token.is_system_admin:
        query = query.filter(
            sa.or_(
                aliased.user_id == user_id,
                sa.and_(aliased.admin.is_(True), aliased.user_id == user_id),
                aliased.shift_id.in_([shift.id for shift in user_shift_admin.all()]),
            )
        )
    return query


def shiftuser_delete_access_logic(cls, user_or_token):
    aliased = safe_aliased(cls)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    user_shift_admin = (
        DBSession()
        .query(Shift)
        .join(GroupUser, GroupUser.group_id == Shift.group_id)
        .filter(sa.and_(GroupUser.user_id == user_id, GroupUser.admin.is_(True)))
    )
    query = DBSession().query(cls).join(aliased, cls.shift_id == aliased.shift_id)
    if not user_or_token.is_system_admin:
        query = query.filter(
            sa.or_(
                aliased.user_id == user_id,
                sa.and_(aliased.admin.is_(True), aliased.user_id == user_id),
                aliased.shift_id.in_([shift.id for shift in user_shift_admin.all()]),
                aliased.needs_replacement.is_(True),
            )
        )
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

    comments = relationship(
        'CommentOnShift',
        back_populates='shift',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="CommentOnShift.created_at",
        doc="Comments posted about this Shift.",
    )


ShiftUser = join_model('shift_users', Shift, User)
ShiftUser.__doc__ = "Join table mapping `Shift`s to `User`s."
ShiftUser.admin = sa.Column(
    sa.Boolean,
    nullable=False,
    default=False,
    doc="Boolean flag indicating whether the User is an admin of the shift.",
)
# add a column that is a boolean saying if a user needs a replacement for the shift
ShiftUser.needs_replacement = sa.Column(
    sa.Boolean,
    nullable=False,
    default=False,
    doc="Boolean flag indicating whether the User needs a replacement for the shift.",
)

ShiftUser.update = CustomUserAccessControl(shiftuser_update_access_logic)
ShiftUser.delete = CustomUserAccessControl(shiftuser_delete_access_logic)

ShiftUser.create = ShiftUser.read
