# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import ast
import asyncio
import binascii
import datetime
import io
import json
import operator  # noqa: F401
import os
import tempfile
import traceback
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload, scoped_session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
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

from ...models import (
    Allocation,
    CatalogQuery,
    DBSession,
    DefaultGcnTag,
    DefaultObservationPlanRequest,
    EventObservationPlan,
    GcnEvent,
    GcnEventUser,
    GcnNotice,
    GcnProperty,
    GcnReport,
    GcnSummary,
    GcnTag,
    GcnTrigger,
    Group,
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
    Source,
    SourcesConfirmedInGCN,
    SurveyEfficiencyForObservations,
    User,
    UserNotification,
)
from ...utils.gcn import (
    from_bytes,
    from_cone,
    from_ellipse,
    from_polygon,
    from_url,
    get_contour,
    get_dateobs,
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
from ...utils.notifications import post_notification
from ...utils.parse import get_page_and_n_per_page
from ...utils.UTCTZnaiveDateTime import UTCTZnaiveDateTime
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


def post_gcn_source(
    dateobs: str, localization_name: str, root, notice_type, user, session
):
    try:
        ra, dec, error = (float(val) for val in localization_name.split("_"))
        if error < SOURCE_RADIUS_THRESHOLD:
            log(
                f"Creating source for event {dateobs} with Localization {localization_name}."
            )
            dateobs_txt = Time(dateobs).isot
            source_name = f"{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}_{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
            source = {
                "id": source_name,
                "ra": ra,
                "dec": dec,
                "origin": None,
            }
            event_tags = []
            if isinstance(root, dict):
                event_tags = get_json_tags(root)
            else:
                event_tags = get_tags(root, notice_type)
            tags_formatted = [tag.upper().strip() for tag in event_tags]

            # set the origin
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

            # set the id/name
            if "GRB" in tags_formatted:
                source["id"] = f"GRB-{source_name}"
            elif "GW" in tags_formatted:
                source["id"] = f"GW-{source_name}"
            elif "EINSTEIN PROBE" in tags_formatted:
                source["id"] = f"EP-{source_name}"
            else:
                source["id"] = f"GCN-{source_name}"

            public_group = session.scalar(
                sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
            )
            if public_group is None:
                log(
                    f"WARNING: Public group {cfg['misc.public_group_name']} not found in the database, cannot post source"
                )
            else:
                public_group_id = public_group.id
                source["group_ids"] = [public_group_id]

                if source.get("id", None) is not None:
                    existing_source = session.scalars(
                        Source.select(user).where(Source.obj_id == source["id"])
                    ).first()
                    if existing_source is None:
                        log(
                            f"Posting source for event {dateobs} with Localization {localization_name} with id {source['id']}."
                        )
                        if source["origin"] is None:
                            del source["origin"]
                        post_source(source, user.id, session)
                        return True
        else:
            log(
                f"Source radius {error:.4f} is larger than threshold {SOURCE_RADIUS_THRESHOLD:.4f}, not creating source for event {dateobs} with Localization {localization_name}."
            )

    except Exception as e:
        # if it's a ValueError that contains the text "could not convert string to float", just ignore
        # as it simply means that the localization name is not a valid ra, dec, error
        if not (
            isinstance(e, ValueError) and "could not convert string to float" in str(e)
        ):
            log(traceback.format_exc())
            log(
                f"Failed to create source for event {dateobs} with Localization {localization_name}: {str(e)}."
            )
    finally:
        return False


def post_gcnevent_from_xml(
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

    user = session.query(User).get(user_id)

    schema = f"{os.path.dirname(__file__)}/../../utils/schema/VOEvent-v2.0.xsd"
    voevent_schema = xmlschema.XMLSchema(schema)
    if voevent_schema.is_valid(payload):
        # check if is string
        try:
            payload = payload.encode("ascii")
        except AttributeError:
            pass
        root = lxml.etree.fromstring(payload)
    else:
        raise ValueError("xml file is not valid VOEvent")

    gcn_notice = session.scalars(
        GcnNotice.select(user).where(GcnNotice.ivorn == root.attrib["ivorn"])
    ).first()
    if gcn_notice is not None:
        raise ValueError(f"GcnNotice with ivorn {root.attrib['ivorn']} already exists.")

    dateobs = get_dateobs(root)
    trigger_id = get_trigger(root)
    if notice_type is None:
        try:
            notice_type = str(gcn.NoticeType(int(gcn.get_notice_type(root))).name)
        except Exception:
            notice_type = get_xml_notice_type(root)

    aliases = get_notice_aliases(
        root, notice_type
    )  # we try to get the aliases from the notice if possible

    if trigger_id is not None:
        event = session.scalars(
            GcnEvent.select(user).where(GcnEvent.trigger_id == trigger_id)
        ).first()
    else:
        event = session.scalars(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        ).first()

    if event is None:
        event = GcnEvent(
            dateobs=dateobs,
            sent_by_id=user_id,
            trigger_id=trigger_id,
            aliases=aliases,
        )
        session.add(event)
        session.commit()
        dateobs = event.dateobs
    else:
        dateobs = event.dateobs
        # we grab the dateobs from the event to overwrite the dateobs from the gcn notice
        # this is important because unfortunately the dateobs in a gcn notice is not always the same as the dateobs in the event
        # what matters is the trigger id if it exists, that allows us to find the actual dateobs of the event

        if not event.is_accessible_by(user, mode="update"):
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
    session.commit()
    notice_id = gcn_notice.id

    properties_dict, tags_list = get_properties(root)
    properties = GcnProperty(dateobs=dateobs, sent_by_id=user_id, data=properties_dict)
    session.add(properties)
    session.commit()

    tags_text = list(get_tags(root, notice_type)) + tags_list
    tags = [
        GcnTag(
            dateobs=dateobs,
            text=text,
            sent_by_id=user_id,
        )
        for text in tags_text
    ]
    session.add_all(tags)
    session.commit()

    mma_detectors = session.scalars(
        MMADetector.select(user).where(MMADetector.nickname.in_(tags_text))
    ).all()
    if len(mma_detectors) > 0:
        event_to_update = session.scalars(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        ).first()
        event_to_update.mma_detectors = mma_detectors
        session.commit()

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
            post_skymap_from_notice(
                dateobs, notice_id, user_id, session, asynchronous, notify
            )
            found_skymap = True
        except Exception:
            found_skymap = False

    if not found_skymap and notify:
        # if there is no skymap, we still want to add the default tags that might not need localization tags
        gcn_tags = add_default_gcn_tags(user, session, dateobs=dateobs)
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


def post_skymap_from_notice(
    dateobs, notice_id, user_id, session, asynchronous=True, notify=True
):
    """Post skymap to database from gcn notice."""
    user = session.query(User).get(user_id)

    gcn_notice = session.scalars(
        GcnNotice.select(user).where(GcnNotice.id == notice_id)
    ).first()

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
    localization = session.scalars(
        Localization.select(user).where(
            Localization.dateobs == skymap["dateobs"],
            Localization.localization_name == skymap["localization_name"],
        )
    ).first()
    if localization is None:
        localization = Localization(**skymap, notice_id=notice_id)
        session.add(localization)
        session.commit()
        localization_id = localization.id

        log(f"Generating tiles/properties/contours for localization {localization.id}")
        if asynchronous:
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
                    url=url,
                    notify=notify,
                    properties=properties,
                    tags=tags,
                ),
            )
        else:
            add_tiles_properties_contour_and_obsplan(
                localization_id,
                user_id,
                session,
                url=url,
                notify=notify,
                properties=properties,
                tags=tags,
            )

        gcn_notice.localization_ingested = True
        session.add(gcn_notice)
        session.commit()

        post_gcn_source(
            dateobs, skymap["localization_name"], root, notice_type, user, session
        )

    else:
        localization_id = localization.id
        log(f"Localization {localization_id} already exists.")

    return localization_id


def post_gcnevent_from_json(
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

    # if payload is a string try to json.load it
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

    user = session.query(User).get(user_id)

    dateobs = Time(payload["trigger_time"], format="isot", precision=0)
    # FIXME: https://github.com/astropy/astropy/issues/7179
    dateobs = Time(dateobs.iso).datetime

    event = None
    ref_ID = payload.get("ref_ID", None)
    if ref_ID is not None:
        event = session.scalars(
            GcnEvent.select(user).where(
                sa.func.lower(cast(GcnEvent.aliases, sa.String)).like(
                    f"%{ref_ID.lower()}%"
                )
            )
        ).first()

    if event is None:
        event = session.scalars(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        ).first()

    if event is None:
        event = GcnEvent(
            dateobs=dateobs,
            sent_by_id=user.id,
        )
        session.add(event)
        session.commit()

        dateobs = event.dateobs
    else:
        dateobs = event.dateobs
        # we grab the dateobs from the event to overwrite the dateobs from the gcn notice
        # this is important because unfortunately the dateobs in a gcn notice is not always the same as the dateobs in the event
        # what matters is the trigger id if it exists, that allows us to find the actual dateobs of the event
        if not event.is_accessible_by(user, mode="update"):
            raise ValueError(
                "Insufficient permissions: GCN event can only be updated by original poster"
            )

    event_id = event.id

    tags = get_json_tags(payload)

    tags = [
        GcnTag(
            dateobs=event.dateobs,
            text=text,
            sent_by_id=user.id,
        )
        for text in tags
    ]

    detectors = []
    for tag in tags:
        session.add(tag)

        mma_detector = session.scalars(
            MMADetector.select(user).where(MMADetector.nickname == tag.text)
        ).first()
        if mma_detector is not None:
            detectors.append(mma_detector)
    event.detectors = detectors
    session.commit()

    date = dateobs
    if "alert_datetime" in payload:
        date = Time(payload["alert_datetime"], format="isot", precision=0)
        # FIXME: https://github.com/astropy/astropy/issues/7179
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
    session.commit()
    notice_id = gcn_notice.id

    found_skymap = False
    if post_skymap:
        try:
            post_skymap_from_notice(
                dateobs, notice_id, user_id, session, asynchronous, notify
            )
            found_skymap = True
        except Exception:
            found_skymap = False

    if not found_skymap and notify:
        # if there is no skymap, we still want to add the default tags that might not need localization tags
        gcn_tags = add_default_gcn_tags(user, session, dateobs=dateobs)
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


def post_gcnevent_from_dictionary(payload, user_id, session, asynchronous=True):
    """Post GcnEvent to database from dictionary.
    payload: dict
        Dictionary containing dateobs and skymap
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.query(User).get(user_id)

    dateobs = arrow.get(payload["dateobs"]).datetime

    event = session.scalars(
        GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
    ).first()

    if event is None:
        event = GcnEvent(dateobs=dateobs, sent_by_id=user.id)
        session.add(event)
    else:
        if not event.is_accessible_by(user, mode="update"):
            raise ValueError(
                "Insufficient permissions: GCN event can only be updated by original poster"
            )

    if "properties" in payload:
        properties = GcnProperty(
            dateobs=event.dateobs, sent_by_id=user.id, data=payload["properties"]
        )
        session.add(properties)

    tags = [
        GcnTag(
            dateobs=event.dateobs,
            text=text,
            sent_by_id=user.id,
        )
        for text in payload.get("tags", [])
    ]

    detectors = []
    for tag in tags:
        session.add(tag)

        mma_detector = session.scalars(
            MMADetector.select(user).where(MMADetector.nickname == tag.text)
        ).first()
        if mma_detector is not None:
            detectors.append(mma_detector)
    event.detectors = detectors
    session.commit()

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

    post_gcn_source(
        event.dateobs, skymap["localization_name"], payload, None, user, session
    )

    localization = session.scalars(
        Localization.select(user).where(
            Localization.dateobs == dateobs,
            Localization.localization_name == skymap["localization_name"],
        )
    ).first()
    if localization is None:
        localization = Localization(**skymap)
        session.add(localization)
        session.commit()
        localization_id = localization.id

        log(f"Generating tiles/properties/contours for localization {localization_id}")
        if asynchronous:
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
        else:
            add_tiles_properties_contour_and_obsplan(
                localization_id,
                user_id,
                session,
                properties=localization_properties,
                tags=localization_tags,
            )

    return dateobs, event.id


class GcnEventAliasesHandler(BaseHandler):
    @auth_or_token
    def post(self, dateobs):
        """
        ---
        summary: Post a GCN Event alias
        description: Post a GCN Event alias
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
            description: The dateobs of the event, as an arrow parseable string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  alias:
                    type: string
                    description: Alias to add to the event
                required:
                  - alias
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
        data = self.get_json()
        alias = data.get("alias", None)

        if alias is None:
            return self.error("alias must be present in data")
        if type(alias) is not str:
            return self.error("alias must be a string")

        with self.Session() as session:
            try:
                event = session.scalars(
                    GcnEvent.select(
                        session.user_or_token,
                        mode="update",
                    ).where(GcnEvent.dateobs == dateobs)
                ).first()
                if event is None:
                    return self.error("GCN event not found", status=404)

                if event.aliases is None:
                    event.aliases = [alias]
                elif alias not in event.aliases:
                    event.aliases = list(set(event.aliases + [alias]))
                else:
                    return self.error(f"{alias} already in {dateobs} aliases.")
                session.commit()

                self.push(
                    action="skyportal/REFRESH_GCN_EVENT",
                    payload={"gcnEvent_dateobs": dateobs},
                )
            except Exception as e:
                return self.error(f"Cannot post alias: {str(e)}")

            return self.success()

    @auth_or_token
    def delete(self, dateobs):
        """
        ---
        summary: Delete a GCN Event alias
        description: Delete a GCN event alias
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: dateobs
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  alias:
                    type: string
                    description: Alias to remove from the event
                required:
                  - alias
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

        data = self.get_json()
        alias = data.get("alias")

        if alias is None:
            return self.error("alias must be present in data to remove")

        forbidden_substrings = ["LVC#", "FERMI#"]
        for forbidden_substring in forbidden_substrings:
            if forbidden_substring in alias:
                return self.error(
                    f"Cannot delete alias with substring {forbidden_substring}"
                )

        with self.Session() as session:
            try:
                event = session.scalars(
                    GcnEvent.select(
                        session.user_or_token,
                        mode="update",
                    ).where(GcnEvent.dateobs == dateobs)
                ).first()
                if event is None:
                    return self.error("GCN event not found", status=404)

                if alias in event.aliases:
                    aliases = event.aliases
                    aliases.remove(alias)
                    setattr(event, "aliases", aliases)
                    flag_modified(event, "aliases")
                else:
                    return self.error(f"{alias} not in {dateobs} aliases.")
                session.commit()

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
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            tags = session.scalars(sa.select(GcnTag.text).distinct()).unique().all()
            return self.success(data=tags)

    @auth_or_token
    def post(self, dateobs=None, tag=None):
        """
        ---
        summary: Post a GCN Event tag
        description: Post a GCN Event tag
        tags:
          - gcn event tags
        requestBody:
          content:
            application/json:
              schema: GcnEventTagPost
        responses:
          200:
            content:
              application/json:
                schema: Success
                properties:
                  data:
                    type: object
                    properties:
                      gcnevent_id:
                        type: integer
                        description: New GcnEvent Tag ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        dateobs = data.get("dateobs", None)
        text = data.get("text", None)

        if dateobs is None:
            return self.error("dateobs must be present in data to add GcnTag")
        if text is None:
            return self.error("text must be present in data to add GcnTag")

        with self.Session() as session:
            try:
                tag = GcnTag(
                    dateobs=dateobs,
                    text=text,
                    sent_by_id=self.associated_user_object.id,
                )
                session.add(tag)
                session.commit()

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
    def delete(self, dateobs):
        """
        ---
        summary: Delete a GCN Event tag
        description: Delete a GCN event tag
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: dateobs
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

        data = self.get_json()
        tag = data.get("tag")
        if tag is None:
            return self.error("tag must be present in data to remove GcnTag")

        with self.Session() as session:
            tag = session.scalars(
                GcnTag.select(session.user_or_token, mode="delete").where(
                    GcnTag.dateobs == dateobs,
                    GcnTag.text == tag,
                )
            ).first()
            if tag is None:
                return self.error("GCN event tag not found", status=404)

            session.delete(tag)
            session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

            return self.success()


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
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            properties = (
                session.scalars(
                    sa.select(sa.func.jsonb_object_keys(GcnProperty.data)).distinct()
                )
                .unique()
                .all()
            )
            return self.success(data=sorted(properties))


class GcnEventSurveyEfficiencyHandler(BaseHandler):
    @auth_or_token
    async def get(self, gcnevent_id):
        """
        ---
        summary: Get an event's survey efficiencies
        description: Get survey efficiency analyses of the GcnEvent.
        tags:
          - gcn events
        parameters:
          - in: path
            name: gcnevent_id
            required: true
            schema:
              type: string
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

        with self.Session() as session:
            event = session.scalars(
                GcnEvent.select(
                    session.user_or_token,
                    options=[joinedload(GcnEvent.survey_efficiency_analyses)],
                ).where(GcnEvent.id == gcnevent_id)
            ).first()
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
    async def get(self, gcnevent_id):
        """
        ---
        summary: Get an event's observation plan requests.
        description: Get observation plan requests of the GcnEvent.
        tags:
          - gcn events
        parameters:
          - in: path
            name: gcnevent_id
            required: true
            schema:
              type: integer
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

        with self.Session() as session:
            event = session.scalars(
                GcnEvent.select(
                    session.user_or_token,
                    options=[
                        joinedload(GcnEvent.observationplan_requests)
                        .joinedload(ObservationPlanRequest.allocation)
                        .joinedload(Allocation.instrument),
                        joinedload(GcnEvent.observationplan_requests)
                        .joinedload(ObservationPlanRequest.allocation)
                        .joinedload(Allocation.group),
                        joinedload(GcnEvent.observationplan_requests).joinedload(
                            ObservationPlanRequest.requester
                        ),
                        joinedload(GcnEvent.observationplan_requests)
                        .joinedload(ObservationPlanRequest.observation_plans)
                        .joinedload(EventObservationPlan.statistics),
                    ],
                ).where(GcnEvent.id == gcnevent_id)
            ).first()

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
    async def get(self, gcnevent_id):
        """
        ---
        summary: Get an event's catalog queries.
        description: Get catalog queries of the GcnEvent.
        tags:
          - gcn events
        parameters:
          - in: path
            name: gcnevent_id
            required: true
            schema:
              type: string
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

        with self.Session() as session:
            queries = session.scalars(
                CatalogQuery.select(
                    session.user_or_token,
                ).where(
                    cast(CatalogQuery.payload["gcnevent_id"].astext, sa.Integer)
                    == gcnevent_id
                )
            ).all()

            return self.success(data=queries)


class GcnEventHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        summary: Post a GCN Event from xml/json/dictionary
        description: Ingest a GCN Event from xml/json/dictionary
        tags:
          - gcn events
          - localizations
        requestBody:
          content:
            application/json:
              schema: GcnHandlerPut
        responses:
          200:
            content:
              application/json:
                schema: Success
                properties:
                  data:
                    type: object
                    properties:
                      gcnevent_id:
                        type: integer
                        description: New GcnEvent ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        # if an xml or json notice is not provided, then a dateobs must be specified
        if not any(format in data for format in ["xml", "json"]):
            required_keys = {"dateobs"}
            if not required_keys.issubset(set(data.keys())):
                return self.error(
                    "Either xml, json or dateobs must be present in data to parse a GcnEvent"
                )

        event_id, dateobs, notice_id = None, None, None
        with self.Session() as session:
            try:
                if "xml" in data:
                    dateobs, event_id, notice_id = post_gcnevent_from_xml(
                        data["xml"], self.associated_user_object.id, session
                    )
                elif "json" in data:
                    dateobs, event_id, notice_id = post_gcnevent_from_json(
                        data["json"], self.associated_user_object.id, session
                    )
                else:
                    dateobs, event_id = post_gcnevent_from_dictionary(
                        data, self.associated_user_object.id, session
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
    async def get(self, dateobs=None):
        f"""
        ---
        single:
          summary: Get a GCN Event
          description: Retrieve a GCN event
          tags:
            - gcn events
          parameters:
            - in: path
              name: dateobs
              required: false
              schema:
                type: string
        multiple:
          summary: Get multiple GCN Events
          description: Retrieve multiple GCN events
          tags:
            - gcn events
          parameters:
            - in: query
              name: startDate
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
                dateobs >= startDate
            - in: query
              name: endDate
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
                dateobs <= endDate
            - in: query
              name: gcnTagKeep
              nullable: true
              schema:
                type: string
              description: |
                Comma-separated string of `GcnTag`s. Returns events that match any of them.
            - in: query
              name: gcnTagRemove
              nullable: true
              schema:
                type: string
              description: |
                Comma-separated string of `GcnTag`s. Returns events that do not have any of these tags.
            - in: query
              name: localizationTagKeep
              nullable: true
              schema:
                type: string
              description: |
                Comma-separated string of `LocalizationTag`s. Returns events that match any of them.
            - in: query
              name: localizationTagRemove
              nullable: true
              schema:
                type: string
              description: |
                Comma-separated string of `LocalizationTag`s. Returns events that do not have any of these tags.
            - in: query
              name: gcnPropertiesFilter
              nullable: true
              schema:
                type: array
                items:
                  type: string
              explode: false
              style: simple
              description: |
                Comma-separated string of "property: value: operator" single(s) or triplet(s) to filter for events matching
                that/those property(ies), i.e. "BNS" or "BNS: 0.5: lt"
            - in: query
              name: localizationPropertiesFilter
              nullable: true
              schema:
                type: array
                items:
                  type: string
              explode: false
              style: simple
              description: |
                Comma-separated string of "property: value: operator" single(s) or triplet(s) to filter for event localizations matching
                that/those property(ies), i.e. "area_90" or "area_90: 500: lt"
            - in: query
              name: numPerPage
              nullable: true
              schema:
                type: integer
              description: |
                Number of GCN events to return per paginated request.
                Defaults to 10. Can be no larger than {MAX_GCNEVENTS}.
            - in: query
              name: pageNumber
              nullable: true
              schema:
                type: integer
              description: Page number for paginated query results. Defaults to 1.
            - in: query
              name: excludeNoticeContent
              nullable: true
              schema:
                type: boolean
              description: |
                If true, do not include the notice content in the response.
                Defaults to false.
        responses:
          200:
            content:
              application/json:
                schema: GcnEventHandlerGet
          400:
            content:
              application/json:
                schema: Error
        """

        partialdateobs = self.get_query_argument("partialdateobs", None)

        if dateobs is not None and partialdateobs is not None:
            return self.error(
                "Cannot specify both dateobs and partialdateobs query parameters"
            )

        page_number = self.get_query_argument("pageNumber", 1)
        n_per_page = self.get_query_argument("numPerPage", 10)
        page_number, n_per_page = get_page_and_n_per_page(
            page_number, n_per_page, MAX_GCNEVENTS
        )

        sort_by = self.get_query_argument("sortBy", None)
        sort_order = self.get_query_argument("sortOrder", "asc")
        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        gcn_tag_keep = self.get_query_argument("gcnTagKeep", None)
        gcn_tag_remove = self.get_query_argument("gcnTagRemove", None)
        localization_tag_keep = self.get_query_argument("localizationTagKeep", None)
        localization_tag_remove = self.get_query_argument("localizationTagRemove", None)
        gcn_properties_filter = self.get_query_argument("gcnPropertiesFilter", None)
        no_notice_content = self.get_query_argument("excludeNoticeContent", False)

        if gcn_tag_keep is not None:
            if isinstance(gcn_tag_keep, str):
                gcn_tag_keep = [c.strip() for c in gcn_tag_keep.split(",")]
            else:
                return self.error(
                    "Invalid gcnTagKeep value -- must provide at least one string value"
                )

        if gcn_tag_remove is not None:
            if isinstance(gcn_tag_remove, str):
                gcn_tag_remove = [c.strip() for c in gcn_tag_remove.split(",")]
            else:
                return self.error(
                    "Invalid gcnTagRemove value -- must provide at least one string value"
                )

        if localization_tag_keep is not None:
            if isinstance(localization_tag_keep, str):
                localization_tag_keep = [
                    c.strip() for c in localization_tag_keep.split(",")
                ]
            else:
                return self.error(
                    "Invalid localizationTagKeep value -- must provide at least one string value"
                )

        if localization_tag_remove is not None:
            if isinstance(localization_tag_remove, str):
                localization_tag_remove = [
                    c.strip() for c in localization_tag_remove.split(",")
                ]
            else:
                return self.error(
                    "Invalid localizationTagRemove value -- must provide at least one string value"
                )

        if gcn_properties_filter is not None:
            if isinstance(gcn_properties_filter, str):
                gcn_properties_filter = [
                    c.strip() for c in gcn_properties_filter.split(",")
                ]
            else:
                return self.error(
                    "Invalid gcnPropertiesFilter value -- must provide at least one string value"
                )

        localization_properties_filter = self.get_query_argument(
            "localizationPropertiesFilter", None
        )

        if localization_properties_filter is not None:
            if isinstance(localization_properties_filter, str):
                localization_properties_filter = [
                    c.strip() for c in localization_properties_filter.split(",")
                ]
            else:
                return self.error(
                    "Invalid localizationPropertiesFilter value -- must provide at least one string value"
                )

        if dateobs is not None:
            with self.Session() as session:
                options = [
                    joinedload(GcnEvent.localizations).joinedload(Localization.tags),
                    joinedload(GcnEvent.localizations).joinedload(
                        Localization.properties
                    ),
                    joinedload(GcnEvent.comments),
                    joinedload(GcnEvent.detectors),
                    joinedload(GcnEvent.properties),
                    joinedload(GcnEvent.summaries),
                    joinedload(GcnEvent.gcn_triggers),
                ]
                if no_notice_content:
                    options.append(joinedload(GcnEvent.gcn_notices))
                else:
                    options.append(
                        joinedload(GcnEvent.gcn_notices).undefer(GcnNotice.content)
                    )
                event = session.scalars(
                    GcnEvent.select(
                        session.user_or_token,
                        options=options,
                    ).where(GcnEvent.dateobs == dateobs)
                ).first()
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

        with self.Session() as session:
            query = GcnEvent.select(
                session.user_or_token,
                options=[
                    joinedload(GcnEvent.localizations),
                    joinedload(GcnEvent.gcn_notices),
                    joinedload(GcnEvent.observationplan_requests),
                    joinedload(GcnEvent.gcn_triggers),
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
                query = query.where(
                    cast(GcnEvent.dateobs, sa.String).like(f"{partialdateobs}%")
                    | sa.func.lower(cast(GcnEvent.aliases, sa.String)).like(
                        f"%{partialdateobs}%"
                    )
                )
            if start_date:
                start_date = arrow.get(start_date.strip()).datetime
                query = query.where(GcnEvent.dateobs >= start_date)
            if end_date:
                end_date = arrow.get(end_date.strip()).datetime
                query = query.where(GcnEvent.dateobs <= end_date)
            if gcn_tag_keep:
                gcn_tag_subquery = (
                    GcnTag.select(session.user_or_token)
                    .where(GcnTag.text.in_(gcn_tag_keep))
                    .subquery()
                )
                query = query.join(
                    gcn_tag_subquery, GcnEvent.dateobs == gcn_tag_subquery.c.dateobs
                )
            if gcn_tag_remove:
                gcn_tag_subquery = (
                    GcnTag.select(session.user_or_token)
                    .where(GcnTag.text.in_(gcn_tag_remove))
                    .subquery()
                )
                gcn_dateobs_query = GcnEvent.select(
                    session.user_or_token, columns=[GcnEvent.dateobs]
                ).where(GcnEvent.dateobs == gcn_tag_subquery.c.dateobs)
                gcn_dateobs_subquery = gcn_dateobs_query.subquery()

                query = query.where(GcnEvent.dateobs.notin_(gcn_dateobs_subquery))
            if localization_tag_keep:
                tag_subquery = (
                    LocalizationTag.select(session.user_or_token)
                    .where(LocalizationTag.text.in_(localization_tag_keep))
                    .subquery()
                )
                localization_id_query = (
                    Localization.select(
                        session.user_or_token, columns=[Localization.dateobs]
                    )
                    .where(Localization.id == tag_subquery.c.localization_id)
                    .subquery()
                )
                query = query.where(GcnEvent.dateobs.in_(localization_id_query))
            if localization_tag_remove:
                tag_subquery = (
                    LocalizationTag.select(session.user_or_token)
                    .where(LocalizationTag.text.in_(localization_tag_remove))
                    .subquery()
                )
                localization_id_query = (
                    Localization.select(
                        session.user_or_token, columns=[Localization.dateobs]
                    )
                    .where(Localization.id == tag_subquery.c.localization_id)
                    .subquery()
                )
                query = query.where(GcnEvent.dateobs.notin_(localization_id_query))
            if gcn_properties_filter is not None:
                for prop_filt in gcn_properties_filter:
                    prop_split = prop_filt.split(":")
                    if not (len(prop_split) == 1 or len(prop_split) == 3):
                        return self.error(
                            "Invalid gcnPropertiesFilter value -- property filter must have 1 or 3 values"
                        )
                    name = prop_split[0].strip()

                    properties_query = GcnProperty.select(session.user_or_token)
                    if len(prop_split) == 3:
                        value = prop_split[1].strip()
                        try:
                            value = float(value)
                        except ValueError as e:
                            return self.error(
                                f"Invalid GCN properties filter value: {e}"
                            )
                        op = prop_split[2].strip()
                        op_options = ["lt", "le", "eq", "ne", "ge", "gt"]
                        if op not in op_options:
                            return self.error(f"Invalid operator: {op}")
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
                        return self.error(
                            "Invalid localizationPropertiesFilter value -- property filter must have 1 or 3 values"
                        )
                    name = prop_split[0].strip()

                    properties_query = LocalizationProperty.select(
                        session.user_or_token
                    )
                    if len(prop_split) == 3:
                        value = prop_split[1].strip()
                        try:
                            value = float(value)
                        except ValueError as e:
                            return self.error(
                                f"Invalid localization properties filter value: {e}"
                            )
                        op = prop_split[2].strip()
                        op_options = ["lt", "le", "eq", "ne", "ge", "gt"]
                        if op not in op_options:
                            return self.error(f"Invalid operator: {op}")
                        comp_function = getattr(operator, op)

                        properties_query = properties_query.where(
                            comp_function(
                                LocalizationProperty.data[name], cast(value, JSONB)
                            )
                        )
                    else:
                        properties_query = properties_query.where(
                            LocalizationProperty.data[name].astext.is_not(None)
                        )

                    properties_subquery = properties_query.subquery()
                    localizations_query = Localization.select(session.user_or_token)
                    localizations_query = localizations_query.join(
                        properties_subquery,
                        Localization.id == properties_subquery.c.localization_id,
                    )
                    localizations_subquery = localizations_query.subquery()

                    query = query.join(
                        localizations_subquery,
                        GcnEvent.dateobs == localizations_subquery.c.dateobs,
                    )

            total_matches = session.scalar(
                sa.select(sa.func.count()).select_from(query.distinct())
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

            query = query.order_by(*order_by)

            if n_per_page is not None:
                query = (
                    query.distinct()
                    .limit(n_per_page)
                    .offset((page_number - 1) * n_per_page)
                )

            events = []
            for event in session.scalars(query).unique().all():
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

    @permissions(["System admin"])
    def delete(self, dateobs):
        """
        ---
        summary: Delete a GCN Event
        description: Delete a GCN event
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: dateobs
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
        with self.Session() as session:
            try:
                event = session.scalars(
                    GcnEvent.select(session.user_or_token, mode="delete").where(
                        GcnEvent.dateobs == dateobs
                    )
                ).first()
                if event is None:
                    return self.error("GCN event not found", status=404)

                # get all of the skymaps on that event
                localizations = session.scalars(
                    Localization.select(session.user_or_token, mode="delete").where(
                        Localization.dateobs == dateobs
                    )
                ).all()
                for localization in localizations:
                    session.delete(localization)
                session.commit()

                # get all of the notices of the event, and delete them
                notices = session.scalars(
                    GcnNotice.select(session.user_or_token, mode="delete").where(
                        GcnNotice.dateobs == dateobs
                    )
                ).all()
                for notice in notices:
                    session.delete(notice)

                # delete all GCN tags
                tags = session.scalars(
                    GcnTag.select(session.user_or_token, mode="delete").where(
                        GcnTag.dateobs == dateobs
                    )
                ).all()
                for tag in tags:
                    session.delete(tag)
                session.commit()

                session.delete(event)
                session.commit()

                return self.success()
            except Exception as e:
                session.rollback()
                return self.error(f"Cannot delete event: {e}")


class GcnEventUserHandler(BaseHandler):
    @auth_or_token
    def post(self, dateobs, *ignored_args):
        """
        ---
        summary: Add a user as GCN event advocate
        description: Add a event user
        tags:
          - gcn events
          - users
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  userID:
                    type: integer
                required:
                  - userID
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()

        user_id = data.get("userID", None)
        if user_id is None:
            return self.error("userID parameter must be specified")
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return self.error("Invalid userID parameter: unable to parse to integer")

        with self.Session() as session:
            event = session.scalar(
                GcnEvent.select(
                    session.user_or_token,
                    options=[joinedload(GcnEvent.gcnevent_users)],
                ).where(GcnEvent.dateobs == dateobs)
            )

            user = session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )

            gu = session.scalar(
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
                    user=user,
                    text=f"You've been added as an advocate to event *{event.dateobs}*",
                    url=f"/gcn_events/{event.dateobs}",
                )
            )
            session.commit()
            self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

            self.push_all(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": event.dateobs},
            )

            return self.success()

    @auth_or_token
    def delete(self, dateobs, user_id):
        """
        ---
        summary: Remove a GCN event advocate
        description: Delete an event user
        tags:
          - shifts
          - users
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
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

        with self.Session() as session:
            event = session.scalar(
                GcnEvent.select(
                    session.user_or_token,
                    options=[joinedload(GcnEvent.gcnevent_users)],
                ).where(GcnEvent.dateobs == dateobs)
            )

            gu = session.scalar(
                GcnEventUser.select(session.user_or_token, mode="delete")
                .where(GcnEventUser.gcnevent_id == event.id)
                .where(GcnEventUser.user_id == user_id)
            )
            if gu is None:
                return self.error(
                    "GcnEventUser does not exist, or you don't have the right to delete them.",
                    status=403,
                )

            session.delete(gu)
            session.commit()

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
                        for notice_type in filters["notice_type"]
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
            except Exception:
                pass

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
                "requester_id": user.id
                if plan.requester_id is None
                else plan.requester_id,
            }
            gcn_observation_plans.append(gcn_observation_plan)

        start_date = str(datetime.datetime.utcnow()).replace("T", "")

        for ii, gcn_observation_plan in enumerate(gcn_observation_plans):
            allocation_id = gcn_observation_plan["allocation_id"]
            allocation = session.scalars(
                Allocation.select(user).where(Allocation.id == allocation_id)
            ).first()
            if allocation is None:
                continue

            end_date = allocation.instrument.telescope.next_sunrise()
            if end_date is None:
                end_date = str(
                    datetime.datetime.utcnow() + datetime.timedelta(days=1)
                ).replace("T", "")
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


class LocalizationHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs, localization_name):
        """
        ---
        summary: Get a GCN localization
        description: Retrieve a GCN localization
        tags:
          - localizations
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: dateobs
          - in: path
            name: localization_name
            required: true
            schema:
              type: localization_name
          - in: query
            name: include2DMap
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include flatted skymap. Defaults to
              false.

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

        include_2D_map = self.get_query_argument("include2DMap", False)

        with self.Session() as session:
            localization = session.scalars(
                Localization.select(session.user_or_token).where(
                    Localization.dateobs == dateobs,
                    Localization.localization_name == localization_name,
                )
            ).first()
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
    def delete(self, dateobs, localization_name):
        """
        ---
        summary: Delete a GCN localization
        description: Delete a GCN localization
        tags:
          - localizations
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: localization_name
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

        with self.Session() as session:
            localization = session.scalars(
                Localization.select(session.user_or_token, mode="delete").where(
                    Localization.dateobs == dateobs,
                    Localization.localization_name == localization_name,
                )
            ).first()

            if localization is None:
                return self.error("Localization not found", status=404)

            dateobs = localization.dateobs

            session.delete(localization)
            session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

            return self.success()


class LocalizationNoticeHandler(BaseHandler):
    @auth_or_token
    async def post(self, dateobs, notice_id):
        # first get the notice, if it exists
        with self.Session() as session:
            gcn_notice = session.scalars(
                GcnNotice.select(session.user_or_token).where(
                    GcnNotice.dateobs == dateobs, GcnNotice.id == notice_id
                )
            ).first()

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
                localization = session.scalars(
                    Localization.select(session.user_or_token).where(
                        Localization.dateobs == dateobs,
                        Localization.localization_name == skymap_metadata["name"],
                    )
                ).first()
                if localization is not None:
                    return self.error("Localization already exists", status=409)
                else:
                    try:
                        post_skymap_from_notice(
                            dateobs,
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
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            properties = (
                session.scalars(
                    sa.select(
                        sa.func.jsonb_object_keys(LocalizationProperty.data)
                    ).distinct()
                )
                .unique()
                .all()
            )
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

        with self.Session() as session:
            tags = (
                session.scalars(sa.select(LocalizationTag.text).distinct())
                .unique()
                .all()
            )
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
        user = session.query(User).get(user_id)
        session.user_or_token = user

        gcn_summary = session.query(GcnSummary).get(summary_id)
        group = session.query(Group).get(group_id)
        event = session.query(GcnEvent).filter(GcnEvent.dateobs == dateobs).first()
        localization = (
            session.query(Localization)
            .filter(
                Localization.dateobs == dateobs,
                Localization.localization_name == localization_name,
            )
            .first()
        )

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
                mentioned_user = session.query(User).get(mentioned_user_id)
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
            sources_text = []
            source_page_number = 1
            sources = []
            while True:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # get the sources in the event
                coroutine = get_sources(
                    user_id=user.id,
                    session=session,
                    group_ids=[group.id],
                    user_accessible_group_ids=user_accessible_group_ids,
                    first_detected_date=start_date,
                    last_detected_date=end_date,
                    localization_dateobs=dateobs,
                    localization_name=localization_name,
                    localization_cumprob=localization_cumprob,
                    number_of_detections=number_of_detections,
                    page_number=source_page_number,
                    num_per_page=MAX_SOURCES_PER_PAGE,
                )
                sources_data = loop.run_until_complete(coroutine)
                sources.extend(sources_data["sources"])
                source_page_number += 1

                if len(sources_data["sources"]) < MAX_SOURCES_PER_PAGE:
                    break
            if len(sources) > 0:
                obj_ids = [source["id"] for source in sources]
                sources_with_status = session.scalars(
                    SourcesConfirmedInGCN.select(user).where(
                        SourcesConfirmedInGCN.obj_id.in_(obj_ids),
                        SourcesConfirmedInGCN.dateobs == dateobs,
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
                        status.append(source_in_gcn.confirmed)
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
                                if source.confirmed is False
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

                sources_text.append(
                    f"\nFound **{len(sources)} {'sources' if len(sources) > 1 else 'source'}** in the event's localization, {df_rejected.shape[0]} of which {'have' if df_rejected.shape[0] > 1 else 'has'} been rejected after characterization:\n"
                ) if not no_text else None

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
                        sources_text.append(
                            f"""\nPhotometry of **{source["id"]}**:\n"""
                        ) if not no_text else None
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
                galaxies_text.append(
                    f"""\nFound **{len(galaxies)} {"galaxies" if len(galaxies) > 1 else "galaxy"}** in the event's localization:\n"""
                ) if not no_text else None
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
                    data = get_observations(
                        session,
                        start_date,
                        end_date,
                        telescope_name=instrument.telescope.name,
                        instrument_name=instrument.name,
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
                        observations_text.append(
                            f"""\n\n{instrument.telescope.name} - {instrument.name}:\n\nWe observed the localization region of {event.gcn_notices[0].stream} trigger {astropy.time.Time(event.dateobs, format="datetime").isot} UTC.  We obtained a total of **{num_observations} images covering {",".join(unique_filters)} bands for a total of {total_time} seconds. The observations covered {area:.1f} square degrees of the localization at least {nb_obs_to_word(number_of_observations)} times**, beginning at {start_observation.isot} ({humanize.naturaldelta(dt)} {before_after} the trigger time). Using the {localization_name} skymap, this corresponds to **~{int(100 * probability)}% of the probability enclosed in the localization region**.\n"""
                        ) if not no_text else None
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
            gcn_summary = session.query(GcnSummary).get(summary_id)
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
    async def post(self, dateobs, summary_id=None):
        """
        ---
          summary: Create a GCN summary
          description: Post a summary of a GCN event.
          tags:
            - gcn events
            - gcn event summaries
          parameters:
            - in: body
              name: title
              schema:
                type: string
            - in: body
              name: number
              schema:
                type: string
            - in: body
              name: subject
              schema:
                type: string
            - in: body
              name: userIds
              schema:
                type: string
              description: User ids to mention in the summary. Comma-separated.
            - in: body
              name: groupId
              required: true
              schema:
                type: string
              description: id of the group that creates the summary.
            - in: body
              name: startDate
              required: true
              schema:
                type: string
              description: Filter by start date
            - in: body
              name: endDate
              required: true
              schema:
                type: string
              description: Filter by end date
            - in: body
              name: localizationName
              schema:
                type: string
              description: Name of localization / skymap to use.
            - in: body
              name: localizationCumprob
              schema:
                type: number
              description: Cumulative probability up to which to include fields. Defaults to 0.95.
            - in: body
              name: numberDetections
              nullable: true
              schema:
                type: number
              description: Return only sources who have at least numberDetections detections. Defaults to 2.
            - in: body
              name: showSources
              required: true
              schema:
                type: bool
              description: Show sources in the summary
            - in: body
              name: showGalaxies
              required: true
              schema:
                type: bool
              description: Show galaxies in the summary
            - in: body
              name: showObservations
              required: true
              schema:
                type: bool
              description: Show observations in the summary
            - in: body
              name: noText
              schema:
                type: bool
              description: Do not include text in the summary, only tables.
            - in: body
              name: photometryInWindow
              schema:
                type: bool
              description: Limit photometry to that within startDate and endDate.
            - in: body
              name: statsMethod
              schema:
                type: string
              description: Method to use for calculating statistics. Defaults to python. Options are python and db.
            - in: body
              name: instrumentIds
              schema:
                type: string
              description: List of instrument ids to include in the summary. Defaults to all instruments if not specified.
            - in: body
              name: acknowledgements
              schema:
                type: string
              description: Acknowledgements to include in the summary.

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
                            type: string
                            description: GCN summary
            400:
              content:
                application/json:
                  schema: Error
        """

        data = self.get_json()
        title = data.get("title", None)
        number = data.get("number", None)
        subject = data.get("subject")
        user_ids = data.get("userIds", None)
        group_id = data.get("groupId", None)
        start_date = data.get("startDate", None)
        end_date = data.get("endDate", None)
        localization_name = data.get("localizationName", None)
        localization_cumprob = data.get("localizationCumprob", 0.95)
        number_of_detections = data.get("numberDetections", 2)
        number_of_observations = data.get("numberObservations", 1)
        show_sources = data.get("showSources", False)
        show_galaxies = data.get("showGalaxies", False)
        show_observations = data.get("showObservations", False)
        no_text = data.get("noText", False)
        photometry_in_window = data.get("photometryInWindow", False)
        stats_method = data.get("statsMethod", "python")
        instrument_ids = data.get("instrumentIds", None)
        acknowledgements = data.get("acknowledgements", None)

        class Validator(Schema):
            start_date = UTCTZnaiveDateTime(required=False, load_default=None)
            end_date = UTCTZnaiveDateTime(required=False, load_default=None)
            number_of_detections = Integer(
                required=False, missing=2, validate=validate.Range(min=1)
            )
            number_of_observations = Integer(
                required=False, missing=1, validate=validate.Range(min=1)
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

        with self.Session() as session:
            stmt = GcnEvent.select(session.user_or_token).where(
                GcnEvent.dateobs == dateobs
            )
            event = session.scalars(stmt).first()

            if event is None:
                return self.error("Event not found", status=404)

            stmt = Group.select(session.user_or_token).where(Group.id == group_id)
            group = session.scalars(stmt).first()
            if group is None:
                return self.error(f"Group not found with ID {group_id}")

            # verify that the user doesn't already have a summary with this title for this event
            stmt = GcnSummary.select(session.user_or_token, mode="read").where(
                GcnSummary.dateobs == dateobs,
                GcnSummary.title == title,
                GcnSummary.group_id == group_id,
                GcnSummary.sent_by_id == self.associated_user_object.id,
            )
            existing_summary = session.scalars(stmt).first()
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
            session.commit()

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
    def get(self, dateobs, summary_id):
        """
        ---
        summary: Get a GCN summary
        description: Retrieve a GCN summary
        tags:
          - gcn events
          - gcn event summaries
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: summary_id
            required: true
            schema:
              type: integer
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

        with self.Session() as session:
            stmt = GcnSummary.select(session.user_or_token, mode="read").where(
                GcnSummary.id == summary_id,
                GcnSummary.dateobs == dateobs,
            )
            summary = session.scalars(stmt).first()
            if summary is None:
                return self.error("Summary not found", status=404)

            # call the deferred text column
            summary.text

            return self.success(data=summary)

    @auth_or_token
    def patch(self, dateobs, summary_id):
        """
        summary: Update a GCN summary
        description: Update a GCN summary
        tags:
          - gcn events
          - gcn event summaries
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: summary_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  text:
                    type: string
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
        data = self.get_json()
        if data is None or data == {}:
            return self.error("No data provided")

        if summary_id is None:
            return self.error("Summary ID is required")

        try:
            summary_id = int(summary_id)
        except ValueError:
            return self.error("Invalid summary_id value.")

        with self.Session() as session:
            stmt = GcnSummary.select(session.user_or_token, mode="update").where(
                GcnSummary.id == summary_id,
                GcnSummary.dateobs == dateobs,
            )
            summary = session.scalars(stmt).first()
            if summary is None:
                return self.error("Summary not found", status=404)

            if data["body"] != {}:
                body_str = data["body"].strip('"')
                summary.text = body_str
            else:
                return self.error("body not found")

            session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

            return self.success(data=summary)

    @auth_or_token
    def delete(self, dateobs, summary_id):
        """
        ---
        summary: Delete a GCN summary
        description: Delete a GCN summary
        tags:
          - gcn events
          - gcn event summaries
        parameters:
          - in: path
            name: summary_id
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
        if summary_id is None:
            return self.error("Summary ID is required")

        with self.Session() as session:
            stmt = GcnSummary.select(session.user_or_token, mode="delete").where(
                GcnSummary.id == summary_id,
                GcnSummary.dateobs == dateobs,
            )
            summary = session.scalars(stmt).first()
            if summary is None:
                return self.error("Summary not found", status=404)

            if summary.text.strip().lower() == "pending" and datetime.datetime.now() < (
                summary.created_at + datetime.timedelta(hours=1)
            ):
                return self.error(
                    "Cannot delete a recently created summary (less than 1 hour) that is still pending"
                )

            session.delete(summary)
            session.commit()

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
        user = session.query(User).get(user_id)
        user_accessible_group_ids = [group.id for group in user.accessible_groups]
        session.user_or_token = user

        gcn_report = session.query(GcnReport).get(report_id)

        try:
            group = session.query(Group).get(group_id)
            event = session.query(GcnEvent).filter(GcnEvent.dateobs == dateobs).first()
            localization = (
                session.query(Localization)
                .filter(
                    Localization.dateobs == dateobs,
                    Localization.localization_name == localization_name,
                )
                .first()
            )
            start_date_mjd = Time(arrow.get(start_date).datetime).mjd
            end_date_mjd = Time(arrow.get(end_date).datetime).mjd

            contents = {}
            if show_sources:
                source_page_number = 1
                sources = []
                while True:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # get the sources in the event
                    coroutine = get_sources(
                        user_id=user.id,
                        session=session,
                        group_ids=[group.id],
                        user_accessible_group_ids=user_accessible_group_ids,
                        first_detected_date=start_date,
                        last_detected_date=end_date,
                        localization_dateobs=dateobs,
                        localization_name=localization_name,
                        localization_cumprob=localization_cumprob,
                        number_of_detections=number_of_detections,
                        page_number=source_page_number,
                        num_per_page=MAX_SOURCES_PER_PAGE,
                    )
                    sources_data = loop.run_until_complete(coroutine)
                    sources.extend(sources_data["sources"])
                    source_page_number += 1

                    if len(sources_data["sources"]) < MAX_SOURCES_PER_PAGE:
                        break
                if len(sources) > 0:
                    obj_ids = [source["id"] for source in sources]
                    sources_with_status = session.scalars(
                        SourcesConfirmedInGCN.select(user).where(
                            SourcesConfirmedInGCN.obj_id.in_(obj_ids),
                            SourcesConfirmedInGCN.dateobs == dateobs,
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
                        data = get_observations(
                            session,
                            start_date,
                            end_date,
                            telescope_name=instrument.telescope.name,
                            instrument_name=instrument.name,
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
                gcn_report = session.query(GcnReport).get(report_id)
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


class GcnReportHandler(BaseHandler):
    @auth_or_token
    async def post(self, dateobs, summary_id=None):
        """
        ---
          summary: Create a GCN report
          description: Post report data of a GCN event.
          tags:
            - gcn events
            - gcn event reports
          parameters:
            - in: body
              name: report_name
              schema:
                type: string
            - in: body
              name: groupId
              required: true
              schema:
                type: string
              description: id of the group that creates the summary.
            - in: body
              name: startDate
              required: true
              schema:
                type: string
              description: Filter by start date
            - in: body
              name: endDate
              required: true
              schema:
                type: string
              description: Filter by end date
            - in: body
              name: localizationName
              schema:
                type: string
              description: Name of localization / skymap to use.
            - in: body
              name: localizationCumprob
              schema:
                type: number
              description: Cumulative probability up to which to include fields. Defaults to 0.95.
            - in: body
              name: numberDetections
              nullable: true
              schema:
                type: number
              description: Return only sources who have at least numberDetections detections. Defaults to 2.
            - in: body
              name: showSources
              required: true
              schema:
                type: bool
              description: Show sources in the summary
            - in: body
              name: showObservations
              required: true
              schema:
                type: bool
              description: Show observations in the summary
            - in: body
              name: noText
              schema:
                type: bool
              description: Do not include text in the summary, only tables.
            - in: body
              name: photometryInWindow
              schema:
                type: bool
              description: Limit photometry to that within startDate and endDate.
            - in: body
              name: statsMethod
              schema:
                type: string
              description: Method to use for calculating statistics. Defaults to python. Options are python and db.
            - in: body
              name: instrumentIds
              schema:
                type: string
              description: List of instrument ids to include in the summary. Defaults to all instruments if not specified.

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
                            type: string
                            description: GCN summary
            400:
              content:
                application/json:
                  schema: Error
        """

        data = self.get_json()
        report_name = data.get("reportName", None)
        group_id = data.get("groupId", None)
        start_date = data.get("startDate", None)
        end_date = data.get("endDate", None)
        localization_name = data.get("localizationName", None)
        localization_cumprob = data.get("localizationCumprob", 0.95)
        number_of_detections = data.get("numberDetections", 2)
        show_sources = data.get("showSources", False)
        show_observations = data.get("showObservations", False)
        show_survey_efficiencies = data.get("showSurveyEfficiencies", False)
        photometry_in_window = data.get("photometryInWindow", False)
        stats_method = data.get("statsMethod", "python")
        instrument_ids = data.get("instrumentIds", None)

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

        with self.Session() as session:
            stmt = GcnEvent.select(session.user_or_token).where(
                GcnEvent.dateobs == dateobs
            )
            event = session.scalars(stmt).first()

            if event is None:
                return self.error("Event not found", status=404)

            stmt = Group.select(session.user_or_token).where(Group.id == group_id)
            group = session.scalars(stmt).first()
            if group is None:
                return self.error(f"Group not found with ID {group_id}")

            # verify that the user doesn't already have a summary with this title for this event
            stmt = GcnReport.select(session.user_or_token, mode="read").where(
                GcnReport.dateobs == dateobs,
                GcnReport.report_name == report_name,
                GcnReport.group_id == group_id,
                GcnReport.sent_by_id == self.associated_user_object.id,
            )
            existing_report = session.scalars(stmt).first()
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
            session.commit()

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
                return self.success({"id": summary_id})
            except Exception as e:
                return self.error(f"Error generating report: {e}")

    @auth_or_token
    def get(self, dateobs, report_id=None):
        """
        ---
        summary: Get a GCN report
        description: Retrieve a GCN report
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: summary_id
            required: true
            schema:
              type: integer
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
        if report_id is None:
            with self.Session() as session:
                stmt = GcnReport.select(session.user_or_token, mode="read").where(
                    GcnReport.dateobs == dateobs
                )
                reports = session.scalars(stmt).all()
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

        with self.Session() as session:
            stmt = GcnReport.select(session.user_or_token, mode="read").where(
                GcnReport.id == report_id,
                GcnReport.dateobs == dateobs,
            )
            report = session.scalars(stmt).first()
            if report is None:
                return self.error("Report not found", status=404)

            report.data  # get the data column (deferred)
            return self.success(data=report)

    @auth_or_token
    async def patch(self, dateobs, report_id):
        """
        summary: Update a GCN report
        description: Update a GCN report
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: report_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: object
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
        data = self.get_json()
        if data is None or data == {}:
            return self.error("No data provided")

        if report_id is None:
            return self.error("Report ID is required")

        with self.Session() as session:
            stmt = GcnReport.select(session.user_or_token, mode="update").where(
                GcnReport.id == report_id,
                GcnReport.dateobs == dateobs,
            )
            report = session.scalars(stmt).first()
            if report is None:
                return self.error("Report not found", status=404)

            report_id = report.id

            if "data" in data:
                if data["data"] != {}:
                    new_data = data["data"]
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
                                photometry = session.scalars(stmt).all()
                                if len(photometry) > 0:
                                    source["photometry"] = [
                                        serialize(phot, "ab", "mag")
                                        for phot in photometry
                                    ]
                                else:
                                    source["photometry"] = []

                                source["source_in_gcn"] = session.scalar(
                                    SourcesConfirmedInGCN.select(
                                        session.user_or_token
                                    ).where(
                                        SourcesConfirmedInGCN.obj_id == source_id,
                                        SourcesConfirmedInGCN.dateobs == dateobs,
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

            if data.get("published", None) is not None and isinstance(
                data.get("published", None), bool
            ):
                publish = data["published"]
                if publish:
                    report.publish()
                else:
                    report.unpublish()
            else:
                report.generate_report()

            session.commit()

            self.push_all(
                action="skyportal/REFRESH_GCNEVENT_REPORT",
                payload={"report_id": report_id},
            )

            return self.success(data=report)

    @auth_or_token
    def delete(self, dateobs, report_id):
        """
        ---
        summary: Delete a GCN report
        description: Delete a GCN report
        tags:
          - gcn events
        parameters:
          - in: path
            name: report_id
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
        if report_id is None:
            return self.error("Report ID is required")

        with self.Session() as session:
            stmt = GcnReport.select(session.user_or_token, mode="delete").where(
                GcnReport.id == report_id,
                GcnReport.dateobs == dateobs,
            )
            report = session.scalars(stmt).first()
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

            session.delete(report)
            session.commit()

            self.push(
                action="skyportal/REFRESH_GCN_EVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

        return self.success()


class LocalizationDownloadHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs, localization_name):
        """
        ---
        summary: Download a localization's skymap
        description: Download a GCN localization skymap
        tags:
          - localizations
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: localization_name
            required: true
            schema:
              type: string
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
            arrow.get(dateobs)
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        localization_name = localization_name.strip()
        local_temp_files = []

        with self.Session() as session:
            try:
                localization = session.scalars(
                    Localization.select(session.user_or_token).where(
                        Localization.dateobs == dateobs,
                        Localization.localization_name == localization_name,
                    )
                ).first()
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


class LocalizationCrossmatchHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: Crossmatch two localizations
        description: A fits file corresponding to the intersection of the input fits files.
        tags:
          - localizations
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: dateobs
          - in: path
            name: localization_name
            required: true
            schema:
              type: localization_name
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
        id1 = self.get_query_argument("id1", None)
        id2 = self.get_query_argument("id2", None)
        if id1 is None or id2 is None:
            return self.error("Please provide two localization id")

        id1 = id1.strip()
        id2 = id2.strip()
        local_temp_files = []

        with self.Session() as session:
            try:
                localization1 = session.scalars(
                    Localization.select(session.user_or_token).where(
                        Localization.id == id1,
                    )
                ).first()
                localization2 = session.scalars(
                    Localization.select(session.user_or_token).where(
                        Localization.id == id2,
                    )
                ).first()

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


class GcnEventInstrumentFieldHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs, instrument_id):
        """
        ---
        summary: Get instrument field probabilities for a skymap
        description: Compute instrument field probabilities for a skymap
        tags:
          - localizations
          - instruments
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: Instrument ID
            required: true
            schema:
              type: integer
          - in: query
            name: localization_name
            required: true
            schema:
              type: string
            description: Localization map name
          - in: query
            name: integrated_probability
            nullable: true
            schema:
              type: float
            description: Cumulative integrated probability threshold
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
            arrow.get(dateobs)
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        localization_name = self.get_query_argument("localization_name", None)
        integrated_probability = self.get_query_argument("integrated_probability", 0.95)

        with self.Session() as session:
            stmt = Localization.select(session.user_or_token).where(
                Localization.dateobs == dateobs
            )
            if localization_name is not None:
                stmt = stmt.where(Localization.localization_name == localization_name)
            localization = session.scalars(stmt).first()
            if localization is None:
                return self.error("Localization not found", status=404)

            stmt = Instrument.select(session.user_or_token).where(
                Instrument.id == int(instrument_id)
            )
            instrument = session.scalars(stmt).first()
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

            field_ids, probs = zip(*session.execute(field_tiles_query).all())

            data_out = {"field_ids": field_ids, "probabilities": probs}
            return self.success(data=data_out)


class GcnEventTriggerHandler(BaseHandler):
    @permissions(["Manage allocations"])
    def get(self, dateobs, allocation_id=None):
        dateobs = dateobs.strip()
        try:
            arrow.get(dateobs)
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        with self.Session() as session:
            if allocation_id is not None:
                try:
                    allocation_id = int(allocation_id)
                except ValueError as e:
                    return self.error(f"Failed to parse allocation_id: str({e})")
                try:
                    gcn_triggered = session.scalars(
                        GcnTrigger.select(session.user_or_token).where(
                            GcnTrigger.dateobs == dateobs,
                            GcnTrigger.allocation_id == allocation_id,
                        )
                    ).all()
                    return self.success(data=gcn_triggered)
                except Exception as e:
                    return self.error(
                        f"Failed to get gcn_event triggered status: str({e})"
                    )

            else:
                try:
                    gcn_triggered = session.scalars(
                        GcnTrigger.select(session.user_or_token).where(
                            GcnTrigger.dateobs == dateobs
                        )
                    ).all()
                    return self.success(data=gcn_triggered)
                except Exception as e:
                    return self.error(
                        f"Failed to get gcn_event triggered status: str({e})"
                    )

    @permissions(["Manage allocations"])
    def put(self, dateobs, allocation_id):
        dateobs = dateobs.strip()
        try:
            arrow.get(dateobs)
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        data = self.get_json()

        triggered = data.get("triggered", None)
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

        with self.Session() as session:
            try:
                gcn_triggered = session.scalars(
                    GcnTrigger.select(session.user_or_token).where(
                        GcnTrigger.dateobs == dateobs,
                        GcnTrigger.allocation_id == allocation_id,
                    )
                ).first()
                if gcn_triggered is None:
                    # verify that the event and allocation exist
                    event = session.scalars(
                        GcnEvent.select(session.user_or_token).where(
                            GcnEvent.dateobs == dateobs
                        )
                    ).first()

                    if event is None:
                        return self.error(f"No event with dateobs: {dateobs}")
                    allocation = session.scalars(
                        Allocation.select(session.user_or_token).where(
                            Allocation.id == allocation_id
                        )
                    ).first()
                    if allocation is None:
                        return self.error(f"No allocation with ID: {allocation_id}")

                    gcn_triggered = GcnTrigger(
                        dateobs=dateobs,
                        allocation_id=allocation_id,
                        triggered=triggered,
                    )
                    session.add(gcn_triggered)
                else:
                    gcn_triggered.triggered = triggered
                session.commit()
                self.push_all(
                    "skyportal/REFRESH_GCN_TRIGGERED",
                    payload={"gcnEvent_dateobs": dateobs},
                )
                return self.success(data=gcn_triggered)
            except Exception as e:
                return self.error(f"Failed to set triggered status: str({e})")

    @permissions(["Manage allocations"])
    def delete(self, dateobs, allocation_id):
        dateobs = dateobs.strip()
        try:
            arrow.get(dateobs)
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        try:
            allocation_id = int(allocation_id)
        except ValueError:
            return self.error(f"Failed to parse allocation_id: {allocation_id}")

        with self.Session() as session:
            try:
                gcn_triggered = (
                    session.query(GcnTrigger)
                    .filter(
                        GcnTrigger.dateobs == dateobs,
                        GcnTrigger.allocation_id == allocation_id,
                    )
                    .first()
                )
                if gcn_triggered is not None:
                    session.delete(gcn_triggered)
                    session.commit()
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


class ObjGcnEventHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_id):
        """
        ---
        summary: Crossmatch an object with GCN events
        description: Retrieve an object's in-out critera for GcnEvents
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  startDate:
                    type: string
                    required: true
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01).
                      If provided, filter by GcnEvent.dateobs >= startDate.
                  endDate:
                    type: string
                    required: true
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01).
                      If provided, filter by GcnEvent.dateobs <= startDate.
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

        data = self.get_json()
        start_date = data.get("startDate", None)
        end_date = data.get("endDate", None)
        integrated_probability = data.get("probability", None)

        if start_date is None or end_date is None:
            return self.error("Must provide startDate and endDate query arguments.")

        try:
            start_date = arrow.get(start_date.strip()).datetime
        except Exception as e:
            return self.error(f"Failed to parse startDate: str({e})")

        try:
            end_date = arrow.get(end_date.strip()).datetime
        except Exception as e:
            return self.error(f"Failed to parse endDate: str({e})")

        if (end_date - start_date).days > 31:
            return self.error(
                "startDate and endDate must be within 31 days of each other."
            )

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token, mode="update").where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            query = GcnEvent.select(
                session.user_or_token,
            ).where(
                GcnEvent.dateobs >= start_date,
                GcnEvent.dateobs <= end_date,
            )

            event_ids = [event.id for event in session.scalars(query).unique().all()]
            if len(event_ids) == 0:
                return self.error("Cannot find GcnEvents in those bounds.")

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

        obj.gcn_crossmatch = events
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
    def post(self):
        """
        ---
        summary: Create a default gcn tag
        description: Create default gcn tag.
        tags:
          - gcn event default tags
        requestBody:
          content:
            application/json:
              schema: DefaultGcnTagPost
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
                            id:
                              type: integer
                              description: New default gcn tag ID
        """
        data = self.get_json()

        with self.Session() as session:
            if "default_tag_name" not in data:
                return self.error("Missing default_tag_name")
            else:
                stmt = DefaultGcnTag.select(session.user_or_token).where(
                    DefaultGcnTag.default_tag_name == data["default_tag_name"]
                )
                existing_default_tag = session.scalars(stmt).first()
                if existing_default_tag is not None:
                    return self.error(
                        f"A default tag called {data['default_tag_name']} already exists. That name must be unique."
                    )

            if "filters" in data:
                if not isinstance(data["filters"], dict):
                    return self.error("filters must be a dictionary")
                if not set(data["filters"].keys()).issubset(
                    {"gcn_tags", "notice_types", "localization_tags"}
                ):
                    return self.error(
                        'filters must be a dictionary with keys in ["gcn_tags", "notice_types", "localization_tags"]'
                    )
                for key in data["filters"]:
                    if not isinstance(data["filters"][key], list):
                        return self.error(f"filters[{key}] must be a list")
                    if not all(isinstance(item, str) for item in data["filters"][key]):
                        return self.error(f"filters[{key}] must be a list of strings")

            default_gcn_tag = DefaultGcnTag.__schema__().load(data)

            session.add(default_gcn_tag)
            session.commit()

            self.push_all(action="skyportal/REFRESH_DEFAULT_GCN_TAGS")
            return self.success(data={"id": default_gcn_tag.id})

    @auth_or_token
    def get(self, default_gcn_tag_id=None):
        """
        ---
        single:
          summary: Get a default gcn tag
          description: Retrieve a single default gcn tag
          tags:
            - gcn event default tags
          parameters:
            - in: path
              name: default_gcn_tag_id
              required: true
              schema:
                type: integer
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

        with self.Session() as session:
            if default_gcn_tag_id is not None:
                default_gcn_tag = session.scalars(
                    DefaultGcnTag.select(
                        session.user_or_token,
                    ).where(DefaultGcnTag.id == default_gcn_tag_id)
                ).first()
                if default_gcn_tag is None:
                    return self.error(
                        f"Cannot find DefaultGcnTag with ID {default_gcn_tag_id}"
                    )
                return self.success(data=default_gcn_tag)

            default_gcn_tags = (
                session.scalars(
                    DefaultGcnTag.select(
                        session.user_or_token,
                    )
                )
                .unique()
                .all()
            )

            return self.success(data=default_gcn_tags)

    @permissions(["Manage GCNs"])
    def delete(self, default_gcn_tag_id):
        """
        ---
        summary: Delete a default gcn tag
        description: Delete a default gcn tag
        tags:
          - gcn event default tags
        parameters:
          - in: path
            name: default_gcn_tag_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            stmt = DefaultGcnTag.select(session.user_or_token).where(
                DefaultGcnTag.id == default_gcn_tag_id
            )
            default_gcn_tag = session.scalars(stmt).first()

            if default_gcn_tag is None:
                return self.error(
                    f"Default GCN tag with ID {default_gcn_tag_id} not found"
                )

            session.delete(default_gcn_tag)
            session.commit()
            self.push_all(action="skyportal/REFRESH_DEFAULT_GCN_TAGS")
            return self.success()


# the following handler is used to download the content of a GCN notice, as a txt file
class GcnEventNoticeDownloadHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs, notice_id):
        """
        ---
        summary: Download a GCN notice
        description: Download a GCN notice
        tags:
          - gcn notices
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: notice_id
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

        dateobs = dateobs.strip()
        try:
            arrow.get(dateobs)
        except arrow.parser.ParserError as e:
            return self.error(f"Failed to parse dateobs: str({e})")

        with self.Session() as session:
            try:
                notice = session.scalars(
                    GcnNotice.select(session.user_or_token).where(
                        GcnNotice.dateobs == dateobs, GcnNotice.id == int(notice_id)
                    )
                ).first()
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
