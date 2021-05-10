# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import datetime
import os
import gcn
import lxml
import xmlschema
from urllib.parse import urlparse

from baselayer.app.env import load_env

from sqlalchemy.orm.exc import NoResultFound

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

gcn.include_notice_types(
    gcn.NoticeType.FERMI_GBM_FLT_POS,
    gcn.NoticeType.FERMI_GBM_GND_POS,
    gcn.NoticeType.FERMI_GBM_FIN_POS,
    gcn.NoticeType.FERMI_GBM_SUBTHRESH,
    gcn.NoticeType.LVC_PRELIMINARY,
    gcn.NoticeType.LVC_INITIAL,
    gcn.NoticeType.LVC_UPDATE,
    gcn.NoticeType.LVC_RETRACTION,
    gcn.NoticeType.AMON_ICECUBE_COINC,
    gcn.NoticeType.AMON_ICECUBE_HESE,
    gcn.NoticeType.ICECUBE_ASTROTRACK_GOLD,
    gcn.NoticeType.ICECUBE_ASTROTRACK_BRONZE,
)

_, cfg = load_env()


class GcnHandler(BaseHandler):
    @auth_or_token
    def put(self):
        """
        ---
        description: Ingest GCN xml file
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
            event = DBSession().merge(GcnEvent(dateobs=dateobs))
            DBSession().commit()

        tags = [GcnTag(dateobs=event.dateobs, text=_) for _ in get_tags(root)]

        gcn_notice = GcnNotice(
            content=payload.encode('ascii'),
            ivorn=root.attrib['ivorn'],
            notice_type=gcn.get_notice_type(root),
            stream=urlparse(root.attrib['ivorn']).path.lstrip('/'),
            date=root.find('./Who/Date').text,
            dateobs=event.dateobs,
        )

        for tag in tags:
            DBSession().merge(tag)
        DBSession().merge(gcn_notice)
        DBSession().commit()

        skymap = get_skymap(root, gcn_notice)
        skymap["dateobs"] = event.dateobs

        localization = Localization.query.filter_by(
            dateobs=dateobs, localization_name=skymap["localization_name"]
        ).all()
        if len(localization) == 0:
            DBSession().merge(Localization(**skymap))
            DBSession().commit()
        localization = Localization.query.filter_by(
            dateobs=dateobs, localization_name=skymap["localization_name"]
        ).one()

        localization = get_contour(localization)
        DBSession().merge(localization)
        DBSession().commit()

        return self.success()


default_prefs = {'maxNumGcnEvents': 10, 'sinceDaysAgo': 3650}


class GcnEventViewsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        top_events_prefs = user_prefs.get('topGcnEvents', {})
        top_events_prefs = {**default_prefs, **top_events_prefs}

        max_num_events = int(top_events_prefs['maxNumGcnEvents'])
        since_days_ago = int(top_events_prefs['sinceDaysAgo'])

        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
        q = GcnEvent.query

        events = []
        for event in q.all():
            if len(events) >= max_num_events:
                continue
            dateobs = event.dateobs
            if dateobs < cutoff_day:
                continue
            tags = [_ for _ in event.tags]
            localizations = [_.localization_name for _ in event.localizations]
            events.append(
                {'localizations': localizations, 'dateobs': dateobs, 'tags': tags}
            )

        return self.success(data=events)


class LocalizationHandler(BaseHandler):
    @auth_or_token
    def get(self, dateobs, localization_name):
        q = Localization.query.filter_by(
            dateobs=dateobs, localization_name=localization_name
        )
        localization = q.first()
        data = {
            'contour': localization.contour,
            'dateobs': localization.dateobs,
            'localization_name': localization.localization_name,
        }
        return self.success(data=data)
