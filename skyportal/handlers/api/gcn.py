# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import os
import gcn
import lxml
import xmlschema
from urllib.parse import urlparse
from tornado.ioloop import IOLoop

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker, scoped_session

from baselayer.app.access import auth_or_token
from baselayer.log import make_log
from ..base import BaseHandler
from ...models import (
    DBSession,
    Allocation,
    GcnEvent,
    GcnNotice,
    GcnTag,
    Localization,
    LocalizationTile,
    ObservationPlanRequest,
    User,
)
from ...utils.gcn import get_dateobs, get_tags, get_skymap, get_contour

log = make_log('api/gcn_event')


Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


def post_gcnevent(payload, user_id, session):
    """Post GcnEvent to database.
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

    try:
        event = GcnEvent.query.filter_by(dateobs=dateobs).one()

        if not event.is_accessible_by(user, mode="update"):
            raise ValueError(
                "Insufficient permissions: GCN event can only be updated by original poster"
            )

    except NoResultFound:
        event = GcnEvent(dateobs=dateobs, sent_by_id=user.id)
        session.add(event)

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

    for tag in tags:
        session.add(tag)
    session.add(gcn_notice)

    skymap = get_skymap(root, gcn_notice)
    if skymap is None:
        return event.id

    skymap["dateobs"] = event.dateobs
    skymap["sent_by_id"] = user.id

    try:
        localization = (
            Localization.query_records_accessible_by(
                user,
            )
            .filter_by(
                dateobs=dateobs,
                localization_name=skymap["localization_name"],
            )
            .one()
        )
    except NoResultFound:
        localization = Localization(**skymap)
        session.add(localization)
        session.commit()

        log(f"Generating tiles/contours for localization {localization.id}")

        IOLoop.current().run_in_executor(None, lambda: add_tiles(localization.id))
        IOLoop.current().run_in_executor(None, lambda: add_contour(localization.id))

    return event.id


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
            return self.error("xml must be present in data to parse GcnEvent")

        payload = data['xml']
        with DBSession() as session:
            event_id = post_gcnevent(payload, self.associated_user_object.id, session)

        return self.success(data={'gcnevent_id': event_id})

    @auth_or_token
    def get(self, dateobs=None):
        """
        ---
        description: Retrieve GCN events
        tags:
          - gcnevents
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
        if dateobs is not None:
            event = (
                GcnEvent.query_records_accessible_by(
                    self.current_user,
                    options=[
                        joinedload(GcnEvent.localizations),
                        joinedload(GcnEvent.gcn_notices),
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
                        joinedload(GcnEvent.comments),
                    ],
                )
                .filter_by(dateobs=dateobs)
                .first()
            )
            if event is None:
                return self.error("GCN event not found", status=404)

            data = {
                **event.to_dict(),
                "tags": event.tags,
                "lightcurve": event.lightcurve,
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

            # go through some pain to get probability and area included
            # as these are properties
            request_data = []
            for ii, req in enumerate(data['observationplan_requests']):
                dat = req.to_dict()
                plan_data = []
                for plan in dat["observation_plans"]:
                    plan_dict = {
                        **plan.to_dict(),
                        "probability": plan.probability,
                        "area": plan.area,
                        "num_observations": plan.num_observations,
                    }
                    plan_data.append(plan_dict)
                dat["observation_plans"] = plan_data
                request_data.append(dat)
            data['observationplan_requests'] = request_data
            return self.success(data=data)

        q = GcnEvent.query_records_accessible_by(
            self.current_user,
            options=[
                joinedload(GcnEvent.localizations),
                joinedload(GcnEvent.gcn_notices),
                joinedload(GcnEvent.observationplan_requests),
            ],
        )

        events = []
        for event in q.all():
            events.append({**event.to_dict(), "tags": event.tags})

        return self.success(data=events)

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
        event = GcnEvent.query.filter_by(dateobs=dateobs).first()
        if event is None:
            return self.error("GCN event not found", status=404)

        if not event.is_accessible_by(self.current_user, mode="delete"):
            return self.error(
                "Insufficient permissions: GCN event can only be deleted by original poster"
            )

        DBSession().delete(event)
        self.verify_and_commit()

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

        localization = (
            Localization.query_records_accessible_by(self.current_user)
            .filter(
                Localization.dateobs == dateobs,
                Localization.localization_name == localization_name,
            )
            .first()
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

        localization = Localization.query.filter_by(
            dateobs=dateobs, localization_name=localization_name
        ).first()

        if localization is None:
            return self.error("Localization not found", status=404)

        if not localization.is_accessible_by(self.current_user, mode="delete"):
            return self.error(
                "Insufficient permissions: Localization can only be deleted by original poster"
            )

        DBSession().delete(localization)
        self.verify_and_commit()

        return self.success()
