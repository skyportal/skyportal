"""Tag the objects of an event whose circular extraction carries a watched class.

The mapping lives in config under `app.gcn_extraction_tags`, keyed by the
taxonomy class name; an unmapped class tags nothing.
"""

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.log import make_log

from ..models import GcnEventObj, ObjTag, ObjTagOption

env, cfg = load_env()
log = make_log("gcn_extraction_tags")


def classification_of(extraction_data):
    """The class name an extraction reports, or None."""
    classification = (extraction_data or {}).get("classification") or {}
    return classification.get("classification")


def wants_classification(preferences, label):
    """Whether a user's notification preferences ask for this class.

    An empty or absent watch list means every classification.
    """
    if not label:
        return False
    watched = (preferences or {}).get("gcn_extractions", {}).get(
        "classifications"
    ) or []
    return not watched or label in watched


def tag_name_for(label):
    """The obj tag configured for a taxonomy class, or None."""
    if not label:
        return None
    mapping = cfg.get("app.gcn_extraction_tags") or {}
    return mapping.get(label)


def apply_tags(session, extraction, author_id):
    """Tag every object linked to the extraction's event. Returns the obj ids tagged."""
    tag_name = tag_name_for(classification_of(extraction.data))
    if tag_name is None:
        return []

    option = session.scalar(
        sa.select(ObjTagOption).where(ObjTagOption.name == tag_name)
    )
    if option is None:
        log(f"no ObjTagOption named {tag_name}; skipping")
        return []

    obj_ids = session.scalars(
        sa.select(GcnEventObj.obj_id).where(GcnEventObj.dateobs == extraction.dateobs)
    ).all()

    tagged = []
    for obj_id in obj_ids:
        exists = session.scalar(
            sa.select(ObjTag).where(
                ObjTag.obj_id == obj_id, ObjTag.objtagoption_id == option.id
            )
        )
        if exists is not None:
            continue
        session.add(
            ObjTag(obj_id=obj_id, objtagoption_id=option.id, author_id=author_id)
        )
        tagged.append(obj_id)
    return tagged
