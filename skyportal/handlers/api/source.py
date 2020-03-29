import datetime
from functools import reduce

import tornado.web
from dateutil.parser import isoparse
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
import arrow
from marshmallow.exceptions import ValidationError

from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession, Comment, Instrument, Photometry, Source, SourceView,
    Thumbnail, GroupSource, Token, User, Group
)
from .internal.source_views import register_source_view
from ...utils import get_nearby_offset_stars, facility_parameters

SOURCES_PER_PAGE = 100


class SourceHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id=None):
        """
        ---
        single:
          description: Retrieve a source
          parameters:
            - in: path
              name: source_id
              required: false
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleSource
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all sources
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfSources
            400:
              content:
                application/json:
                  schema: Error
        """
        info = {}
        page_number = self.get_query_argument('pageNumber', None)
        ra = self.get_query_argument('ra', None)
        dec = self.get_query_argument('dec', None)
        radius = self.get_query_argument('radius', None)
        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        sourceID = self.get_query_argument('sourceID', None)  # Partial ID to match
        simbad_class = self.get_query_argument('simbadClass', None)
        has_tns_name = self.get_query_argument('hasTNSname', None)
        total_matches = self.get_query_argument('totalMatches', None)
        is_token_request = isinstance(self.current_user, Token)
        if source_id:
            if is_token_request:
                # Logic determining whether to register front-end request as view lives in front-end
                register_source_view(source_id=source_id,
                                     username_or_token_id=self.current_user.id,
                                     is_token=True)
            info['sources'] = Source.get_if_owned_by(
                source_id, self.current_user,
                options=[joinedload(Source.comments),
                         joinedload(Source.thumbnails)
                         .joinedload(Thumbnail.photometry)
                         .joinedload(Photometry.instrument)
                         .joinedload(Instrument.telescope)])
        elif page_number:
            try:
                page = int(page_number)
            except ValueError:
                return self.error("Invalid page number value.")
            q = Source.query.filter(Source.id.in_(DBSession.query(
                GroupSource.source_id).filter(GroupSource.group_id.in_(
                    [g.id for g in self.current_user.groups]))))
            if sourceID:
                q = q.filter(Source.id.contains(sourceID.strip()))
            if any([ra, dec, radius]):
                if not all([ra, dec, radius]):
                    return self.error("If any of 'ra', 'dec' or 'radius' are "
                                      "provided, all three are required.")
                try:
                    ra = float(ra)
                    dec = float(dec)
                    radius = float(radius)
                except ValueError:
                    return self.error("Invalid values for ra, dec or radius - could not convert to float")
                q = q.filter(Source.ra <= ra + radius)\
                     .filter(Source.ra >= ra - radius)\
                     .filter(Source.dec <= dec + radius)\
                     .filter(Source.dec >= dec - radius)
            if start_date:
                start_date = arrow.get(start_date.strip())
                q = q.filter(Source.last_detected >= start_date)
            if end_date:
                end_date = arrow.get(end_date.strip())
                q = q.filter(Source.last_detected <= end_date)
            if simbad_class:
                q = q.filter(func.lower(Source.simbad_class) == simbad_class.lower())
            if has_tns_name == 'true':
                q = q.filter(Source.tns_name.isnot(None))

            if total_matches:
                info['totalMatches'] = int(total_matches)
            else:
                info['totalMatches'] = q.count()
            if (((info['totalMatches'] < (page - 1) * SOURCES_PER_PAGE and
                  info['totalMatches'] % SOURCES_PER_PAGE != 0) or
                 (info['totalMatches'] < page * SOURCES_PER_PAGE and
                  info['totalMatches'] % SOURCES_PER_PAGE == 0) and
                 info['totalMatches'] != 0) or
                    page <= 0 or (info['totalMatches'] == 0 and page != 1)):
                return self.error("Page number out of range.")
            info['sources'] = q.limit(SOURCES_PER_PAGE).offset(
                (page - 1) * SOURCES_PER_PAGE).all()

            info['pageNumber'] = page
            info['lastPage'] = info['totalMatches'] <= page * SOURCES_PER_PAGE
            info['sourceNumberingStart'] = (page - 1) * SOURCES_PER_PAGE + 1
            info['sourceNumberingEnd'] = min(info['totalMatches'],
                                             page * SOURCES_PER_PAGE)
            if info['totalMatches'] == 0:
                info['sourceNumberingStart'] = 0
        else:
            if is_token_request:
                token = self.current_user
                info['sources'] = list(reduce(
                    set.union, (set(group.sources) for group in token.groups)))
            else:
                info['sources'] = self.current_user.sources

        if info['sources'] is not None:
            return self.success(data=info)
        else:
            return self.error(f"Could not load source {source_id}",
                              data={"source_id": source_id})

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload a source. If group_ids is not specified, the user or token's groups will be used.
        requestBody:
          content:
            application/json:
              schema: Source
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        id:
                          type: string
                          description: New source ID
        """
        data = self.get_json()
        schema = Source.__schema__()
        user_group_ids = [g.id for g in self.current_user.groups]
        if not user_group_ids:
            return self.error("You must belong to one or more groups before "
                              "you can add sources.")
        try:
            group_ids = [id for id in data.pop('group_ids') if id in user_group_ids]
        except KeyError:
            group_ids = user_group_ids
        if not group_ids:
            return self.error("Invalid group_ids field. Please specify at least "
                              "one valid group ID that you belong to.")
        try:
            s = schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        groups = Group.query.filter(Group.id.in_(group_ids)).all()
        if not groups:
            return self.error("Invalid group_ids field. Please specify at least "
                              "one valid group ID that you belong to.")
        s.groups = groups
        DBSession.add(s)
        DBSession().commit()

        self.push_all(action='skyportal/FETCH_SOURCES')
        return self.success(data={"id": s.id})

    @permissions(['Manage sources'])
    def put(self, source_id):
        """
        ---
        description: Update a source
        parameters:
          - in: path
            name: source_id
            required: True
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema: SourceNoID
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
        s = Source.get_if_owned_by(source_id, self.current_user)
        data = self.get_json()
        data['id'] = source_id

        schema = Source.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success(action='skyportal/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def delete(self, source_id):
        """
        ---
        description: Delete a source
        parameters:
          - in: path
            name: source_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        s = Source.get_if_owned_by(source_id, self.current_user)
        DBSession.query(Source).filter(Source.id == source_id).delete()
        DBSession().commit()

        return self.success(action='skyportal/FETCH_SOURCES')


class SourcePhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id):
        """
        ---
        description: Retrieve a source's photometry
        parameters:
        - in: path
          name: source_id
          required: true
          schema:
            type: string
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfPhotometrys
          400:
            content:
              application/json:
                schema: Error
        """
        source = Source.query.get(source_id)
        if not source:
            return self.error('Invalid source ID.')
        if not set(source.groups).intersection(set(self.current_user.groups)):
            return self.error('Inadequate permissions.')
        return self.success(data={'photometry': source.photometry})


class SourceOffsetsHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id):
        """
        ---
        description: Retrieve offset stars to aid in spectroscopy
        parameters:
        - in: path
          name: source_id
          required: true
          schema:
            type: string
        - in: query
          name: facility
          nullable: true
          schema:
            type: string
            enum: [Keck, Shane, P200]
          description: Which facility to generate the starlist for
        - in: query
          name: how_many
          nullable: true
          schema:
            type: integer
            minimum: 0
            maximum: 10
          description: |
            Requested number of offset stars (set to zero to get starlist
            of just the source itself)
        - in: query
          name: obstime
          nullable: True
          schema:
            type: string
          description: |
            datetime of observation in isoformat (e.g. 2020-12-30T12:34:10)
        responses:
          200:
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    data:
                      type: object
                      properties:
                        facility:
                          type: string
                          enum: [Keck, Shane, P200]
                          description: Facility queried for starlist
                        starlist_str:
                          type: string
                          description: formatted starlist in facility format
                        starlist_info:
                          type: array
                          description: |
                            list of source and offset star information
                          items:
                            type: object
                            properties:
                              str:
                                type: string
                                description: single-line starlist format per object
                              ra:
                                type: number
                                format: float
                                description: object RA in degrees (J2000)
                              dec:
                                type: number
                                format: float
                                description: object DEC in degrees (J2000)
                              name:
                                type: string
                                description: object name
                              dras:
                                type: string
                                description: offset from object to source in RA
                              ddecs:
                                type: string
                                description: offset from object to source in DEC
                              mag:
                                type: number
                                format: float
                                description: |
                                  magnitude of object (from
                                  Gaia phot_rp_mean_mag)
                        ra:
                          type: number
                          format: float
                          description: source RA in degrees (J2000)
                        dec:
                          type: number
                          format: float
                          description: source DEC in degrees (J2000)
                        queries_issued:
                          type: integer
                          description: |
                            Number of times the catalog was queried to find
                            noffsets
                        noffsets:
                          type: integer
                          description: |
                            Number of suitable offset stars found (may be less)
                            than requested
                        query:
                          type: string
                          description: SQL query submitted to Gaia
          400:
            content:
              application/json:
                schema: Error
        """
        source = Source.get_if_owned_by(source_id, self.current_user)
        if source is None:
            return self.error('Invalid source ID.')

        facility = self.get_query_argument('facility', 'Keck')
        how_many = self.get_query_argument('how_many', '3')
        obstime_isoformat = \
            self.get_query_argument('obstime',
                                    datetime.datetime.utcnow().isoformat())
        if not isinstance(isoparse(obstime_isoformat), datetime.datetime):
            return self.error('obstime is not valid isoformat')

        if facility not in facility_parameters:
            return self.error('Invalid facility')

        radius_degrees = facility_parameters[facility]["radius_degrees"]
        mag_limit = facility_parameters[facility]["mag_limit"]
        min_sep_arcsec = facility_parameters[facility]["min_sep_arcsec"]
        mag_min = facility_parameters[facility]["mag_min"]

        try:
            how_many = int(how_many)
        except ValueError:
            # could not handle inputs
            return self.error('Invalid argument for `how_many`')

        try:
            starlist_info, query_string, queries_issued, noffsets = \
                get_nearby_offset_stars(source.ra, source.dec,
                                        source_id,
                                        how_many=how_many,
                                        radius_degrees=radius_degrees,
                                        mag_limit=mag_limit,
                                        min_sep_arcsec=min_sep_arcsec,
                                        starlist_type=facility,
                                        mag_min=mag_min,
                                        obstime_isoformat=obstime_isoformat,
                                        allowed_queries=2)

        except ValueError:
            return self.error('Error while querying for nearby offset stars')

        starlist_str = "\n".join([x["str"].replace(" ", "&nbsp;") for x in starlist_info])
        return self.success(data={'facility': facility,
                                  'starlist_str': starlist_str,
                                  'starlist_info': starlist_info,
                                  'ra': source.ra,
                                  'dec': source.dec,
                                  'noffsets': noffsets,
                                  'queries_issued': queries_issued,
                                  'query': query_string})


