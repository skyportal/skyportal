"""Groups a catalog is shared with.

GalaxyCatalog and SpatialCatalog read as accessible_by_groups_members, so a
catalog attached to no group is invisible to everyone but system admins, and
the galaxies and entries beneath it go with it. Every creation path therefore
has to name groups, and falls back to the sitewide public group, which is the
visibility every catalog ingested before access control already had.
"""

import sqlalchemy as sa

from baselayer.app.env import load_env

from ..models import Group

_, cfg = load_env()

__all__ = ["public_group_id", "resolve_group_ids", "groups_for_ids"]


class NoVisibleGroup(ValueError):
    """Raised when a catalog would end up visible to nobody."""


def public_group_id(session):
    """The sitewide public group's id, or None if the instance has none."""
    return session.scalar(
        sa.select(Group.id).where(Group.name == cfg["misc.public_group_name"])
    )


async def resolve_group_ids(session, user, group_ids):
    """Validate the groups a catalog is to be shared with, defaulting to public.

    ``user`` scopes the lookup, so a requester cannot attach a catalog to a
    group they cannot see.
    """
    if not group_ids:
        public = await session.scalar(
            sa.select(Group.id).where(Group.name == cfg["misc.public_group_name"])
        )
        if public is None:
            raise NoVisibleGroup(
                "No groups were given and the public group "
                f"{cfg['misc.public_group_name']!r} does not exist, so the "
                "catalog would be visible to nobody."
            )
        return [public]

    found = (
        (await session.scalars(Group.select(user).where(Group.id.in_(group_ids))))
        .unique()
        .all()
    )
    missing = set(group_ids) - {group.id for group in found}
    if missing:
        raise NoVisibleGroup(
            f"Cannot find one or more groups with IDs: {sorted(missing)}."
        )
    return [group.id for group in found]


def groups_for_ids(session, group_ids):
    """The Group rows for ``group_ids``, for attaching in a background session.

    The ids have already been validated against the requester; falling back to
    the public group covers the paths that never had one to validate against.
    """
    if not group_ids:
        public = public_group_id(session)
        if public is None:
            raise NoVisibleGroup(
                "No groups were given and the public group "
                f"{cfg['misc.public_group_name']!r} does not exist, so the "
                "catalog would be visible to nobody."
            )
        group_ids = [public]
    return list(
        session.scalars(sa.select(Group).where(Group.id.in_(group_ids))).unique().all()
    )
