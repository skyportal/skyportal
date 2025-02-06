__all__ = ['GroupedObject', 'GroupedObjectObj']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql
from baselayer.app.models import Base, join_model
from skyportal.models import Obj

from baselayer.app.models import public, AccessibleIfUserMatches


class GroupedObject(Base):
    """A collection of related astronomical objects.

    This represents a higher-level astronomical entity composed of multiple Objs, such as:
    - Multiple observations of the same moving object
    - Multiple detections of the same static object
    - Any other collection of objects that are physically related
    """

    create = read = public  # Anyone can create and read
    update = delete = AccessibleIfUserMatches('created_by')

    name = sa.Column(
        sa.String, primary_key=True, doc="Name/identifier for this grouped object"
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

    created_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User that created this grouped object",
    )

    created_by = relationship(
        'User',
        foreign_keys=[created_by_id],
        doc="The User that created this grouped object",
    )

    origin = sa.Column(
        sa.String,
        nullable=True,
        doc="Source/origin of the grouped object (e.g. the name of a pipeline, script)",
    )

    properties = sa.Column(
        postgresql.JSONB,
        nullable=True,
        doc="Additional properties or metadata about this grouped object",
    )

    def to_dict(self):
        d = super().to_dict()
        d['obj_ids'] = [obj.id for obj in self.objs]
        return d


# Create the many-to-many relationship (creates linking table)
GroupedObjectObj = join_model("grouped_object_objs", GroupedObject, Obj)

GroupedObject.objs = relationship(
    "Obj",
    secondary="grouped_object_objs",
    back_populates="grouped_objects",
    overlaps="grouped_objects,objs",
    doc="Objects that are part of this grouped object",
)
