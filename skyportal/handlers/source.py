from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Source
import tornado.web


class SourceHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, source_id=None):
        if source_id is not None:
            info = Source.query.get(source_id)
        else:
            info = list(Source.query)

        if info is None:
            return self.error(f"Could not load source {source_id}",
                              {"source_id": source_id})
        else:
            return self.success(info)

    @tornado.web.authenticated
    def post(self):
        data = self.get_json()

        s = Source(name=data['sourceName'], ra=data['sourceRA'],
                   dec=data['sourceDec'], red_shift=data.get('sourceRedShift'))
        DBSession().add(s)
        DBSession().commit()

        return self.success({"id": s.id}, 'cesium/FETCH_SOURCES')

    @tornado.web.authenticated
    def put(self, source_id):
        data = self.get_json()

        s = Source.query.get(source_id)
        s.name = data['sourceName']
        s.ra = data['sourceRA']
        dec = data['sourceDec']
        red_shift = data.get('sourceRedShift')
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')

    @tornado.web.authenticated
    def delete(self, source_id):
        s = Source.query.get(source_id)
        DBSession().delete(s)
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')
