__all__ = ["SuperObj", "ObjToSuperObj"]

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import column_property, relationship

from baselayer.app.env import load_env
from baselayer.app.models import (
    Base,
)
from baselayer.log import make_log

from .obj import Obj

_, cfg = load_env()
log = make_log("models.super_obj")


class ObjToSuperObj(Base):
    """Association table linking Objs and SuperObjs in a many-to-many relationship
    (i.e., a SuperObj can have multiple Objs, and each Obj can link to multiple SuperObjs).
    """

    __tablename__ = "obj_to_super_obj"

    obj_id = sa.Column(
        sa.String,
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        primary_key=True,
        doc="ID of the associated Obj.",
    )
    super_obj_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("super_objs.id", ondelete="CASCADE"),
        primary_key=True,
        doc="ID of the associated SuperObj.",
    )


class SuperObj(Base):
    """While we can have multiple Obj entries for the same astrophysical
    object (e.g., from different surveys), we may want to link them
    together as being the same object. This table represents such
    'superobjects' that can be linked to multiple Objs.
    """

    __tablename__ = "super_objs"

    name = sa.Column(
        sa.String,
        nullable=True,
        doc="Name of the super-object (e.g., its AT name from the Transient Name Server).",
    )
    is_roid = sa.Column(
        sa.Boolean,
        default=False,
        doc="Boolean indicating whether the super-object is a moving object.",
    )

    objs = relationship(
        "Obj",
        secondary=ObjToSuperObj.__table__,
        back_populates="super_objs",
        cascade="delete",
        passive_deletes=True,
        doc="Obj entries associated with this SuperObj.",
    )


Obj.super_objs = relationship(
    "SuperObj",
    secondary=ObjToSuperObj.__table__,
    back_populates="objs",
    cascade="delete",
    passive_deletes=True,
    doc="SuperObj entries associated with this Obj.",
)
