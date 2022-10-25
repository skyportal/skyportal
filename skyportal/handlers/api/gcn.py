# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import ast
from astropy.time import Time
import binascii
import os
import gcn
import lxml
import xmlschema
from urllib.parse import urlparse
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

from .source import post_source
from ..base import BaseHandler
from ...models import (
    DBSession,
    Allocation,
    CatalogQuery,
    GcnEvent,
    GcnNotice,
    GcnProperty,
    GcnTag,
    Localization,
    LocalizationTile,
    MMADetector,
    ObservationPlanRequest,
    User,
    Instrument,
    Group,
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

log = make_log('api/gcn_event')


Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))

SOURCE_RADIUS_THRESHOLD = 5 / 60.0


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

        IOLoop.current().run_in_executor(None, lambda: add_tiles(localization.id))
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

        IOLoop.current().run_in_executor(None, lambda: add_tiles(localization.id))
        IOLoop.current().run_in_executor(None, lambda: add_contour(localization.id))

    return event.id


class GcnEventTagsHandler(BaseHandler):
    @auth_or_token
    def get(self):
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
    def get(self):
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
                        joinedload(GcnEvent.observationplan_requests).joinedload(
                            ObservationPlanRequest.observation_plans
                        ),
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
                    plan_dict = {
                        **plan.to_dict(),
                    }
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
            if 'xml' in data:
                event_id = post_gcnevent_from_xml(
                    data['xml'], self.associated_user_object.id, session
                )
            else:
                event_id = post_gcnevent_from_dictionary(
                    data, self.associated_user_object.id, session
                )

            self.push(action='skyportal/REFRESH_GCN_EVENTS')

            return self.success(data={'gcnevent_id': event_id})

    @auth_or_token
    async def get(self, dateobs=None):
        """
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
              name: propertiesFilter
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

        n_per_page = self.get_query_argument("numPerPage", 100)
        try:
            n_per_page = int(n_per_page)
        except ValueError as e:
            return self.error(f'numPerPage fails: {e}')

        sort_by = self.get_query_argument("sortBy", None)
        sort_order = self.get_query_argument("sortOrder", "asc")

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        tag_keep = self.get_query_argument('tagKeep', None)
        tag_remove = self.get_query_argument('tagRemove', None)
        properties_filter = self.get_query_argument("propertiesFilter", None)

        if properties_filter is not None:
            if isinstance(properties_filter, str) and "," in properties_filter:
                properties_filter = [c.strip() for c in properties_filter.split(",")]
            elif isinstance(properties_filter, str):
                properties_filter = [properties_filter]
            else:
                raise ValueError(
                    "Invalid propertiesFilter value -- must provide at least one string value"
                )

        if dateobs is not None:
            with self.Session() as session:
                event = session.scalars(
                    GcnEvent.select(
                        session.user_or_token,
                        options=[
                            joinedload(GcnEvent.localizations),
                            joinedload(GcnEvent.gcn_notices),
                            joinedload(GcnEvent.observationplan_requests)
                            .joinedload(ObservationPlanRequest.allocation)
                            .joinedload(Allocation.instrument),
                            joinedload(GcnEvent.comments),
                            joinedload(GcnEvent.detectors),
                            joinedload(GcnEvent.properties),
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
                        (loc.to_dict() for loc in event.localizations),
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

            if properties_filter is not None:
                for prop_filt in properties_filter:
                    prop_split = prop_filt.split(":")
                    if not (len(prop_split) == 1 or len(prop_split) == 3):
                        raise ValueError(
                            "Invalid propertiesFilter value -- property filter must have 1 or 3 values"
                        )
                    name = prop_split[0].strip()

                    properties_query = GcnProperty.select(session.user_or_token)
                    if len(prop_split) == 3:
                        value = prop_split[1].strip()
                        try:
                            value = float(value)
                        except ValueError as e:
                            raise ValueError(f"Invalid propotation filter value: {e}")
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
                events.append({**event.to_dict(), "tags": list(set(event.tags))})

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


def add_tiles(localization_id):
    session = Session()
    try:
        localization = session.query(Localization).get(localization_id)

        tiles = [
            LocalizationTile(
                localization_id=localization.id, healpix=uniq, probdensity=probdensity
            )
            for uniq, probdensity in zip(localization.uniq, localization.probdensity)
        ]

        session.add(localization)
        session.add_all(tiles)
        session.commit()
        return log(f"Generated tiles for localization {localization_id}")
    except Exception as e:
        return log(
            f"Unable to generate contour for localization {localization_id}: {e}"
        )
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
        return log(
            f"Unable to generate contour for localization {localization_id}: {e}"
        )
    finally:
        Session.remove()


class LocalizationHandler(BaseHandler):
    @auth_or_token
    def get(self, dateobs, localization_name):
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


class GcnSummaryHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs):
        """
        ---
          description: Get a summary of a GCN event.
          tags:
            - observations
          parameters:
            - in: query
              name: title
              schema:
                type: string
            - in: query
              name: number
              schema:
                type: string
            - in: query
              name: subject
              schema:
                type: string
            - in: query
              name: userIds
              schema:
                type: string
              description: User ids to mention in the summary. Comma-separated.
            - in: query
              name: groupId
              required: true
              schema:
                type: string
              description: id of the group that creates the summary.
            - in: query
              name: startDate
              required: true
              schema:
                type: string
              description: Filter by start date
            - in: query
              name: endDate
              required: true
              schema:
                type: string
              description: Filter by end date
            - in: query
              name: localizationName
              schema:
                type: string
              description: Name of localization / skymap to use.
            - in: query
              name: localizationCumprob
              schema:
                type: number
              description: Cumulative probability up to which to include fields. Defaults to 0.95.
            - in: query
              name: showSources
              required: true
              schema:
                type: bool
              description: Show sources in the summary
            - in: query
              name: showGalaxies
              required: true
              schema:
                type: bool
              description: Show galaxies in the summary
            - in: query
              name: showObservations
              required: true
              schema:
                type: bool
              description: Show observations in the summary
            - in: query
              name: noText
              schema:
                type: bool
              description: Do not include text in the summary, only tables.
            - in: query
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

        title = self.get_query_argument("title", None)
        number = self.get_query_argument("number", None)
        subject = self.get_query_argument("subject")
        user_ids = self.get_query_argument("userIds", None)
        group_id = self.get_query_argument("groupId", None)
        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        localization_name = self.get_query_argument('localizationName', None)
        localization_cumprob = self.get_query_argument('localizationCumprob', 0.95)
        show_sources = self.get_query_argument('showSources', False)
        show_galaxies = self.get_query_argument('showGalaxies', False)
        show_observations = self.get_query_argument('showObservations', False)
        no_text = self.get_query_argument('noText', False)
        photometry_in_window = self.get_query_argument('photometryInWindow', False)

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

        if not no_text:
            if title is None:
                return self.error("Title is required")
            if number is not None:
                try:
                    number = int(number)
                except ValueError:
                    return self.error("Number must be an integer")
            if subject is None:
                return self.error("Subject is required")
            if user_ids is not None:
                user_ids = [int(user_id) for user_id in user_ids.split(",")]
                try:
                    user_ids = [int(user_id) for user_id in user_ids]
                except ValueError:
                    return self.error("User IDs must be integers")
            else:
                user_ids = []
            if group_id is None:
                return self.error("Group ID is required")

        start_date_mjd = Time(arrow.get(start_date).datetime).mjd
        end_date_mjd = Time(arrow.get(end_date).datetime).mjd

        try:
            with self.Session() as session:
                contents = []
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                event = session.scalars(stmt).first()

                if event is None:
                    return self.error("Event not found", status=404)
                if not no_text:

                    stmt = Group.select(session.user_or_token).where(
                        Group.id == group_id
                    )
                    group = session.scalars(stmt).first()
                    if group is None:
                        return self.error(f"Group not found with ID {group_id}")

                    header_text = []

                    header_text.append(f"""TITLE: {title.upper()}\n""")
                    if number is not None:
                        header_text.append(f"""NUMBER: {number}\n""")
                    header_text.append(
                        f"""SUBJECT: {subject[0].upper()+subject[1:]}\n"""
                    )
                    now_date = astropy.time.Time.now()
                    header_text.append(f"""DATE: {now_date}\n""")
                    # add a "FROM full name and affiliation"
                    from_str = f"""FROM:  {self.associated_user_object.first_name} {self.associated_user_object.last_name} at Affiliation"""
                    if self.associated_user_object.contact_email is not None:
                        from_str += (
                            f""" <{self.associated_user_object.contact_email}>\n"""
                        )
                    header_text.append(from_str)

                    if len(user_ids) > 0:
                        # query user objects for all user_ids
                        users = []
                        for user_id in user_ids:
                            user = User.query.get(user_id)
                            if user is None:
                                return self.error(f"User ID {user_id} not found")
                            users.append(user)

                        users_txt = []
                        for user in users:
                            if (
                                user.first_name is not None
                                and user.last_name is not None
                            ):
                                users_txt.append(
                                    f"""{user.first_name[0].upper()}. {user.last_name} (Affiliation)"""  # hardcoded affiliation as it is not implemented yet
                                )
                        # create a string of all users, with 5 users per line
                        users_txt = "\n".join(
                            [
                                ", ".join(users_txt[i : i + 5])
                                for i in range(0, len(users_txt), 5)
                            ]
                        )
                        header_text.append(f"""\n{users_txt}\n""")

                    header_text.append(
                        f"""\non behalf of the {group.name}, report:\n"""
                    )
                    contents.extend(header_text)

                if show_sources:
                    sources_text = []
                    source_page_number = 1
                    sources = []
                    while True:
                        # get the sources in the event
                        sources_data = get_sources(
                            user_id=self.associated_user_object.id,
                            session=session,
                            first_detected_date=start_date,
                            last_detected_date=end_date,
                            localization_dateobs=dateobs,
                            localization_name=localization_name,
                            localization_cumprob=localization_cumprob,
                            page_number=source_page_number,
                            num_per_page=MAX_SOURCES_PER_PAGE,
                        )
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
                            aliases.append(
                                source['alias'] if 'alias' in source else None
                            )
                            ras.append(source['ra'] if 'ra' in source else None)
                            decs.append(source['dec'] if 'dec' in source else None)
                            redshift = (
                                source['redshift'] if 'redshift' in source else None
                            )
                            if 'redshift_error' in source and redshift is not None:
                                if source['redshift_error'] is not None:
                                    redshift = f"{redshift}±{source['redshift_error']}"  # maybe round to N decimal places?
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
                            tabulate(
                                df, headers='keys', tablefmt='psql', showindex=False
                            )
                            + "\n"
                        )
                        # now, create a photometry table per source
                        for source in sources:
                            stmt = Photometry.select(session.user_or_token).where(
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
                                        mags.append(
                                            f"< {np.round(phot['limiting_mag'], 1)}"
                                        )
                                    else:
                                        mags.append(None)
                                    filters.append(
                                        phot['filter'] if 'filter' in phot else None
                                    )
                                    origins.append(
                                        phot['origin'] if 'origin' in phot else None
                                    )
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
                                galaxy['catalog_name']
                                if 'catalog_name' in galaxy
                                else None
                            )
                            names.append(galaxy['name'] if 'name' in galaxy else None)
                            ras.append(galaxy['ra'] if 'ra' in galaxy else None)
                            decs.append(galaxy['dec'] if 'dec' in galaxy else None)
                            distmpcs.append(
                                galaxy['distmpc'] if 'distmpc' in galaxy else None
                            )
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
                            tabulate(
                                df, headers='keys', tablefmt='psql', showindex=False
                            )
                            + "\n"
                        )
                    contents.extend(galaxies_text)

                if show_observations:
                    # get the executed obs, by instrument
                    observations_text = []
                    start_date = arrow.get(start_date).datetime
                    end_date = arrow.get(end_date).datetime

                    stmt = Instrument.select(session.user_or_token).options(
                        joinedload(Instrument.telescope)
                    )
                    instruments = session.scalars(stmt).all()
                    if instruments is None:
                        return self.error("No instruments found")

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
                            total_time = sum(
                                obs["exposure_time"] for obs in observations
                            )
                            probability = data["probability"]
                            area = data["area"]

                            dt = start_observation.datetime - event.dateobs
                            before_after = (
                                "after" if dt.total_seconds() > 0 else "before"
                            )
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
                                    astropy.time.Time(
                                        obs["obstime"], format='datetime'
                                    ).mjd
                                    if "obstime" in obs
                                    else None
                                )
                                ras.append(
                                    obs['field']["ra"] if "ra" in obs['field'] else None
                                )
                                decs.append(
                                    obs['field']["dec"]
                                    if "dec" in obs['field']
                                    else None
                                )
                                filters.append(obs["filt"] if "filt" in obs else None)
                                exposures.append(
                                    obs["exposure_time"]
                                    if "exposure_time" in obs
                                    else None
                                )
                                limmags.append(
                                    obs["limmag"] if "limmag" in obs else None
                                )
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
        except Exception as e:
            return self.error(f"Error generating summary: {e}")
        return self.success(data=contents)
