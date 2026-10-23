import sqlalchemy as sa

from baselayer.app.env import load_env

from ..models import Group
from .data_access import accessible_group_ids_async

_, cfg = load_env()

__all__ = ["resolve_groups", "groups_for_ids"]


def _select_groups(group_ids):
    if group_ids:
        return sa.select(Group).where(Group.id.in_(group_ids))
    return sa.select(Group).where(Group.name == cfg["misc.public_group_name"])


def _checked(groups, group_ids):
    if not group_ids and not groups:
        raise ValueError(
            f"Public group {cfg['misc.public_group_name']!r} not found, "
            "the catalog would be visible to nobody."
        )
    missing = set(group_ids or []) - {group.id for group in groups}
    if missing:
        raise ValueError(
            f"Invalid group_ids: {sorted(missing)} not found or not accessible"
        )
    return list(groups)


async def resolve_groups(session, user, group_ids):
    stmt = _select_groups(group_ids)
    if group_ids:
        stmt = stmt.where(Group.id.in_(await accessible_group_ids_async(user, session)))
    return _checked((await session.scalars(stmt)).all(), group_ids)


def groups_for_ids(session, group_ids):
    return _checked(session.scalars(_select_groups(group_ids)).all(), group_ids)
