__all__ = ["TermsOfServiceAcceptance"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base, restricted


class TermsOfServiceAcceptance(Base):
    # Append-only audit trail: a new version inserts a row rather than updating.
    read = create = AccessibleIfUserMatches("user")
    update = delete = restricted

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User who accepted the terms.",
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        doc="The User who accepted the terms.",
    )

    version = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        doc="`app.terms_of_service.version` that was in force when accepted.",
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id",
            "version",
            name="terms_of_service_acceptances_user_version_uniq",
        ),
    )
