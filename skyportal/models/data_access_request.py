__all__ = ["DataAccessRequest"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfUserMatches,
    Base,
    CustomUserAccessControl,
    UserAccessControl,
    public,
)

from .group import GroupUser


def _admin_of_a_holding_group(cls, user_id):
    """Whether the user administers one of the groups that held the data."""
    return sa.exists().where(
        GroupUser.user_id == user_id,
        GroupUser.admin.is_(True),
        GroupUser.group_id == sa.any_(cls.owner_group_ids),
    )


def _visible_to_parties(cls, user_or_token):
    """Readable by the requester and by anyone who could grant it."""
    if user_or_token.is_admin:
        return public.select_accessible_rows(cls, user_or_token)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    return sa.select(cls).where(
        sa.or_(
            cls.requester_id == user_id,
            cls.owner_id == user_id,
            _admin_of_a_holding_group(cls, user_id),
        )
    )


def _grantable_by(cls, user_or_token):
    """Answerable by the data's owner, or an admin of a group holding it."""
    if user_or_token.is_admin:
        return public.select_accessible_rows(cls, user_or_token)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    return sa.select(cls).where(
        sa.or_(cls.owner_id == user_id, _admin_of_a_holding_group(cls, user_id))
    )


class DataAccessRequest(Base):
    """A request to be given data on an object that the requester cannot see.

    One row is one dataset asked of one owner: a spectrum, or the photometry
    an owner holds on an object in a single instrument/filter combination.
    Which points that resolves to is settled when the request is granted, not
    when it is made.
    """

    # Base would derive "dataaccessrequests"; spell it out as the other
    # multi-word tables do.
    __tablename__ = "data_access_requests"

    read = CustomUserAccessControl(_visible_to_parties)
    create = AccessibleIfUserMatches("requester")
    update = CustomUserAccessControl(_grantable_by)
    delete = AccessibleIfUserMatches("requester")

    __table_args__ = (
        sa.CheckConstraint(
            "(data_type = 'photometry' AND instrument_id IS NOT NULL "
            "AND filter IS NOT NULL AND spectrum_id IS NULL) OR "
            "(data_type = 'spectrum' AND spectrum_id IS NOT NULL "
            "AND instrument_id IS NULL AND filter IS NULL)",
            name="data_access_requests_dataset_shape",
        ),
    )

    requester_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User asking for the data.",
    )
    requester = relationship(
        "User",
        foreign_keys=[requester_id],
        doc="The User asking for the data.",
    )
    owner_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User who owns the data being asked for.",
    )
    owner = relationship(
        "User",
        foreign_keys=[owner_id],
        doc="The User who owns the data being asked for.",
    )
    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Obj the data is attached to.",
    )
    obj = relationship("Obj", doc="The Obj the data is attached to.")
    data_type = sa.Column(
        sa.Enum(
            "photometry",
            "spectrum",
            name="data_access_request_type",
            validate_strings=True,
        ),
        nullable=False,
        doc="Which kind of data is being asked for.",
    )
    instrument_id = sa.Column(
        sa.ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Instrument of the requested photometry; null for a spectrum.",
    )
    instrument = relationship(
        "Instrument", doc="Instrument of the requested photometry."
    )
    filter = sa.Column(
        sa.String,
        nullable=True,
        doc="Bandpass of the requested photometry; null for a spectrum.",
    )
    spectrum_id = sa.Column(
        sa.ForeignKey("spectra.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="The requested spectrum; null for photometry.",
    )
    spectrum = relationship("Spectrum", doc="The requested spectrum.")
    owner_group_ids = sa.Column(
        ARRAY(sa.Integer),
        nullable=False,
        server_default="{}",
        doc="Groups holding the data when the request was made. Snapshotted "
        "so that the set of people who can answer it does not shift as the "
        "data is shared onward.",
    )
    status = sa.Column(
        sa.Enum(
            "pending",
            "accepted",
            "declined",
            name="data_access_request_status",
            validate_strings=True,
        ),
        nullable=False,
        default="pending",
        index=True,
        doc="Whether the request has been answered, and how.",
    )
    message = sa.Column(
        sa.String,
        nullable=True,
        doc="What the requester said when asking.",
    )
    responded_by_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the User who answered the request.",
    )
    responded_by = relationship(
        "User",
        foreign_keys=[responded_by_id],
        doc="The User who answered the request.",
    )
    granted_group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
        doc="Group the data was shared into on acceptance.",
    )
    granted_group = relationship(
        "Group", doc="Group the data was shared into on acceptance."
    )
