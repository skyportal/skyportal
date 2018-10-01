import tornado.web
from sqlalchemy.orm import joinedload
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.handlers import BaseHandler
from ..models import (DBSession, Comment, Instrument, Photometry, Source,
                      Thumbnail)


class SourceHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id_or_page_num=None, page_number_given=False):
        info = {}
        sources_per_page = 100
        if source_id_or_page_num is not None and not page_number_given:
            source_id = source_id_or_page_num
            info['sources'] = Source.get_if_owned_by(source_id, self.current_user,
                                          options=[joinedload(Source.comments)
                                                   .joinedload(Comment.user),
                                                   joinedload(Source.thumbnails)
                                                   .joinedload(Thumbnail.photometry)
                                                   .joinedload(Photometry.instrument)
                                                   .joinedload(Instrument.telescope)])
        elif page_number_given:
            page = int(source_id_or_page_num)
            info['sources'] = list(self.current_user.sources)[
                ((page - 1) * sources_per_page):(page * sources_per_page)]
            info['page_number'] = page

        if info['sources'] is not None:
            return self.success(info)
        else:
            return self.error(f"Could not load source {source_id}",
                              {"source_id": source_id_or_page_num})

    @permissions(['Manage sources'])
    def post(self):
        data = self.get_json()

        s = Source(ra=data['sourceRA'], dec=data['sourceDec'],
                   redshift=data.get('sourceRedShift'))
        DBSession().add(s)
        DBSession().commit()

        return self.success({"id": s.id}, 'cesium/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def put(self, source_id):
        data = self.get_json()

        s = Source.query.get(source_id)
        s.ra = data['sourceRA']
        s.dec = data['sourceDec']
        s.redshift = data.get('sourceRedShift')
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def delete(self, source_id):
        s = Source.query.get(source_id)
        DBSession().delete(s)
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')
