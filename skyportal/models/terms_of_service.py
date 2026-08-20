__all__ = ["TermsOfServiceAcceptance"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base, restricted


class TermsOfServiceAcceptance(Base):
    """One user's acceptance of one version of the instance's terms of service.

    Rows are an append-only audit trail: a new version prompts the user again
    and inserts another row, rather than updating the existing one, so the
    history of what was agreed to and when is preserved.
    """

    # A user records and reads their own acceptances; the trail is append-only,
    # so editing and deleting are left to system admins.
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
