__all__ = ["Deployment", "InstanceManager"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, restricted


class Deployment(Base):
    """A version of the code that started serving this instance."""

    create = update = delete = restricted

    version = sa.Column(sa.String, nullable=False, doc="SkyPortal version string")
    commit = sa.Column(
        JSONB,
        nullable=True,
        doc="Git log entry of the deployed commit (see `utils.gitlog.parse_gitlog`)",
    )


class InstanceManager(Base):
    """A user listed as managing this instance, on the login and About pages."""

    __tablename__ = "instance_managers"

    create = update = delete = restricted

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="ID of the managing User",
    )
    user = relationship("User", foreign_keys=[user_id], doc="The managing User")
