__all__ = ["TNSRetrievalRequest"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfRelatedRowsAreAccessible,
    Base,
    restricted,
)


class TNSRetrievalRequest(Base):
    """A user's search for an Obj on TNS, run by the TNS retrieval queue."""

    create = read = AccessibleIfRelatedRowsAreAccessible(obj="read")
    update = delete = restricted

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Obj to look for on TNS.",
    )
    obj = relationship("Obj", doc="The Obj to look for on TNS.")
    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User who requested the search.",
    )
    user = relationship("User", doc="The User who requested the search.")
    radius = sa.Column(
        sa.Float, nullable=False, doc="Search radius around the Obj, in arcsec."
    )
    status = sa.Column(
        sa.String,
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
        doc="One of pending, processing, found, not_found or error.",
    )
    error = sa.Column(sa.String, nullable=True, doc="Why the search failed.")
