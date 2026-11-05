__all__ = ["ZooniverseToken"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base


class ZooniverseToken(Base):
    """A SkyPortal user's Zooniverse credentials.

    Volunteers authenticate with Zooniverse so their classifications are
    attributed to them, which the IFE guidance requires. Tokens live here
    rather than in `User.preferences` because preferences are served to the
    browser, and these must never leave the server.
    """

    create = read = update = delete = AccessibleIfUserMatches("user")

    id = sa.Column(sa.Integer, primary_key=True)

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="SkyPortal user these Zooniverse credentials belong to.",
    )
    user = relationship("User", doc="The SkyPortal user.")

    zooniverse_user_id = sa.Column(
        sa.String, nullable=True, doc="Panoptes user id, for attribution."
    )
    zooniverse_login = sa.Column(
        sa.String, nullable=True, doc="Panoptes login, shown in the UI."
    )

    access_token = sa.Column(sa.String, nullable=False, doc="Panoptes bearer token.")
    refresh_token = sa.Column(
        sa.String, nullable=True, doc="Used to renew the bearer token."
    )
    expires_at = sa.Column(
        sa.DateTime,
        nullable=True,
        doc="When the bearer token expires; Panoptes issues two-hour tokens.",
    )
