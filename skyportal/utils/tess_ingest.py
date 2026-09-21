"""Record which TESS sectors have covered an object.

The footprints are ordinary instrument fields, so coverage is the healpix
containment query every other survey already uses; this only turns the answer
into an annotation the scanning page can filter on.
"""

import healpix_alchemy
import sqlalchemy as sa

from ..models import (
    Annotation,
    Candidate,
    Group,
    InstrumentField,
    InstrumentFieldTile,
    Obj,
)
from .tess import ANNOTATION_ORIGIN, annotation_data, sector_of


def sectors_containing(session, instrument_id, healpix):
    """Sectors whose cameras cover this position, in order."""
    field_ids = session.scalars(
        sa.select(InstrumentField.field_id).where(
            InstrumentFieldTile.instrument_id == instrument_id,
            InstrumentFieldTile.instrument_field_id == InstrumentField.id,
            # Bound as a Point. Tile's bind param reads a bare integer as a
            # NUNIQ index and would decode this nested level-29 pixel into a
            # range at an unrelated position.
            InstrumentFieldTile.healpix.contains(
                sa.literal(healpix, healpix_alchemy.Point)
            ),
        )
    ).all()
    return sorted({sector_of(field_id) for field_id in field_ids})


def annotate_object(session, obj, instrument_id, author_id, group_ids, when=None):
    """Upsert this object's TESS coverage annotation.

    Returns the annotation data, or None if the object has no position to
    match on.
    """
    if obj.healpix is None:
        return None

    data = annotation_data(
        sectors_containing(session, instrument_id, obj.healpix), when=when
    )
    annotation = session.scalar(
        sa.select(Annotation).where(
            Annotation.obj_id == obj.id, Annotation.origin == ANNOTATION_ORIGIN
        )
    )
    if annotation is None:
        groups = (
            session.scalars(sa.select(Group).where(Group.id.in_(group_ids)))
            .unique()
            .all()
        )
        session.add(
            Annotation(
                obj_id=obj.id,
                origin=ANNOTATION_ORIGIN,
                data=data,
                author_id=author_id,
                groups=groups,
            )
        )
    else:
        # The sectors an object has been in only grow, but which one is current
        # changes every few weeks, so the annotation is rewritten in place.
        annotation.data = data
    return data


def stale(now):
    """Whether an annotation disagrees with the sector observing now.

    `sectors` only grows, but which one is current changes every few weeks, so an
    annotation goes stale where the object did not.
    """
    stored = Annotation.data["in_current_sector"].astext.cast(sa.Boolean)
    if now is None:
        # Between sectors nothing is in one, so any stored true is stale.
        return stored.is_(True)
    in_now = Annotation.data["sectors"].contains(sa.func.to_jsonb(sa.literal(now)))
    return stored.is_distinct_from(in_now)


def needs_annotation(now, limit):
    """Candidates whose TESS annotation is missing or no longer true of `now`.

    EXISTS / NOT EXISTS rather than IN / NOT IN: those become semi- and
    anti-joins, where the IN form built a hash of every candidate row and then
    re-checked the annotation subquery once per object.

    One annotation per object per origin is guaranteed by a unique index, so
    "unannotated, or annotated and stale" is the same as "has no annotation
    that is still current" -- a single anti-join rather than two subqueries
    under an OR.
    """
    current = (
        sa.select(1)
        .where(
            Annotation.obj_id == Obj.id,
            Annotation.origin == ANNOTATION_ORIGIN,
            sa.not_(stale(now)),
        )
        .exists()
    )
    return (
        sa.select(Obj)
        .where(
            sa.select(1).where(Candidate.obj_id == Obj.id).exists(),
            Obj.healpix.isnot(None),
            sa.not_(current),
        )
        .limit(limit)
    )
