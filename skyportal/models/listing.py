import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, AccessibleIfUserMatches


class Listing(Base):
    create = read = update = delete = AccessibleIfUserMatches("user")

    user_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this Listing.",
    )

    user = relationship(
        "User",
        foreign_keys=user_id,
        back_populates="listings",
        doc="The user that saved this object/listing",
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the object that is on this Listing",
    )

    obj = relationship(
        "Obj",
        doc="The object referenced by this listing",
    )

    list_name = sa.Column(
        sa.String,
        index=True,
        nullable=False,
        doc="Name of the list, e.g., 'favorites'. ",
    )


Listing.__table_args__ = (
    sa.Index(
        "listings_main_index",
        Listing.user_id,
        Listing.obj_id,
        Listing.list_name,
        unique=True,
    ),
    sa.Index(
        "listings_reverse_index",
        Listing.list_name,
        Listing.obj_id,
        Listing.user_id,
        unique=True,
    ),
)
