__all__ = ["Shift", "ShiftUser"]

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import column_property, relationship

from baselayer.app.env import load_env
from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    DBSession,
    User,
    UserAccessControl,
    join_model,
    safe_aliased,
)

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

    name = sa.Column(sa.String, nullable=True, index=True, doc="Name of the shift.")

    description = sa.Column(
        sa.Text, nullable=True, doc="Longer description of the shift."
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
        "User",
        secondary="shift_users",
        back_populates="shifts",
        passive_deletes=True,
        doc="The members of this shift.",
    )

    shift_users = relationship(
        "ShiftUser",
        back_populates="shift",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Elements of a join table mapping Users to Shifts.",
        overlaps="shifts, users",
    )

    comments = relationship(
        "CommentOnShift",
        back_populates="shift",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by="CommentOnShift.created_at",
        doc="Comments posted about this Shift.",
    )

    reminders = relationship(
        "ReminderOnShift",
        back_populates="shift",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by="ReminderOnShift.created_at",
        doc="Reminders about this Shift.",
    )

    required_users_number = sa.Column(
        sa.Integer,
        nullable=True,
        doc="The number of users required to join this shift for it to be considered full",
    )


ShiftUser = join_model("shift_users", Shift, User)
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

# We add a column_property to Shift that is an array of the ids of the shift_users in the shift.
# This is useful for the frontend, to track how many users out of the required number are in the shift,
# and also tro track if the current user using the frontend is in the shift or not, while avoiding a joinedload with the ShiftUser table.
# Compared to a property or a hybrid_property, a column_property will be loaded by default and doesnt need to be called explicitly, just like a normal column.
Shift.shift_users_ids = column_property(
    select(func.array_agg(ShiftUser.user_id))
    .where(ShiftUser.shift_id == Shift.id)
    .correlate_except(ShiftUser)
)
