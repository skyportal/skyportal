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
