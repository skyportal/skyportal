"""Record which TESS sectors have covered an object.

The footprints are ordinary instrument fields, so coverage is the healpix
containment query every other survey already uses; this only turns the answer
into an annotation the scanning page can filter on.
"""

import sqlalchemy as sa

from ..models import Annotation, Group, InstrumentField, InstrumentFieldTile
from .tess import ANNOTATION_ORIGIN, annotation_data, sector_of


def sectors_containing(session, instrument_id, healpix):
    """Sectors whose cameras cover this position, in order."""
    field_ids = session.scalars(
        sa.select(InstrumentField.field_id).where(
            InstrumentFieldTile.instrument_id == instrument_id,
            InstrumentFieldTile.instrument_field_id == InstrumentField.id,
            InstrumentFieldTile.healpix.contains(healpix),
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
