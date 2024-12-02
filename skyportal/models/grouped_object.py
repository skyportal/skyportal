__all__ = ['GroupedObject', 'GroupedObjectObj']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql
from baselayer.app.models import Base, join_model
from skyportal.models import Obj


class GroupedObject(Base):
    """A collection of related astronomical objects.

    This represents a higher-level astronomical entity composed of multiple Objs, such as:
    - Multiple observations of the same moving object
    - Multiple detections of the same static object
    - Any other collection of objects that are physically related
    """

    name = sa.Column(
        sa.String, nullable=False, doc="Name/identifier for this grouped object"
    )

    type = sa.Column(
        sa.String,
        nullable=False,
        doc="Type of grouped object (e.g., 'moving_object', 'duplicate_detection')",
    )

    description = sa.Column(
        sa.String,
        nullable=True,
        doc="Optional description of why these objects are related",
    )

    # Todo: add created_by User?
    created_by = sa.Column(
        postgresql.JSONB,
        nullable=True,
        doc="Metadata about what/who created this group (user, pipeline name, etc)",
    )

    properties = sa.Column(
        postgresql.JSONB,
        nullable=True,
        doc="Additional properties or metadata about this grouped object",
    )


# Create the many-to-many relationship (creates linking table)
GroupedObjectObj = join_model("grouped_object_objs", GroupedObject, Obj)

# Set up the relationship between GroupedObject and Obj
GroupedObject.objs = relationship(
    "Obj",
    secondary="grouped_object_objs",
    back_populates="grouped_objects",
    doc="Objects that are part of this grouped object",
)
