__all__ = ["Thumbnail"]

import os

import requests
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfRelatedRowsAreAccessible, Base
from baselayer.log import make_log

from ..enum_types import thumbnail_types
from ..utils.thumbnail import image_is_grayscale

log = make_log("models.thumbnail")


class Thumbnail(Base):
    """Thumbnail image centered on the location of an Obj."""

    create = read = AccessibleIfRelatedRowsAreAccessible(obj="read")

    # TODO delete file after deleting row
    type = sa.Column(
        thumbnail_types, doc="Thumbnail type (e.g., ref, new, sub, ls, ps1, ...)"
    )
    file_uri = sa.Column(
        sa.String(),
        nullable=True,
        index=False,
        unique=False,
        doc="Path of the Thumbnail on the machine running SkyPortal.",
    )
    public_url = sa.Column(
        sa.String(),
        nullable=True,
        index=False,
        unique=False,
        doc="Publically accessible URL of the thumbnail.",
    )
    origin = sa.Column(sa.String, nullable=True, doc="Origin of the Thumbnail.")
    obj = relationship(
        "Obj",
        back_populates="thumbnails",
        uselist=False,
        doc="The Thumbnail's Obj.",
    )
    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="ID of the thumbnail's obj.",
    )
    is_grayscale = sa.Column(
        sa.Boolean(),
        nullable=False,
        default=False,
        doc="Boolean indicating whether the thumbnail is (mostly) grayscale or not.",
    )


@event.listens_for(Thumbnail, "before_insert")
def classify_thumbnail_grayscale(mapper, connection, target):
    if target.file_uri is not None:
        target.is_grayscale = image_is_grayscale(target.file_uri)
    else:
        try:
            target.is_grayscale = image_is_grayscale(
                requests.get(target.public_url, stream=True).raw
            )
        except requests.exceptions.RequestException:
            pass


# Also see the similar event listener on Obj
@event.listens_for(Thumbnail, "after_delete")
def delete_thumbnail_from_disk(mapper, connection, target):
    if target.file_uri is not None:
        try:
            os.remove(target.file_uri)
        except (FileNotFoundError, OSError) as e:
            log(f"Error deleting thumbnail file {target.file_uri}: {e}")
