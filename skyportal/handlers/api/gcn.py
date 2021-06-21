# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import datetime
import os
import gcn
import lxml
import xmlschema
from urllib.parse import urlparse

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    GcnEvent,
    GcnNotice,
    GcnTag,
    Localization,
)
from ...utils.gcn import get_dateobs, get_tags, get_skymap, get_contour


class GcnHandler(BaseHandler):
    @auth_or_token
    def put(self):
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
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        payload = data['xml']

        schema = f'{os.path.dirname(__file__)}/../../utils/schema/VOEvent-v2.0.xsd'
        voevent_schema = xmlschema.XMLSchema(schema)
        if voevent_schema.is_valid(payload):
            root = lxml.etree.fromstring(payload.encode('ascii'))
        else:
            raise Exception("xml file is not valid VOEvent")

        dateobs = get_dateobs(root)

        try:
            event = GcnEvent.query.filter_by(dateobs=dateobs).one()
        except NoResultFound:
            DBSession().add(
                GcnEvent(dateobs=dateobs, sent_by_id=self.associated_user_object.id)
            )
            self.verify_and_commit()
            event = GcnEvent.query.filter_by(dateobs=dateobs).one()

        tags = [GcnTag(dateobs=event.dateobs, text=text) for text in get_tags(root)]

        gcn_notice = GcnNotice(
            content=payload.encode('ascii'),
            ivorn=root.attrib['ivorn'],
            notice_type=gcn.get_notice_type(root),
            stream=urlparse(root.attrib['ivorn']).path.lstrip('/'),
            date=root.find('./Who/Date').text,
            dateobs=event.dateobs,
        )

        for tag in tags:
            DBSession().add(tag)
            self.verify_and_commit()
        DBSession().add(gcn_notice)

        skymap = get_skymap(root, gcn_notice)
        skymap["dateobs"] = event.dateobs

        try:
            localization = Localization.query.filter_by(
                dateobs=dateobs, localization_name=skymap["localization_name"]
            ).one()
        except NoResultFound:
            localization = Localization(**skymap)
            localization = get_contour(localization)
            DBSession().add(localization)

        self.verify_and_commit()

        return self.success()


default_prefs = {'maxNumGcnEvents': 10, 'sinceDaysAgo': 3650}


class GcnEventViewsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve GCN events
        tags:
          - gcnevents
        responses:
          200:
            content:
              application/json:
                schema: GcnEventViewsHandlerGet
          400:
            content:
              application/json:
                schema: Error
        """
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        top_events_prefs = user_prefs.get('topGcnEvents', {})
        top_events_prefs = {**default_prefs, **top_events_prefs}

        max_num_events = int(top_events_prefs['maxNumGcnEvents'])
        since_days_ago = int(top_events_prefs['sinceDaysAgo'])

        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
        q = (
            GcnEvent.query.options(joinedload(GcnEvent.localizations))
            .filter(GcnEvent.dateobs > cutoff_day)
            .limit(max_num_events)
        )

        events = []
        for event in q.all():
            events.append({**event.to_dict(), "tags": event.tags})

        return self.success(data=events)


class GcnEventHandler(BaseHandler):
    @auth_or_token
    def get(self, dateobs):
        """
        ---
        description: Retrieve a GCN event
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
                schema: GcnEventHandlerGet
          400:
            content:
              application/json:
                schema: Error
        """

        event = (
            GcnEvent.query.options(
                joinedload(GcnEvent.localizations),
                joinedload(GcnEvent.gcn_notices),
            )
            .filter_by(dateobs=dateobs)
            .first()
        )
        data = {**event.to_dict(), "tags": event.tags}

        return self.success(data=data)


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
        localization = Localization.query.filter_by(
            dateobs=dateobs, localization_name=localization_name
        ).first()
        data = {**localization.to_dict(), "flat_2d": localization.flat_2d}

        return self.success(data=data)
