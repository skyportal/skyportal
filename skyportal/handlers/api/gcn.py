# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import asyncio
import ast
from astropy.time import Time
from astropy.table import Table
import binascii
import healpy as hp
import io
import os
import gcn
from ligo.skymap.postprocess import crossmatch
from ligo.skymap import distance, moc
import ligo.skymap.bayestar as ligo_bayestar
import ligo.skymap.io
import ligo.skymap.postprocess
import lxml
import xmlschema
from urllib.parse import urlparse
import tempfile
from tornado.ioloop import IOLoop
import arrow
import astropy
import humanize
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql.expression import cast
from sqlalchemy.dialects.postgresql import JSONB
from marshmallow import Schema
from marshmallow.exceptions import ValidationError
import numpy as np
import operator  # noqa: F401

from skyportal.models.photometry import Photometry

from .observation import get_observations
from .source import get_sources, serialize, MAX_SOURCES_PER_PAGE
from .galaxy import get_galaxies, MAX_GALAXIES
import pandas as pd
from tabulate import tabulate
import datetime
from ...utils.UTCTZnaiveDateTime import UTCTZnaiveDateTime

from baselayer.app.access import auth_or_token
from baselayer.log import make_log
from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from .source import post_source
from .observation_plan import (
    post_observation_plan,
    post_survey_efficiency_analysis,
)
from ..base import BaseHandler
from ...models import (
    DBSession,
    Allocation,
    CatalogQuery,
    DefaultObservationPlanRequest,
    EventObservationPlan,
    GcnEvent,
    GcnNotice,
    GcnProperty,
    GcnSummary,
    GcnTag,
    Localization,
    LocalizationProperty,
    LocalizationTile,
    LocalizationTag,
    MMADetector,
    ObservationPlanRequest,
    User,
    Instrument,
    Group,
    UserNotification,
)
from ...utils.gcn import (
    get_dateobs,
    get_properties,
    get_tags,
    get_trigger,
    get_skymap,
    get_contour,
    from_url,
    from_bytes,
    from_cone,
    from_polygon,
)

from skyportal.models.gcn import SOURCE_RADIUS_THRESHOLD

log = make_log('api/gcn_event')

env, cfg = load_env()

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))

MAX_GCNEVENTS = 1000


def post_gcnevent_from_xml(payload, user_id, session):
    """Post GcnEvent to database from voevent xml.
    payload: str
        VOEvent readable string
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.query(User).get(user_id)

    schema = f'{os.path.dirname(__file__)}/../../utils/schema/VOEvent-v2.0.xsd'
    voevent_schema = xmlschema.XMLSchema(schema)
    if voevent_schema.is_valid(payload):
        # check if is string
        try:
            payload = payload.encode('ascii')
        except AttributeError:
            pass
        root = lxml.etree.fromstring(payload)
    else:
        raise ValueError("xml file is not valid VOEvent")

    gcn_notice = session.scalars(
        GcnNotice.select(user).where(GcnNotice.ivorn == root.attrib['ivorn'])
    ).first()
    if gcn_notice is not None:
        raise ValueError(f"GcnNotice with ivorn {root.attrib['ivorn']} already exists.")

    dateobs = get_dateobs(root)
    trigger_id = get_trigger(root)

    if trigger_id is not None:
        event = session.scalars(
            GcnEvent.select(user).where(GcnEvent.trigger_id == trigger_id)
        ).first()
    else:
        event = session.scalars(
            GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        ).first()

    if event is None:
        event = GcnEvent(dateobs=dateobs, sent_by_id=user.id, trigger_id=trigger_id)
        session.add(event)
    else:
        if not event.is_accessible_by(user, mode="update"):
            raise ValueError(
                "Insufficient permissions: GCN event can only be updated by original poster"
            )

    properties_dict = get_properties(root)
    properties = GcnProperty(
        dateobs=event.dateobs, sent_by_id=user.id, data=properties_dict
    )
    session.add(properties)

    tags = [
        GcnTag(
            dateobs=event.dateobs,
            text=text,
            sent_by_id=user.id,
        )
        for text in get_tags(root)
    ]

    gcn_notice = GcnNotice(
        content=payload,
        ivorn=root.attrib['ivorn'],
        notice_type=gcn.get_notice_type(root),
        stream=urlparse(root.attrib['ivorn']).path.lstrip('/'),
        date=root.find('./Who/Date').text,
        dateobs=event.dateobs,
        sent_by_id=user.id,
    )

    detectors = []
    for tag in tags:
        session.add(tag)

        mma_detector = session.scalars(
            MMADetector.select(user).where(MMADetector.nickname == tag.text)
        ).first()
        if mma_detector is not None:
            detectors.append(mma_detector)
    session.add(gcn_notice)
    event.detectors = detectors

    skymap = get_skymap(root, gcn_notice)
    if skymap is None:
        session.commit()
        return event.id

    skymap["dateobs"] = event.dateobs
    skymap["sent_by_id"] = user.id

    try:
        ra, dec, error = (float(val) for val in skymap["localization_name"].split("_"))
        if error < SOURCE_RADIUS_THRESHOLD:
            name = root.find('./Why/Inference/Name')
            if name is not None:
                source = {
                    'id': (name.text).replace(' ', ''),
                    'ra': ra,
                    'dec': dec,
                }
            elif any([True if 'GRB' in tag.text.upper() else False for tag in tags]):
                dateobs_txt = Time(dateobs).isot
                source_name = f"GRB{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
                source = {
                    'id': source_name,
                    'ra': ra,
                    'dec': dec,
                }
            elif any([True if 'GW' in tag.text.upper() else False for tag in tags]):
                dateobs_txt = Time(dateobs).isot
                source_name = f"GW{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
                source = {
                    'id': source_name,
                    'ra': ra,
                    'dec': dec,
                }
            else:
                source = {
                    'id': Time(event.dateobs).isot.replace(":", "-"),
                    'ra': ra,
                    'dec': dec,
                }
            post_source(source, user_id, session)
    except Exception:
        pass

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

        log(f"Generating tiles/contours for localization {localization.id}")

        IOLoop.current().run_in_executor(
            None, lambda: add_skymap_properties(localization.id, user_id)
        )

        IOLoop.current().run_in_executor(
            None, lambda: add_tiles_and_observation_plans(localization.id, user_id)
        )
        IOLoop.current().run_in_executor(None, lambda: add_contour(localization.id))

    return event.id


def post_gcnevent_from_dictionary(payload, user_id, session):
    """Post GcnEvent to database from dictionary.
    payload: dict
        Dictionary containing dateobs and skymap
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.query(User).get(user_id)

    dateobs = payload['dateobs']

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
        for text in payload.get('tags', [])
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

    skymap = payload.get('skymap', None)
    if skymap is None:
        session.commit()
        return event.id

    if type(skymap) is dict:
        required_keys = {'localization_name', 'uniq', 'probdensity'}
        if not required_keys.issubset(set(skymap.keys())):
            required_cone_keys = {'ra', 'dec', 'error'}
            required_polygon_keys = {'localization_name', 'polygon'}
            if required_cone_keys.issubset(set(skymap.keys())):
                skymap = from_cone(skymap['ra'], skymap['dec'], skymap['error'])
            elif required_polygon_keys.issubset(set(skymap.keys())):
                if type(skymap['polygon']) == str:
                    polygon = ast.literal_eval(skymap['polygon'])
                else:
                    polygon = skymap['polygon']
                skymap = from_polygon(skymap['localization_name'], polygon)
            else:
                raise ValueError("ra, dec, and error must be in skymap to parse")
    else:
        try:
            skymap = from_bytes(skymap)
        except binascii.Error:
            skymap = from_url(skymap)

    skymap["dateobs"] = event.dateobs
    skymap["sent_by_id"] = user.id

    try:
        ra, dec, error = (float(val) for val in skymap["localization_name"].split("_"))
        if error < SOURCE_RADIUS_THRESHOLD:
            source = {
                'id': Time(event.dateobs).isot.replace(":", "-"),
                'ra': ra,
                'dec': dec,
            }
            post_source(source, user_id, session)
    except Exception:
        pass

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

        log(f"Generating tiles/contours for localization {localization.id}")

        IOLoop.current().run_in_executor(
            None, lambda: add_skymap_properties(localization.id, user.id)
        )
        IOLoop.current().run_in_executor(
            None, lambda: add_tiles_and_observation_plans(localization.id, user_id)
        )
        IOLoop.current().run_in_executor(None, lambda: add_contour(localization.id))

    return event.id


class GcnEventTagsHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
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


class GcnEventPropertiesHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
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
        description: Get survey efficiency analyses of the GcnEvent.
        tags:
          - gcnevents
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
                        'number_of_transients': analysis.number_of_transients,
                        'number_in_covered': analysis.number_in_covered,
                        'number_detected': analysis.number_detected,
                        'efficiency': analysis.efficiency,
                    }
                )

            return self.success(data=analysis_data)


class GcnEventObservationPlanRequestsHandler(BaseHandler):
    @auth_or_token
    async def get(self, gcnevent_id):
        """
        ---
        description: Get observation plan requests of the GcnEvent.
        tags:
          - gcnevents
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
                schema: ArrayOfObservationPlanRequests
        """

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
            for ii, req in enumerate(event.observationplan_requests):
                dat = req.to_dict()
                plan_data = []
                for plan in dat["observation_plans"]:
                    plan_dict = plan.to_dict()
                    plan_dict['statistics'] = [
                        statistics.to_dict() for statistics in plan_dict['statistics']
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
        description: Get catalog queries of the GcnEvent.
        tags:
          - gcnevents
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

        with self.Session() as session:
            queries = session.scalars(
                CatalogQuery.select(
                    session.user_or_token,
                ).where(CatalogQuery.payload['gcnevent_id'] == gcnevent_id)
            ).all()

            return self.success(data=queries)


class GcnEventHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Ingest GCN xml file
        tags:
          - gcnevents
          - gcntags
          - gcnnotices
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
        if 'xml' not in data:
            required_keys = {'dateobs'}
            if not required_keys.issubset(set(data.keys())):
                return self.error(
                    "Either xml or dateobs must be present in data to parse GcnEvent"
                )

        with self.Session() as session:
            try:
                if 'xml' in data:
                    event_id = post_gcnevent_from_xml(
                        data['xml'], self.associated_user_object.id, session
                    )
                else:
                    event_id = post_gcnevent_from_dictionary(
                        data, self.associated_user_object.id, session
                    )

                self.push(action='skyportal/REFRESH_GCN_EVENTS')
            except Exception as e:
                return self.error(f'Cannot post event: {str(e)}')

            return self.success(data={'gcnevent_id': event_id})

    @auth_or_token
    async def get(self, dateobs=None):
        f"""
        ---
        single:
          description: Retrieve a GCN event
          tags:
            - gcnevents
          parameters:
            - in: path
              name: dateobs
              required: false
              schema:
                type: string
        multiple:
          description: Retrieve multiple GCN events
          tags:
            - gcnevents
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
              name: tagKeep
              nullable: true
              schema:
                type: string
              description: |
                Gcn Tag to match against
            - in: query
              name: tagRemove
              nullable: true
              schema:
                type: string
              description: |
                Gcn Tag to filter out
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

        page_number = self.get_query_argument("pageNumber", 1)
        try:
            page_number = int(page_number)
        except ValueError as e:
            return self.error(f'pageNumber fails: {e}')

        n_per_page = self.get_query_argument("numPerPage", 10)
        try:
            n_per_page = int(n_per_page)
        except ValueError as e:
            return self.error(f'numPerPage fails: {e}')

        if n_per_page > MAX_GCNEVENTS:
            return self.error(f'numPerPage should be no larger than {MAX_GCNEVENTS}.')

        sort_by = self.get_query_argument("sortBy", None)
        sort_order = self.get_query_argument("sortOrder", "asc")

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        tag_keep = self.get_query_argument('tagKeep', None)
        tag_remove = self.get_query_argument('tagRemove', None)
        gcn_properties_filter = self.get_query_argument("gcnPropertiesFilter", None)

        if gcn_properties_filter is not None:
            if isinstance(gcn_properties_filter, str) and "," in gcn_properties_filter:
                gcn_properties_filter = [
                    c.strip() for c in gcn_properties_filter.split(",")
                ]
            elif isinstance(gcn_properties_filter, str):
                gcn_properties_filter = [gcn_properties_filter]
            else:
                raise ValueError(
                    "Invalid gcnPropertiesFilter value -- must provide at least one string value"
                )

        localization_properties_filter = self.get_query_argument(
            "localizationPropertiesFilter", None
        )

        if localization_properties_filter is not None:
            if (
                isinstance(localization_properties_filter, str)
                and "," in localization_properties_filter
            ):
                localization_properties_filter = [
                    c.strip() for c in localization_properties_filter.split(",")
                ]
            elif isinstance(localization_properties_filter, str):
                localization_properties_filter = [localization_properties_filter]
            else:
                raise ValueError(
                    "Invalid localizationPropertiesFilter value -- must provide at least one string value"
                )

        if dateobs is not None:
            with self.Session() as session:
                event = session.scalars(
                    GcnEvent.select(
                        session.user_or_token,
                        options=[
                            joinedload(GcnEvent.localizations).joinedload(
                                Localization.tags
                            ),
                            joinedload(GcnEvent.localizations).joinedload(
                                Localization.properties
                            ),
                            joinedload(GcnEvent.gcn_notices),
                            joinedload(GcnEvent.observationplan_requests)
                            .joinedload(ObservationPlanRequest.allocation)
                            .joinedload(Allocation.instrument),
                            joinedload(GcnEvent.comments),
                            joinedload(GcnEvent.detectors),
                            joinedload(GcnEvent.properties),
                            joinedload(GcnEvent.summaries),
                        ],
                    ).where(GcnEvent.dateobs == dateobs)
                ).first()
                if event is None:
                    return self.error("GCN event not found", status=404)

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
                }

                return self.success(data=data)

        with self.Session() as session:

            query = GcnEvent.select(
                session.user_or_token,
                options=[
                    joinedload(GcnEvent.localizations),
                    joinedload(GcnEvent.gcn_notices),
                    joinedload(GcnEvent.observationplan_requests),
                ],
            )

            if start_date:
                start_date = arrow.get(start_date.strip()).datetime
                query = query.where(GcnEvent.dateobs >= start_date)
            if end_date:
                end_date = arrow.get(end_date.strip()).datetime
                query = query.where(GcnEvent.dateobs <= end_date)
            if tag_keep:
                tag_subquery = (
                    GcnTag.select(session.user_or_token)
                    .where(GcnTag.text.contains(tag_keep))
                    .subquery()
                )
                query = query.join(
                    tag_subquery, GcnEvent.dateobs == tag_subquery.c.dateobs
                )
            if tag_remove:
                tag_subquery = (
                    GcnTag.select(session.user_or_token)
                    .where(GcnTag.text.contains(tag_remove))
                    .subquery()
                )
                query = query.join(
                    tag_subquery, GcnEvent.dateobs != tag_subquery.c.dateobs
                )

            if gcn_properties_filter is not None:
                for prop_filt in gcn_properties_filter:
                    prop_split = prop_filt.split(":")
                    if not (len(prop_split) == 1 or len(prop_split) == 3):
                        raise ValueError(
                            "Invalid gcnPropertiesFilter value -- property filter must have 1 or 3 values"
                        )
                    name = prop_split[0].strip()

                    properties_query = GcnProperty.select(session.user_or_token)
                    if len(prop_split) == 3:
                        value = prop_split[1].strip()
                        try:
                            value = float(value)
                        except ValueError as e:
                            raise ValueError(
                                f"Invalid GCN properties filter value: {e}"
                            )
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

                    properties_query = LocalizationProperty.select(
                        session.user_or_token
                    )
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
                sa.select(sa.func.count()).select_from(query)
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
                event_info = {**event.to_dict(), "tags": list(set(event.tags))}
                event_info["localizations"] = sorted(
                    (
                        {
                            **loc.to_dict(),
                            "tags": [tag.to_dict() for tag in loc.tags],
                        }
                        for loc in event.localizations
                    ),
                    key=lambda x: x["created_at"],
                    reverse=True,
                )
                events.append(event_info)

            query_results = {"events": events, "totalMatches": int(total_matches)}

            return self.success(data=query_results)

    @auth_or_token
    def delete(self, dateobs):
        """
        ---
        description: Delete a GCN event
        tags:
          - gcnevents
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
            event = session.scalars(
                GcnEvent.select(session.user_or_token, model="delete").where(
                    GcnEvent.dateobs == dateobs
                )
            ).first()
            if event is None:
                return self.error("GCN event not found", status=404)

            session.delete(event)
            session.commit()

            return self.success()


def add_tiles_and_observation_plans(localization_id, user_id):
    session = Session()
    try:
        localization = session.scalar(
            sa.select(Localization).where(Localization.id == localization_id)
        )
        user = session.scalar(sa.select(User).where(User.id == user_id))

        tiles = [
            LocalizationTile(
                localization_id=localization.id, healpix=uniq, probdensity=probdensity
            )
            for uniq, probdensity in zip(localization.uniq, localization.probdensity)
        ]

        session.add(localization)
        session.add_all(tiles)
        session.commit()

        config_gcn_observation_plans_all = [
            observation_plan for observation_plan in cfg["gcn.observation_plans"]
        ]
        config_gcn_observation_plans = []
        for config_gcn_observation_plan in config_gcn_observation_plans_all:
            allocation = session.scalars(
                Allocation.select(user).where(
                    Allocation.proposal_id
                    == config_gcn_observation_plan["allocation-proposal_id"]
                )
            ).first()
            if allocation is not None:
                config_gcn_observation_plan["allocation_id"] = allocation.id
                config_gcn_observation_plan["survey_efficiencies"] = []
                config_gcn_observation_plans.append(config_gcn_observation_plan)

        default_observation_plans = (
            (
                session.scalars(
                    DefaultObservationPlanRequest.select(
                        user,
                        options=[
                            joinedload(
                                DefaultObservationPlanRequest.default_survey_efficiencies
                            )
                        ],
                    )
                )
            )
            .unique()
            .all()
        )
        gcn_observation_plans = []
        for plan in default_observation_plans:
            allocation = session.scalars(
                Allocation.select(user).where(Allocation.id == plan.allocation_id)
            ).first()

            gcn_observation_plan = {
                'allocation_id': allocation.id,
                'payload': plan.payload,
                'survey_efficiencies': [
                    survey_efficiency.to_dict()
                    for survey_efficiency in plan.default_survey_efficiencies
                ],
            }
            gcn_observation_plans.append(gcn_observation_plan)
        gcn_observation_plans = gcn_observation_plans + config_gcn_observation_plans

        event = session.scalars(
            GcnEvent.select(user).where(GcnEvent.dateobs == localization.dateobs)
        ).first()
        start_date = str(datetime.datetime.utcnow()).replace("T", "")
        end_date = str(datetime.datetime.utcnow() + datetime.timedelta(days=1)).replace(
            "T", ""
        )

        for ii, gcn_observation_plan in enumerate(gcn_observation_plans):
            allocation_id = gcn_observation_plan['allocation_id']
            allocation = session.scalars(
                Allocation.select(user).where(Allocation.id == allocation_id)
            ).first()

            if allocation is not None:
                payload = {
                    **gcn_observation_plan['payload'],
                    'start_date': start_date,
                    'end_date': end_date,
                    'queue_name': f'{allocation.instrument.name}-{start_date}-{ii}',
                }
                plan = {
                    'payload': payload,
                    'allocation_id': allocation.id,
                    'gcnevent_id': event.id,
                    'localization_id': localization.id,
                }

                plan_id = post_observation_plan(
                    plan, user_id, session, asynchronous=False
                )
                for survey_efficiency in gcn_observation_plan['survey_efficiencies']:
                    post_survey_efficiency_analysis(
                        survey_efficiency, plan_id, user_id, session, asynchronous=False
                    )

        return log(
            f"Generated tiles / observation plans for localization {localization_id}"
        )
    except Exception as e:
        log(
            f"Unable to generate tiles / observation plans for localization {localization_id}: {e}"
        )
    finally:
        Session.remove()


def add_skymap_properties(localization_id, user_id):
    session = Session()
    try:
        localization = session.scalar(
            sa.select(Localization).where(Localization.id == localization_id)
        )
        user = session.scalar(sa.select(User).where(User.id == user_id))
        sky_map = localization.table

        properties_dict = {}
        tags_list = []
        result = crossmatch(sky_map, contours=(0.9,), areas=(500,))
        area = result.contour_areas[0]
        prob = result.area_probs[0]

        if not np.isnan(area):
            properties_dict["area_90"] = area
            if properties_dict["area_90"] < 500:
                tags_list.append("< 500 sq. deg.")
        if not np.isnan(prob):
            properties_dict["probability_500"] = prob
            if properties_dict["probability_500"] >= 0.9:
                tags_list.append("> 0.9 in 500 sq. deg.")

        # Distance stats
        if 'DISTMU' in sky_map.dtype.names:
            # Calculate the cumulative area in deg2 and the cumulative probability.
            dA = moc.uniq2pixarea(sky_map['UNIQ'])
            dP = sky_map['PROBDENSITY'] * dA
            mu = sky_map['DISTMU']
            sigma = sky_map['DISTSIGMA']

            distmean, _ = distance.parameters_to_marginal_moments(dP, mu, sigma)
            if not np.isnan(distmean):
                properties_dict["distance"] = distmean
                if distmean <= 150:
                    tags_list.append("< 150 Mpc")

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

        session.commit()
        log(f"Generated properties for localization {localization_id}")
    except Exception as e:
        log(f"Unable to generate properties for localization {localization_id}: {e}")
    finally:
        Session.remove()


def add_contour(localization_id):
    session = Session()
    try:
        localization = session.query(Localization).get(localization_id)
        localization = get_contour(localization)
        session.add(localization)
        session.commit()
        return log(f"Generated contour for localization {localization_id}")
    except Exception as e:
        log(f"Unable to generate contour for localization {localization_id}: {e}")
    finally:
        Session.remove()


class LocalizationHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs, localization_name):
        """
        ---
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

            session.delete(localization)
            session.commit()

            return self.success()


class LocalizationPropertiesHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
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


def add_gcn_summary(
    summary_id,
    user_id,
    dateobs,
    title,
    number,
    subject,
    user_ids,
    group_id,
    start_date,
    end_date,
    localization_name,
    localization_cumprob,
    number_of_detections,
    show_sources,
    show_galaxies,
    show_observations,
    no_text,
    photometry_in_window,
):
    session = Session()
    try:
        user = session.query(User).get(user_id)
        session.user_or_token = user

        gcn_summary = session.query(GcnSummary).get(summary_id)
        group = session.query(Group).get(group_id)
        event = session.query(GcnEvent).filter(GcnEvent.dateobs == dateobs).first()

        start_date_mjd = Time(arrow.get(start_date).datetime).mjd
        end_date_mjd = Time(arrow.get(end_date).datetime).mjd

        contents = []
        if not no_text:
            header_text = []
            header_text.append(f"""TITLE: {title.upper()}\n""")
            if number is not None:
                header_text.append(f"""NUMBER: {number}\n""")
            header_text.append(f"""SUBJECT: {subject[0].upper()+subject[1:]}\n""")
            now_date = astropy.time.Time.now()
            header_text.append(f"""DATE: {now_date}\n""")

            if user.affiliations is not None and len(user.affiliations) > 0:
                affiliations = ", ".join(user.affiliations)
            else:
                affiliations = "..."

            # add a "FROM full name and affiliation"
            from_str = (
                f"""FROM:  {user.first_name} {user.last_name} at {affiliations}"""
            )
            if user.contact_email is not None:
                from_str += f""" <{user.contact_email}>\n"""
            header_text.append(from_str)

            if len(user_ids) > 0:
                # query user objects for all user_ids
                users = []
                for mentioned_user_id in user_ids:
                    mentioned_user = User.query.get(mentioned_user_id)
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
                    [
                        ", ".join(users_txt[i : i + 5])
                        for i in range(0, len(users_txt), 5)
                    ]
                )
                header_text.append(f"""\n{users_txt}\n""")

            header_text.append(f"""\non behalf of the {group.name}, report:\n""")
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
                sources.extend(sources_data['sources'])
                source_page_number += 1

                if len(sources_data['sources']) < MAX_SOURCES_PER_PAGE:
                    break
            if len(sources) > 0:
                sources_text.append(
                    f"\nFound {len(sources)} {'sources' if len(sources) > 1 else 'source'} in the event's localization, given the specified date range:\n"
                ) if not no_text else None
                ids, aliases, ras, decs, redshifts = (
                    [],
                    [],
                    [],
                    [],
                    [],
                )
                for source in sources:
                    ids.append(source['id'] if 'id' in source else None)
                    aliases.append(source['alias'] if 'alias' in source else None)
                    ras.append(source['ra'] if 'ra' in source else None)
                    decs.append(source['dec'] if 'dec' in source else None)
                    redshift = source['redshift'] if 'redshift' in source else None
                    if 'redshift_error' in source and redshift is not None:
                        if source['redshift_error'] is not None:
                            redshift = f"{redshift}±{source['redshift_error']}"
                    redshifts.append(redshift)
                df = pd.DataFrame(
                    {
                        "id": ids,
                        "alias": aliases,
                        "ra": ras,
                        "dec": decs,
                        "redshift": redshifts,
                    }
                )
                sources_text.append(
                    tabulate(df, headers='keys', tablefmt='psql', showindex=False)
                    + "\n"
                )
                # now, create a photometry table per source
                for source in sources:
                    stmt = Photometry.select(user).where(
                        Photometry.obj_id == source['id']
                    )
                    if photometry_in_window:
                        stmt = stmt.where(
                            Photometry.mjd >= start_date_mjd,
                            Photometry.mjd <= end_date_mjd,
                        )
                    photometry = session.scalars(stmt).all()
                    if len(photometry) > 0:
                        sources_text.append(
                            f"""\nPhotometry for source {source['id']}:\n"""
                        ) if not no_text else None
                        mjds, mags, filters, origins, instruments = (
                            [],
                            [],
                            [],
                            [],
                            [],
                        )
                        for phot in photometry:
                            phot = serialize(phot, 'ab', 'mag')
                            mjds.append(phot['mjd'] if 'mjd' in phot else None)
                            if (
                                'mag' in phot
                                and 'magerr' in phot
                                and phot['mag'] is not None
                                and phot['magerr'] is not None
                            ):
                                mags.append(
                                    f"{np.round(phot['mag'],2)}±{np.round(phot['magerr'],2)}"
                                )
                            elif (
                                'limiting_mag' in phot
                                and phot['limiting_mag'] is not None
                            ):
                                mags.append(f"< {np.round(phot['limiting_mag'], 1)}")
                            else:
                                mags.append(None)
                            filters.append(phot['filter'] if 'filter' in phot else None)
                            origins.append(phot['origin'] if 'origin' in phot else None)
                            instruments.append(
                                phot['instrument_name']
                                if 'instrument_name' in phot
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
                                column='obj_id',
                                value=[p["obj_id"] for p in photometry],
                            )
                        sources_text.append(
                            tabulate(
                                df_phot,
                                headers='keys',
                                tablefmt='psql',
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
                )
                galaxies.extend(galaxies_data['galaxies'])
                galaxies_page_number += 1
                if len(galaxies_data['galaxies']) < MAX_GALAXIES:
                    break
            if len(galaxies) > 0:
                galaxies_text.append(
                    f"""\nFound {len(galaxies)} {'galaxies' if len(galaxies) > 1 else 'galaxy'} in the event's localization:\n"""
                ) if not no_text else None
                catalogs, names, ras, decs, distmpcs, redshifts = (
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                )
                for galaxy in galaxies:
                    galaxy = galaxy.to_dict()
                    catalogs.append(
                        galaxy['catalog_name'] if 'catalog_name' in galaxy else None
                    )
                    names.append(galaxy['name'] if 'name' in galaxy else None)
                    ras.append(galaxy['ra'] if 'ra' in galaxy else None)
                    decs.append(galaxy['dec'] if 'dec' in galaxy else None)
                    distmpcs.append(galaxy['distmpc'] if 'distmpc' in galaxy else None)
                    redshifts.append(
                        galaxy['redshift'] if 'redshift' in galaxy else None
                    )
                df = pd.DataFrame(
                    {
                        "catalog": catalogs,
                        "name": names,
                        "ra": ras,
                        "dec": decs,
                        "distmpc": distmpcs,
                        "redshift": redshifts,
                    }
                )
                galaxies_text.append(
                    tabulate(df, headers='keys', tablefmt='psql', showindex=False)
                    + "\n"
                )
            contents.extend(galaxies_text)

        if show_observations:
            # get the executed obs, by instrument
            observations_text = []
            start_date = arrow.get(start_date).datetime
            end_date = arrow.get(end_date).datetime

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
                        return_statistics=True,
                    )

                    observations = data["observations"]
                    num_observations = len(observations)
                    if num_observations > 0:
                        start_observation = astropy.time.Time(
                            min(obs["obstime"] for obs in observations),
                            format='datetime',
                        )
                        unique_filters = list({obs["filt"] for obs in observations})
                        total_time = sum(obs["exposure_time"] for obs in observations)
                        probability = data["probability"]
                        area = data["area"]

                        dt = start_observation.datetime - event.dateobs
                        before_after = "after" if dt.total_seconds() > 0 else "before"
                        observations_text.append(
                            f"""\n\n{instrument.telescope.name} - {instrument.name}:\n\nWe observed the localization region of {event.gcn_notices[0].stream} trigger {astropy.time.Time(event.dateobs, format='datetime').isot} UTC.  We obtained a total of {num_observations} images covering {",".join(unique_filters)} bands for a total of {total_time} seconds. The observations covered {area:.1f} square degrees beginning at {start_observation.isot} ({humanize.naturaldelta(dt)} {before_after} the burst trigger time) corresponding to ~{int(100 * probability)}% of the probability enclosed in the localization region.\nThe table below shows the photometry for each observation.\n"""
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
                                astropy.time.Time(obs["obstime"], format='datetime').mjd
                                if "obstime" in obs
                                else None
                            )
                            ras.append(
                                obs['field']["ra"] if "ra" in obs['field'] else None
                            )
                            decs.append(
                                obs['field']["dec"] if "dec" in obs['field'] else None
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
                        observations_text.append(
                            tabulate(
                                df_obs,
                                headers='keys',
                                tablefmt='psql',
                                showindex=False,
                                floatfmt=(
                                    ".2f",
                                    ".5f",
                                    ".5f",
                                    ".5f",
                                    "%s",
                                    "%d",
                                    ".2f",
                                ),
                            )
                            + "\n"
                        )
                if len(observations_text) > 0 and not no_text:
                    observations_text = ["\nObservations:"] + observations_text
                    contents.extend(observations_text)

        gcn_summary.text = "\n".join(contents)
        session.commit()

        flow = Flow()
        flow.push(
            user_id=user.id,
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


class GcnSummaryHandler(BaseHandler):
    @auth_or_token
    async def post(self, dateobs, summary_id=None):
        """
        ---
          description: Post a summary of a GCN event.
          tags:
            - gcnsummarys
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
        show_sources = data.get("showSources", False)
        show_galaxies = data.get("showGalaxies", False)
        show_observations = data.get("showObservations", False)
        no_text = data.get("noText", False)
        photometry_in_window = data.get("photometryInWindow", False)

        class Validator(Schema):
            start_date = UTCTZnaiveDateTime(required=False, missing=None)
            end_date = UTCTZnaiveDateTime(required=False, missing=None)

        validator_instance = Validator()
        params_to_be_validated = {}
        if start_date is not None:
            params_to_be_validated['start_date'] = start_date
        if end_date is not None:
            params_to_be_validated['end_date'] = end_date

        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        start_date = validated['start_date']
        end_date = validated['end_date']

        if title is None:
            return self.error("Title is required")

        if group_id is None:
            return self.error("Group ID is required")

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
                    if type(user_ids) == list:
                        user_ids = [int(user_id) for user_id in user_ids]
                    else:
                        user_ids = [int(user_ids)]
                except ValueError:
                    return self.error("User IDs must be integers")
            else:
                user_ids = []

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

            try:
                IOLoop.current().run_in_executor(
                    None,
                    lambda: add_gcn_summary(
                        summary_id=summary_id,
                        user_id=user_id,
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
                        show_sources=show_sources,
                        show_galaxies=show_galaxies,
                        show_observations=show_observations,
                        no_text=no_text,
                        photometry_in_window=photometry_in_window,
                    ),
                )
                return self.success({"id": summary_id})
            except Exception as e:
                return self.error(f"Error generating summary: {e}")

    @auth_or_token
    def get(self, dateobs, summary_id):
        """
        ---
        description: Retrieve a GCN summary
        tags:
          - gcn
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
    def delete(self, dateobs, summary_id):
        """
        ---
        description: Delete a GCN summary
        tags:
          - gcn
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


class LocalizationDownloadHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs, localization_name):
        """
        ---
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
            return self.error(f'Failed to parse dateobs: str({e})')

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

                output_format = 'fits'
                with tempfile.NamedTemporaryFile(suffix='.fits') as fitsfile:
                    ligo.skymap.io.write_sky_map(
                        fitsfile.name, localization.table, moc=True
                    )

                    with open(fitsfile.name, mode='rb') as g:
                        content = g.read()
                    local_temp_files.append(fitsfile.name)

                data = io.BytesIO(content)
                filename = f"{localization.localization_name}.{output_format}"

                await self.send_file(data, filename, output_type=output_format)

            except Exception as e:
                return self.error(f'Failed to create skymap for download: str({e})')
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

                output_format = 'fits'

                skymap1 = localization1.flat_2d
                skymap2 = localization2.flat_2d
                skymap = skymap1 * skymap2
                skymap = skymap / np.sum(skymap)

                skymap = hp.reorder(skymap, 'RING', 'NESTED')
                skymap = ligo_bayestar.derasterize(Table([skymap], names=['PROB']))
                with tempfile.NamedTemporaryFile(suffix='.fits') as fitsfile:
                    ligo.skymap.io.write_sky_map(
                        fitsfile.name, skymap, format='fits', moc=True
                    )

                    with open(fitsfile.name, mode='rb') as g:
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
                return self.error(f'Failed to create skymap for download: str({e})')
            finally:
                # clean up local files
                for f in local_temp_files:
                    try:
                        os.remove(f)
                    except:  # noqa E722
                        pass
