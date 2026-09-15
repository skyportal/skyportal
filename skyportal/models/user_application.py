__all__ = ["UserApplication"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils import EmailType

from baselayer.app.models import Base, CustomUserAccessControl, public

from ..utils.user_applications import may_decide


def decider_access_logic(cls, user_or_token):
    if may_decide(user_or_token):
        return sa.select(cls)
    # return an empty query
    return sa.select(cls).where(cls.id == -1)


class UserApplication(Base):
    """A request for an account from someone who does not have one yet.

    Anyone may submit one; whoever may decide on it (a peer endorser or an
    administrator, per config) issues the Invitation the applicant signs up with.
    """

    # Submitted by prospective users, who have no account to be matched against.
    create = public
    read = update = delete = CustomUserAccessControl(decider_access_logic)

    first_name = sa.Column(sa.String, nullable=False, doc="Applicant's first name.")
    last_name = sa.Column(sa.String, nullable=False, doc="Applicant's last name.")
    contact_email = sa.Column(
        EmailType(),
        nullable=False,
        index=True,
        doc="Address the invitation is sent to once the application is endorsed.",
    )
    affiliation = sa.Column(
        sa.String, nullable=True, doc="Applicant's stated institution or affiliation."
    )
    statement = sa.Column(
        sa.String, nullable=True, doc="Applicant's stated reason for wanting access."
    )
    endorser_email = sa.Column(
        sa.String,
        nullable=True,
        doc="Address of the endorser the applicant named, as typed by them.",
    )
    endorser_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the User matching `endorser_email`, if the address is one we know.",
    )
    endorser = relationship(
        "User",
        foreign_keys=[endorser_id],
        doc="The User the applicant named as their endorser.",
    )
    status = sa.Column(
        sa.Enum(
            "pending",
            "endorsed",
            "declined",
            name="user_application_status",
            validate_strings=True,
        ),
        nullable=False,
        default="pending",
        index=True,
        doc=(
            "Application status. Can be one of either 'pending', 'endorsed', "
            "or 'declined'."
        ),
    )
    endorsed_by_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the User who endorsed or declined the application.",
    )
    endorsed_by = relationship(
        "User",
        foreign_keys=[endorsed_by_id],
        doc="The User who endorsed or declined the application.",
    )
    decided_at = sa.Column(
        sa.DateTime,
        nullable=True,
        doc="UTC time the application was endorsed or declined.",
    )
    decline_reason = sa.Column(
        sa.String, nullable=True, doc="Why the application was declined."
    )
    invitation_id = sa.Column(
        sa.ForeignKey("invitations.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the Invitation the endorsement issued.",
    )
    invitation = relationship(
        "Invitation", doc="The Invitation the endorsement issued."
    )
