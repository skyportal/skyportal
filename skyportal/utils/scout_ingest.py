"""Ingest JPL Scout NEO ToO candidate events into SkyPortal.

Consumes the event schema published by lsst-sssc/scout-alert-bridge, which applies
the SSSC NEOs WG "Filter Criteria for NEO Rubin ToO Triggers" (v0.2) to the JPL
Scout NEOCP feed.
"""

import astropy.units as u
import healpix_alchemy as ha
import sqlalchemy as sa

from baselayer.log import make_log

from ..models import Annotation, Group, Obj, ObjTag, ObjTagOption, Source, SuperObj
from .sso_ingest import designation_to_obj_id, sso_label

log = make_log("scout_ingest")

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
ANNOTATION_ORIGIN = "jpl-scout"

# NEOCP candidates are unconfirmed, so they get their own namespace: a tdes is
# an uncontrolled external string, and one ("ZTF10Fd") can read as a survey id.
OBJ_ID_PREFIX = "scout_"

# JPL Scout's impact rating is a 0-4 scale, not a flag: any non-zero value means
# the orbit admits an Earth impact, and higher is more concerning.
IMPACTOR_TAG = "impactor"
IMPACTOR_TAG_COLOR = "#b71c1c"

IN_CANDIDATE_SET = {"new_candidate", "updated"}
LEAVES_CANDIDATE_SET = {"cancelled", "left_neocp"}


class ScoutIngestError(ValueError):
    pass


def _scout_annotation_data(event):
    """Flatten the scored fields and per-filter results for sorting/filtering."""
    scout = event.get("scout") or {}
    filters = event.get("filters") or {}

    data = {
        key: scout.get(key)
        for key in (
            "neo_score",
            "geocentric_score",
            "impact_rating",
            "rms",
            "num_obs",
            "arc_days",
            "vmag",
            "rate",
            "uncertainty_arcmin",
            "uncertainty_p1_arcmin",
            "ca_dist_ld",
            "h_mag",
            "last_run",
            "url",
        )
        if scout.get(key) is not None
    }
    data["event_type"] = event.get("event_type")
    data["filters_pass"] = filters.get("passes")
    data["filters_version"] = filters.get("version")
    for key, passed in (filters.get("results") or {}).items():
        data[f"filter_{key}"] = passed

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
    else:
        annotation.data = data


def _apply_impactor_tag(session, obj_id, impact_rating, author_id):
    """Tag the object while Scout rates it a possible impactor, untag when not."""
    option = session.scalar(
        sa.select(ObjTagOption).where(ObjTagOption.name == IMPACTOR_TAG)
    )
    tagged = bool(impact_rating)

    if option is None:
        if not tagged:
            return
        option = ObjTagOption(name=IMPACTOR_TAG, color=IMPACTOR_TAG_COLOR)
        session.add(option)
        session.flush()

    existing = session.scalar(
        sa.select(ObjTag).where(
            ObjTag.obj_id == obj_id, ObjTag.objtagoption_id == option.id
        )
    )
    if tagged and existing is None:
        session.add(
            ObjTag(obj_id=obj_id, objtagoption_id=option.id, author_id=author_id)
        )
    elif not tagged and existing is not None:
        session.delete(existing)


def _link_designation(session, obj_id, tdes, iau_designation):
    """Link the NEOCP designation and its permanent IAU name under one SuperObj."""
    label = sso_label(iau_designation or tdes)
    # Found by name, as the survey path does, falling back to whichever group
    # already holds this object under its earlier NEOCP name.
    named = session.scalar(sa.select(SuperObj).where(SuperObj.name == label))
    holding = session.scalar(
        sa.select(SuperObj).where(SuperObj.objs.any(Obj.id == obj_id))
    )

    super_obj = named or holding
    if super_obj is None:
        super_obj = SuperObj(name=label, is_roid=True)
        session.add(super_obj)
    elif named is not None and holding is not None and named is not holding:
        # One body, grouped twice: once by the survey under its designation and
        # once here under the NEOCP name it had first.
        held = {obj.id for obj in named.objs}
        for obj in list(holding.objs):
            if obj.id not in held:
                named.objs.append(obj)
        session.delete(holding)

    super_obj.is_roid = True
    super_obj.name = label

    # The survey path stores a designated body under its own prefixed id.
    designated_id = designation_to_obj_id(iau_designation) if iau_designation else None
    linked = {obj.id for obj in super_obj.objs}
    for candidate_id in (obj_id, designated_id):
        if not candidate_id or candidate_id in linked:
            continue
        obj = session.scalar(sa.select(Obj).where(Obj.id == candidate_id))
        if obj is not None:
            super_obj.objs.append(obj)

    return super_obj

    return super_obj


def ingest_scout_event(
    session,
    event,
    group_ids,
    author_id,
    allow_relaxed=False,
):
    """Apply one scout-alert-bridge event to the database.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session. The caller commits.
    event : dict
        A message validated against the bridge's event schema.
    group_ids : list of int
        Groups the candidate is saved to.
    author_id : int
        User ID recorded as the saver and annotation author.
    allow_relaxed : bool
        Ingest events published under the bridge's `relaxed_test` filter mode,
        which waives all but the identity filters. Off by default so test
        traffic cannot masquerade as a real trigger.

    Returns
    -------
    dict
        Summary with the obj_id and the action taken.
    """
    schema_version = event.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ScoutIngestError(f"Unsupported scout schema_version: {schema_version}")

    event_type = event.get("event_type")
    if event_type not in IN_CANDIDATE_SET | LEAVES_CANDIDATE_SET:
        raise ScoutIngestError(f"Unknown scout event_type: {event_type}")

    tdes = event.get("tdes")
    if not tdes:
        raise ScoutIngestError("Scout event is missing tdes")
    obj_id = designation_to_obj_id(tdes, prefix=OBJ_ID_PREFIX)

    filter_mode = (event.get("provenance") or {}).get("filter_mode", "strict")
    if filter_mode == "relaxed_test" and not allow_relaxed:
        return {"obj_id": obj_id, "action": "skipped_relaxed_test"}

    if event_type in LEAVES_CANDIDATE_SET:
        sources = (
            session.scalars(sa.select(Source).where(Source.obj_id == obj_id))
            .unique()
            .all()
        )
        for source in sources:
            source.active = False
        return {
            "obj_id": obj_id,
            "action": "deactivated",
            "sources": len(sources),
        }

    scout = event.get("scout") or {}
    ra, dec = scout.get("ra_deg"), scout.get("dec_deg")
    if ra is None or dec is None:
        raise ScoutIngestError(f"Scout event for {obj_id} has no position")

    # Scout reports a single positional uncertainty; Obj stores it per axis in degrees.
    uncertainty_deg = None
    if scout.get("uncertainty_arcmin") is not None:
        uncertainty_deg = float(scout["uncertainty_arcmin"]) / 60.0

    obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))
    created = obj is None
    if created:
        obj = Obj(id=obj_id)
        session.add(obj)

    obj.ra, obj.dec = ra, dec
    obj.ra_err = obj.dec_err = uncertainty_deg
    obj.is_roid = True
    obj.healpix = ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)
    if event.get("iau_designation"):
        # Same prefix as the survey path, so one alias query finds every
        # solar-system object however it was ingested.
        aliases = set(obj.alias or [])
        aliases.add(sso_label(event["iau_designation"]))
        obj.alias = sorted(aliases)

    session.flush()

    for group_id in group_ids:
        source = session.scalar(
            sa.select(Source).where(
                Source.obj_id == obj_id, Source.group_id == group_id
            )
        )
        if source is None:
            session.add(
                Source(
                    obj_id=obj_id,
                    group_id=group_id,
                    saved_by_id=author_id,
                    active=True,
                )
            )
        else:
            source.active = True

    groups = (
        session.scalars(sa.select(Group).where(Group.id.in_(group_ids))).unique().all()
    )

    _upsert_annotation(
        session, obj_id, _scout_annotation_data(event), author_id, groups
    )
    _apply_impactor_tag(
        session, obj_id, (event.get("scout") or {}).get("impact_rating"), author_id
    )
    _link_designation(session, obj_id, tdes, event.get("iau_designation"))

    return {
        "obj_id": obj_id,
        "action": "created" if created else "updated",
    }
