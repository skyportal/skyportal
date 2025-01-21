__all__ = ["Taxonomy"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfRelatedRowsAreAccessible,
    Base,
    CustomUserAccessControl,
    DBSession,
    restricted,
)

from .group import Group, accessible_by_groups_members


def taxonomy_update_logic(cls, user_or_token):
    """This function generates the query for taxonomies that the current user
    can update. If the querying user doesn't have System admin or Post taxonomy
    acl, then no taxonomies are accessible to that user under this policy .
    """
    if len({"Delete taxonomy", "System admin"} & set(user_or_token.permissions)) == 0:
        # nothing accessible
        return restricted.query_accessible_rows(cls, user_or_token)

    return DBSession().query(cls)


def taxonomy_delete_logic(cls, user_or_token):
    """This function generates the query for taxonomies that the current user
    can update or delete. If the querying user doesn't have System admin or
    Delete taxonomy acl, then no taxonomies are accessible to that user under
    this policy . Otherwise, the only taxonomies that the user can delete are
    those that have no associated classifications, preventing classifications
    from getting deleted in a cascade when their parent taxonomy is deleted.
    """
    from .classification import Classification

    if len({"Delete taxonomy", "System admin"} & set(user_or_token.permissions)) == 0:
        # nothing accessible
        return restricted.query_accessible_rows(cls, user_or_token)

    # dont allow deletion of any taxonomies that have classifications attached
    return (
        DBSession()
        .query(cls)
        .outerjoin(Classification)
        .group_by(cls.id)
        .having(sa.func.bool_and(Classification.id.is_(None)))
    )


def get_taxonomy_usable_by_user(taxonomy_id, user_or_token, session):
    """Query the database and return the requested Taxonomy if it is accessible
    to the requesting User or Token owner. If the Taxonomy is not accessible or
    if it does not exist, return an empty list.

    Parameters
    ----------
    taxonomy_id : integer
       The ID of the requested Taxonomy.
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.
    session: sqlalchemy.Session
        Database session for this transaction

    Returns
    -------
    tax : `skyportal.models.Taxonomy`
       The requested Taxonomy.
    """

    return session.scalars(
        Taxonomy.select(session.user_or_token)
        .where(Taxonomy.id == taxonomy_id)
        .where(
            Taxonomy.groups.any(
                Group.id.in_([g.id for g in user_or_token.accessible_groups])
            )
        )
    ).all()


# To create or read a classification, you must have read access to the
# underlying taxonomy, and be a member of at least one of the
# classification's target groups
ok_if_tax_and_obj_readable = AccessibleIfRelatedRowsAreAccessible(
    taxonomy="read", obj="read"
)


class Taxonomy(Base):
    """An ontology within which Objs can be classified."""

    # TODO: Add ownership logic to taxonomy
    read = accessible_by_groups_members

    __tablename__ = "taxonomies"
    name = sa.Column(
        sa.String,
        nullable=False,
        doc="Short string to make this taxonomy memorable to end users.",
    )
    hierarchy = sa.Column(
        JSONB,
        nullable=False,
        doc="Nested JSON describing the taxonomy "
        "which should be validated against "
        "a schema before entry.",
    )
    provenance = sa.Column(
        sa.String,
        nullable=True,
        doc="Identifier (e.g., URL or git hash) that "
        "uniquely ties this taxonomy back "
        "to an origin or place of record.",
    )
    version = sa.Column(
        sa.String, nullable=False, doc="Semantic version of this taxonomy"
    )

    isLatest = sa.Column(
        sa.Boolean,
        default=True,
        nullable=False,
        doc="Consider this the latest version of "
        "the taxonomy with this name? Defaults "
        "to True.",
    )
    groups = relationship(
        "Group",
        secondary="group_taxonomy",
        cascade="save-update,merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="List of Groups that have access to this Taxonomy.",
    )

    classifications = relationship(
        "Classification",
        back_populates="taxonomy",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        order_by="Classification.created_at",
        doc="Classifications made within this Taxonomy.",
    )


# system admins can delete any taxonomy that has no classifications attached
# people with the delete taxonomy ACL can delete any taxonomy that has no
# classifications attached and is shared with at least one of their groups
Taxonomy.update = CustomUserAccessControl(taxonomy_update_logic) & Taxonomy.read
Taxonomy.delete = CustomUserAccessControl(taxonomy_delete_logic) & Taxonomy.read
Taxonomy.get_taxonomy_usable_by_user = get_taxonomy_usable_by_user
