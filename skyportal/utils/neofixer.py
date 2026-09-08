"""NEOFixer target-list ingestion.

NEOFixer (https://neofixer.arizona.edu) scores and ranks NEOs needing
follow-up, per telescope site. It has no scoring of its own in SkyPortal, so
its score rides along as an annotation on objects SkyPortal already tracks.
"""

import requests
import sqlalchemy as sa

from skyportal.models import Annotation, Group, Obj

ANNOTATION_ORIGIN = "neofixer"

# The subset worth carrying: the ranking itself, the numbers an observer picks
# a target on, and the flags that say why it matters. NEOFixer serves 40 fields
# per object; the rest belong on their site.
FIELDS = (
    "score",
    "priority",
    "urgency",
    "importance",
    "vmag",
    "uncert",
    "u",
    "moid",
    "rate",
    "elong",
    "neo",
    "impact",
    "h",
    "nhats",
    "radar",
    "comet",
    "neocp",
)


def fetch_targets(endpoint, site, timeout=300):
    """The site's full target list. NEOFixer serves no partial responses."""
    response = requests.get(endpoint, params={"site": site}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def designation_key(name):
    """Normalize a minor planet designation so "2026 DM1" and "2026DM1" agree."""
    if not name:
        return None
    return "".join(str(name).split()).upper()


def build_target_index(payload):
    """Map every designation NEOFixer offers for a target to that target.

    Targets are keyed by packed designation, but SkyPortal stores whatever the
    broker supplied, so index the provisional and numbered forms too.
    """
    objects = (payload.get("result") or {}).get("objects") or {}
    index = {}
    for packed, target in objects.items():
        for name in (packed, target.get("packed"), target.get("provisional")):
            key = designation_key(name)
            if key:
                index.setdefault(key, target)
        number = target.get("number")
        if number:
            index.setdefault(designation_key(f"({number})"), target)
            index.setdefault(designation_key(number), target)
    return index


def annotation_data(target):
    """The fields worth annotating, dropping the ones NEOFixer left empty."""
    data = {key: target[key] for key in FIELDS if target.get(key) is not None}
    if "time" in target:
        data["time"] = target["time"]
    return data


def _upsert_annotation(session, obj_id, data, author_id, groups):
    annotation = session.scalar(
        sa.select(Annotation).where(
            Annotation.obj_id == obj_id, Annotation.origin == ANNOTATION_ORIGIN
        )
    )
    if annotation is None:
        session.add(
            Annotation(
                obj_id=obj_id,
                origin=ANNOTATION_ORIGIN,
                data=data,
                author_id=author_id,
                groups=groups,
            )
        )
        return "created"
    annotation.data = data
    return "updated"


def annotate_matching_objects(session, payload, author_id, group_ids):
    """Annotate the solar system objects SkyPortal tracks that NEOFixer ranks.

    Only existing objects are touched: NEOFixer lists tens of thousands of
    targets, and SkyPortal knows the handful its brokers have reported.

    Parameters
    ----------
    group_ids : list of int
        Groups the annotations are visible to.
    author_id : int
        User ID recorded as the annotation author.

    Returns
    -------
    dict
        Counts of objects created, updated and considered.
    """
    index = build_target_index(payload)
    if not index:
        return {"created": 0, "updated": 0, "considered": 0, "matched": 0}

    groups = (
        session.scalars(sa.select(Group).where(Group.id.in_(group_ids))).unique().all()
    )

    objs = session.scalars(
        sa.select(Obj).where(Obj.is_roid.is_(True), Obj.mpc_name.isnot(None))
    ).all()

    counts = {"created": 0, "updated": 0, "considered": len(objs), "matched": 0}
    for obj in objs:
        target = index.get(designation_key(obj.mpc_name))
        if target is None:
            continue
        counts["matched"] += 1
        action = _upsert_annotation(
            session, obj.id, annotation_data(target), author_id, groups
        )
        counts[action] += 1
    return counts
