import tornado.web
from baselayer.app.access import permissions
from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Source


class SourceHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, source_id=None):
        if source_id is not None:
            info = Source.get_if_owned_by(source_id, self.current_user)
        else:
            info = list(self.current_user.sources)

        if info is None:
            return self.error(f"Could not load source {source_id}",
                              {"source_id": source_id})
        else:
            return self.success(info)

    @permissions(['Manage sources'])
    def post(self):
        data = self.get_json()

        s = Source(name=data['sourceName'], ra=data['sourceRA'],
                   dec=data['sourceDec'], red_shift=data.get('sourceRedShift'))
        DBSession().add(s)
        DBSession().commit()

        return self.success({"id": s.id}, 'cesium/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def put(self, source_id):
        data = self.get_json()

        s = Source.query.get(source_id)
        s.name = data['sourceName']
        s.ra = data['sourceRA']
        dec = data['sourceDec']
        red_shift = data.get('sourceRedShift')
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def delete(self, source_id):
        s = Source.query.get(source_id)
        DBSession().delete(s)
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')
