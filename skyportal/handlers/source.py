import tornado.web
from sqlalchemy.orm import joinedload
from sqlalchemy.dialects import postgresql
import datetime
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.handlers import BaseHandler
from ..models import (DBSession, Comment, Instrument, Photometry, Source,
                      Thumbnail)


SOURCES_PER_PAGE = 100


class SourceHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id_or_page_num=None, page_number_given=False):
        info = {}
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
                ((page - 1) * SOURCES_PER_PAGE):(page * SOURCES_PER_PAGE)]
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


class FilterSourcesHandler(BaseHandler):
    @auth_or_token
    # def get(self, sourceID=None, ra=None, dec=None, radius=None,
    #          startDate=None, endDate=None, simbadClass=None, hasTNSname=None):
    def post(self):
        data = self.get_json()
        info = {}
        page = int(data['pageNumber'])
        info['page_number'] = page
        q = Source.query

        if data['sourceID']:
            q = q.filter(Source.id.contains(data['sourceID'].strip()))
        if data['ra'] and data['dec'] and data['radius']:
            ra = float(data['ra'])
            dec = float(data['dec'])
            radius = float(data['radius'])
            q = q.filter(Source.ra <= ra + radius)\
                 .filter(Source.ra >= ra - radius)\
                 .filter(Source.dec <= dec + radius)\
                 .filter(Source.dec >= dec - radius)
        if data['startDate'] and data['endDate']:
            start_date = datetime.datetime.strptime(data['startDate'].strip(),
                                                    '%Y-%m-%dT%H:%M:%S')
            end_date = datetime.datetime.strptime(data['endDate'].strip(),
                                                  '%Y-%m-%dT%H:%M:%S')
            q = q.filter(Source.last_detected >= start_date).filter(
                Source.last_detected <= end_date)
        if data['simbadClass']:
            q = q.filter(Source.simbad_class == data['simbadClass'])
        if data['hasTNSname']:
            q = q.filter(Source.tns_name.isnot(None))
        sql_str = str(q.statement.compile(dialect=postgresql.dialect(),
                                          compile_kwargs={'literal_binds': True}))
        # TODO: Create materialized view with above SQL code
        info['sources'] = [s for s in list(q) if s in self.current_user.sources][
            ((page - 1) * SOURCES_PER_PAGE):(page * SOURCES_PER_PAGE)]
        info['last_page'] = len(info['sources']) < 100

        return self.success(info)
