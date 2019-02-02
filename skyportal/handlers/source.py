import tornado.web
from sqlalchemy.orm import joinedload
from sqlalchemy.dialects import postgresql
from sqlalchemy import func
import arrow
from sqlalchemy.engine.result import RowProxy

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.handlers import BaseHandler
from ..models import (DBSession, Comment, Instrument, Photometry, Source,
                      Thumbnail, GroupSource, MatView)


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
            q = Source.query.filter(Source.id.in_(DBSession.query(
                GroupSource.source_id).filter(GroupSource.group_id.in_(
                    [g.id for g in self.current_user.groups]))))
            sql_str = str(q.statement.compile(dialect=postgresql.dialect(),
                                              compile_kwargs={'literal_binds': True}))
            mv_name = (self.current_user.username.translate({
                ord(ch): '_' for ch in "!#$%&'*+-/=?^_`{|}~(),:;<>@[\]."}) +
                             "_all_sources")
            mv_sql_str = ("CREATE MATERIALIZED VIEW IF NOT EXISTS "
                          f"{mv_name} "
                          f"as {sql_str}")
            # mv_sql_str += " LIMIT 1000"
            DBSession.execute(mv_sql_str)
            mv = MatView.query.get(mv_name)
            if not mv:
                mv = MatView(id=mv_name, query_str=sql_str)
                DBSession.add(mv)
            else:
                mv.last_used = arrow.now()
            DBSession.commit()
            q = DBSession.execute(f'SELECT * FROM {mv_name}')
            all_matches = list(q)
            info['totalMatches'] = len(all_matches)
            info['sources'] = all_matches[
                ((page - 1) * SOURCES_PER_PAGE):(page * SOURCES_PER_PAGE)]
            if isinstance(info['sources'][0], RowProxy):
                info['sources'] = [dict(el.items()) if isinstance(el, RowProxy)
                                   else el for el in info['sources']]
            info['pageNumber'] = page
            info['sourceNumberingStart'] = (page - 1) * SOURCES_PER_PAGE + 1
            info['sourceNumberingEnd'] = min(info['totalMatches'],
                                             page * SOURCES_PER_PAGE)
            info['lastPage'] = info['totalMatches'] <= page * SOURCES_PER_PAGE
            if info['totalMatches'] == 0:
                info['sourceNumberingStart'] = 0

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
        page = int(data.get('pageNumber', 1))
        info['pageNumber'] = page
        # q = Source.query.filter(Source.id.in_(DBSession.query(
        #         GroupSource.source_id).filter(GroupSource.group_id.in_(
        #             [g.id for g in self.current_user.groups]))))
        # sql_str = str(q.statement.compile(dialect=postgresql.dialect(),
        #                                   compile_kwargs={'literal_binds': True}))
        # mv_name = self.current_user.username.translate({
        #     ord(ch): '_' for ch in "!#$%&'*+-/=?^_`{|}~(),:;<>@[\]."}) + "_all_sources"
        # mv_sql_str = ("CREATE MATERIALIZED VIEW IF NOT EXISTS "
        #                     f"{mv_name} "
        #                     f"as {sql_str}")
        # q = DBSession.execute(f'SELECT * FROM {mv_name}')
        # all_matches = q.fetchall()
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
        if data['startDate']:
            start_date = arrow.get(data['startDate'].strip())
            q = q.filter(Source.last_detected >= start_date)
        if data['endDate']:
            end_date = arrow.get(data['endDate'].strip())
            q = q.filter(Source.last_detected <= end_date)
        if data['simbadClass']:
            q = q.filter(func.lower(Source.simbad_class) ==
                         data['simbadClass'].lower())
        if data['hasTNSname']:
            q = q.filter(Source.tns_name.isnot(None))

        mv_name = (self.current_user.username.translate({
            ord(ch): '_' for ch in "!#$%&'*+-/=?^_`{|}~(),:;<>@[\]."}) + "_all_sources")
        query_sql_str = str(q.statement.compile(dialect=postgresql.dialect(),
                                                compile_kwargs={'literal_binds': True}))
        mv_query_sql_str = query_sql_str.replace('sources', mv_name)
        try:
            q = DBSession.execute(mv_query_sql_str)
        except Exception as e:
            DBSession.rollback()
            if f'relation "{mv_name}" does not exist' in str(e):
                q = Source.query.filter(Source.id.in_(DBSession.query(
                    GroupSource.source_id).filter(GroupSource.group_id.in_(
                        [g.id for g in self.current_user.groups]))))
                sql_str = str(q.statement.compile(dialect=postgresql.dialect(),
                                                  compile_kwargs={'literal_binds': True}))
                # sql_str += " LIMIT 1000"
                mv_sql_str = ("CREATE MATERIALIZED VIEW IF NOT EXISTS "
                              f"{mv_name} "
                              f"as {sql_str}")
                DBSession.execute(mv_sql_str)
                q = DBSession.execute(mv_query_sql_str)
            else:
                raise(e)

        all_matches = q.fetchall()
        info['totalMatches'] = len(all_matches)
        info['sources'] = all_matches[
            ((page - 1) * SOURCES_PER_PAGE):(page * SOURCES_PER_PAGE)]
        if isinstance(info['sources'][0], RowProxy):
            info['sources'] = [dict(el.items()) if isinstance(el, RowProxy)
                               else el for el in info['sources']]
        info['lastPage'] = info['totalMatches'] <= page * SOURCES_PER_PAGE
        info['sourceNumberingStart'] = (page - 1) * SOURCES_PER_PAGE + 1
        info['sourceNumberingEnd'] = min(info['totalMatches'],
                                         page * SOURCES_PER_PAGE)
        if info['totalMatches'] == 0:
            info['sourceNumberingStart'] = 0

        return self.success(info)
