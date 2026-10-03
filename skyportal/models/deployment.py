__all__ = ["Deployment"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

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
