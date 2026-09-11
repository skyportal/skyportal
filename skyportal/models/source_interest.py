__all__ = ["SourceInterest"]

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, selectinload

from baselayer.app.models import (
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
    Base,
)

USER_FIELDS = (
    "id",
    "username",
    "first_name",
    "last_name",
    "gravatar_url",
    "is_bot",
)


class ObjUserMixin:
    """Shared columns of the records tying a User to an Obj they collaborate on."""

    create = read = AccessibleIfRelatedRowsAreAccessible(obj="read")
    update = delete = AccessibleIfUserMatches("user")

    @declared_attr
    def obj_id(cls):
        return sa.Column(
            sa.ForeignKey("objs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            doc="ID of the Obj the record relates to.",
        )

    @declared_attr
    def obj(cls):
        return relationship("Obj", doc="The Obj the record relates to.")

    @declared_attr
    def user_id(cls):
        return sa.Column(
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            doc="ID of the User the record belongs to.",
        )

    @declared_attr
    def user(cls):
        return relationship("User", doc="The User the record belongs to.")

    @classmethod
    def for_obj(cls, user_or_token, obj_id):
        return (
            cls.select(user_or_token, options=[selectinload(cls.user)])
            .where(cls.obj_id == obj_id)
            .order_by(cls.created_at)
        )

    def to_dict(self):
        return {
            **{c.name: getattr(self, c.name) for c in self.__table__.columns},
            "user": {field: getattr(self.user, field) for field in USER_FIELDS},
        }


class SourceInterest(ObjUserMixin, Base):
    """A User's declared intent to work on an Obj, so that researchers who would
    otherwise lead parallel efforts on the same source can find each other. A
    User may register several, one per planned publication."""

    __tablename__ = "source_interests"

    title = sa.Column(sa.String, nullable=False, doc="Title of the planned work.")
    description = sa.Column(
        sa.String, nullable=True, doc="Description of the planned work."
    )
    link = sa.Column(
        sa.String, nullable=True, doc="Link to a related page or document."
    )
