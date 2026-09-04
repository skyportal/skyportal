# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import ast
import asyncio
import binascii
import datetime
import io
import json
import operator  # noqa: F401
import os
import re
import tempfile
import traceback
from datetime import timedelta
from typing import Annotated, ClassVar
from urllib.parse import urlparse, urlsplit

import arrow
import astropy
import gcn
import healpy as hp
import humanize
import ligo.skymap.bayestar as ligo_bayestar
import ligo.skymap.io
import ligo.skymap.postprocess
import lxml
import numpy as np
import pandas as pd
import requests
import sqlalchemy as sa
import xmlschema
from astropy.table import Table
from astropy.time import Time
from marshmallow import Schema, validate
from marshmallow.exceptions import ValidationError
from marshmallow.fields import Integer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    joinedload,
    scoped_session,
    selectinload,
    sessionmaker,
    undefer,
)
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.sql.expression import cast
from tabulate import tabulate
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.json_util import to_json
from baselayer.log import make_log
from skyportal.models.gcn import SOURCE_RADIUS_THRESHOLD
from skyportal.models.photometry import Photometry

from ...enum_types import GCN_EVENT_OBJ_STATUSES
from ...models import (
    Allocation,
    CatalogQuery,
    CommentOnGCN,
    DBSession,
    DefaultGcnTag,
    DefaultObservationPlanRequest,
    EventObservationPlan,
    GcnAssociationRule,
    GcnEvent,
    GcnEventAssociation,
    GcnEventExtraction,
    GcnEventMMADetector,
    GcnEventObj,
    GcnEventUser,
    GcnNotice,
    GcnProperty,
    GcnReport,
    GcnSummary,
    GcnTag,
    GcnTrigger,
    Group,
    GroupGcnEvent,
    Instrument,
    InstrumentField,
    InstrumentFieldTile,
    Localization,
    LocalizationProperty,
    LocalizationTag,
    LocalizationTile,
    MMADetector,
    Obj,
    ObservationPlanRequest,
    PhotStat,
    Source,
    SurveyEfficiencyForObservations,
    User,
    UserNotification,
)
from ...utils.crossmatch import skymap_overlap_integral
from ...utils.gcn import (
    from_bytes,
    from_cone,
    from_ellipse,
    from_igwn_gwalert,
    from_polygon,
    from_url,
    get_contour,
    get_dateobs,
    get_designation_date,
    get_json_tags,
    get_notice_aliases,
    get_properties,
    get_skymap,
    get_skymap_metadata,
    get_skymap_properties,
    get_tags,
    get_trigger,
    get_xml_notice_type,
    has_skymap,
)
from ...utils.naive_datetime import UTCTZnaiveDateTime, utcnow_naive
from ...utils.notifications import post_notification
from ...utils.parse import get_page_and_n_per_page
from ..base import BaseHandler
from .galaxy import MAX_GALAXIES, get_galaxies, get_galaxies_completeness
from .gcn_gracedb import post_gracedb_data
from .observation import MAX_OBSERVATIONS, get_observations
from .observation_plan import post_observation_plan
from .source import (
    MAX_SOURCES_PER_PAGE,
    get_source,
    get_sources,
    post_source,
    post_source_async,
    serialize,
)

log = make_log("api/gcn_event")

env, cfg = load_env()

Session = scoped_session(sessionmaker())

MAX_GCNEVENTS = 1000

op_options = [
    "lt",
    "le",
    "eq",
    "ne",
    "ge",
    "gt",
]


async def gcnevent_group_ids(session, dateobs):
    """Group ids a GcnEvent is restricted to, looked up by dateobs.

    Queried explicitly rather than read off ``event.groups``: that relationship
    lazy-loads, which raises MissingGreenlet under an async session whenever the
    event was fetched rather than freshly constructed.
    """
    return list(
        (
            await session.scalars(
                sa.select(GroupGcnEvent.group_id)
                .join(GcnEvent, GcnEvent.id == GroupGcnEvent.gcnevent_id)
                .where(GcnEvent.dateobs == dateobs)
            )
        ).all()
    )


async def resolve_gcnevent_groups(session, user, group_ids=None):
    """Resolve the groups a newly created GcnEvent should be readable by.

    GcnEvent.read is group-scoped, so an event with no groups is invisible to
    everyone but system admins. Public streams therefore default to the sitewide
    public group, preserving the pre-restriction behavior where every GCN event
    was readable by all users. Proprietary streams (e.g. the Einstein Probe
    unverified-candidate feed) pass an explicit ``group_ids`` list instead.

    Parameters
    ----------
    session : sqlalchemy session
    user : `skyportal.models.User`
        The user on whose behalf the event is being created.
    group_ids : list of int, optional
        Groups to restrict the event to. If None or empty, the sitewide public
        group is used.

    Returns
    -------
    list of `skyportal.models.Group`
    """
    if group_ids:
        groups = (
            (await session.scalars(Group.select(user).where(Group.id.in_(group_ids))))
            .unique()
            .all()
        )
        missing = set(group_ids) - {g.id for g in groups}
        if missing:
            raise ValueError(
                f"Invalid group_ids: {sorted(missing)} not found or not accessible"
            )
        return list(groups)

    public_group = await session.scalar(
        sa.select(Group).where(Group.name == cfg["misc"]["public_group_name"])
    )
    if public_group is None:
        raise ValueError(
            "Sitewide public group not found; cannot determine GCN event access"
        )
    return [public_group]


class GcnEventAliasPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str | None = Field(default=None, description="Alias to add to the event")


class GcnEventAliasDeleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str | None = Field(
        default=None, description="Alias to remove from the event"
    )


class GcnEventTagPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dateobs: str | None = Field(default=None, description="UTC event timestamp")
    text: str | None = Field(default=None, description="GCN Event tag")


class GcnEventTagPostResponse(BaseModel):
    gcntag_id: int = Field(description="New GcnEvent Tag ID")


class GcnEventTagDeleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag: str | None = Field(default=None, description="Tag to remove from the event")


class GcnEventPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    xml: str | None = Field(default=None, description="VOEvent XML content.")
    json_notice: str | dict | None = Field(
        default=None, alias="json", description="JSON notice content."
    )
    dateobs: str | None = Field(default=None, description="UTC event timestamp")
    trigger_id: str | int | None = Field(
        default=None, description="Trigger ID of the event, if any"
    )
    aliases: list[str] | None = Field(default=None, description="Event aliases")
    group_ids: list[int] | None = Field(
        default=None,
        description="Groups the event is readable by. Defaults to the sitewide "
        "public group.",
    )
    tags: list[str] | None = Field(default=None, description="Event tags")
    properties: dict | None = Field(default=None, description="Event properties")
    skymap: dict | str | None = Field(
        default=None,
        description="Localization skymap: a dict (cone/ellipse/polygon/healpix), "
        "a base64/bytes string, or a URL.",
    )


class GcnEventPostResponse(BaseModel):
    gcnevent_id: int | None = Field(description="New GcnEvent ID")
    dateobs: str | None = Field(description="UTC event timestamp of the event")
    notice_id: int | None = Field(description="ID of the created GCN notice, if any")


class GcnEventUserPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    userID: int | None = Field(
        default=None, description="ID of the user to add as advocate"
    )


class GcnSummaryPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, description="Title of the summary")
    number: str | int | None = Field(default=None, description="GCN circular number")
    subject: str | None = Field(default=None, description="Subject of the summary")
    userIds: list[int] | int | None = Field(
        default=None,
        description="User ids to mention in the summary. Comma-separated.",
    )
    groupId: int | None = Field(
        default=None, description="id of the group that creates the summary."
    )
    startDate: str | None = Field(default=None, description="Filter by start date")
    endDate: str | None = Field(default=None, description="Filter by end date")
    localizationName: str | None = Field(
        default=None, description="Name of localization / skymap to use."
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include fields. Defaults to 0.95.",
    )
    numberDetections: int | None = Field(
        default=2,
        description="Return only sources who have at least numberDetections detections. Defaults to 2.",
    )
    numberObservations: int | None = Field(
        default=1,
        description="Return only sources with at least this many observations. Defaults to 1.",
    )
    showSources: bool = Field(default=False, description="Show sources in the summary")
    showGalaxies: bool = Field(
        default=False, description="Show galaxies in the summary"
    )
    showObservations: bool = Field(
        default=False, description="Show observations in the summary"
    )
    noText: bool = Field(
        default=False, description="Do not include text in the summary, only tables."
    )
    photometryInWindow: bool = Field(
        default=False,
        description="Limit photometry to that within startDate and endDate.",
    )
    statsMethod: str = Field(
        default="python",
        description="Method to use for calculating statistics. Defaults to python. Options are python and db.",
    )
    instrumentIds: list[int] | None = Field(
        default=None,
        description="List of instrument ids to include in the summary. Defaults to all instruments if not specified.",
    )
    acknowledgements: str | None = Field(
        default=None, description="Acknowledgements to include in the summary."
    )


class GcnSummaryPostResponse(BaseModel):
    id: int = Field(description="ID of the created GCN summary")


class GcnSummaryPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str | None = Field(default=None, description="Updated summary text")


class GcnReportPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reportName: str | None = Field(default=None, description="Name of the report")
    groupId: int | None = Field(
        default=None, description="id of the group that creates the report."
    )
    startDate: str | None = Field(default=None, description="Filter by start date")
    endDate: str | None = Field(default=None, description="Filter by end date")
    localizationName: str | None = Field(
        default=None, description="Name of localization / skymap to use."
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include fields. Defaults to 0.95.",
    )
    numberDetections: int | None = Field(
        default=2,
        description="Return only sources who have at least numberDetections detections. Defaults to 2.",
    )
    showSources: bool = Field(default=False, description="Show sources in the report")
    showObservations: bool = Field(
        default=False, description="Show observations in the report"
    )
    showSurveyEfficiencies: bool = Field(
        default=False, description="Show survey efficiencies in the report"
    )
    photometryInWindow: bool = Field(
        default=False,
        description="Limit photometry to that within startDate and endDate.",
    )
    statsMethod: str = Field(
        default="python",
        description="Method to use for calculating statistics. Defaults to python. Options are python and db.",
    )
    instrumentIds: list[int] | None = Field(
        default=None,
        description="List of instrument ids to include in the report. Defaults to all instruments if not specified.",
    )


class GcnReportPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict | None = Field(
        default=None, description="Report data (e.g. sources) to update"
    )
    published: bool | None = Field(
        default=None, description="Whether the report is published"
    )


class GcnEventTriggerPutBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    triggered: bool | str | None = Field(
        default=None,
        description="Triggered status of the allocation for this event",
    )


class ObjGcnEventPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). "
        "If provided, filter by GcnEvent.dateobs >= startDate.",
    )
    endDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). "
        "If provided, filter by GcnEvent.dateobs <= endDate.",
    )
    probability: float | None = Field(
        default=None,
        description="Integrated probability contour to crossmatch within (default 0.95).",
    )
    beforeFirstDetection: bool = Field(
        default=False,
        description="If true, only crossmatch GCN events at or before the source's "
        "first detection.",
    )
    gcnTagKeep: list[str] | str | None = Field(
        default=None, description="Only crossmatch events having any of these GCN tags."
    )
    gcnTagRemove: list[str] | str | None = Field(
        default=None, description="Exclude events having any of these GCN tags."
    )
    localizationTagKeep: list[str] | str | None = Field(
        default=None,
        description="Only crossmatch events with a localization having any of these tags.",
    )
    localizationTagRemove: list[str] | str | None = Field(
        default=None,
        description="Exclude events with a localization having any of these tags.",
    )
    gcnPropertiesFilter: list[str] | str | None = Field(
        default=None,
        description='GCN property filters, each "name" or "name:value:op" '
        "(op in lt,le,eq,ne,ge,gt).",
    )
    localizationPropertiesFilter: list[str] | str | None = Field(
        default=None,
        description="Localization property filters, same format as gcnPropertiesFilter.",
    )


class DefaultGcnTagPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_tag_name: str | None = Field(default=None, description="Default tag name.")
    filters: dict | None = Field(
        default=None,
        description="Filters to determine which of the default gcn tags get executed for which events",
    )


class DefaultGcnTagPostResponse(BaseModel):
    id: int = Field(description="New default gcn tag ID")


async def post_gcn_source(
    dateobs: str,
    localization_name: str,
    root,
    notice_type,
    user,
    session,
    group_ids=None,
):
    """Create a source at the event's own position, if the localization is tight enough.

    ``group_ids`` must be the groups of the GcnEvent this source is derived
    from. Nothing is created for an event that is not in the sitewide public
    group: the source sits at the event's own sky position, and Obj.read is
    ``public`` in SkyPortal by design (access control lives on Source and
    Candidate, not Obj). Creating one would therefore disclose the position of
    a restricted event to every user -- and the object id is derived from
    dateobs, so it is enumerable rather than merely discoverable.

    This is not hypothetical for the proprietary Einstein Probe feed: its real
    position errors are ~2-3 arcmin, comfortably inside SOURCE_RADIUS_THRESHOLD
    (8 arcmin), so every EP candidate reaches this path.
    """
    try:
        ra, dec, error = (float(val) for val in localization_name.split("_"))
        if error < SOURCE_RADIUS_THRESHOLD:
            log(
                f"Creating source for event {dateobs} with Localization {localization_name}."
            )
            event_time = Time(dateobs)
            dateobs_txt = event_time.isot
            source_name = f"{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}_{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
            source = {
                "id": source_name,
                "ra": ra,
                "dec": dec,
                "origin": None,
                "t0": event_time.mjd,
            }
            event_tags = []
            if isinstance(root, dict):
                event_tags = get_json_tags(root)
            else:
                event_tags = get_tags(root, notice_type)
            tags_formatted = [tag.upper().strip() for tag in event_tags]

            if "LVC" in tags_formatted:
                source["origin"] = "LVC"
            elif "SWIFT" in tags_formatted:
                source["origin"] = "Swift"
            elif "FERMI" in tags_formatted:
                source["origin"] = "Fermi"
            elif "SVOM" in tags_formatted:
                source["origin"] = "SVOM"
            elif "EINSTEIN PROBE" in tags_formatted:
                source["origin"] = "Einstein Probe"

            if "GRB" in tags_formatted:
                source["id"] = f"GRB-{source_name}"
            elif "GW" in tags_formatted:
                source["id"] = f"GW-{source_name}"
            elif "EINSTEIN PROBE" in tags_formatted:
                source["id"] = f"EP-{source_name}"
            else:
                source["id"] = f"GCN-{source_name}"

            public_group = await session.scalar(
                sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
            )
            if public_group is None:
                log(
                    f"WARNING: Public group {cfg['misc.public_group_name']} not found in the database, cannot post source"
                )
                return False

            if group_ids is not None and public_group.id not in group_ids:
                log(
                    f"Event {dateobs} is restricted to groups {sorted(group_ids)}; "
                    f"not creating a source for it, since Obj.read is public and "
                    f"would expose the event's position to all users."
                )
                return False

            source["group_ids"] = [public_group.id]

            if source.get("id", None) is not None:
                existing_source = await session.scalar(
                    Source.select(user).where(Source.obj_id == source["id"])
                )
                if existing_source is None:
                    log(
                        f"Posting source for event {dateobs} with Localization {localization_name} with id {source['id']}."
                    )
                    if source["origin"] is None:
                        del source["origin"]
                    await post_source_async(source, user.id, session)
                    return True
        else:
            log(
                f"Source radius {error:.4f} is larger than threshold {SOURCE_RADIUS_THRESHOLD:.4f}, not creating source for event {dateobs} with Localization {localization_name}."
            )

    except Exception as e:
        if not (
            isinstance(e, ValueError) and "could not convert string to float" in str(e)
        ):
            log(traceback.format_exc())
            log(
                f"Failed to create source for event {dateobs} with Localization {localization_name}: {str(e)}."
            )
    finally:
        return False


async def detectors_from_tags(session, user, tag_texts):
    """MMADetectors named by any of ``tag_texts``, by nickname or alias.

    Notices do not agree on a detector's name -- GCN tags Fermi-GBM alerts
    "Fermi" and Einstein Probe ones "Einstein Probe" -- so a nickname-only match
    silently links nothing for those missions.
    """
    if not tag_texts:
        return []
    texts = list(set(tag_texts))
    result = await session.scalars(
        MMADetector.select(user).where(
            sa.or_(
                MMADetector.nickname.in_(texts),
                *[MMADetector.aliases.any(text) for text in texts],
            )
        )
    )
    return result.unique().all()


async def link_detectors_to_event(session, user, event, tag_texts):
    """Attach the detectors named by ``tag_texts`` to an event.

    Additive: a later notice naming fewer detectors must not drop the ones an
    earlier one established. Takes the event rather than its id, which a newly
    created one does not have until the flush below.
    """
    detectors = await detectors_from_tags(session, user, tag_texts)
    if not detectors:
        return []

    await session.flush()
    event_loaded = await session.scalar(
        sa.select(GcnEvent)
        .where(GcnEvent.id == event.id)
        .options(selectinload(GcnEvent.detectors))
    )
    if event_loaded is None:
        return []
    existing = {d.id for d in event_loaded.detectors}
    added = [d for d in detectors if d.id not in existing]
    if added:
        event_loaded.detectors = list(event_loaded.detectors) + added
    return added


async def post_gcn_circular(circular, session, window_hours=12):
    """Record one GCN circular on the event it reports on.

    Circulars carry the designation GCN itself assigned them (``eventId``), so
    the association needs no parsing of the body — unlike the TACH backfill,
    which regexes designations out of circular text after the fact.

    The circular is added to ``GcnEvent.circulars`` and its designation to
    ``GcnEvent.aliases``, which is what makes the event findable by name
    afterwards. Circulars never create events: one whose event has no notice in
    the database is skipped, since the alternative is manufacturing events with
    no localization from prose alone.

    Returns the event's dateobs, or None if nothing was recorded.
    """
    try:
        circular_id = int(circular.get("circularId"))
    except (TypeError, ValueError):
        return None
    event_id = circular.get("eventId")
    subject = circular.get("subject") or ""
    if not event_id:
        return None

    event = await _find_event_for_designation(
        event_id, session, window_hours, text=str(circular.get("body") or "")
    )
    if event is None:
        return None

    # JSONB keys are strings; keep the type stable so the membership test holds
    # across restarts and matches what TACH writes.
    key = str(circular_id)
    circulars = dict(event.circulars or {})
    if circulars.get(key) == subject and _alias_present(event, event_id):
        return event.dateobs  # already recorded

    circulars[key] = subject
    event.circulars = circulars
    flag_modified(event, "circulars")

    if not _alias_present(event, event_id):
        event.aliases = list(event.aliases or []) + [event_id]
        flag_modified(event, "aliases")

    await session.commit()
    return event.dateobs


def _alias_present(event, event_id):
    """Aliases are stored in several spellings (GRB 260604C, GRB260604C, LVC#S...)."""
    needle = event_id.replace(" ", "").lower()
    return any(
        needle in str(alias).replace(" ", "").lower() for alias in (event.aliases or [])
    )


async def _find_event_for_designation(event_id, session, window_hours, text=""):
    """The event a designation names, by alias, then trigger id, then date.

    A designation fixes only the UTC day, so the date search spans a window and
    takes the single event in it — an ambiguous day is left alone rather than
    guessed at, since attaching a circular to the wrong event is worse than
    attaching it to none. A trigger id shared by the notice and the circular
    (SVOM's "burst-id sb26060404") settles it outright, so it is tried first.
    """
    needle = event_id.replace(" ", "").lower()
    event = await session.scalar(
        sa.select(GcnEvent).where(
            sa.func.replace(
                sa.func.lower(cast(GcnEvent.aliases, sa.String)), " ", ""
            ).like(f"%{needle}%")
        )
    )
    if event is not None:
        return event

    # Only reasonably distinctive ids: a short numeric one would match digits
    # anywhere in the prose.
    candidates = set(re.findall(r"\b[A-Za-z0-9_-]{6,}\b", text))
    if candidates:
        event = await session.scalar(
            sa.select(GcnEvent).where(GcnEvent.trigger_id.in_(candidates))
        )
        if event is not None:
            return event

    day = get_designation_date(event_id)
    if day is None:
        return None
    # GcnEvent.dateobs is a naive UTC column, so compare against naive datetimes.
    centre = datetime.datetime(day.year, day.month, day.day, 12)  # noqa: DTZ001
    events = (
        await session.scalars(
            sa.select(GcnEvent).where(
                GcnEvent.dateobs >= centre - timedelta(hours=window_hours),
                GcnEvent.dateobs <= centre + timedelta(hours=window_hours),
            )
        )
    ).all()
    return events[0] if len(events) == 1 else None


async def post_gcnevent_from_xml(
    payload,
    user_id,
    session,
    notice_type=None,
    post_skymap=True,
    asynchronous=True,
    notify=True,
):
    """Post GcnEvent to database from voevent xml.
    payload: str
        VOEvent readable string
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """
    user = await session.get(User, user_id)

    schema = f"{os.path.dirname(__file__)}/../../utils/schema/VOEvent-v2.0.xsd"
    voevent_schema = xmlschema.XMLSchema(schema)
    if voevent_schema.is_valid(payload):
        try:
            payload = payload.encode("ascii")
        except AttributeError:
            pass
        root = lxml.etree.fromstring(payload)
    else:
        raise ValueError("xml file is not valid VOEvent")

    gcn_notice = await session.scalar(
        GcnNotice.select(user).where(GcnNotice.ivorn == root.attrib["ivorn"])
    )
    if gcn_notice is not None:
        raise ValueError(f"GcnNotice with ivorn {root.attrib['ivorn']} already exists.")

    dateobs = get_dateobs(root)
    trigger_id = get_trigger(root)
    if notice_type is None:
        try:
            notice_type = str(gcn.NoticeType(int(gcn.get_notice_type(root))).name)
        except Exception:
            notice_type = get_xml_notice_type(root)

    aliases = get_notice_aliases(root, notice_type)

    if trigger_id is not None:
        event = await session.scalar(
            GcnEvent.select(user).where(GcnEvent.trigger_id == trigger_id)
        )
    else:
        event = await session.scalar(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        )

    if event is None:
        event = GcnEvent(
            dateobs=dateobs,
            sent_by_id=user_id,
            trigger_id=trigger_id,
            aliases=aliases,
        )
        # VOEvent XML always comes off the public GCN stream, so it takes the
        # public-group default.
        event.groups = await resolve_gcnevent_groups(session, user)
        session.add(event)
        await session.commit()
        dateobs = event.dateobs
    else:
        dateobs = event.dateobs
        update_check = await session.scalar(
            GcnEvent.select(user, mode="update").where(GcnEvent.id == event.id)
        )
        if update_check is None:
            raise ValueError(
                "Insufficient permissions: GCN event can only be updated by original poster"
            )

    event_id = event.id

    gcn_notice = GcnNotice(
        content=payload,
        ivorn=root.attrib["ivorn"],
        notice_type=notice_type,
        stream=urlparse(root.attrib["ivorn"]).path.lstrip("/"),
        date=root.find("./Who/Date").text,
        has_localization=has_skymap(root, notice_type),
        localization_ingested=False,
        dateobs=dateobs,
        sent_by_id=user_id,
        notice_format="voevent",
    )
    session.add(gcn_notice)
    await session.commit()
    notice_id = gcn_notice.id

    properties_dict, tags_list = get_properties(root)
    properties = GcnProperty(dateobs=dateobs, sent_by_id=user_id, data=properties_dict)
    session.add(properties)
    await session.commit()

    tags_text = list(get_tags(root, notice_type)) + tags_list
    # Every notice for an event re-emits its tags; only store the new ones.
    existing_tags = set(
        (
            await session.scalars(
                sa.select(GcnTag.text).where(GcnTag.dateobs == dateobs)
            )
        ).all()
    )
    tags = [
        GcnTag(
            dateobs=dateobs,
            text=text,
            sent_by_id=user_id,
        )
        for text in dict.fromkeys(tags_text)
        if text not in existing_tags
    ]
    session.add_all(tags)
    await session.commit()

    if await link_detectors_to_event(session, user, event, tags_text):
        await session.commit()

    gracedb_id = None
    aliases = event.aliases
    for alias in aliases:
        if "LVC" in alias:
            gracedb_id = alias.split("#")[-1]
            break

    if gracedb_id is not None:
        if asynchronous:
            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            IOLoop.current().run_in_executor(
                None,
                lambda: post_gracedb_data(event.dateobs, gracedb_id, user_id),
            )
        else:
            post_gracedb_data(event.dateobs, gracedb_id, user_id)

    found_skymap = False
    if post_skymap:
        try:
            await post_skymap_from_notice(
                dateobs, notice_id, user_id, session, asynchronous, notify
            )
            found_skymap = True
        except Exception:
            found_skymap = False

    if not found_skymap and notify:
        gcn_tags = await add_default_gcn_tags_async(user, session, dateobs=dateobs)
        if gcn_tags is not None and len(gcn_tags) > 0:
            session.add_all(gcn_tags)
        try:
            asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        request_body = {
            "target_class_name": "GcnNotice",
            "target_id": notice_id,
        }

        IOLoop.current().run_in_executor(
            None,
            lambda: post_notification(request_body, timeout=30),
        )

    return dateobs, event_id, notice_id


async def post_skymap_from_notice(
    dateobs, notice_id, user_id, session, asynchronous=True, notify=True
):
    """Post skymap to database from gcn notice."""
    user = await session.get(User, user_id)

    gcn_notice = await session.scalar(
        GcnNotice.select(user).where(GcnNotice.id == notice_id)
    )

    if gcn_notice is None:
        raise ValueError(f"No GcnNotice with id {notice_id} found.")

    notice_type = gcn_notice.notice_type

    try:
        root = lxml.etree.fromstring(gcn_notice.content)
    except lxml.etree.XMLSyntaxError:
        root = json.loads(gcn_notice.content.decode("utf8"))

    skymap, url, properties, tags = None, None, None, None
    try:
        skymap, url, properties, tags = get_skymap(root, notice_type)
    except Exception as e:
        raise ValueError(f"Failed to get skymap from gcn notice {gcn_notice.id}: {e}")

    if skymap is None:
        raise Exception(f"No skymap found for event {dateobs} with notice {notice_id}")

    skymap["dateobs"] = dateobs
    skymap["sent_by_id"] = user_id

    localization_id = None
    localization = await session.scalar(
        Localization.select(user).where(
            Localization.dateobs == skymap["dateobs"],
            Localization.localization_name == skymap["localization_name"],
        )
    )
    if localization is None:
        localization = Localization(**skymap, notice_id=notice_id)
        session.add(localization)
        await session.commit()
        localization_id = localization.id

        log(f"Generating tiles/properties/contours for localization {localization.id}")
        # The tiles/properties helpers run in a sync executor thread with their
        # own sync session — async caller cannot await them, so always dispatch.
        try:
            asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        IOLoop.current().run_in_executor(
            None,
            lambda: add_tiles_properties_contour_and_obsplan(
                localization_id,
                user_id,
                url=url,
                notify=notify,
                properties=properties,
                tags=tags,
            ),
        )

        gcn_notice.localization_ingested = True
        session.add(gcn_notice)
        await session.commit()

        await post_gcn_source(
            dateobs,
            skymap["localization_name"],
            root,
            notice_type,
            user,
            session,
            group_ids=await gcnevent_group_ids(session, dateobs),
        )

    else:
        localization_id = localization.id
        log(f"Localization {localization_id} already exists.")

    return localization_id


async def post_gcnevent_from_json(
    payload, user_id, session, post_skymap=True, asynchronous=True, notify=True
):
    """Post GcnEvent to database from JSON.
    payload: dict
        JSON containing alert payload
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception as e:
            raise ValueError(f"Could not load str payload: {e}")
    elif isinstance(payload, bytes):
        try:
            payload = json.loads(payload.decode("utf8"))
        except Exception as e:
            raise ValueError(f"Could not load str payload: {e}")
    elif not isinstance(payload, dict):
        raise ValueError(
            f"Unsupported JSON payload dtype, must be one of string, bytes, or dict, not {type(payload)}"
        )

    # Raw IGWN/LVK gwalert alerts are normalized to the canonical notice shape.
    # from_igwn_gwalert is idempotent, so this is safe if already normalized.
    if payload.get("superevent_id") is not None and payload.get("alert_type"):
        payload = from_igwn_gwalert(payload)

    user = await session.get(User, user_id)

    # A retraction (e.g. an IGWN gwalert) carries no trigger_time; its dateobs is
    # resolved from the existing event matched below via ref_ID/aliases.
    dateobs = None
    if payload.get("trigger_time"):
        dateobs = Time(payload["trigger_time"], format="isot", precision=0)
        dateobs = Time(dateobs.iso).datetime

    event = None
    ref_ID = payload.get("ref_ID", None)
    if ref_ID is not None:
        event = await session.scalar(
            GcnEvent.select(user).where(
                sa.func.lower(cast(GcnEvent.aliases, sa.String)).like(
                    f"%{ref_ID.lower()}%"
                )
            )
        )

    if event is None and dateobs is not None:
        event = await session.scalar(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        )

    aliases = payload.get("aliases") or []
    if event is None:
        if dateobs is None:
            raise ValueError(
                "Cannot ingest GCN notice: no trigger_time and no existing event "
                "to update (e.g. retraction of an unknown event)."
            )
        event = GcnEvent(
            dateobs=dateobs,
            aliases=aliases or None,
            sent_by_id=user.id,
        )
        event.groups = await resolve_gcnevent_groups(
            session, user, payload.get("group_ids")
        )
        session.add(event)
        await session.commit()

        dateobs = event.dateobs
    else:
        dateobs = event.dateobs
        update_check = await session.scalar(
            GcnEvent.select(user, mode="update").where(GcnEvent.id == event.id)
        )
        if update_check is None:
            raise ValueError(
                "Insufficient permissions: GCN event can only be updated by original poster"
            )
        # add any new aliases (e.g. LVC#superevent) not already present
        new_aliases = [a for a in aliases if a not in (event.aliases or [])]
        if new_aliases:
            event.aliases = (event.aliases or []) + new_aliases
            session.add(event)
            await session.commit()

    event_id = event.id

    tag_texts = get_json_tags(payload)

    # A later notice for the same event (e.g. an IGWN update/retraction) re-emits
    # tags already stored; skip those to avoid a unique-constraint violation.
    existing_tags = set(
        (
            await session.scalars(
                sa.select(GcnTag.text).where(GcnTag.dateobs == event.dateobs)
            )
        ).all()
    )

    tags = [
        GcnTag(
            dateobs=event.dateobs,
            text=text,
            sent_by_id=user.id,
        )
        for text in tag_texts
        if text not in existing_tags
    ]

    for tag in tags:
        session.add(tag)

    await link_detectors_to_event(session, user, event, tag_texts)

    # Store classification/astro/FAR properties (e.g. from an IGWN gwalert).
    if payload.get("properties"):
        session.add(
            GcnProperty(
                dateobs=event.dateobs,
                sent_by_id=user.id,
                data=payload["properties"],
            )
        )
    await session.commit()

    date = dateobs
    if "alert_datetime" in payload:
        date = Time(payload["alert_datetime"], format="isot", precision=0)
        date = Time(date.iso).datetime

    if "instrument" in payload:
        instrument = payload["instrument"]
    elif "type" in payload:
        instrument = payload["type"].replace(" ", "-")
    else:
        instrument = "Unknown"

    notice_type = payload.get("notice_type")
    gcn_notice = GcnNotice(
        content=json.dumps(payload).encode("utf-8"),
        ivorn=f"{instrument}-{date.strftime('%Y-%m-%dT%H:%M:%S')}",
        notice_type=notice_type,
        stream=instrument,
        date=date,
        has_localization=True,
        localization_ingested=False,
        dateobs=event.dateobs,
        sent_by_id=user_id,
        notice_format="json",
    )
    session.add(gcn_notice)
    await session.commit()
    notice_id = gcn_notice.id

    found_skymap = False
    if post_skymap:
        try:
            await post_skymap_from_notice(
                dateobs, notice_id, user_id, session, asynchronous, notify
            )
            found_skymap = True
        except Exception:
            found_skymap = False

    if not found_skymap and notify:
        gcn_tags = await add_default_gcn_tags_async(user, session, dateobs=dateobs)
        if gcn_tags is not None and len(gcn_tags) > 0:
            session.add_all(gcn_tags)
        try:
            loop = asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        request_body = {
            "target_class_name": "GcnNotice",
            "target_id": notice_id,
        }

        IOLoop.current().run_in_executor(
            None,
            lambda: post_notification(request_body, timeout=30),
        )

    return dateobs, event_id, notice_id


async def post_gcnevent_from_dictionary(payload, user_id, session, asynchronous=True):
    """Post GcnEvent to database from dictionary.
    payload: dict
        Dictionary containing dateobs and skymap
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """
    user = await session.get(User, user_id)

    dateobs = arrow.get(payload["dateobs"]).naive

    # Prefer trigger_id for identity when the caller supplies one, matching the
    # VOEvent path. Streams that revise an event's time between versions (e.g.
    # the Einstein Probe data center) would otherwise create a fresh event per
    # revision instead of adding a localization to the existing one.
    trigger_id = payload.get("trigger_id")
    event = None
    if trigger_id is not None:
        event = await session.scalar(
            GcnEvent.select(user).where(GcnEvent.trigger_id == str(trigger_id))
        )
    if event is None:
        event = await session.scalar(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        )

    if event is None:
        event = GcnEvent(
            dateobs=dateobs,
            sent_by_id=user.id,
            trigger_id=str(trigger_id) if trigger_id is not None else None,
            aliases=payload.get("aliases") or None,
        )
        event.groups = await resolve_gcnevent_groups(
            session, user, payload.get("group_ids")
        )
        session.add(event)
    else:
        update_check = await session.scalar(
            GcnEvent.select(user, mode="update").where(GcnEvent.id == event.id)
        )
        if update_check is None:
            raise ValueError(
                "Insufficient permissions: GCN event can only be updated by original poster"
            )

    if "properties" in payload:
        properties = GcnProperty(
            dateobs=event.dateobs, sent_by_id=user.id, data=payload["properties"]
        )
        session.add(properties)

    tag_texts = list(payload.get("tags", []))
    existing_tags = set(
        (
            await session.scalars(
                sa.select(GcnTag.text).where(GcnTag.dateobs == event.dateobs)
            )
        ).all()
    )
    tags = [
        GcnTag(
            dateobs=event.dateobs,
            text=text,
            sent_by_id=user.id,
        )
        for text in dict.fromkeys(tag_texts)
        if text not in existing_tags
    ]
    for tag in tags:
        session.add(tag)

    await link_detectors_to_event(session, user, event, tag_texts)
    await session.commit()

    # From here on use the event's own dateobs, which differs from the payload's
    # when the event was matched by trigger_id and the stream revised its time.
    dateobs = event.dateobs

    skymap = payload.get("skymap", None)
    if skymap is None:
        return dateobs, event.id

    localization_properties, localization_tags = None, None
    if type(skymap) is dict:
        required_keys = {"localization_name", "uniq", "probdensity"}
        if not required_keys.issubset(set(skymap.keys())):
            required_cone_keys = {"ra", "dec", "error"}
            required_polygon_keys = {"localization_name", "polygon"}
            required_ellipse_keys = {
                "localization_name",
                "ra",
                "dec",
                "amaj",
                "amin",
                "phi",
            }
            if required_cone_keys.issubset(set(skymap.keys())):
                skymap = from_cone(skymap["ra"], skymap["dec"], skymap["error"])
            elif required_ellipse_keys.issubset(set(skymap.keys())):
                skymap = from_ellipse(
                    skymap["localization_name"],
                    skymap["ra"],
                    skymap["dec"],
                    skymap["amaj"],
                    skymap["amin"],
                    skymap["phi"],
                )
            elif required_polygon_keys.issubset(set(skymap.keys())):
                if isinstance(skymap["polygon"], str):
                    polygon = ast.literal_eval(skymap["polygon"])
                else:
                    polygon = skymap["polygon"]
                skymap = from_polygon(skymap["localization_name"], polygon)
            else:
                raise ValueError("ra, dec, and error must be in skymap to parse")
    else:
        try:
            skymap, localization_properties, localization_tags = from_bytes(skymap)
        except binascii.Error:
            skymap, localization_properties, localization_tags = from_url(skymap)

    skymap["dateobs"] = event.dateobs
    skymap["sent_by_id"] = user.id

    await post_gcn_source(
        event.dateobs,
        skymap["localization_name"],
        payload,
        None,
        user,
        session,
        group_ids=await gcnevent_group_ids(session, event.dateobs),
    )

    localization = await session.scalar(
        Localization.select(user).where(
            Localization.dateobs == dateobs,
            Localization.localization_name == skymap["localization_name"],
        )
    )
    if localization is None:
        localization = Localization(**skymap)
        session.add(localization)
        await session.commit()
        localization_id = localization.id

        log(f"Generating tiles/properties/contours for localization {localization_id}")
        try:
            loop = asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        IOLoop.current().run_in_executor(
            None,
            lambda: add_tiles_properties_contour_and_obsplan(
                localization_id,
                user_id,
                properties=localization_properties,
                tags=localization_tags,
            ),
        )

    return dateobs, event.id


class GcnEventAssociationsGetQuery(BaseModel):
    """Query parameters for reading an event's associations."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset(
        {"minConsistency", "maxDays", "includeRejected"}
    )

    minConsistency: float | None = Field(
        default=None,
        description=(
            "Minimum sky-map consistency, 0 to 1. Defaults to your rule for "
            "this pair of messengers."
        ),
    )
    maxDays: float | None = Field(
        default=None,
        description=(
            "Maximum separation in days. Defaults to the configured window for "
            "the detector pair: a neutrino-GW coincidence is judged on seconds, "
            "a GRB-GW one on minutes."
        ),
    )
    includeRejected: bool = Field(
        default=False, description="Include associations already rejected."
    )


class GcnEventAssociationPatch(BaseModel):
    """Body for ruling on an association."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        description="One of pending, confirmed, ambiguous, rejected.",
    )
    explanation: str | None = Field(
        default=None, description="Why it was confirmed or rejected."
    )


async def visible_association_rules(session, user):
    """The association cuts this user can see, from every group they are in.

    A pair is shown if any of those rules admits it, so being in a second group
    can only widen what you see, never narrow it.
    """
    # a list, not a dict keyed by the pair: two groups may both have a rule for
    # the same messengers, and the wider one must not be dropped
    return (await session.scalars(GcnAssociationRule.select(user))).unique().all()


# A rule covers this pair of messengers but its tag requirement was not met:
# different from no rule at all, which leaves a pair uncut.
EXCLUDED_BY_RULE = object()


def association_cuts(rules, event_1, event_2):
    """(max_days, min_consistency), (None, None), or ``EXCLUDED_BY_RULE``.

    Which coincidences count is a science choice -- a neutrino arrives within
    seconds of a GW, a GRB within minutes -- and it differs by group, so it is
    only ever a user's own rule. A pair no rule mentions is left uncut rather
    than judged by a default nobody chose.

    A rule may also require tags, so "GW with GRB" can be narrowed to the GW
    events tagged BNS or NSBH; the same "any of" rule as a crossmatch filter's
    gcn_tags, where an empty list is no restriction. Failing that requirement
    excludes the pair -- the point of asking for it.
    """
    types = {
        id(event): {d.type for d in (event.detectors or [])}
        for event in (event_1, event_2)
    }
    if not types[id(event_1)] or not types[id(event_2)] or not rules:
        return None, None

    def tagged(event, wanted):
        return not wanted or any(tag in (event.tags or []) for tag in wanted)

    covered = False
    for rule in rules:
        # either event may be either side of the rule
        for first, second in ((event_1, event_2), (event_2, event_1)):
            if (
                rule.detector_type_1 not in types[id(first)]
                or rule.detector_type_2 not in types[id(second)]
            ):
                continue
            covered = True
            if tagged(first, rule.tags_1) and tagged(second, rule.tags_2):
                return rule.days, rule.min_consistency

    return EXCLUDED_BY_RULE if covered else (None, None)


class GcnEventAssociationsHandler(BaseHandler):
    @auth_or_token
    async def get(
        self,
        dateobs: Annotated[
            str,
            Field(description="The dateobs of the event, as an arrow parseable string"),
        ],
        association_id: Annotated[
            str | None, Field(description="Unused; the listing is per event")
        ] = None,
        *,
        query: GcnEventAssociationsGetQuery = None,
    ):
        """
        ---
        summary: Events associated with this one
        description: |
          Other GCN events whose localization overlaps this one's, as found by
          the crossmatch service, ranked by RAVEN's sky-map overlap integral.
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        query = self.parse_query(GcnEventAssociationsGetQuery)
        try:
            dateobs_parsed = arrow.get(dateobs.strip()).datetime.replace(tzinfo=None)
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            user = session.user_or_token
            stmt = GcnEventAssociation.select(user).where(
                sa.or_(
                    GcnEventAssociation.dateobs_1 == dateobs_parsed,
                    GcnEventAssociation.dateobs_2 == dateobs_parsed,
                )
            )
            if not query.includeRejected:
                stmt = stmt.where(GcnEventAssociation.status != "rejected")
            associations = (await session.scalars(stmt)).unique().all()

            mine = await session.scalar(
                GcnEvent.select(user)
                # tags as well as detectors: the rules read both
                .options(selectinload(GcnEvent.detectors), selectinload(GcnEvent._tags))
                .where(GcnEvent.dateobs == dateobs_parsed)
            )
            if mine is None:
                return self.error(f"No event {dateobs}", status=404)
            rules = await visible_association_rules(
                session, self.associated_user_object
            )

            out = []
            for association in associations:
                other_dateobs = (
                    association.dateobs_2
                    if association.dateobs_1 == dateobs_parsed
                    else association.dateobs_1
                )
                other = await session.scalar(
                    GcnEvent.select(user)
                    .options(
                        selectinload(GcnEvent.detectors), selectinload(GcnEvent._tags)
                    )
                    .where(GcnEvent.dateobs == other_dateobs)
                )
                if other is None:
                    continue
                cuts = association_cuts(rules, mine, other)
                if cuts is EXCLUDED_BY_RULE:
                    continue
                max_days, min_consistency = cuts
                if query.maxDays is not None:
                    max_days = float(query.maxDays)
                if query.minConsistency is not None:
                    min_consistency = float(query.minConsistency)
                if max_days is not None and abs(association.dt_days) > max_days:
                    continue
                # An association recorded before consistency was measured has
                # none; that is unknown, not zero, so it is shown rather than
                # cut. The pass fills it in on the next sweep.
                if (
                    min_consistency is not None
                    and association.consistency is not None
                    and association.consistency < min_consistency
                ):
                    continue
                out.append(
                    {
                        "id": association.id,
                        "dateobs": other_dateobs,
                        "trigger_id": other.trigger_id,
                        "aliases": other.aliases,
                        "tags": other.tags,
                        "detectors": [d.nickname for d in other.detectors],
                        "overlap": round(association.overlap, 4),
                        "consistency": (
                            None
                            if association.consistency is None
                            else round(association.consistency, 4)
                        ),
                        "dt_days": round(association.dt_days, 6),
                        "status": association.status,
                        "explanation": association.explanation,
                    }
                )

            out.sort(key=lambda a: a["overlap"], reverse=True)
            return self.success(data=out)

    @permissions(["Upload data"])
    async def post(
        self,
        dateobs: Annotated[
            str,
            Field(description="The dateobs of the event"),
        ],
        association_id: Annotated[
            str | None, Field(description="Unused; the search is per event")
        ] = None,
    ):
        """
        ---
        summary: Search for associations now
        description: |
          Runs the sky-map overlap against every other event in range, rather
          than waiting for the crossmatch service's next pass. Existing
          associations keep their verdict.
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        from ...utils.gcn_crossmatch import associate_events

        async with self.AsyncSession() as session:
            user = self.associated_user_object
            session.user_or_token = user
            try:
                found = await associate_events(session, user)
            except Exception as e:
                await session.rollback()
                return self.error(f"Could not search for associations: {e}")

            self.push_all(
                action="skyportal/REFRESH_GCNEVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )
            return self.success(data={"found": found})

    @permissions(["Upload data"])
    async def patch(
        self,
        dateobs: Annotated[
            str,
            Field(description="The dateobs of the event"),
        ],
        association_id: Annotated[
            int, Field(description="ID of the association being ruled on")
        ],
        *,
        body: GcnEventAssociationPatch = None,
    ):
        """
        ---
        summary: Rule on an association
        description: Confirm, reject, or mark ambiguous a pair of events.
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: association_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(GcnEventAssociationPatch)
        if body.status not in GCN_EVENT_OBJ_STATUSES:
            return self.error(
                f"status must be one of {', '.join(GCN_EVENT_OBJ_STATUSES)}"
            )

        async with self.AsyncSession() as session:
            association = await session.scalar(
                GcnEventAssociation.select(session.user_or_token, mode="update").where(
                    GcnEventAssociation.id == int(association_id)
                )
            )
            if association is None:
                return self.error("Association not found", status=404)

            association.status = body.status
            association.explanation = body.explanation
            association.confirmer_id = self.associated_user_object.id
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_GCNEVENT",
                payload={"gcnEvent_dateobs": str(association.dateobs_1)},
            )
            return self.success()


class GcnEventAliasesHandler(BaseHandler):
    @auth_or_token
    async def post(
        self,
        dateobs: Annotated[
            str,
            Field(description="The dateobs of the event, as an arrow parseable string"),
        ],
        *,
        body: GcnEventAliasPostBody = None,
    ):
        """
        ---
        summary: Post a GCN Event alias
        description: Post a GCN Event alias
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(GcnEventAliasPostBody)
        alias = body.alias

        if alias is None:
            return self.error("alias must be present in data")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            try:
                event = await session.scalar(
                    GcnEvent.select(
                        session.user_or_token,
                        mode="update",
                    ).where(GcnEvent.dateobs == dateobs_parsed)
                )
                if event is None:
                    return self.error("GCN event not found", status=404)

                if event.aliases is None:
                    event.aliases = [alias]
                elif alias not in event.aliases:
                    event.aliases = list(set(event.aliases + [alias]))
                else:
                    return self.error(f"{alias} already in {dateobs} aliases.")
                await session.commit()

                self.push(
                    action="skyportal/REFRESH_GCN_EVENT",
                    payload={"gcnEvent_dateobs": dateobs},
                )
            except Exception as e:
                return self.error(f"Cannot post alias: {str(e)}")

            return self.success()

    @auth_or_token
    async def delete(self, dateobs: str, *, body: GcnEventAliasDeleteBody = None):
        """
        ---
        summary: Delete a GCN Event alias
        description: Delete a GCN event alias
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        body = self.parse_body(GcnEventAliasDeleteBody)
        alias = body.alias

        if alias is None:
            return self.error("alias must be present in data to remove")

        forbidden_substrings = ["LVC#", "FERMI#"]
        for forbidden_substring in forbidden_substrings:
            if forbidden_substring in alias:
                return self.error(
                    f"Cannot delete alias with substring {forbidden_substring}"
                )

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            try:
                event = await session.scalar(
                    GcnEvent.select(
                        session.user_or_token,
                        mode="update",
                    ).where(GcnEvent.dateobs == dateobs_parsed)
                )
                if event is None:
                    return self.error("GCN event not found", status=404)

                if alias in event.aliases:
                    aliases = event.aliases
                    aliases.remove(alias)
                    setattr(event, "aliases", aliases)
                    flag_modified(event, "aliases")
                else:
                    return self.error(f"{alias} not in {dateobs} aliases.")
                await session.commit()

                self.push(
                    action="skyportal/REFRESH_GCN_EVENT",
                    payload={"gcnEvent_dateobs": dateobs},
                )
            except Exception as e:
                return self.error(f"Cannot remove alias: {str(e)}")

            return self.success()


class GcnEventTagsHandler(BaseHandler):
    @auth_or_token
    async def get(self, *ignored_args):
        """
        ---
        summary: Get all GCN Event tags
        description: Get all GCN Event tags
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: array
                          items:
                            type: string
          400:
            content:
              application/json:
                schema: Error
        """

        # Optional: only the tags events of one messenger have actually carried,
        # so a rule about gravitational waves is offered BNS and NSBH rather than
        # every tag in the database.
        detector_type = self.get_query_argument("detectorType", None)

        async with self.AsyncSession() as session:
            stmt = sa.select(GcnTag.text).distinct()
            if detector_type is not None:
                stmt = stmt.where(
                    GcnTag.dateobs.in_(
                        sa.select(GcnEvent.dateobs)
                        .join(
                            GcnEventMMADetector,
                            GcnEventMMADetector.gcnevent_id == GcnEvent.id,
                        )
                        .join(
                            MMADetector,
                            sa.and_(
                                MMADetector.id == GcnEventMMADetector.mmadetector_id,
                                MMADetector.type == detector_type,
                            ),
                        )
                    )
                )
            result = await session.scalars(stmt)
            tags = result.unique().all()
            return self.success(data=tags)

    @auth_or_token
    async def post(
        self, dateobs: str = None, tag: str = None, *, body: GcnEventTagPostBody = None
    ) -> GcnEventTagPostResponse:
        """
        ---
        summary: Post a GCN Event tag
        description: Post a GCN Event tag
        tags:
          - gcn event tags
        """
        body = self.parse_body(GcnEventTagPostBody)
        dateobs = body.dateobs
        text = body.text

        if dateobs is None:
            return self.error("dateobs must be present in data to add GcnTag")
        if text is None:
            return self.error("text must be present in data to add GcnTag")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            try:
                tag = GcnTag(
                    dateobs=dateobs_parsed,
                    text=text,
                    sent_by_id=self.associated_user_object.id,
                )
                session.add(tag)
                await session.commit()

                try:
                    loop = asyncio.get_event_loop()
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                request_body = {
                    "target_class_name": "GcnTag",
                    "target_id": tag.id,
                }

                IOLoop.current().run_in_executor(
                    None,
                    lambda: post_notification(request_body, timeout=30),
                )

                self.push(
                    action="skyportal/REFRESH_GCN_EVENT",
                    payload={"gcnEvent_dateobs": dateobs},
                )
            except Exception as e:
                return self.error(f"Cannot post tag: {str(e)}")

            return self.success(data={"gcntag_id": tag.id})

    @auth_or_token
    async def delete(self, dateobs: str, *, body: GcnEventTagDeleteBody = None):
        """
        ---
        summary: Delete a GCN Event tag
        description: Delete a GCN event tag
        tags:
          - gcn events
        parameters:
          - in: query
            name: tag
            required: true
            schema:
              type: tag
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        body = self.parse_body(GcnEventTagDeleteBody)
        tag = body.tag
        if tag is None:
            return self.error("tag must be present in data to remove GcnTag")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            tag = await session.scalar(
                GcnTag.select(session.user_or_token, mode="delete").where(
                    GcnTag.dateobs == dateobs_parsed,
                    GcnTag.text == tag,
                )
            )
            if tag is None:
                return self.error("GCN event tag not found", status=404)

            await session.delete(tag)
            await session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

            return self.success()


class GcnEventExtractionsHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs):
        """
        ---
        summary: Get structured extractions for a GCN event
        description: |
            Retrieve the structured data producers have extracted from an
            event's circulars and notices. Filter by `origin` to select one
            producer, or by `circularId` for a single circular.
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
            description: The dateobs of the event, as an arrow parseable string
          - in: query
            name: origin
            schema:
              type: string
            description: Only return extractions from this producer
          - in: query
            name: circularId
            schema:
              type: integer
            description: Only return extractions from this GCN circular
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        origin = self.get_query_argument("origin", None)
        circular_id = self.get_query_argument("circularId", None)
        try:
            dateobs = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            event = await session.scalar(
                GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
            )
            if event is None:
                return self.error("GCN event not found", status=404)

            stmt = GcnEventExtraction.select(session.user_or_token).where(
                GcnEventExtraction.dateobs == dateobs
            )
            if origin is not None:
                stmt = stmt.where(GcnEventExtraction.origin == origin)
            if circular_id is not None:
                try:
                    stmt = stmt.where(
                        GcnEventExtraction.circular_id == int(circular_id)
                    )
                except ValueError:
                    return self.error("circularId must be an integer")

            extractions = (await session.scalars(stmt)).unique().all()
            return self.success(data=[e.to_dict() for e in extractions])

    @permissions(["Manage GCNs"])
    async def post(self, dateobs):
        """
        ---
        summary: Add a structured extraction to a GCN event
        description: |
            Store structured data extracted from an event's text. `origin`
            names the producer and `data` is that producer's own shape; nothing
            is assumed about it.
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  origin:
                    type: string
                    description: What produced this extraction, e.g. circex
                  data:
                    type: object
                    description: The extraction itself
                  circular_id:
                    type: integer
                    description: GCN circular it came from, if it came from one
                required:
                  - origin
                  - data
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        payload = self.get_json()
        origin = payload.get("origin")
        data = payload.get("data")
        if not origin:
            return self.error("origin must be present in data")
        if not isinstance(data, dict):
            return self.error("data must be an object")
        circular_id = payload.get("circular_id")
        if circular_id is not None and not isinstance(circular_id, int):
            return self.error("circular_id must be an integer")

        try:
            dateobs = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            event = await session.scalar(
                GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
            )
            if event is None:
                return self.error("GCN event not found", status=404)

            extraction = GcnEventExtraction(
                dateobs=dateobs,
                origin=origin,
                data=data,
                circular_id=circular_id,
                sent_by_id=self.associated_user_object.id,
            )
            session.add(extraction)
            await session.commit()
            return self.success(data={"id": extraction.id})


class GcnEventPropertiesHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: Get all GCN Event properties
        description: Get all GCN Event properties
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: array
                          items:
                            $ref: '#/components/schemas/GcnProperty'
          400:
            content:
              application/json:
                schema: Error
        """

        async with self.AsyncSession() as session:
            result = await session.scalars(
                sa.select(sa.func.jsonb_object_keys(GcnProperty.data)).distinct()
            )
            properties = result.unique().all()
            return self.success(data=sorted(properties))


class GcnEventSurveyEfficiencyHandler(BaseHandler):
    @auth_or_token
    async def get(self, gcnevent_id: int):
        """
        ---
        summary: Get an event's survey efficiencies
        description: Get survey efficiency analyses of the GcnEvent.
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfSurveyEfficiencyForObservationss
        """

        try:
            gcnevent_id = int(gcnevent_id)
        except ValueError:
            return self.error("Invalid GCN event ID", status=400)

        async with self.AsyncSession() as session:
            event = await session.scalar(
                GcnEvent.select(
                    session.user_or_token,
                    options=[selectinload(GcnEvent.survey_efficiency_analyses)],
                ).where(GcnEvent.id == gcnevent_id)
            )
            if event is None:
                return self.error("GCN event not found", status=404)

            analysis_data = []
            for analysis in event.survey_efficiency_analyses:
                analysis_data.append(
                    {
                        **analysis.to_dict(),
                        "number_of_transients": analysis.number_of_transients,
                        "number_in_covered": analysis.number_in_covered,
                        "number_detected": analysis.number_detected,
                        "efficiency": analysis.efficiency,
                    }
                )

            return self.success(data=analysis_data)


class GcnEventObservationPlanRequestsHandler(BaseHandler):
    @auth_or_token
    async def get(self, gcnevent_id: int):
        """
        ---
        summary: Get an event's observation plan requests.
        description: Get observation plan requests of the GcnEvent.
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfObservationPlanRequests
        """

        try:
            gcnevent_id = int(gcnevent_id)
        except ValueError:
            return self.error("Invalid GCN event ID", status=400)

        async with self.AsyncSession() as session:
            event = await session.scalar(
                GcnEvent.select(
                    session.user_or_token,
                    options=[
                        selectinload(GcnEvent.observationplan_requests)
                        .selectinload(ObservationPlanRequest.allocation)
                        .selectinload(Allocation.instrument),
                        selectinload(GcnEvent.observationplan_requests)
                        .selectinload(ObservationPlanRequest.allocation)
                        .selectinload(Allocation.group),
                        selectinload(GcnEvent.observationplan_requests).selectinload(
                            ObservationPlanRequest.requester
                        ),
                        # to_dict() only serializes loaded attributes, so eager-load
                        # the localization (dateobs/name) — otherwise it's omitted
                        # from each request and the frontend skymap can't fetch its
                        # contour (spins).
                        selectinload(GcnEvent.observationplan_requests).selectinload(
                            ObservationPlanRequest.localization
                        ),
                        selectinload(GcnEvent.observationplan_requests)
                        .selectinload(ObservationPlanRequest.observation_plans)
                        .selectinload(EventObservationPlan.statistics),
                    ],
                ).where(GcnEvent.id == gcnevent_id)
            )

            # go through some pain to get probability and area included
            # as these are properties
            request_data = []
            if event is not None:
                for ii, req in enumerate(event.observationplan_requests):
                    dat = req.to_dict()
                    plan_data = []
                    for plan in dat["observation_plans"]:
                        plan_dict = plan.to_dict()
                        plan_dict["statistics"] = [
                            statistics.to_dict()
                            for statistics in plan_dict["statistics"]
                        ]
                        plan_data.append(plan_dict)

                    dat["observation_plans"] = plan_data
                    request_data.append(dat)

            return self.success(data=request_data)


class GcnEventCatalogQueryHandler(BaseHandler):
    @auth_or_token
    async def get(self, gcnevent_id: int):
        """
        ---
        summary: Get an event's catalog queries.
        description: Get catalog queries of the GcnEvent.
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfCatalogQuerys
        """
        try:
            gcnevent_id = int(gcnevent_id)
        except ValueError:
            return self.error("Invalid GCN event ID", status=400)

        async with self.AsyncSession() as session:
            result = await session.scalars(
                CatalogQuery.select(
                    session.user_or_token,
                ).where(
                    cast(CatalogQuery.payload["gcnevent_id"].astext, sa.Integer)
                    == gcnevent_id
                )
            )
            queries = result.all()

            return self.success(data=queries)


class GcnEventGetQuery(BaseModel):
    """Query parameters for retrieving GCN events."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"excludeNoticeContent"})

    startDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by dateobs >= startDate",
    )
    endDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by dateobs <= endDate",
    )
    partialdateobs: str | None = Field(
        default=None,
        description=(
            "Partial dateobs string (or alias substring) to filter events whose "
            "dateobs starts with the given value or whose aliases contain it."
        ),
    )
    gcnTagKeep: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `GcnTag`s. Returns events that match any of them.",
    )
    gcnTagRemove: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `GcnTag`s. Returns events that do not have any of these tags.",
    )
    localizationTagKeep: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `LocalizationTag`s. Returns events that match any of them.",
    )
    localizationTagRemove: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `LocalizationTag`s. Returns events that do not have any of these tags.",
    )
    gcnPropertiesFilter: list[str] | None = Field(
        default=None,
        description=(
            'Comma-separated string of "property: value: operator" single(s) or triplet(s) to filter for events matching '
            'that/those property(ies), i.e. "BNS" or "BNS: 0.5: lt"'
        ),
    )
    localizationPropertiesFilter: list[str] | None = Field(
        default=None,
        description=(
            'Comma-separated string of "property: value: operator" single(s) or triplet(s) to filter for event localizations matching '
            'that/those property(ies), i.e. "area_90" or "area_90: 500: lt"'
        ),
    )
    numPerPage: int = Field(
        default=10,
        description=(
            "Number of GCN events to return per paginated request. "
            f"Defaults to 10. Can be no larger than {MAX_GCNEVENTS}."
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    sortBy: str | None = Field(
        default=None,
        description='Field to sort by. Currently only "dateobs" is supported.',
    )
    sortOrder: str = Field(
        default="asc",
        description='Sort order, "asc" or "desc". Defaults to "asc".',
    )
    excludeNoticeContent: bool = Field(
        default=False,
        description="If true, do not include the notice content in the response. Defaults to false.",
    )
    # comma-separated: the handler owns the split and its error message
    groupIds: str | None = Field(
        default=None,
        description=(
            "Comma-separated string of group IDs. If provided, only return events "
            "shared with those groups."
        ),
    )
    mmadetectorIds: list[int] | None = Field(
        default=None,
        description=(
            "Comma-separated string of `MMADetector` IDs. Returns events any of "
            "them contributed to."
        ),
    )


class GcnEventHandler(BaseHandler):
    @auth_or_token
    async def post(self, *, body: GcnEventPostBody = None) -> GcnEventPostResponse:
        """
        ---
        summary: Post a GCN Event from xml/json/dictionary
        description: Ingest a GCN Event from xml/json/dictionary
        tags:
          - gcn events
          - localizations
        """
        body = self.parse_body(GcnEventPostBody)
        fields_set = body.model_fields_set
        # If neither an XML nor a JSON notice is provided, a dateobs must be specified
        if not any(fmt in fields_set for fmt in ["xml", "json_notice"]):
            if "dateobs" not in fields_set:
                return self.error(
                    "Either xml, json or dateobs must be present in data to parse a GcnEvent"
                )

        event_id, dateobs, notice_id = None, None, None
        async with self.AsyncSession() as session:
            try:
                if "xml" in fields_set:
                    dateobs, event_id, notice_id = await post_gcnevent_from_xml(
                        body.xml, self.associated_user_object.id, session
                    )
                elif "json_notice" in fields_set:
                    dateobs, event_id, notice_id = await post_gcnevent_from_json(
                        body.json_notice, self.associated_user_object.id, session
                    )
                else:
                    dateobs, event_id = await post_gcnevent_from_dictionary(
                        body.model_dump(exclude_unset=True),
                        self.associated_user_object.id,
                        session,
                    )

                self.push(action="skyportal/REFRESH_GCN_EVENTS")
                self.push(action="skyportal/REFRESH_RECENT_GCNEVENTS")
            except Exception as e:
                return self.error(f"Cannot post event: {str(e)}")

            return self.success(
                data={
                    "gcnevent_id": event_id,
                    "dateobs": dateobs,
                    "notice_id": notice_id,
                }
            )

    @auth_or_token
    async def get(self, dateobs: str = None, *, query: GcnEventGetQuery = None):
        """
        ---
        single:
          summary: Get a GCN Event
          description: Retrieve a GCN event
          tags:
            - gcn events
          responses:
            200:
              content:
                application/json:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: object
                        properties:
                          data:
                            $ref: '#/components/schemas/GcnEvent'
            404:
              content:
                application/json:
                  schema: Error
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get multiple GCN Events
          description: Retrieve multiple GCN events
          tags:
            - gcn events
          responses:
            200:
              content:
                application/json:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: object
                        properties:
                          data:
                            type: object
                            properties:
                              events:
                                type: array
                                items:
                                  $ref: '#/components/schemas/GcnEvent'
                              totalMatches:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        query = self.parse_query(GcnEventGetQuery)

        partialdateobs = query.partialdateobs

        if dateobs is not None and partialdateobs is not None:
            return self.error(
                "Cannot specify both dateobs and partialdateobs query parameters"
            )

        try:
            page_number, n_per_page = get_page_and_n_per_page(
                query.pageNumber, query.numPerPage, MAX_GCNEVENTS
            )
        except ValueError as e:
            return self.error(str(e))

        sort_by = query.sortBy
        sort_order = query.sortOrder
        start_date = query.startDate
        end_date = query.endDate
        gcn_tag_keep = query.gcnTagKeep
        gcn_tag_remove = query.gcnTagRemove
        localization_tag_keep = query.localizationTagKeep
        localization_tag_remove = query.localizationTagRemove
        gcn_properties_filter = query.gcnPropertiesFilter
        no_notice_content = query.excludeNoticeContent
        group_ids = query.groupIds

        localization_properties_filter = query.localizationPropertiesFilter

        mmadetector_ids = query.mmadetectorIds

        if dateobs is not None:
            try:
                dateobs_parsed = arrow.get(dateobs).naive
            except Exception as e:
                return self.error(f"Invalid dateobs: {e}")

            async with self.AsyncSession() as session:
                options = [
                    selectinload(GcnEvent.localizations).selectinload(
                        Localization.tags
                    ),
                    selectinload(GcnEvent.localizations).selectinload(
                        Localization.properties
                    ),
                    selectinload(GcnEvent.localizations).undefer(Localization.uniq),
                    selectinload(GcnEvent.localizations).undefer(
                        Localization.probdensity
                    ),
                    selectinload(GcnEvent.localizations).undefer(Localization.contour),
                    selectinload(GcnEvent.comments).selectinload(CommentOnGCN.author),
                    selectinload(GcnEvent.detectors),
                    selectinload(GcnEvent._tags),
                    selectinload(GcnEvent.properties),
                    selectinload(GcnEvent.summaries).selectinload(GcnSummary.sent_by),
                    selectinload(GcnEvent.summaries).selectinload(GcnSummary.group),
                    selectinload(GcnEvent.gcn_triggers),
                    selectinload(GcnEvent.gcnevent_users).selectinload(
                        GcnEventUser.user
                    ),
                    undefer(GcnEvent.gracedb_log),
                    undefer(GcnEvent.gracedb_labels),
                ]
                # event.lightcurve / gracesa parse notice.content (a deferred
                # column), so it must be loaded even when excludeNoticeContent
                # keeps it out of the response (handled below). Lazy-loading it
                # here would raise MissingGreenlet under the async session.
                options.append(
                    selectinload(GcnEvent.gcn_notices).undefer(GcnNotice.content)
                )
                event = await session.scalar(
                    GcnEvent.select(
                        session.user_or_token,
                        options=options,
                    ).where(GcnEvent.dateobs == dateobs_parsed)
                )
                if event is None:
                    return self.error("GCN event not found", status=404)

                # .to_dict() fetches the deferred properties, so we build the dict
                # manually to avoid fetching the content if no_notice_content is True
                notices = []
                for notice in event.gcn_notices:
                    notice_dict = {
                        "id": notice.id,
                        "dateobs": notice.dateobs,
                        "ivorn": notice.ivorn,
                        "notice_type": notice.notice_type,
                        "stream": notice.stream,
                        "date": notice.date,
                        "notice_format": notice.notice_format,
                        "has_localization": notice.has_localization,
                        "localization_ingested": notice.localization_ingested,
                        "created_at": notice.created_at,
                        "modified": notice.modified,
                        "sent_by_id": notice.sent_by_id,
                    }
                    if not no_notice_content:
                        notice_dict["content"] = notice.content
                    notices.append(notice_dict)

                data = {
                    **event.to_dict(),
                    "tags": list(set(event.tags)),
                    "lightcurve": event.lightcurve,
                    "localizations": sorted(
                        (
                            {
                                **loc.to_dict(),
                                "tags": [tag.to_dict() for tag in loc.tags],
                                "properties": [
                                    properties.to_dict()
                                    for properties in loc.properties
                                ],
                                "center": loc.center,
                            }
                            for loc in event.localizations
                        ),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                    "event_users": [
                        {
                            **u.to_dict(),
                            "username": u.user.username,
                            "first_name": u.user.first_name,
                            "last_name": u.user.last_name,
                        }
                        for u in event.gcnevent_users
                    ],
                    "comments": sorted(
                        (
                            {
                                **{
                                    k: v
                                    for k, v in c.to_dict().items()
                                    if k != "attachment_bytes"
                                },
                                "author": {
                                    **c.author.to_dict(),
                                    "gravatar_url": c.author.gravatar_url,
                                },
                                "resourceType": "gcn_event",
                            }
                            for c in event.comments
                        ),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                    "summaries": sorted(
                        (
                            {
                                **s.to_dict(),
                                "sent_by": s.sent_by.to_dict(),
                                "group": s.group.to_dict(),
                            }
                            for s in event.summaries
                        ),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                    "gcn_notices": notices,
                    # sort the properties by created_at date descending
                    "properties": sorted(
                        (
                            {
                                **s.to_dict(),
                            }
                            for s in event.properties
                        ),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                    "gracedb_log": event.gracedb_log,
                    "gracedb_labels": event.gracedb_labels,
                }

                return self.success(data=data)

        async with self.AsyncSession() as session:
            stmt = GcnEvent.select(
                session.user_or_token,
                options=[
                    selectinload(GcnEvent.localizations).selectinload(
                        Localization.tags
                    ),
                    selectinload(GcnEvent.gcn_notices),
                    selectinload(GcnEvent.observationplan_requests),
                    selectinload(GcnEvent.gcn_triggers),
                    selectinload(GcnEvent._tags),
                ],
            )

            if partialdateobs is not None and partialdateobs != "":
                try:
                    arrow.get(partialdateobs.strip()).datetime
                    partialdateobs = partialdateobs.replace("T", " ")
                except Exception:
                    if len(partialdateobs) > 10 and partialdateobs[10] == "T":
                        partialdateobs = partialdateobs.replace("T", " ")
                partialdateobs = partialdateobs.strip().lower()
                stmt = stmt.where(
                    cast(GcnEvent.dateobs, sa.String).like(f"{partialdateobs}%")
                    | sa.func.lower(cast(GcnEvent.aliases, sa.String)).like(
                        f"%{partialdateobs}%"
                    )
                )
            if start_date:
                start_date = arrow.get(start_date.strip()).datetime
                stmt = stmt.where(GcnEvent.dateobs >= start_date)
            if end_date:
                end_date = arrow.get(end_date.strip()).datetime
                stmt = stmt.where(GcnEvent.dateobs <= end_date)
            if group_ids:
                # Narrow to events shared with particular groups. Access is
                # already enforced by GcnEvent.read; this is the user asking to
                # see, say, only the proprietary stream rather than everything
                # they happen to be entitled to.
                try:
                    group_ids = [int(g) for g in str(group_ids).split(",") if g != ""]
                except ValueError:
                    return self.error("Invalid groupIds: must be comma-separated ints")
                if group_ids:
                    stmt = stmt.where(
                        GcnEvent.id.in_(
                            sa.select(GroupGcnEvent.gcnevent_id).where(
                                GroupGcnEvent.group_id.in_(group_ids)
                            )
                        )
                    )
            try:
                stmt = apply_gcn_event_filters(
                    stmt,
                    session.user_or_token,
                    gcn_tag_keep=gcn_tag_keep,
                    gcn_tag_remove=gcn_tag_remove,
                    localization_tag_keep=localization_tag_keep,
                    localization_tag_remove=localization_tag_remove,
                    gcn_properties_filter=gcn_properties_filter,
                    localization_properties_filter=localization_properties_filter,
                    mmadetector_ids=mmadetector_ids,
                )
            except ValueError as e:
                return self.error(str(e))

            total_matches = await session.scalar(
                sa.select(sa.func.count()).select_from(stmt.distinct())
            )

            order_by = None
            if sort_by is not None:
                if sort_by == "dateobs":
                    order_by = (
                        [GcnEvent.dateobs]
                        if sort_order == "asc"
                        else [GcnEvent.dateobs.desc()]
                    )

            if order_by is None:
                order_by = [GcnEvent.dateobs.desc()]

            stmt = stmt.order_by(*order_by)

            if n_per_page is not None:
                stmt = (
                    stmt.distinct()
                    .limit(n_per_page)
                    .offset((page_number - 1) * n_per_page)
                )

            events = []
            events_result = await session.scalars(stmt)
            for event in events_result.unique().all():
                event.gcn_notices = sorted(
                    event.gcn_notices, key=lambda notice: notice.date, reverse=True
                )
                for notice in event.gcn_notices:
                    if notice.notice_type is not None:
                        try:
                            # though we've transitioned to string notice types
                            # for backwards compatibility, we still try to convert
                            # integer notice types to string
                            notice.notice_type = gcn.NoticeType(
                                int(notice.notice_type)
                            ).name
                        except ValueError:
                            pass
                event_info = {
                    **event.to_dict(),
                    "tags": list(set(event.tags)),
                    "localizations": sorted(
                        (
                            {
                                **loc.to_dict(),
                                "tags": [tag.to_dict() for tag in loc.tags],
                            }
                            for loc in event.localizations
                        ),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                }
                events.append(event_info)

            query_results = {"events": events, "totalMatches": int(total_matches)}

            return self.success(data=query_results)

    @permissions(["Manage GCNs"])
    async def delete(self, dateobs: str):
        """
        ---
        summary: Delete a GCN Event
        description: Delete a GCN event
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            try:
                event = await session.scalar(
                    GcnEvent.select(session.user_or_token, mode="delete").where(
                        GcnEvent.dateobs == dateobs_parsed
                    )
                )
                if event is None:
                    return self.error("GCN event not found", status=404)

                localizations_result = await session.scalars(
                    Localization.select(session.user_or_token, mode="delete").where(
                        Localization.dateobs == dateobs_parsed
                    )
                )
                for localization in localizations_result.all():
                    await session.delete(localization)
                await session.commit()

                notices_result = await session.scalars(
                    GcnNotice.select(session.user_or_token, mode="delete").where(
                        GcnNotice.dateobs == dateobs_parsed
                    )
                )
                for notice in notices_result.all():
                    await session.delete(notice)

                tags_result = await session.scalars(
                    GcnTag.select(session.user_or_token, mode="delete").where(
                        GcnTag.dateobs == dateobs_parsed
                    )
                )
                for tag in tags_result.all():
                    await session.delete(tag)
                await session.commit()

                await session.delete(event)
                await session.commit()

                return self.success()
            except Exception as e:
                await session.rollback()
                return self.error(f"Cannot delete event: {e}")


class GcnEventUserHandler(BaseHandler):
    @auth_or_token
    async def post(
        self, dateobs: str, *ignored_args, body: GcnEventUserPostBody = None
    ):
        """
        ---
        summary: Add a user as GCN event advocate
        description: Add a event user
        tags:
          - gcn events
          - users
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        body = self.parse_body(GcnEventUserPostBody)

        user_id = body.userID
        if user_id is None:
            return self.error("userID parameter must be specified")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            event = await session.scalar(
                GcnEvent.select(
                    session.user_or_token,
                    options=[selectinload(GcnEvent.gcnevent_users)],
                ).where(GcnEvent.dateobs == dateobs_parsed)
            )
            if event is None:
                return self.error("GCN event not found", status=404)

            user = await session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            if user is None:
                return self.error(f"User with ID {user_id} not found", status=404)

            gu = await session.scalar(
                GcnEventUser.select(session.user_or_token)
                .where(GcnEventUser.gcnevent_id == event.id)
                .where(GcnEventUser.user_id == user_id)
            )
            if gu is not None:
                return self.error(
                    f"User {user_id} is already a member of event {event.dateobs}."
                )

            session.add(
                GcnEventUser(
                    gcnevent_id=event.id,
                    user_id=user_id,
                )
            )
            session.add(
                UserNotification(
                    user_id=user.id,
                    text=f"You've been added as an advocate to event *{event.dateobs}*",
                    url=f"/gcn_events/{event.dateobs}",
                )
            )
            await session.commit()
            self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

            self.push_all(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": event.dateobs},
            )

            return self.success()

    @auth_or_token
    async def delete(self, dateobs: str, user_id: int):
        """
        ---
        summary: Remove a GCN event advocate
        description: Delete an event user
        tags:
          - shifts
          - users
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return self.error("Invalid userID parameter: unable to parse to integer")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            event = await session.scalar(
                GcnEvent.select(
                    session.user_or_token,
                    options=[selectinload(GcnEvent.gcnevent_users)],
                ).where(GcnEvent.dateobs == dateobs_parsed)
            )
            if event is None:
                return self.error("GCN event not found", status=404)

            gu = await session.scalar(
                GcnEventUser.select(session.user_or_token, mode="delete")
                .where(GcnEventUser.gcnevent_id == event.id)
                .where(GcnEventUser.user_id == user_id)
            )
            if gu is None:
                return self.error(
                    "GcnEventUser does not exist, or you don't have the right to delete them.",
                    status=403,
                )

            await session.delete(gu)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": event.dateobs},
            )

            return self.success()


def add_tiles_and_properties_and_contour(
    localization_id,
    user_id,
    parent_session=None,
    url=None,
    notify=True,
    properties=None,
    tags=None,
):
    if parent_session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    try:
        user = session.scalar(sa.select(User).where(User.id == user_id))
        localization = session.scalar(
            sa.select(Localization).where(Localization.id == localization_id)
        )

        log(f"Retrieving skymap properties for localization {localization_id}")
        properties_dict, tags_list = get_skymap_properties(localization)
        if properties is not None:
            properties_dict.update(properties)
        if tags is not None:
            tags_list.extend(tags)

        properties = LocalizationProperty(
            localization_id=localization_id, sent_by_id=user.id, data=properties_dict
        )
        session.add(properties)

        tags = [
            LocalizationTag(
                localization_id=localization_id,
                text=text,
                sent_by_id=user.id,
            )
            for text in tags_list
        ]
        session.add_all(tags)

        log(f"Adding default localization tags for localization {localization_id}")
        gcn_tags = add_default_gcn_tags(user, session, localization=localization)
        if gcn_tags is not None and len(gcn_tags) > 0:
            session.add_all(gcn_tags)
            session.commit()

        if notify:
            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            request_body = {
                "target_class_name": "Localization",
                "target_id": localization_id,
            }
            IOLoop.current().run_in_executor(
                None,
                lambda: post_notification(request_body, timeout=30),
            )

        log(f"Adding tiles for localization {localization_id}")
        tiles = [
            LocalizationTile(
                localization_id=localization_id,
                healpix=uniq,
                probdensity=probdensity,
                dateobs=localization.dateobs,
            )
            for uniq, probdensity in zip(localization.uniq, localization.probdensity)
        ]

        if parent_session is None:
            session.add(localization)
        session.add_all(tiles)
        session.commit()

        log(f"Adding contour for localization {localization_id}")
        localization = get_contour(localization)
        session.add(localization)
        session.commit()

        # The contour is generated in this background task after the event is
        # ingested, so the page initially fetches the localization with a null
        # contour and the skymap spins. Emit a refresh now that the contour is
        # committed so the frontend re-fetches and renders it.
        # isoformat() to match the frontend's dateobs query arg (the per-id
        # GcnEvent cache tag is keyed on it); str(datetime) uses a space, not
        # the "T" the page uses, and would miss the per-id invalidation.
        Flow().push(
            "*",
            "skyportal/REFRESH_GCN_EVENT",
            payload={"gcnEvent_dateobs": localization.dateobs.isoformat()},
        )

        if url is not None:
            log(f"Fetching and saving raw skymap data to disk {localization_id}")
            try:
                r = requests.get(url, allow_redirects=True, timeout=15)
                data_to_disk = r.content
                urlpath = urlsplit(url).path
                localization_name = os.path.basename(urlpath)
                if data_to_disk is not None:
                    localization.save_data(localization_name, data_to_disk)
                    session.commit()
            except Exception as e:
                log(
                    f"Localization {localization_id} URL {url} failed to download: {str(e)}."
                )
        log(
            f"Generated tiles / properties / contour for localization {localization_id}"
        )
        return
    except ObjectDeletedError:
        # Localization was deleted (e.g. event removed) mid-generation; benign race.
        log(
            f"Localization {localization_id} was deleted during contour generation; skipping."
        )
        session.rollback()
    except Exception as e:
        traceback.print_exc()
        log(
            f"Unable to generate tiles / properties / contour for localization {localization_id}: {e}"
        )
        session.rollback()
    finally:
        if parent_session is None:
            session.close()
            Session.remove()


def add_default_gcn_tags(user, session, dateobs=None, localization=None):
    gcn_tags = []
    try:
        if dateobs is None and localization is None:
            return gcn_tags
        if dateobs is None:
            event = session.scalars(
                GcnEvent.select(user).where(GcnEvent.dateobs == localization.dateobs)
            ).first()
        else:
            event = session.scalars(
                GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
            ).first()
        event_notice_types = [notice.notice_type for notice in event.gcn_notices]
        event_tags = event.tags
        if localization is not None:
            localization_tags = [tag.text for tag in localization.tags]
        else:
            localization_tags = []

        default_gcn_tags = (
            (
                session.scalars(
                    DefaultGcnTag.select(
                        user,
                    )
                )
            )
            .unique()
            .all()
        )

        for default_gcn_tag in default_gcn_tags:
            try:
                filters = default_gcn_tag.filters
                if len(filters.get("gcn_tags", [])) > 0:
                    if not any(tag in event_tags for tag in filters["gcn_tags"]):
                        continue
                if len(filters.get("notice_types", [])) > 0:
                    if not any(
                        notice_type in event_notice_types
                        for notice_type in filters["notice_types"]
                    ):
                        continue
                if len(filters.get("localization_tags", [])) > 0:
                    if not any(
                        tag in localization_tags for tag in filters["localization_tags"]
                    ):
                        continue
                tag_name = default_gcn_tag.default_tag_name
                if tag_name not in event_tags and tag_name not in gcn_tags:
                    gcn_tags.append(tag_name)
            except Exception as e:
                # Don't let one malformed default stop the others, but say so:
                # a silent pass here hid a bad filter key for a long time.
                log(f"Skipping default GCN tag {default_gcn_tag.id}: {e}")

        gcn_tags = [
            GcnTag(
                text=text,
                dateobs=event.dateobs,
                sent_by_id=user.id,
            )
            for text in gcn_tags
        ]
    except Exception as e:
        log(f"Unable to add default GCN tags: {str(e)}")
        gcn_tags = []

    return gcn_tags


async def add_default_gcn_tags_async(user, session, dateobs=None, localization=None):
    """Async equivalent of ``add_default_gcn_tags``."""
    from sqlalchemy.orm import selectinload

    gcn_tags = []
    try:
        if dateobs is None and localization is None:
            return gcn_tags
        if dateobs is None:
            event = await session.scalar(
                GcnEvent.select(user)
                .where(GcnEvent.dateobs == localization.dateobs)
                .options(
                    selectinload(GcnEvent.gcn_notices),
                    selectinload(GcnEvent._tags),
                )
            )
        else:
            event = await session.scalar(
                GcnEvent.select(user)
                .where(GcnEvent.dateobs == dateobs)
                .options(
                    selectinload(GcnEvent.gcn_notices),
                    selectinload(GcnEvent._tags),
                )
            )
        event_notice_types = [notice.notice_type for notice in event.gcn_notices]
        event_tags = event.tags
        if localization is not None:
            localization_tags = [tag.text for tag in localization.tags]
        else:
            localization_tags = []

        default_gcn_tags_result = await session.scalars(DefaultGcnTag.select(user))
        default_gcn_tags = default_gcn_tags_result.unique().all()

        for default_gcn_tag in default_gcn_tags:
            try:
                filters = default_gcn_tag.filters
                if len(filters.get("gcn_tags", [])) > 0:
                    if not any(tag in event_tags for tag in filters["gcn_tags"]):
                        continue
                if len(filters.get("notice_types", [])) > 0:
                    if not any(
                        notice_type in event_notice_types
                        for notice_type in filters["notice_types"]
                    ):
                        continue
                if len(filters.get("localization_tags", [])) > 0:
                    if not any(
                        tag in localization_tags for tag in filters["localization_tags"]
                    ):
                        continue
                tag_name = default_gcn_tag.default_tag_name
                if tag_name not in event_tags and tag_name not in gcn_tags:
                    gcn_tags.append(tag_name)
            except Exception as e:
                # Don't let one malformed default stop the others, but say so:
                # a silent pass here hid a bad filter key for a long time.
                log(f"Skipping default GCN tag {default_gcn_tag.id}: {e}")

        gcn_tags = [
            GcnTag(
                text=text,
                dateobs=event.dateobs,
                sent_by_id=user.id,
            )
            for text in gcn_tags
        ]
    except Exception as e:
        log(f"Unable to add default GCN tags: {str(e)}")
        gcn_tags = []

    return gcn_tags


def add_observation_plans(localization_id, user_id, parent_session=None):
    if parent_session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    try:
        user = session.scalar(sa.select(User).where(User.id == user_id))
        localization = session.scalars(
            sa.select(Localization).where(Localization.id == localization_id)
        ).first()
        if localization is None:
            # Localization was deleted (e.g. event removed) while this
            # background job ran; nothing to plan for.
            log(f"Localization {localization_id} no longer exists; skipping obs plans.")
            return
        dateobs = localization.dateobs
        localization_tags = [
            tags.text
            for tags in session.scalars(
                sa.select(LocalizationTag).where(
                    LocalizationTag.localization_id == localization_id
                )
            ).all()
        ]
        localization_properties = session.scalars(
            sa.select(LocalizationProperty).where(
                LocalizationProperty.localization_id == localization_id
            )
        ).first()
        if localization_properties is not None:
            localization_properties = localization_properties.data

        event = session.scalars(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        ).first()
        if not isinstance(event.gcn_notices, list) or len(event.gcn_notices) == 0:
            log(
                f"No GCN notices found for event {event.id}, skipping default observation plan"
            )
            return
        # sort the notices by date (which is a datetime object)
        notices = sorted(event.gcn_notices, key=lambda x: x.date)
        if localization.notice_id is not None:
            notices = [n for n in notices if n.id == localization.notice_id]
        notice = notices[-1]

        event_properties = event.properties
        if not isinstance(event_properties, list) or len(event_properties) == 0:
            log(
                f"No GCN properties found for event {event.id}, skipping default observation plan"
            )
            return
        event_properties = sorted(event_properties, key=lambda x: x.created_at)[-1].data
        if not isinstance(event_properties, dict):
            log(
                f"No GCN valid properties found for event {event.id}, skipping default observation plan"
            )
            return

        default_observation_plans = (
            session.scalars(DefaultObservationPlanRequest.select(user)).unique().all()
        )
        gcn_observation_plans = []
        for plan in default_observation_plans:
            gcn_observation_plan = {
                "allocation_id": plan.allocation_id,
                "filters": plan.filters,
                "payload": plan.payload,
                "default": plan.id,
                "auto_send": plan.auto_send,
                "requester_id": (
                    user.id if plan.requester_id is None else plan.requester_id
                ),
            }
            gcn_observation_plans.append(gcn_observation_plan)

        start_date = str(utcnow_naive()).replace("T", "")

        for ii, gcn_observation_plan in enumerate(gcn_observation_plans):
            allocation_id = gcn_observation_plan["allocation_id"]
            allocation = session.scalars(
                Allocation.select(user).where(Allocation.id == allocation_id)
            ).first()
            if allocation is None:
                continue

            end_date = allocation.instrument.telescope.next_sunrise()
            if end_date is None:
                end_date = str(utcnow_naive() + datetime.timedelta(days=1)).replace(
                    "T", ""
                )
            else:
                end_date = Time(end_date, format="jd").iso

            payload = {
                **gcn_observation_plan["payload"],
                "start_date": start_date,
                "end_date": end_date,
                "queue_name": f"{allocation.instrument.name}-{start_date}-{ii}",
            }
            if "default" in gcn_observation_plan:
                payload["default"] = gcn_observation_plan["default"]
            plan = {
                "payload": payload,
                "allocation_id": allocation.id,
                "gcnevent_id": event.id,
                "localization_id": localization_id,
                "requester_id": gcn_observation_plan["requester_id"],
            }

            if isinstance(gcn_observation_plan.get("filters"), dict):
                filters = gcn_observation_plan["filters"]
                # this is a default plan, which we only run on localizations
                # that have an associated GCN notice
                if (
                    localization.notice_id is None
                    or notice.id != localization.notice_id
                ):
                    log(
                        f"Skipping default observation plan {gcn_observation_plan.id} because it does not match the localization notice"
                    )
                    continue

                if (
                    isinstance(filters.get("notice_types"), list)
                    and len(filters["notice_types"]) > 0
                ):
                    if notice.notice_type is not None:
                        notice_type = notice.notice_type
                        try:
                            # though we've transitioned to string notice types
                            # for backwards compatibility, we still try to convert
                            # integer notice types to string
                            notice_type = gcn.NoticeType(int(notice.notice_type)).name
                        except ValueError:
                            pass
                        if notice_type not in filters["notice_types"]:
                            continue

                if (
                    isinstance(filters.get("gcn_tags"), list)
                    and len(filters["gcn_tags"]) > 0
                ):
                    intersection = list(set(event.tags) & set(filters["gcn_tags"]))
                    if len(intersection) == 0:
                        continue

                if (
                    isinstance(filters.get("localization_tags"), list)
                    and len(filters["localization_tags"]) > 0
                ):
                    intersection = list(
                        set(localization_tags) & set(filters["localization_tags"])
                    )
                    if len(intersection) == 0:
                        continue

                if (
                    isinstance(filters.get("gcn_properties"), list)
                    and len(filters["gcn_properties"]) > 0
                ):
                    properties_pass = True
                    for prop_filt in filters["gcn_properties"]:
                        prop_split = prop_filt.split(":")
                        if len(prop_split) != 3:
                            log(
                                f"Invalid propertiesFilter value -- property filter must have 3 values, skipping default observation plan {gcn_observation_plan.id}"
                            )
                            properties_pass = False
                            break

                        name = prop_split[0].strip()
                        if name not in event_properties:
                            properties_pass = False
                            break

                        value = prop_split[1].strip()
                        try:
                            value = float(value)
                        except ValueError as e:
                            log(
                                f"Invalid propertiesFilter value: {e}, skipping default observation plan {gcn_observation_plan.id}"
                            )
                            properties_pass = False
                            break

                        op = prop_split[2].strip()
                        if op not in op_options:
                            log(
                                f"Invalid operator: {op}, skipping default observation plan {gcn_observation_plan.id}"
                            )
                            properties_pass = False
                            break
                        comp_function = getattr(operator, op)
                        if not comp_function(event_properties[name], value):
                            properties_pass = False
                            break

                    if not properties_pass:
                        continue

                if (
                    isinstance(filters.get("localization_properties"), list)
                    and len(filters["localization_properties"]) > 0
                ):
                    if not isinstance(localization_properties, dict):
                        log(
                            f"Skipping default observation plan {gcn_observation_plan.id} because localization properties are not available"
                        )
                        continue
                    valid_properties = True
                    for prop_filt in filters["localization_properties"]:
                        prop_split = prop_filt.split(":")
                        if len(prop_split) != 3:
                            log(
                                f"Invalid propertiesFilter value -- property filter must have 3 values, skipping default observation plan {gcn_observation_plan.id}"
                            )
                            valid_properties = False
                            break

                        name = prop_split[0].strip()
                        if name not in localization_properties:
                            valid_properties = False
                            break

                        value = prop_split[1].strip()
                        try:
                            value = float(value)
                        except ValueError as e:
                            log(
                                f"Invalid propertiesFilter value: {e}, skipping default observation plan {gcn_observation_plan.id}"
                            )
                            valid_properties = False
                            break

                        op = prop_split[2].strip()
                        if op not in op_options:
                            log(
                                f"Invalid operator: {op}, skipping default observation plan {gcn_observation_plan.id}"
                            )
                            valid_properties = False
                            break
                        comp_function = getattr(operator, op)
                        if not comp_function(
                            localization_properties[name],
                            value,
                        ):
                            valid_properties = False
                            break

                    if not valid_properties:
                        continue

            elif gcn_observation_plan.get("auto_send", False):
                # default plans must have filters defined to use auto_send
                log(
                    f"auto_send set to True but no filters, skipping default observation plan {gcn_observation_plan.id}"
                )

            post_observation_plan(
                plan,
                user_id=user.id,
                session=session,
                default_plan=True,
                asynchronous=False,
            )
        log(f"Triggered observation plans for localization {localization_id}")
    except Exception as e:
        traceback.print_exc()
        log(
            f"Unable to trigger observation plans for localization {localization_id}: {e}"
        )
    finally:
        if parent_session is None:
            session.close()
            Session.remove()


def add_tiles_properties_contour_and_obsplan(
    localization_id,
    user_id,
    parent_session=None,
    url=None,
    notify=True,
    properties=None,
    tags=None,
):
    if parent_session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    try:
        add_tiles_and_properties_and_contour(
            localization_id,
            user_id,
            session,
            url=url,
            notify=notify,
            properties=properties,
            tags=tags,
        )
        add_observation_plans(localization_id, user_id, session)
    except Exception as e:
        traceback.print_exc()
        log(
            f"Unable to generate tiles / properties / observation plans / contour for localization {localization_id}: {e}"
        )
    finally:
        if parent_session is None:
            session.close()
            Session.remove()


class LocalizationGetQuery(BaseModel):
    """Query parameters for retrieving a GCN localization."""

    model_config = ConfigDict(extra="forbid")

    include2DMap: bool = Field(
        default=False,
        description="Boolean indicating whether to include flatted skymap. Defaults to false.",
    )


class LocalizationHandler(BaseHandler):
    @auth_or_token
    async def get(
        self,
        dateobs: str,
        localization_name: str,
        *,
        query: LocalizationGetQuery = None,
    ):
        """
        ---
        summary: Get a GCN localization
        description: Retrieve a GCN localization
        tags:
          - localizations
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Localization'
          400:
            content:
              application/json:
                schema: Error
        """
        query = self.parse_query(LocalizationGetQuery)

        include_2D_map = query.include2DMap

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            localization = await session.scalar(
                Localization.select(session.user_or_token)
                .where(
                    Localization.dateobs == dateobs_parsed,
                    Localization.localization_name == localization_name,
                )
                .options(
                    undefer(Localization.uniq),
                    undefer(Localization.probdensity),
                    undefer(Localization.distmu),
                    undefer(Localization.distsigma),
                    undefer(Localization.distnorm),
                    undefer(Localization.contour),
                )
            )
            if localization is None:
                return self.error("Localization not found", status=404)

            if include_2D_map:
                data = {
                    **localization.to_dict(),
                    "flat_2d": localization.flat_2d,
                    "contour": localization.contour,
                }
            else:
                data = {
                    **localization.to_dict(),
                    "contour": localization.contour,
                }
            return self.success(data=data)

    @auth_or_token
    async def delete(self, dateobs: str, localization_name: str):
        """
        ---
        summary: Delete a GCN localization
        description: Delete a GCN localization
        tags:
          - localizations
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            localization = await session.scalar(
                Localization.select(session.user_or_token, mode="delete").where(
                    Localization.dateobs == dateobs_parsed,
                    Localization.localization_name == localization_name,
                )
            )

            if localization is None:
                return self.error("Localization not found", status=404)

            dateobs = localization.dateobs

            await session.delete(localization)
            await session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

            return self.success()


class LocalizationNoticeHandler(BaseHandler):
    @auth_or_token
    async def post(self, dateobs: str, notice_id: int):
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        try:
            notice_id_int = int(notice_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid notice_id: {notice_id}")

        # first get the notice, if it exists
        async with self.AsyncSession() as session:
            gcn_notice = await session.scalar(
                GcnNotice.select(session.user_or_token).where(
                    GcnNotice.dateobs == dateobs_parsed,
                    GcnNotice.id == notice_id_int,
                )
            )

            if gcn_notice is None:
                return self.error("Notice not found", status=404)

            root, notice_type = None, None

            # try reading xml notice
            try:
                root = lxml.etree.fromstring(gcn_notice.content)
                notice_type = gcn_notice.notice_type
            except lxml.etree.XMLSyntaxError:
                pass

            # try reading json notice
            if root is None:
                try:
                    root = json.loads(gcn_notice.content.decode("utf8"))
                    notice_type = None
                except json.JSONDecodeError:
                    pass

            if root is None:
                return self.error(f"Could not read the content of notice {notice_id}")

            status, skymap_metadata = get_skymap_metadata(root, notice_type)
            if status == "unavailable":
                return self.error(
                    "Skymap present in notice isn't available (yet)", status=404
                )
            elif status in ["available", "cone"]:
                if (
                    not isinstance(skymap_metadata, dict)
                    or "name" not in skymap_metadata
                ):
                    return self.error(
                        f"Could not retrieve the skymap's name for notice {notice_id}"
                    )
                localization = await session.scalar(
                    Localization.select(session.user_or_token).where(
                        Localization.dateobs == dateobs_parsed,
                        Localization.localization_name == skymap_metadata["name"],
                    )
                )
                if localization is not None:
                    return self.error("Localization already exists", status=409)
                else:
                    try:
                        await post_skymap_from_notice(
                            dateobs_parsed,
                            gcn_notice.id,
                            self.associated_user_object.id,
                            session,
                        )
                        flow = Flow()
                        flow.push(
                            "*",
                            "skyportal/REFRESH_GCN_EVENT",
                            payload={"gcnEvent_dateobs": dateobs},
                        )
                        return self.success()
                    except Exception as e:
                        return self.error(f"Error posting skymap from notice: {e}")
            elif status == "retracted":
                return self.error(
                    "Notice is for a retraction, no skymap needs to be posted",
                    status=404,
                )
            else:
                return self.error("Notice is missing skymap metadata", status=404)


class LocalizationPropertiesHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: Get all Localization properties
        description: Get all Localization properties
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: array
                          items:
                            $ref: '#/components/schemas/LocalizationProperty'
          400:
            content:
              application/json:
                schema: Error
        """

        async with self.AsyncSession() as session:
            result = await session.scalars(
                sa.select(
                    sa.func.jsonb_object_keys(LocalizationProperty.data)
                ).distinct()
            )
            properties = result.unique().all()
            return self.success(data=sorted(properties))


class LocalizationTagsHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: Get all Localization tags
        description: Get all Localization tags
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        async with self.AsyncSession() as session:
            result = await session.scalars(
                LocalizationTag.select(
                    session.user_or_token, columns=[LocalizationTag.text]
                ).distinct()
            )
            tags = result.unique().all()
            return self.success(data=tags)


def nb_obs_to_word(nb_obs):
    if nb_obs < 1:
        raise ValueError("nb_obs must be >= 1")
    if nb_obs == 1:
        return "once"
    elif nb_obs == 2:
        return "twice"
    elif nb_obs > 2:
        return f"{nb_obs} times"


def add_gcn_summary(
    summary_id,
    user_id,
    user_accessible_group_ids,
    dateobs,
    title,
    number,
    subject,
    user_ids,
    group_id,
    start_date,
    end_date,
    localization_name,
    localization_cumprob=0.90,
    number_of_detections=1,
    number_of_observations=1,
    show_sources=True,
    show_galaxies=False,
    show_observations=False,
    no_text=False,
    photometry_in_window=True,
    stats_method="python",
    instrument_ids=None,
    acknowledgements=None,
):
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        user = session.get(User, user_id)
        session.user_or_token = user

        if isinstance(dateobs, str):
            dateobs = arrow.get(dateobs).naive

        gcn_summary = session.get(GcnSummary, summary_id)
        group = session.get(Group, group_id)
        event = session.scalars(
            sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
        ).first()
        localization = session.scalars(
            sa.select(Localization).where(
                Localization.dateobs == dateobs,
                Localization.localization_name == localization_name,
            )
        ).first()

        start_date_mjd = Time(arrow.get(start_date).datetime).mjd
        end_date_mjd = Time(arrow.get(end_date).datetime).mjd

        contents = []
        if not no_text:
            header_text = []
            header_text.append(f"""## TITLE: {title.upper()}\n""")
            if number is not None:
                header_text.append(f"""#### NUMBER: {number}\n""")
            header_text.append(
                f"""#### SUBJECT: {subject[0].upper() + subject[1:]}\n"""
            )
            now_date = astropy.time.Time.now()
            header_text.append(f"""#### DATE: {now_date}\n""")

            if user.affiliations is not None and len(user.affiliations) > 0:
                affiliations = ", ".join(user.affiliations)
            else:
                affiliations = "..."

            # add a "FROM full name and affiliation"
            from_str = (
                f"""#### FROM: {user.first_name} {user.last_name} at {affiliations}"""
            )
            if user.contact_email is not None:
                from_str += f""" <{user.contact_email}>\n"""
            header_text.append(from_str)

            if user_id not in user_ids:
                user_ids = [user_id] + user_ids

            user_ids = list(set(user_ids))

            users = []
            for mentioned_user_id in user_ids:
                mentioned_user = session.get(User, mentioned_user_id)
                if mentioned_user is not None:
                    users.append(mentioned_user)

            users_txt = []
            for mentioned_user in users:
                if (
                    mentioned_user.first_name is not None
                    and mentioned_user.last_name is not None
                ):
                    if (
                        mentioned_user.affiliations is not None
                        and len(mentioned_user.affiliations) > 0
                    ):
                        affiliations = ", ".join(mentioned_user.affiliations)
                    else:
                        affiliations = "..."

                    users_txt.append(
                        f"""{mentioned_user.first_name[0].upper()}. {mentioned_user.last_name} ({affiliations})"""
                    )
            # create a string of all users, with 5 users per line
            users_txt = "\n".join(
                [", ".join(users_txt[i : i + 5]) for i in range(0, len(users_txt), 5)]
            )
            header_text.append(
                f"""\n{users_txt} report{"s" if len(user_ids) == 1 else ""} on behalf of the {group.name} group:\n"""
            )
            contents.extend(header_text)

        if show_sources:
            from baselayer.app.models import AsyncVerifiedSession

            sources_text = []
            source_page_number = 1
            sources = []
            while True:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def _fetch_sources(page_number=source_page_number):
                    async with AsyncVerifiedSession(user) as asession:
                        return await get_sources(
                            user_id=user.id,
                            session=asession,
                            group_ids=[group.id],
                            user_accessible_group_ids=user_accessible_group_ids,
                            detected_window_start=start_date,
                            detected_window_end=end_date,
                            localization_dateobs=dateobs,
                            localization_name=localization_name,
                            localization_cumprob=localization_cumprob,
                            number_of_detections=number_of_detections,
                            page_number=page_number,
                            num_per_page=MAX_SOURCES_PER_PAGE,
                        )

                sources_data = loop.run_until_complete(_fetch_sources())
                sources.extend(sources_data["sources"])
                source_page_number += 1

                if len(sources_data["sources"]) < MAX_SOURCES_PER_PAGE:
                    break
            if len(sources) > 0:
                obj_ids = [source["id"] for source in sources]
                sources_with_status = session.scalars(
                    GcnEventObj.select(user).where(
                        GcnEventObj.obj_id.in_(obj_ids),
                        GcnEventObj.dateobs == dateobs,
                    )
                ).all()

                ids, tns_name, ras, decs, redshifts, status, explanation = (
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                )
                for source in sources:
                    ids.append(source["id"] if "id" in source else None)
                    tns_name.append(
                        str(source["tns_name"]).replace(" ", "")
                        if isinstance(source.get("tns_name"), str)
                        else ""
                    )
                    ras.append(np.round(source["ra"], 5) if "ra" in source else None)
                    decs.append(np.round(source["dec"], 5) if "dec" in source else None)
                    if (
                        source.get("redshift") is not None
                        and not pd.isna(source["redshift"])
                        and not np.isinf(source["redshift"])
                    ):
                        redshift = source["redshift"]
                    else:
                        redshift = ""
                    if source.get("redshift_error") is not None and redshift != "":
                        redshift = f"{redshift}±{source['redshift_error']}"
                    redshifts.append(redshift)
                    source_in_gcn = next(
                        (
                            source_in_gcn
                            for source_in_gcn in sources_with_status
                            if source_in_gcn.obj_id == source["id"]
                        ),
                        None,
                    )
                    if source_in_gcn is not None:
                        status.append(source_in_gcn.status)
                        explanation.append(source_in_gcn.explanation)
                    else:
                        status.append(None)
                        explanation.append(None)

                df = pd.DataFrame(
                    {
                        "id": ids,
                        "tns": tns_name,
                        "ra": ras,
                        "dec": decs,
                        "redshift": redshifts,
                        "status": status,
                        "comment": explanation,
                    }
                )

                df_rejected = df[
                    (
                        df["id"].isin(
                            [
                                source.obj_id
                                for source in sources_with_status
                                if source.status == "rejected"
                            ]
                        )
                    )
                ]

                df_confirmed_or_unknown = df[(~df["id"].isin(df_rejected["id"]))]

                df_confirmed_or_unknown = df_confirmed_or_unknown.drop(
                    columns=["status"]
                )
                df_rejected = df_rejected.drop(columns=["status"])
                df = df.fillna("--")

                (
                    sources_text.append(
                        f"\nFound **{len(sources)} {'sources' if len(sources) > 1 else 'source'}** in the event's localization, {df_rejected.shape[0]} of which {'have' if df_rejected.shape[0] > 1 else 'has'} been rejected after characterization:\n"
                    )
                    if not no_text
                    else None
                )

                if df_confirmed_or_unknown.shape[0] > 0:
                    if not no_text:
                        sources_text.append("Sources:")
                    sources_text.append(
                        tabulate(
                            df_confirmed_or_unknown,
                            headers="keys",
                            tablefmt="github",
                            showindex=False,
                            floatfmt=".4f",
                        )
                        + "\n"
                    )
                if df_rejected.shape[0] > 0:
                    if not no_text:
                        sources_text.append("Rejected sources:")
                    sources_text.append(
                        tabulate(
                            df_rejected,
                            headers="keys",
                            tablefmt="github",
                            showindex=False,
                            floatfmt=".4f",
                        )
                        + "\n"
                    )

                for source in sources:
                    stmt = Photometry.select(user).where(
                        Photometry.obj_id == source["id"]
                    )
                    if photometry_in_window:
                        stmt = stmt.where(
                            Photometry.mjd >= start_date_mjd,
                            Photometry.mjd <= end_date_mjd,
                        )
                    photometry = session.scalars(stmt).all()
                    if len(photometry) > 0:
                        (
                            sources_text.append(
                                f"""\nPhotometry of **{source["id"]}**:\n"""
                            )
                            if not no_text
                            else None
                        )
                        mjds, mags, filters, origins, instruments = (
                            [],
                            [],
                            [],
                            [],
                            [],
                        )
                        for phot in photometry:
                            phot = serialize(phot, "ab", "mag")
                            mjds.append(phot["mjd"] if "mjd" in phot else None)
                            if (
                                "mag" in phot
                                and "magerr" in phot
                                and phot["mag"] is not None
                                and phot["magerr"] is not None
                            ):
                                mags.append(
                                    f"{np.round(phot['mag'], 2)}±{np.round(phot['magerr'], 2)}"
                                )
                            elif (
                                "limiting_mag" in phot
                                and phot["limiting_mag"] is not None
                            ):
                                mags.append(f"< {np.round(phot['limiting_mag'], 1)}")
                            else:
                                mags.append(None)
                            filters.append(phot["filter"] if "filter" in phot else None)
                            if (
                                "origin" in phot
                                and phot["origin"] is not None
                                and not pd.isna(phot["origin"])
                                and len(str(phot["origin"]).replace(" ", "")) != 0
                            ):
                                origins.append(phot["origin"])
                            else:
                                origins.append("")
                            instruments.append(
                                phot["instrument_name"]
                                if "instrument_name" in phot
                                else None
                            )
                        df_phot = pd.DataFrame(
                            {
                                "mjd": mjds,
                                "mag±err (ab)": mags,
                                "filter": filters,
                                "origin": origins,
                                "instrument": instruments,
                            }
                        )
                        if no_text:
                            df_phot.insert(
                                loc=0,
                                column="obj_id",
                                value=[p.obj_id for p in photometry],
                            )
                        df_phot = df_phot.fillna("--")
                        sources_text.append(
                            tabulate(
                                df_phot,
                                headers="keys",
                                tablefmt="github",
                                showindex=False,
                                floatfmt=".5f",
                            )
                            + "\n"
                        )
            contents.extend(sources_text)

        if show_galaxies:
            galaxies_text = []
            galaxies_page_number = 1
            galaxies = []
            # get the galaxies in the event
            while True:
                galaxies_data = get_galaxies(
                    session,
                    localization_dateobs=event.dateobs,
                    localization_name=localization_name,
                    localization_cumprob=localization_cumprob,
                    page_number=galaxies_page_number,
                    num_per_page=MAX_GALAXIES,
                    return_probability=True,
                )
                galaxies.extend(galaxies_data["galaxies"])
                galaxies_page_number += 1
                if len(galaxies_data["galaxies"]) < MAX_GALAXIES:
                    break
            if len(galaxies) > 0:
                (
                    galaxies_text.append(
                        f"""\nFound **{len(galaxies)} {"galaxies" if len(galaxies) > 1 else "galaxy"}** in the event's localization:\n"""
                    )
                    if not no_text
                    else None
                )
                names, ras, decs, distmpcs, magks, mag_nuvs, mag_w1s, probabilities = (
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                )
                for galaxy in galaxies:
                    if galaxy["probability"] is None or galaxy["probability"] == 0:
                        continue

                    names.append(galaxy["name"] if "name" in galaxy else None)
                    ras.append(galaxy["ra"] if "ra" in galaxy else None)
                    decs.append(galaxy["dec"] if "dec" in galaxy else None)
                    distmpcs.append(galaxy["distmpc"] if "distmpc" in galaxy else None)
                    magks.append(galaxy["magk"] if "magk" in galaxy else None)
                    mag_nuvs.append(galaxy["mag_nuv"] if "mag_nuv" in galaxy else None)
                    mag_w1s.append(galaxy["mag_w1"] if "mag_w1" in galaxy else None)
                    probabilities.append(
                        galaxy["probability"] if "probability" in galaxy else None
                    )
                df = pd.DataFrame(
                    {
                        "name": names,
                        "ra": ras,
                        "dec": decs,
                        "distmpc": distmpcs,
                        "magk": magks,
                        "mag_nuv": mag_nuvs,
                        "mag_w1": mag_w1s,
                        "probability": probabilities,
                    }
                )
                df.sort_values("probability", inplace=True, ascending=False)
                df = df[df["probability"] >= np.max(df["probability"]) * 0.01]
                df = df.fillna("--")
                galaxies_text.append(
                    tabulate(
                        df,
                        headers=[
                            "Galaxy",
                            "RA [deg]",
                            "Dec [deg]",
                            "Distance [Mpc]",
                            "m_Ks [mag]",
                            "m_NUV [mag]",
                            "m_W1 [mag]",
                            "dP_dV",
                        ],
                        tablefmt="github",
                        showindex=False,
                        floatfmt=(str, ".4f", ".4f", ".1f", ".1f", ".1f", ".1f", ".3e"),
                    )
                    + "\n"
                )
            contents.extend(galaxies_text)

            if localization is not None:
                distmean, distsigma = localization.marginal_moments
                if (distmean is not None) and (distsigma is not None):
                    min_distance = np.max([distmean - 3 * distsigma, 0])
                    max_distance = np.min([distmean + 3 * distsigma, 10000])
                    try:
                        completeness = get_galaxies_completeness(
                            galaxies, dist_min=min_distance, dist_max=max_distance
                        )
                    except Exception:
                        completeness = None

                    if completeness is not None and not no_text:
                        completeness_text = f"\n\nThe estimated mass completeness of the catalog for the skymap distance is ~{int(round(completeness * 100, 0))}%. This calculation was made by comparing the total mass within the catalog to a stellar mass function described by a Schechter function in the range {distmean:.1f} ± {distsigma:.1f} Mpc (within 3 sigma of the skymap).\n"
                        contents.append(completeness_text)

        if show_observations:
            from baselayer.app.models import AsyncVerifiedSession

            # get the executed obs, by instrument
            observations_text = []
            start_date = arrow.get(start_date).datetime
            end_date = arrow.get(end_date).datetime

            if instrument_ids is not None:
                stmt = Instrument.select(user).where(Instrument.id.in_(instrument_ids))
            else:
                stmt = Instrument.select(user).options(joinedload(Instrument.telescope))
            instruments = session.scalars(stmt).all()
            if instruments is not None:
                for instrument in instruments:
                    _telescope_name = instrument.telescope.name
                    _instrument_name = instrument.name
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    async def _fetch_observations(
                        telescope_name=_telescope_name,
                        instrument_name=_instrument_name,
                    ):
                        async with AsyncVerifiedSession(user) as asession:
                            return await get_observations(
                                asession,
                                start_date,
                                end_date,
                                telescope_name=telescope_name,
                                instrument_name=instrument_name,
                                localization_dateobs=dateobs,
                                localization_name=localization_name,
                                localization_cumprob=localization_cumprob,
                                min_observations_per_field=number_of_observations,
                                return_statistics=True,
                                stats_method=stats_method,
                                n_per_page=MAX_OBSERVATIONS,
                                page_number=1,
                                sort_by="obstime",
                                sort_order="asc",
                            )

                    try:
                        data = loop.run_until_complete(_fetch_observations())
                    finally:
                        loop.close()

                    observations = data["observations"]
                    num_observations = len(observations)
                    if num_observations > 0:
                        start_observation = astropy.time.Time(
                            min(obs["obstime"] for obs in observations),
                            format="datetime",
                        )
                        unique_filters = list({obs["filt"] for obs in observations})
                        total_time = sum(obs["exposure_time"] for obs in observations)
                        probability = data["probability"]
                        area = data["area"]

                        dt = start_observation.datetime - event.dateobs
                        before_after = "after" if dt.total_seconds() > 0 else "before"
                        (
                            observations_text.append(
                                f"""\n\n{instrument.telescope.name} - {instrument.name}:\n\nWe observed the localization region of {event.gcn_notices[0].stream} trigger {astropy.time.Time(event.dateobs, format="datetime").isot} UTC.  We obtained a total of **{num_observations} images covering {",".join(unique_filters)} bands for a total of {total_time} seconds. The observations covered {area:.1f} square degrees of the localization at least {nb_obs_to_word(number_of_observations)} times**, beginning at {start_observation.isot} ({humanize.naturaldelta(dt)} {before_after} the trigger time). Using the {localization_name} skymap, this corresponds to **~{int(100 * probability)}% of the probability enclosed in the localization region**.\n"""
                            )
                            if not no_text
                            else None
                        )
                        t0s, mjds, ras, decs, filters, exposures, limmags = (
                            [],
                            [],
                            [],
                            [],
                            [],
                            [],
                            [],
                        )
                        for obs in observations:
                            t0s.append(
                                (obs["obstime"] - event.dateobs)
                                / datetime.timedelta(hours=1)
                                if "obstime" in obs
                                else None
                            )
                            mjds.append(
                                astropy.time.Time(obs["obstime"], format="datetime").mjd
                                if "obstime" in obs
                                else None
                            )
                            ras.append(
                                obs["field"]["ra"] if "ra" in obs["field"] else None
                            )
                            decs.append(
                                obs["field"]["dec"] if "dec" in obs["field"] else None
                            )
                            filters.append(obs["filt"] if "filt" in obs else None)
                            exposures.append(
                                obs["exposure_time"] if "exposure_time" in obs else None
                            )
                            limmags.append(obs["limmag"] if "limmag" in obs else None)
                        df_obs = pd.DataFrame(
                            {
                                "T-T0 (hr)": t0s,
                                "mjd": mjds,
                                "ra": ras,
                                "dec": decs,
                                "filter": filters,
                                "exposure": exposures,
                                "limmag (ab)": limmags,
                            }
                        )
                        if no_text:
                            df_obs.insert(
                                loc=0,
                                column="tel/inst",
                                value=[
                                    f"{instrument.telescope.name}/{instrument.name}"
                                    for obs in observations
                                ],
                            )
                        df_obs = df_obs.fillna("--")
                        floatfmt = [".2f", ".5f", ".5f", ".5f", "%s", "%d", ".2f"]
                        if no_text:
                            floatfmt.insert(0, "%s")

                        observations_text.append(
                            tabulate(
                                df_obs,
                                headers="keys",
                                tablefmt="github",
                                showindex=False,
                                floatfmt=floatfmt,
                            )
                            + "\n"
                        )
                if len(observations_text) > 0 and not no_text:
                    observations_text.insert(0, "\nObservations:")

                if len(observations_text) > 0:
                    contents.extend(observations_text)

        if not no_text and acknowledgements is not None and len(acknowledgements) > 0:
            contents.append("\n*" + acknowledgements + "*")
        gcn_summary.text = "\n".join(contents)
        session.commit()

        flow = Flow()
        flow.push(
            user_id="*",
            action_type="skyportal/REFRESH_GCN_EVENT",
            payload={"gcnEvent_dateobs": event.dateobs},
        )

        notification = UserNotification(
            user=user,
            text=f"GCN summary *{gcn_summary.title}* on *{event.dateobs}* created.",
            notification_type="gcn_summary",
            url=f"/gcn_events/{event.dateobs}",
        )
        session.add(notification)
        session.commit()

        log(f"Successfully generated GCN summary {gcn_summary.id}")

    except Exception as e:
        try:
            gcn_summary = session.get(GcnSummary, summary_id)
            gcn_summary.text = "Failed to generate summary."
            session.commit()
        except Exception:
            pass
        log(f"Unable to create GCN summary: {e}")
        raise e
    finally:
        session.close()
        Session.remove()


class GcnSummaryHandler(BaseHandler):
    @auth_or_token
    async def post(
        self,
        dateobs: str,
        summary_id: int | None = None,
        *,
        body: GcnSummaryPostBody = None,
    ) -> GcnSummaryPostResponse:
        """
        ---
        summary: Create a GCN summary
        description: Post a summary of a GCN event.
        tags:
          - gcn events
          - gcn event summaries
        """

        body = self.parse_body(GcnSummaryPostBody)
        title = body.title
        number = body.number
        subject = body.subject
        user_ids = body.userIds
        group_id = body.groupId
        start_date = body.startDate
        end_date = body.endDate
        localization_name = body.localizationName
        localization_cumprob = body.localizationCumprob
        number_of_detections = body.numberDetections
        number_of_observations = body.numberObservations
        show_sources = body.showSources
        show_galaxies = body.showGalaxies
        show_observations = body.showObservations
        no_text = body.noText
        photometry_in_window = body.photometryInWindow
        stats_method = body.statsMethod
        instrument_ids = body.instrumentIds
        acknowledgements = body.acknowledgements

        class Validator(Schema):
            start_date = UTCTZnaiveDateTime(required=False, load_default=None)
            end_date = UTCTZnaiveDateTime(required=False, load_default=None)
            number_of_detections = Integer(
                required=False, load_default=2, validate=validate.Range(min=1)
            )
            number_of_observations = Integer(
                required=False, load_default=1, validate=validate.Range(min=1)
            )

        validator_instance = Validator()
        params_to_be_validated = {}
        if start_date is not None:
            params_to_be_validated["start_date"] = start_date
        if end_date is not None:
            params_to_be_validated["end_date"] = end_date
        if number_of_detections is not None:
            params_to_be_validated["number_of_detections"] = number_of_detections
        if number_of_observations is not None:
            params_to_be_validated["number_of_observations"] = number_of_observations

        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f"Error parsing query params: {e.args[0]}.")

        start_date = validated["start_date"]
        end_date = validated["end_date"]
        number_of_detections = validated["number_of_detections"]
        number_of_observations = validated["number_of_observations"]

        if title is None:
            return self.error("Title is required")

        if group_id is None:
            return self.error("Group ID is required")

        if stats_method not in ["db", "python"]:
            return self.error(
                "statsMethod for observations querying must be 'db' or 'python'"
            )

        if instrument_ids is not None:
            try:
                instrument_ids = [
                    int(instrument_id) for instrument_id in instrument_ids
                ]
                if len(instrument_ids) == 0:
                    instrument_ids = None
            except ValueError:
                return self.error("Instrument IDs must be a list of integers")

        try:
            number_of_detections = int(number_of_detections)
        except ValueError:
            return self.error("numberDetections must be an integer")

        if not no_text:
            if number is not None:
                try:
                    number = int(number)
                except ValueError:
                    return self.error("Number must be an integer")
            if subject is None:
                return self.error("Subject is required")
            if user_ids is not None:
                try:
                    if isinstance(user_ids, list):
                        user_ids = [int(user_id) for user_id in user_ids]
                    else:
                        user_ids = [int(user_ids)]
                except ValueError:
                    return self.error("User IDs must be integers")
            else:
                user_ids = []

            if acknowledgements is not None:
                acknowledgements = acknowledgements.strip('"')
                if len(acknowledgements) == 0:
                    acknowledgements = None

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            stmt = GcnEvent.select(session.user_or_token).where(
                GcnEvent.dateobs == dateobs_parsed
            )
            event = await session.scalar(stmt)

            if event is None:
                return self.error("Event not found", status=404)

            stmt = Group.select(session.user_or_token).where(Group.id == group_id)
            group = await session.scalar(stmt)
            if group is None:
                return self.error(f"Group not found with ID {group_id}")

            # verify that the user doesn't already have a summary with this title for this event
            stmt = GcnSummary.select(session.user_or_token, mode="read").where(
                GcnSummary.dateobs == dateobs_parsed,
                GcnSummary.title == title,
                GcnSummary.group_id == group_id,
                GcnSummary.sent_by_id == self.associated_user_object.id,
            )
            existing_summary = await session.scalar(stmt)
            if existing_summary is not None:
                return self.error(
                    "A summary with the same title, group, and event already exists for this user"
                )

            gcn_summary = GcnSummary(
                dateobs=event.dateobs,
                title=title,
                text="pending",
                sent_by_id=self.associated_user_object.id,
                group_id=group_id,
            )
            session.add(gcn_summary)
            await session.commit()

            summary_id = gcn_summary.id
            user_id = self.associated_user_object.id
            user_accessible_group_ids = [
                group.id for group in self.associated_user_object.accessible_groups
            ]
            from skyportal.utils.asynchronous import run_async

            try:
                run_async(
                    add_gcn_summary,
                    summary_id=summary_id,
                    user_id=user_id,
                    user_accessible_group_ids=user_accessible_group_ids,
                    dateobs=dateobs,
                    title=title,
                    number=number,
                    subject=subject,
                    user_ids=user_ids,
                    group_id=group_id,
                    start_date=start_date,
                    end_date=end_date,
                    localization_name=localization_name,
                    localization_cumprob=localization_cumprob,
                    number_of_detections=number_of_detections,
                    number_of_observations=number_of_observations,
                    show_sources=show_sources,
                    show_galaxies=show_galaxies,
                    show_observations=show_observations,
                    no_text=no_text,
                    photometry_in_window=photometry_in_window,
                    stats_method=stats_method,
                    instrument_ids=instrument_ids,
                    acknowledgements=acknowledgements,
                )
                return self.success({"id": summary_id})
            except Exception as e:
                return self.error(f"Error generating summary: {e}")

    @auth_or_token
    async def get(self, dateobs: str, summary_id: int):
        """
        ---
        summary: Get a GCN summary
        description: Retrieve a GCN summary
        tags:
          - gcn events
          - gcn event summaries
        responses:
          200:
            content:
              application/json:
                schema: SingleGcnSummary
          400:
            content:
              application/json:
                schema: Error
        """
        if summary_id is None:
            return self.error("Summary ID is required")

        try:
            summary_id_int = int(summary_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid summary_id: {summary_id}")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            stmt = GcnSummary.select(
                session.user_or_token,
                mode="read",
                options=[undefer(GcnSummary.text)],
            ).where(
                GcnSummary.id == summary_id_int,
                GcnSummary.dateobs == dateobs_parsed,
            )
            summary = await session.scalar(stmt)
            if summary is None:
                return self.error("Summary not found", status=404)

            return self.success(data=summary)

    @auth_or_token
    async def patch(
        self, dateobs: str, summary_id: int, *, body: GcnSummaryPatchBody = None
    ):
        """
        summary: Update a GCN summary
        description: Update a GCN summary
        tags:
          - gcn events
          - gcn event summaries
        responses:
          200:
            content:
              application/json:
                schema: SingleGcnSummary
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(GcnSummaryPatchBody)
        if not body.model_fields_set:
            return self.error("No data provided")

        if summary_id is None:
            return self.error("Summary ID is required")

        try:
            summary_id = int(summary_id)
        except ValueError:
            return self.error("Invalid summary_id value.")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            stmt = GcnSummary.select(
                session.user_or_token,
                mode="update",
                options=[undefer(GcnSummary.text)],
            ).where(
                GcnSummary.id == summary_id,
                GcnSummary.dateobs == dateobs_parsed,
            )
            summary = await session.scalar(stmt)
            if summary is None:
                return self.error("Summary not found", status=404)

            if body.body is not None:
                summary.text = body.body.strip('"')
            else:
                return self.error("body not found")

            await session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

            return self.success(data=summary)

    @auth_or_token
    async def delete(self, dateobs: str, summary_id: int):
        """
        ---
        summary: Delete a GCN summary
        description: Delete a GCN summary
        tags:
          - gcn events
          - gcn event summaries
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        if summary_id is None:
            return self.error("Summary ID is required")

        try:
            summary_id_int = int(summary_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid summary_id: {summary_id}")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            stmt = GcnSummary.select(
                session.user_or_token,
                mode="delete",
                options=[undefer(GcnSummary.text)],
            ).where(
                GcnSummary.id == summary_id_int,
                GcnSummary.dateobs == dateobs_parsed,
            )
            summary = await session.scalar(stmt)
            if summary is None:
                return self.error("Summary not found", status=404)

            if summary.text.strip().lower() == "pending" and datetime.datetime.now() < (
                summary.created_at + datetime.timedelta(hours=1)
            ):
                return self.error(
                    "Cannot delete a recently created summary (less than 1 hour) that is still pending"
                )

            await session.delete(summary)
            await session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

        return self.success()


def add_gcn_report(
    report_id,
    user_id,
    user_accessible_group_ids,
    dateobs,
    group_id,
    start_date,
    end_date,
    localization_name,
    localization_cumprob=0.90,
    number_of_detections=1,
    show_sources=True,
    show_observations=False,
    show_survey_efficiencies=False,
    photometry_in_window=True,
    stats_method="python",
    instrument_ids=None,
):
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        user = session.get(User, user_id)
        user_accessible_group_ids = [group.id for group in user.accessible_groups]
        session.user_or_token = user

        if isinstance(dateobs, str):
            dateobs = arrow.get(dateobs).naive

        gcn_report = session.get(GcnReport, report_id)

        try:
            group = session.get(Group, group_id)
            event = session.scalars(
                sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
            ).first()
            localization = session.scalars(
                sa.select(Localization).where(
                    Localization.dateobs == dateobs,
                    Localization.localization_name == localization_name,
                )
            ).first()
            start_date_mjd = Time(arrow.get(start_date).datetime).mjd
            end_date_mjd = Time(arrow.get(end_date).datetime).mjd

            contents = {}
            if show_sources:
                from baselayer.app.models import AsyncVerifiedSession

                source_page_number = 1
                sources = []
                while True:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    async def _fetch_sources(page_number=source_page_number):
                        async with AsyncVerifiedSession(user) as asession:
                            return await get_sources(
                                user_id=user.id,
                                session=asession,
                                group_ids=[group.id],
                                user_accessible_group_ids=user_accessible_group_ids,
                                detected_window_start=start_date,
                                detected_window_end=end_date,
                                localization_dateobs=dateobs,
                                localization_name=localization_name,
                                localization_cumprob=localization_cumprob,
                                number_of_detections=number_of_detections,
                                page_number=page_number,
                                num_per_page=MAX_SOURCES_PER_PAGE,
                            )

                    sources_data = loop.run_until_complete(_fetch_sources())
                    sources.extend(sources_data["sources"])
                    source_page_number += 1

                    if len(sources_data["sources"]) < MAX_SOURCES_PER_PAGE:
                        break
                if len(sources) > 0:
                    obj_ids = [source["id"] for source in sources]
                    sources_with_status = session.scalars(
                        GcnEventObj.select(user).where(
                            GcnEventObj.obj_id.in_(obj_ids),
                            GcnEventObj.dateobs == dateobs,
                        )
                    ).all()
                    for source in sources:
                        source["source_in_gcn"] = next(
                            (
                                source_in_gcn.to_dict()
                                for source_in_gcn in sources_with_status
                                if source_in_gcn.obj_id == source["id"]
                            ),
                            None,
                        )

                        stmt = Photometry.select(user).where(
                            Photometry.obj_id == source["id"]
                        )
                        if photometry_in_window:
                            stmt = stmt.where(
                                Photometry.mjd >= start_date_mjd,
                                Photometry.mjd <= end_date_mjd,
                            )
                        photometry = session.scalars(stmt).all()
                        if len(photometry) > 0:
                            source["photometry"] = [
                                serialize(phot, "ab", "mag") for phot in photometry
                            ]
                        else:
                            source["photometry"] = []

                contents["sources"] = sources

            if show_observations:
                from baselayer.app.models import AsyncVerifiedSession

                # get the executed obs, by instrument
                observations = []
                observation_statistics = []

                start_date = arrow.get(start_date).datetime
                end_date = arrow.get(end_date).datetime

                if instrument_ids is not None:
                    stmt = Instrument.select(user).where(
                        Instrument.id.in_(instrument_ids)
                    )
                else:
                    stmt = Instrument.select(user).options(
                        joinedload(Instrument.telescope)
                    )
                instruments = session.scalars(stmt).all()
                if instruments is not None:
                    for instrument in instruments:
                        _telescope_name = instrument.telescope.name
                        _instrument_name = instrument.name
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        async def _fetch_observations(
                            telescope_name=_telescope_name,
                            instrument_name=_instrument_name,
                        ):
                            async with AsyncVerifiedSession(user) as asession:
                                return await get_observations(
                                    asession,
                                    start_date,
                                    end_date,
                                    telescope_name=telescope_name,
                                    instrument_name=instrument_name,
                                    localization_dateobs=dateobs,
                                    localization_name=localization_name,
                                    localization_cumprob=localization_cumprob,
                                    return_statistics=True,
                                    includeGeoJSON=True,
                                    stats_method=stats_method,
                                    n_per_page=MAX_OBSERVATIONS,
                                    page_number=1,
                                    sort_by="obstime",
                                    sort_order="asc",
                                )

                        try:
                            data = loop.run_until_complete(_fetch_observations())
                        finally:
                            loop.close()
                        observation_statistics.append(
                            {
                                "telescope_name": instrument.telescope.name,
                                "instrument_name": instrument.name,
                                "probability": data["probability"],
                                "area": data["area"],
                            }
                        )
                        for o in data["observations"]:
                            idx = data["field_ids"].index(o["instrument_field_id"])
                            if idx is not None:
                                o["field_coordinates"] = data["geojson"][idx][
                                    "features"
                                ][0]["geometry"]["coordinates"]
                            if "field" in o:
                                del o["field"]

                        observations.extend(data["observations"])

                contents["observations"] = observations
                contents["observation_statistics"] = observation_statistics

            if show_survey_efficiencies:
                if instrument_ids is not None:
                    stmt = SurveyEfficiencyForObservations.select(user).where(
                        SurveyEfficiencyForObservations.instrument_id.in_(
                            instrument_ids
                        )
                    )
                else:
                    stmt = SurveyEfficiencyForObservations.select(user)
                survey_efficiency_analyses = session.scalars(stmt).all()

                contents["survey_efficiency_analyses"] = [
                    {
                        **analysis.to_dict(),
                        "number_of_transients": analysis.number_of_transients,
                        "number_in_covered": analysis.number_in_covered,
                        "number_detected": analysis.number_detected,
                        "efficiency": analysis.efficiency,
                    }
                    for analysis in survey_efficiency_analyses
                ]

            tags = event.tags
            aliases = event.aliases
            event_properties = event.properties
            localization_properties = localization.properties

            name = None
            for alias in aliases:
                if alias.startswith(("LVC#", "FERMI#")):
                    name = alias.split("#")[1]
                    break

            contents["event"] = {
                "status": "success",
                "name": name,
                "localization_name": localization_name,
                "cumulative_probability": float(localization_cumprob) * 100,
                "tags": list(set(tags)),
                "aliases": list(set(aliases)),
                "event_properties": event_properties,
                "localization_properties": localization_properties,
            }

            gcn_report.data = to_json(contents)
            session.commit()

            flow = Flow()
            flow.push(
                user_id="*",
                action_type="skyportal/REFRESH_GCNEVENT_REPORTS",
                payload={"gcnEvent_dateobs": event.dateobs},
            )

            notification = UserNotification(
                user=user,
                text=f"GCN report *{gcn_report.report_name}* on *{event.dateobs}* created.",
                notification_type="gcn_report",
                url=f"/gcn_events/{event.dateobs}",
            )
            session.add(notification)
            session.commit()

            log(f"Successfully generated GCN report {gcn_report.id}")
        except Exception as e:
            try:
                session.rollback()
                gcn_report = session.get(GcnReport, report_id)
                gcn_report.data = to_json({"status": "error", "message": str(e)})
                session.commit()
            except Exception:
                session.rollback()
            log(f"Unable to update GCN report: {str(e)}")

    except Exception as e:
        log(f"Unable to create GCN report: {str(e)}")
        raise e
    finally:
        session.close()
        Session.remove()


class GcnReportPostResponse(BaseModel):
    """ID of the created GCN report."""

    id: int = Field(description="ID of the created GCN report")


class GcnReportHandler(BaseHandler):
    @auth_or_token
    async def post(
        self,
        dateobs: str,
        report_id: int | None = None,
        *,
        body: GcnReportPostBody = None,
    ) -> GcnReportPostResponse:
        """
        ---
        summary: Create a GCN report
        description: Post report data of a GCN event.
        tags:
          - gcn events
          - gcn event reports
        """

        body = self.parse_body(GcnReportPostBody)
        report_name = body.reportName
        group_id = body.groupId
        start_date = body.startDate
        end_date = body.endDate
        localization_name = body.localizationName
        localization_cumprob = body.localizationCumprob
        number_of_detections = body.numberDetections
        show_sources = body.showSources
        show_observations = body.showObservations
        show_survey_efficiencies = body.showSurveyEfficiencies
        photometry_in_window = body.photometryInWindow
        stats_method = body.statsMethod
        instrument_ids = body.instrumentIds

        class Validator(Schema):
            start_date = UTCTZnaiveDateTime(required=False, load_default=None)
            end_date = UTCTZnaiveDateTime(required=False, load_default=None)

        validator_instance = Validator()
        params_to_be_validated = {}
        if start_date is not None:
            params_to_be_validated["start_date"] = start_date
        if end_date is not None:
            params_to_be_validated["end_date"] = end_date

        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f"Error parsing query params: {e.args[0]}.")

        start_date = validated["start_date"]
        end_date = validated["end_date"]

        if report_name is None:
            return self.error("reportName is required")

        if group_id is None:
            return self.error("Group ID is required")

        if stats_method not in ["db", "python"]:
            return self.error(
                "statsMethod for observations querying must be 'db' or 'python'"
            )

        if instrument_ids is not None:
            try:
                instrument_ids = [
                    int(instrument_id) for instrument_id in instrument_ids
                ]
                if len(instrument_ids) == 0:
                    instrument_ids = None
            except ValueError:
                return self.error("Instrument IDs must be a list of integers")

        try:
            number_of_detections = int(number_of_detections)
        except ValueError:
            return self.error("numberDetections must be an integer")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            stmt = GcnEvent.select(session.user_or_token).where(
                GcnEvent.dateobs == dateobs_parsed
            )
            event = await session.scalar(stmt)

            if event is None:
                return self.error("Event not found", status=404)

            stmt = Group.select(session.user_or_token).where(Group.id == group_id)
            group = await session.scalar(stmt)
            if group is None:
                return self.error(f"Group not found with ID {group_id}")

            # verify that the user doesn't already have a summary with this title for this event
            stmt = GcnReport.select(session.user_or_token, mode="read").where(
                GcnReport.dateobs == dateobs_parsed,
                GcnReport.report_name == report_name,
                GcnReport.group_id == group_id,
                GcnReport.sent_by_id == self.associated_user_object.id,
            )
            existing_report = await session.scalar(stmt)
            if existing_report is not None:
                return self.error(
                    "A report with the same name, group, and event already exists for this user"
                )

            gcn_report = GcnReport(
                dateobs=event.dateobs,
                report_name=report_name,
                data={"status": "pending"},
                sent_by_id=self.associated_user_object.id,
                group_id=group_id,
            )
            session.add(gcn_report)
            await session.commit()

            report_id = gcn_report.id
            user_id = self.associated_user_object.id
            user_accessible_group_ids = [
                group.id for group in self.associated_user_object.accessible_groups
            ]

            try:
                IOLoop.current().run_in_executor(
                    None,
                    lambda: add_gcn_report(
                        report_id=report_id,
                        user_id=user_id,
                        user_accessible_group_ids=user_accessible_group_ids,
                        dateobs=dateobs,
                        group_id=group_id,
                        start_date=start_date,
                        end_date=end_date,
                        localization_name=localization_name,
                        localization_cumprob=localization_cumprob,
                        number_of_detections=number_of_detections,
                        show_sources=show_sources,
                        show_observations=show_observations,
                        show_survey_efficiencies=show_survey_efficiencies,
                        photometry_in_window=photometry_in_window,
                        stats_method=stats_method,
                        instrument_ids=instrument_ids,
                    ),
                )
                return self.success({"id": report_id})
            except Exception as e:
                return self.error(f"Error generating report: {e}")

    @auth_or_token
    async def get(self, dateobs: str, report_id: int | None = None):
        """
        ---
        summary: Get a GCN report
        description: Retrieve a GCN report
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: SingleGcnReport
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        if report_id is None:
            async with self.AsyncSession() as session:
                stmt = GcnReport.select(
                    session.user_or_token,
                    mode="read",
                    options=[
                        selectinload(GcnReport.sent_by),
                        selectinload(GcnReport.group),
                    ],
                ).where(GcnReport.dateobs == dateobs_parsed)
                result = await session.scalars(stmt)
                reports = result.all()
                reports = sorted(
                    (
                        {
                            **p.to_dict(),
                            "sent_by": p.sent_by.to_dict(),
                            "group": p.group.to_dict(),
                        }
                        for p in reports
                    ),
                    key=lambda x: x["created_at"],
                    reverse=True,
                )
                return self.success(data=reports)

        try:
            report_id_int = int(report_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid report_id: {report_id}")

        async with self.AsyncSession() as session:
            stmt = GcnReport.select(
                session.user_or_token,
                mode="read",
                options=[undefer(GcnReport.data)],
            ).where(
                GcnReport.id == report_id_int,
                GcnReport.dateobs == dateobs_parsed,
            )
            report = await session.scalar(stmt)
            if report is None:
                return self.error("Report not found", status=404)

            return self.success(data=report)

    @auth_or_token
    async def patch(
        self, dateobs: str, report_id: int, *, body: GcnReportPatchBody = None
    ):
        """
        summary: Update a GCN report
        description: Update a GCN report
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: SingleGcnReport
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(GcnReportPatchBody)
        if not body.model_fields_set:
            return self.error("No data provided")

        if report_id is None:
            return self.error("Report ID is required")

        try:
            report_id_int = int(report_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid report_id: {report_id}")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            stmt = GcnReport.select(
                session.user_or_token,
                mode="update",
                options=[undefer(GcnReport.data)],
            ).where(
                GcnReport.id == report_id_int,
                GcnReport.dateobs == dateobs_parsed,
            )
            report = await session.scalar(stmt)
            if report is None:
                return self.error("Report not found", status=404)

            report_id = report.id

            if "data" in body.model_fields_set:
                if body.data != {}:
                    new_data = body.data
                    if len(new_data.get("sources", [])) > 0:
                        try:
                            loop = asyncio.get_event_loop()
                        except Exception:
                            loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        old_data = report.data
                        old_data = (
                            json.loads(old_data)
                            if isinstance(old_data, str)
                            else old_data
                        )

                        # if there is any duplicate source, return error
                        if len(new_data.get("sources", [])) != len(
                            {
                                source.get("id", None)
                                for source in new_data.get("sources", [])
                            }
                        ):
                            return self.error(
                                "Duplicate sources in report, please remove duplicates and try again"
                            )
                        for i, source in enumerate(new_data.get("sources", [])):
                            if source not in old_data.get("sources", []):
                                # check if source exists in the database
                                source_id = source.get("id", None)
                                source = await get_source(
                                    source_id,
                                    self.associated_user_object.id,
                                    session,
                                    include_photometry=False,
                                )
                                if source is None:
                                    return self.error(
                                        f"Source {source_id} not found in the database, not updating report"
                                    )

                                stmt = Photometry.select(session.user_or_token).where(
                                    Photometry.obj_id == source["id"]
                                )
                                phot_result = await session.scalars(stmt)
                                photometry = phot_result.all()
                                if len(photometry) > 0:
                                    source["photometry"] = [
                                        serialize(phot, "ab", "mag")
                                        for phot in photometry
                                    ]
                                else:
                                    source["photometry"] = []

                                source["source_in_gcn"] = await session.scalar(
                                    GcnEventObj.select(session.user_or_token).where(
                                        GcnEventObj.obj_id == source_id,
                                        GcnEventObj.dateobs == dateobs_parsed,
                                    )
                                )

                                source["comment"] = new_data["sources"][i].get(
                                    "comment", ""
                                )
                                # add source to report
                                new_data["sources"][i] = source

                    report.data = to_json(new_data)
                else:
                    return self.error("data not found")

            if body.published is not None and isinstance(body.published, bool):
                publish = body.published
                if publish:
                    report.publish()
                else:
                    report.unpublish()
            else:
                report.generate_report()

            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_GCNEVENT_REPORT",
                payload={"report_id": report_id},
            )

            return self.success(data=report)

    @auth_or_token
    async def delete(self, dateobs: str, report_id: int):
        """
        ---
        summary: Delete a GCN report
        description: Delete a GCN report
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        if report_id is None:
            return self.error("Report ID is required")

        try:
            report_id_int = int(report_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid report_id: {report_id}")

        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            stmt = GcnReport.select(
                session.user_or_token,
                mode="delete",
                options=[undefer(GcnReport.data)],
            ).where(
                GcnReport.id == report_id_int,
                GcnReport.dateobs == dateobs_parsed,
            )
            report = await session.scalar(stmt)
            if report is None:
                return self.error("Report not found", status=404)

            data = report.data
            if isinstance(data, str):
                data = json.loads(data)

            if len(data.keys()) == 0 and datetime.datetime.now() < (
                report.created_at + datetime.timedelta(hours=1)
            ):
                return self.error(
                    "Cannot delete a recently created report (less than 1 hour) that is still pending"
                )

            report.unpublish()

            await session.delete(report)
            await session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

        return self.success()


class LocalizationDownloadHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs: str, localization_name: str):
        """
        ---
        summary: Download a localization's skymap
        description: Download a GCN localization skymap
        tags:
          - localizations
        responses:
          200:
            content:
              application/json:
                schema: LocalizationHandlerGet
          400:
            content:
              application/json:
                schema: Error
        """

        dateobs = dateobs.strip()
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        localization_name = localization_name.strip()
        local_temp_files = []

        async with self.AsyncSession() as session:
            try:
                localization = await session.scalar(
                    Localization.select(
                        session.user_or_token,
                        options=[
                            undefer(Localization.uniq),
                            undefer(Localization.probdensity),
                            # 3D distance columns are deferred; undefer them so
                            # is_3d / table don't trigger a lazy load (which
                            # raises MissingGreenlet under the async session).
                            undefer(Localization.distmu),
                            undefer(Localization.distsigma),
                            undefer(Localization.distnorm),
                        ],
                    ).where(
                        Localization.dateobs == dateobs_parsed,
                        Localization.localization_name == localization_name,
                    )
                )
                if localization is None:
                    return self.error("Localization not found", status=404)

                output_format = "fits"
                with tempfile.NamedTemporaryFile(suffix=".fits") as fitsfile:
                    localization_path = localization.get_localization_path()
                    if localization_path is None:
                        ligo.skymap.io.write_sky_map(
                            fitsfile.name, localization.table, moc=True
                        )
                        with open(fitsfile.name, mode="rb") as g:
                            content = g.read()
                        local_temp_files.append(fitsfile.name)
                    else:
                        with open(localization_path, mode="rb") as g:
                            content = g.read()

                data = io.BytesIO(content)
                filename = f"{localization.localization_name}.{output_format}"

                await self.send_file(data, filename, output_type=output_format)

            except Exception as e:
                return self.error(f"Failed to create skymap for download: str({e})")
            finally:
                # clean up local files
                for f in local_temp_files:
                    try:
                        os.remove(f)
                    except:  # noqa E722
                        pass


class LocalizationCrossmatchGetQuery(BaseModel):
    """Query parameters for crossmatching two localizations."""

    model_config = ConfigDict(extra="forbid")

    id1: int = Field(description="ID of the first localization.")
    id2: int = Field(description="ID of the second localization.")


class LocalizationCrossmatchHandler(BaseHandler):
    @auth_or_token
    async def get(self, *, query: LocalizationCrossmatchGetQuery = None):
        """
        ---
        summary: Crossmatch two localizations
        description: A fits file corresponding to the intersection of the input fits files.
        tags:
          - localizations
        responses:
          200:
            content:
              application/fits:
                schema:
                  type: string
                  format: binary
          400:
            content:
              application/json:
                schema: Error
        """
        query = self.parse_query(LocalizationCrossmatchGetQuery)

        id1_int = query.id1
        id2_int = query.id2

        local_temp_files = []

        async with self.AsyncSession() as session:
            try:
                localization1 = await session.scalar(
                    Localization.select(
                        session.user_or_token,
                        options=[
                            undefer(Localization.uniq),
                            undefer(Localization.probdensity),
                        ],
                    ).where(
                        Localization.id == id1_int,
                    )
                )
                localization2 = await session.scalar(
                    Localization.select(
                        session.user_or_token,
                        options=[
                            undefer(Localization.uniq),
                            undefer(Localization.probdensity),
                        ],
                    ).where(
                        Localization.id == id2_int,
                    )
                )

                if localization1 is None or localization2 is None:
                    return self.error("Localization not found", status=404)

                output_format = "fits"

                skymap1 = localization1.flat_2d
                skymap2 = localization2.flat_2d
                skymap = skymap1 * skymap2
                skymap = skymap / np.sum(skymap)

                skymap = hp.reorder(skymap, "RING", "NESTED")
                skymap = ligo_bayestar.derasterize(Table([skymap], names=["PROB"]))
                with tempfile.NamedTemporaryFile(suffix=".fits") as fitsfile:
                    ligo.skymap.io.write_sky_map(
                        fitsfile.name, skymap, format="fits", moc=True
                    )

                    with open(fitsfile.name, mode="rb") as g:
                        content = g.read()
                    local_temp_files.append(fitsfile.name)

                data = io.BytesIO(content)
                filename = f"{localization1.localization_name}_{localization2.localization_name}.{output_format}"

                await self.send_file(
                    data,
                    filename,
                    output_type=output_format,
                )

            except Exception as e:
                return self.error(f"Failed to create skymap for download: str({e})")
            finally:
                # clean up local files
                for f in local_temp_files:
                    try:
                        os.remove(f)
                    except:  # noqa E722
                        pass


class GcnEventInstrumentFieldGetQuery(BaseModel):
    """Query parameters for instrument field probabilities for a skymap."""

    model_config = ConfigDict(extra="forbid")

    localization_name: str | None = Field(
        default=None, description="Localization map name"
    )
    integrated_probability: float = Field(
        default=0.95, description="Cumulative integrated probability threshold"
    )


class GcnEventInstrumentFieldHandler(BaseHandler):
    @auth_or_token
    async def get(
        self,
        dateobs: str,
        instrument_id: int,
        *,
        query: GcnEventInstrumentFieldGetQuery = None,
    ):
        """
        ---
        summary: Get instrument field probabilities for a skymap
        description: Compute instrument field probabilities for a skymap
        tags:
          - localizations
          - instruments
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        query = self.parse_query(GcnEventInstrumentFieldGetQuery)

        dateobs = dateobs.strip()
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        localization_name = query.localization_name
        integrated_probability = query.integrated_probability

        async with self.AsyncSession() as session:
            stmt = Localization.select(session.user_or_token).where(
                Localization.dateobs == dateobs_parsed
            )
            if localization_name is not None:
                stmt = stmt.where(Localization.localization_name == localization_name)
            localization = await session.scalar(stmt)
            if localization is None:
                return self.error("Localization not found", status=404)

            stmt = Instrument.select(session.user_or_token).where(
                Instrument.id == int(instrument_id)
            )
            instrument = await session.scalar(stmt)
            if instrument is None:
                return self.error(f"No instrument with ID: {instrument_id}")

            cum_prob = (
                sa.func.sum(
                    LocalizationTile.probdensity * LocalizationTile.healpix.area
                )
                .over(order_by=LocalizationTile.probdensity.desc())
                .label("cum_prob")
            )
            localizationtile_subquery = (
                sa.select(LocalizationTile.probdensity, cum_prob).filter(
                    LocalizationTile.localization_id == localization.id
                )
            ).subquery()

            min_probdensity = (
                sa.select(
                    sa.func.min(localizationtile_subquery.columns.probdensity)
                ).filter(
                    localizationtile_subquery.columns.cum_prob <= integrated_probability
                )
            ).scalar_subquery()

            area = (InstrumentFieldTile.healpix * LocalizationTile.healpix).area
            prob = sa.func.sum(LocalizationTile.probdensity * area)

            field_tiles_query = (
                sa.select(InstrumentField.field_id, prob)
                .where(
                    LocalizationTile.localization_id == localization.id,
                    LocalizationTile.probdensity >= min_probdensity,
                    InstrumentFieldTile.instrument_id == instrument.id,
                    InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                    InstrumentFieldTile.healpix.overlaps(LocalizationTile.healpix),
                )
                .group_by(InstrumentField.field_id)
            )

            tiles_result = await session.execute(field_tiles_query)
            rows = tiles_result.all()
            if not rows:
                return self.success(data={"field_ids": [], "probabilities": []})
            field_ids, probs = zip(*rows)

            data_out = {"field_ids": list(field_ids), "probabilities": list(probs)}
            return self.success(data=data_out)


class GcnEventTriggerHandler(BaseHandler):
    @permissions(["Manage allocations"])
    async def get(self, dateobs: str, allocation_id: int | None = None):
        dateobs = dateobs.strip()
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        async with self.AsyncSession() as session:
            if allocation_id is not None:
                try:
                    allocation_id = int(allocation_id)
                except ValueError as e:
                    return self.error(f"Failed to parse allocation_id: str({e})")
                try:
                    result = await session.scalars(
                        GcnTrigger.select(session.user_or_token).where(
                            GcnTrigger.dateobs == dateobs_parsed,
                            GcnTrigger.allocation_id == allocation_id,
                        )
                    )
                    gcn_triggered = result.all()
                    return self.success(data=gcn_triggered)
                except Exception as e:
                    return self.error(
                        f"Failed to get gcn_event triggered status: str({e})"
                    )

            else:
                try:
                    result = await session.scalars(
                        GcnTrigger.select(session.user_or_token).where(
                            GcnTrigger.dateobs == dateobs_parsed
                        )
                    )
                    gcn_triggered = result.all()
                    return self.success(data=gcn_triggered)
                except Exception as e:
                    return self.error(
                        f"Failed to get gcn_event triggered status: str({e})"
                    )

    @permissions(["Manage allocations"])
    async def put(
        self, dateobs: str, allocation_id: int, *, body: GcnEventTriggerPutBody = None
    ):
        body = self.parse_body(GcnEventTriggerPutBody)
        dateobs = dateobs.strip()
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        triggered = body.triggered
        if triggered is None:
            return self.error("Must specify triggered status")
        elif triggered in ["True", "true", "t", "T", True, "triggered"]:
            triggered = True
        elif triggered in ["False", "false", "f", "F", False, "passed"]:
            triggered = False
        else:
            return self.error("Invalid triggered status")

        try:
            allocation_id = int(allocation_id)
        except ValueError:
            return self.error(f"Failed to parse allocation_id: {allocation_id}")

        async with self.AsyncSession() as session:
            try:
                gcn_triggered = await session.scalar(
                    GcnTrigger.select(session.user_or_token).where(
                        GcnTrigger.dateobs == dateobs_parsed,
                        GcnTrigger.allocation_id == allocation_id,
                    )
                )
                if gcn_triggered is None:
                    # verify that the event and allocation exist
                    event = await session.scalar(
                        GcnEvent.select(session.user_or_token).where(
                            GcnEvent.dateobs == dateobs_parsed
                        )
                    )

                    if event is None:
                        return self.error(f"No event with dateobs: {dateobs}")
                    allocation = await session.scalar(
                        Allocation.select(session.user_or_token).where(
                            Allocation.id == allocation_id
                        )
                    )
                    if allocation is None:
                        return self.error(f"No allocation with ID: {allocation_id}")

                    gcn_triggered = GcnTrigger(
                        dateobs=dateobs_parsed,
                        allocation_id=allocation_id,
                        triggered=triggered,
                    )
                    session.add(gcn_triggered)
                else:
                    gcn_triggered.triggered = triggered
                await session.commit()
                self.push_all(
                    "skyportal/REFRESH_GCN_TRIGGERED",
                    payload={"gcnEvent_dateobs": dateobs},
                )
                return self.success(data=gcn_triggered)
            except Exception as e:
                return self.error(f"Failed to set triggered status: str({e})")

    @permissions(["Manage allocations"])
    async def delete(self, dateobs: str, allocation_id: int):
        dateobs = dateobs.strip()
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        try:
            allocation_id = int(allocation_id)
        except ValueError:
            return self.error(f"Failed to parse allocation_id: {allocation_id}")

        async with self.AsyncSession() as session:
            try:
                gcn_triggered = await session.scalar(
                    sa.select(GcnTrigger).where(
                        GcnTrigger.dateobs == dateobs_parsed,
                        GcnTrigger.allocation_id == allocation_id,
                    )
                )
                if gcn_triggered is not None:
                    await session.delete(gcn_triggered)
                    await session.commit()
                    self.push_all(
                        "skyportal/REFRESH_GCN_TRIGGERED",
                        payload={"gcnEvent_dateobs": dateobs},
                    )
                    return self.success(data=gcn_triggered)
                else:
                    return self.error(
                        f"No gcn triggered status for dateobs={dateobs} and allocation_id={allocation_id}"
                    )
            except Exception as e:
                return self.error(f"Failed to delete triggered status: str({e})")


def apply_gcn_event_filters(
    query,
    user_or_token,
    gcn_tag_keep=None,
    gcn_tag_remove=None,
    localization_tag_keep=None,
    localization_tag_remove=None,
    gcn_properties_filter=None,
    localization_properties_filter=None,
    mmadetector_ids=None,
):
    """Apply GCN/localization tag and property filters to a GcnEvent select query.

    Shared by the events list handler and the object crossmatch handler. Raises
    ValueError on a malformed property filter (callers translate to self.error).
    """
    # The outer query already restricts to accessible events, and tags/localizations
    # are keyed by dateobs (1:1 with an event), so these filters use plain dateobs
    # IN/NOT IN rather than re-joining the group-access chain per tag subquery.
    # Keyed on the event id rather than dateobs: the join table is the only one
    # of these that references GcnEvent.id.
    if mmadetector_ids:
        query = query.where(
            GcnEvent.id.in_(
                sa.select(GcnEventMMADetector.gcnevent_id).where(
                    GcnEventMMADetector.mmadetector_id.in_(mmadetector_ids)
                )
            )
        )
    if gcn_tag_keep:
        query = query.where(
            GcnEvent.dateobs.in_(
                sa.select(GcnTag.dateobs).where(GcnTag.text.in_(gcn_tag_keep))
            )
        )
    if gcn_tag_remove:
        query = query.where(
            GcnEvent.dateobs.notin_(
                sa.select(GcnTag.dateobs).where(GcnTag.text.in_(gcn_tag_remove))
            )
        )
    if localization_tag_keep:
        query = query.where(
            GcnEvent.dateobs.in_(
                sa.select(Localization.dateobs)
                .join(
                    LocalizationTag,
                    LocalizationTag.localization_id == Localization.id,
                )
                .where(LocalizationTag.text.in_(localization_tag_keep))
            )
        )
    if localization_tag_remove:
        query = query.where(
            GcnEvent.dateobs.notin_(
                sa.select(Localization.dateobs)
                .join(
                    LocalizationTag,
                    LocalizationTag.localization_id == Localization.id,
                )
                .where(LocalizationTag.text.in_(localization_tag_remove))
            )
        )
    if gcn_properties_filter is not None:
        for prop_filt in gcn_properties_filter:
            prop_split = prop_filt.split(":")
            if not (len(prop_split) == 1 or len(prop_split) == 3):
                raise ValueError(
                    "Invalid gcnPropertiesFilter value -- property filter must have 1 or 3 values"
                )
            name = prop_split[0].strip()

            properties_query = GcnProperty.select(user_or_token)
            if len(prop_split) == 3:
                value = prop_split[1].strip()
                try:
                    value = float(value)
                except ValueError as e:
                    raise ValueError(f"Invalid GCN properties filter value: {e}")
                op = prop_split[2].strip()
                op_options = ["lt", "le", "eq", "ne", "ge", "gt"]
                if op not in op_options:
                    raise ValueError(f"Invalid operator: {op}")
                comp_function = getattr(operator, op)

                properties_query = properties_query.where(
                    comp_function(GcnProperty.data[name], cast(value, JSONB))
                )
            else:
                properties_query = properties_query.where(
                    GcnProperty.data[name].astext.is_not(None)
                )

            properties_subquery = properties_query.subquery()
            query = query.join(
                properties_subquery,
                GcnEvent.dateobs == properties_subquery.c.dateobs,
            )

    if localization_properties_filter is not None:
        for prop_filt in localization_properties_filter:
            prop_split = prop_filt.split(":")
            if not (len(prop_split) == 1 or len(prop_split) == 3):
                raise ValueError(
                    "Invalid localizationPropertiesFilter value -- property filter must have 1 or 3 values"
                )
            name = prop_split[0].strip()

            properties_query = LocalizationProperty.select(user_or_token)
            if len(prop_split) == 3:
                value = prop_split[1].strip()
                try:
                    value = float(value)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid localization properties filter value: {e}"
                    )
                op = prop_split[2].strip()
                op_options = ["lt", "le", "eq", "ne", "ge", "gt"]
                if op not in op_options:
                    raise ValueError(f"Invalid operator: {op}")
                comp_function = getattr(operator, op)

                properties_query = properties_query.where(
                    comp_function(LocalizationProperty.data[name], cast(value, JSONB))
                )
            else:
                properties_query = properties_query.where(
                    LocalizationProperty.data[name].astext.is_not(None)
                )

            properties_subquery = properties_query.subquery()
            localizations_query = Localization.select(user_or_token)
            localizations_query = localizations_query.join(
                properties_subquery,
                Localization.id == properties_subquery.c.localization_id,
            )
            localizations_subquery = localizations_query.subquery()

            query = query.join(
                localizations_subquery,
                GcnEvent.dateobs == localizations_subquery.c.dateobs,
            )

    return query


def parse_gcn_filter_list(value, name):
    """Parse a filter argument (JSON array or comma-separated string) into a list."""
    if value in (None, "", []):
        return None
    if isinstance(value, list):
        return [str(c).strip() for c in value]
    if isinstance(value, str):
        return [c.strip() for c in value.split(",")]
    raise ValueError(f"Invalid {name} value -- must provide at least one string value")


class ObjGcnEventHandler(BaseHandler):
    @auth_or_token
    async def post(self, obj_id: str, *, body: ObjGcnEventPostBody = None):
        """
        ---
        summary: Crossmatch an object with GCN events
        description: Retrieve an object's in-out critera for GcnEvents
        tags:
          - objs
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        body = self.parse_body(ObjGcnEventPostBody)
        start_date = body.startDate
        end_date = body.endDate
        integrated_probability = body.probability
        before_first_detection = body.beforeFirstDetection

        try:
            gcn_tag_keep = parse_gcn_filter_list(body.gcnTagKeep, "gcnTagKeep")
            gcn_tag_remove = parse_gcn_filter_list(body.gcnTagRemove, "gcnTagRemove")
            localization_tag_keep = parse_gcn_filter_list(
                body.localizationTagKeep, "localizationTagKeep"
            )
            localization_tag_remove = parse_gcn_filter_list(
                body.localizationTagRemove, "localizationTagRemove"
            )
            gcn_properties_filter = parse_gcn_filter_list(
                body.gcnPropertiesFilter, "gcnPropertiesFilter"
            )
            localization_properties_filter = parse_gcn_filter_list(
                body.localizationPropertiesFilter, "localizationPropertiesFilter"
            )
        except ValueError as e:
            return self.error(str(e))

        if start_date is None or end_date is None:
            return self.error("Must provide startDate and endDate query arguments.")

        try:
            start_date = arrow.get(start_date.strip()).naive
        except Exception as e:
            return self.error(f"Failed to parse startDate: str({e})")

        try:
            end_date = arrow.get(end_date.strip()).naive
        except Exception as e:
            return self.error(f"Failed to parse endDate: str({e})")

        if (end_date - start_date).days > 31:
            return self.error(
                "startDate and endDate must be within 31 days of each other."
            )

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token, mode="update").where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            query = GcnEvent.select(
                session.user_or_token,
            ).where(
                GcnEvent.dateobs >= start_date,
                GcnEvent.dateobs <= end_date,
            )

            # Optionally restrict to events at/before the source's first detection.
            if before_first_detection:
                photstat = await session.scalar(
                    sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
                )
                first_detected_mjd = getattr(photstat, "first_detected_mjd", None)
                if first_detected_mjd is None:
                    return self.error(
                        f"Cannot restrict to events before first detection: {obj_id} "
                        "has no detection statistics."
                    )
                query = query.where(
                    GcnEvent.dateobs <= Time(first_detected_mjd, format="mjd").datetime
                )

            try:
                query = apply_gcn_event_filters(
                    query,
                    session.user_or_token,
                    gcn_tag_keep=gcn_tag_keep,
                    gcn_tag_remove=gcn_tag_remove,
                    localization_tag_keep=localization_tag_keep,
                    localization_tag_remove=localization_tag_remove,
                    gcn_properties_filter=gcn_properties_filter,
                    localization_properties_filter=localization_properties_filter,
                )
            except ValueError as e:
                return self.error(str(e))

            result = await session.scalars(query)
            event_ids = [event.id for event in result.unique().all()]
            if len(event_ids) == 0:
                return self.error(
                    f"Cannot find GcnEvents between {start_date} and {end_date} "
                    "matching the selected filters."
                )

            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            IOLoop.current().run_in_executor(
                None,
                lambda: crossmatch_gcn_objects(
                    obj_id,
                    event_ids,
                    self.associated_user_object.id,
                    integrated_probability=integrated_probability,
                ),
            )

            return self.success()


def crossmatch_gcn_objects(obj_id, event_ids, user_id, integrated_probability=0.95):
    """Find events in which an object is within the integrated probability contour.
    obj_id : str
        Object ID
    events_id : List[int]
        GCN Event IDs to crossmatch against
    user_id : int
        SkyPortal ID of User posting the crossmatch results
    integrated_probability : float
        Confidence level up to which to perform crossmatch
    """

    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    user = session.scalar(sa.select(User).where(User.id == user_id))

    try:
        obj = session.scalars(
            Obj.select(user, mode="update").where(Obj.id == obj_id)
        ).first()
        if obj is None:
            raise ValueError(f"Cannot find object with ID {obj_id}.")

        events = []
        for event_id in event_ids:
            event = session.scalars(
                GcnEvent.select(
                    user,
                    options=[
                        joinedload(GcnEvent.localizations),
                    ],
                ).where(GcnEvent.id == event_id)
            ).first()
            if event is None:
                continue
            if len(event.localizations) == 0:
                continue
            localization_id = event.localizations[0].id

            partition_key = event.dateobs
            # now get the dateobs in the format YYYY_MM
            localizationtile_partition_name = (
                f"{partition_key.year}_{partition_key.month:02d}"
            )
            localizationtilescls = LocalizationTile.partitions.get(
                localizationtile_partition_name, None
            )
            if localizationtilescls is None:
                localizationtilescls = LocalizationTile
            else:
                # check that there is actually a localizationTile with the given localization_id in the partition
                # if not, use the default partition
                if not (
                    session.scalars(
                        sa.select(localizationtilescls.localization_id).where(
                            localizationtilescls.localization_id == localization_id
                        )
                    ).first()
                ):
                    localizationtilescls = LocalizationTile.partitions.get(
                        "def", LocalizationTile
                    )

            cum_prob = (
                sa.func.sum(
                    localizationtilescls.probdensity * localizationtilescls.healpix.area
                )
                .over(order_by=localizationtilescls.probdensity.desc())
                .label("cum_prob")
            )
            localizationtile_subquery = (
                sa.select(localizationtilescls.probdensity, cum_prob).filter(
                    localizationtilescls.localization_id == localization_id
                )
            ).subquery()

            min_probdensity = (
                sa.select(
                    sa.func.min(localizationtile_subquery.columns.probdensity)
                ).filter(
                    localizationtile_subquery.columns.cum_prob <= integrated_probability
                )
            ).scalar_subquery()

            obj_query = sa.select(Obj.id).where(
                Obj.id == obj.id,
                localizationtilescls.localization_id == localization_id,
                localizationtilescls.probdensity >= min_probdensity,
                localizationtilescls.healpix.contains(Obj.healpix),
            )
            obj_check = session.scalars(obj_query).first()
            if obj_check is not None:
                events.append(event.dateobs)

        # Record each containment as a pending association: the crossmatch
        # proposes, a human rules on it. Existing rows are left alone so a
        # decision already made is not reset to pending.
        existing = {
            row.dateobs
            for row in session.scalars(
                sa.select(GcnEventObj).where(
                    GcnEventObj.obj_id == obj.id,
                    GcnEventObj.dateobs.in_(events),
                )
            ).all()
        }
        for dateobs in events:
            if dateobs in existing:
                continue
            session.add(
                GcnEventObj(
                    obj_id=obj.id,
                    dateobs=dateobs,
                    status="pending",
                    confirmer_id=user_id,
                )
            )
        session.commit()

        flow = Flow()
        flow.push(
            "*",
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": obj.internal_key},
        )

        log(f"Generated GCN crossmatch for {obj_id}")
    except Exception as e:
        log(f"Unable to generate GCN crossmatch for {obj_id}: {e}")
    finally:
        session.close()
        Session.remove()


class DefaultGcnTagHandler(BaseHandler):
    @permissions(["Manage GCNs"])
    async def post(
        self, *, body: DefaultGcnTagPostBody = None
    ) -> DefaultGcnTagPostResponse:
        """
        ---
        summary: Create a default gcn tag
        description: Create default gcn tag.
        tags:
          - gcn event default tags
        """
        body = self.parse_body(DefaultGcnTagPostBody)

        async with self.AsyncSession() as session:
            if "default_tag_name" not in body.model_fields_set:
                return self.error("Missing default_tag_name")
            else:
                stmt = DefaultGcnTag.select(session.user_or_token).where(
                    DefaultGcnTag.default_tag_name == body.default_tag_name
                )
                existing_default_tag = await session.scalar(stmt)
                if existing_default_tag is not None:
                    return self.error(
                        f"A default tag called {body.default_tag_name} already exists. That name must be unique."
                    )

            if "filters" in body.model_fields_set:
                if not isinstance(body.filters, dict):
                    return self.error("filters must be a dictionary")
                if not set(body.filters.keys()).issubset(
                    {"gcn_tags", "notice_types", "localization_tags"}
                ):
                    return self.error(
                        'filters must be a dictionary with keys in ["gcn_tags", "notice_types", "localization_tags"]'
                    )
                for key in body.filters:
                    if not isinstance(body.filters[key], list):
                        return self.error(f"filters[{key}] must be a list")
                    if not all(isinstance(item, str) for item in body.filters[key]):
                        return self.error(f"filters[{key}] must be a list of strings")

            default_gcn_tag = DefaultGcnTag.__schema__().load(
                body.model_dump(exclude_unset=True)
            )

            session.add(default_gcn_tag)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_DEFAULT_GCN_TAGS")
            return self.success(data={"id": default_gcn_tag.id})

    @auth_or_token
    async def get(self, default_gcn_tag_id: int | None = None):
        """
        ---
        single:
          summary: Get a default gcn tag
          description: Retrieve a single default gcn tag
          tags:
            - gcn event default tags
          responses:
            200:
              content:
                application/json:
                  schema: SingleDefaultGcnTag
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all default gcn tags
          description: Retrieve all default gcn tags
          tags:
            - filters
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfDefaultGcnTags
            400:
              content:
                application/json:
                  schema: Error
        """

        async with self.AsyncSession() as session:
            if default_gcn_tag_id is not None:
                try:
                    default_gcn_tag_id_int = int(default_gcn_tag_id)
                except (ValueError, TypeError):
                    return self.error(
                        f"Invalid default_gcn_tag_id: {default_gcn_tag_id}"
                    )
                default_gcn_tag = await session.scalar(
                    DefaultGcnTag.select(
                        session.user_or_token,
                    ).where(DefaultGcnTag.id == default_gcn_tag_id_int)
                )
                if default_gcn_tag is None:
                    return self.error(
                        f"Cannot find DefaultGcnTag with ID {default_gcn_tag_id}"
                    )
                return self.success(data=default_gcn_tag)

            result = await session.scalars(
                DefaultGcnTag.select(
                    session.user_or_token,
                )
            )
            default_gcn_tags = result.unique().all()

            return self.success(data=default_gcn_tags)

    @permissions(["Manage GCNs"])
    async def delete(self, default_gcn_tag_id: int):
        """
        ---
        summary: Delete a default gcn tag
        description: Delete a default gcn tag
        tags:
          - gcn event default tags
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        try:
            default_gcn_tag_id_int = int(default_gcn_tag_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid default_gcn_tag_id: {default_gcn_tag_id}")

        async with self.AsyncSession() as session:
            stmt = DefaultGcnTag.select(session.user_or_token).where(
                DefaultGcnTag.id == default_gcn_tag_id_int
            )
            default_gcn_tag = await session.scalar(stmt)

            if default_gcn_tag is None:
                return self.error(
                    f"Default GCN tag with ID {default_gcn_tag_id} not found"
                )

            await session.delete(default_gcn_tag)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_DEFAULT_GCN_TAGS")
            return self.success()


# the following handler is used to download the content of a GCN notice, as a txt file
class GcnEventNoticeDownloadHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs: str, notice_id: int):
        """
        ---
        summary: Download a GCN notice
        description: Download a GCN notice
        tags:
          - gcn notices
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        dateobs = dateobs.strip()
        try:
            dateobs_parsed = arrow.get(dateobs).naive
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        try:
            notice_id_int = int(notice_id)
        except (ValueError, TypeError):
            return self.error(f"Invalid notice_id: {notice_id}")

        async with self.AsyncSession() as session:
            try:
                notice = await session.scalar(
                    GcnNotice.select(
                        session.user_or_token,
                        options=[undefer(GcnNotice.content)],
                    ).where(
                        GcnNotice.dateobs == dateobs_parsed,
                        GcnNotice.id == notice_id_int,
                    )
                )
                if notice is None:
                    return self.error("Notice not found", status=404)

                output_format = "txt"
                if notice.notice_format == "voevent":
                    output_format = "xml"
                elif notice.notice_format == "json":
                    output_format = "json"

                data = io.BytesIO(notice.content)
                try:
                    filename = f"{notice.ivorn.split('/')[-1]}_{notice.dateobs}.{output_format}"
                except Exception:
                    filename = f"{notice.dateobs}_{notice.id}.{output_format}"

                print(filename)

                await self.send_file(data, filename, output_type=output_format)
            except Exception as e:
                return self.error(f"Failed to create notice for download: str({e})")
