import datetime
from functools import reduce

import tornado.web
from dateutil.parser import isoparse
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
import arrow
from marshmallow.exceptions import ValidationError
import healpix_alchemy as ha
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession, Comment, Instrument, Photometry, Obj, Source, SourceView,
    Thumbnail, Token, User, Group, FollowupRequest
)
from .internal.source_views import register_source_view
from ...utils import (
    get_nearby_offset_stars, facility_parameters, source_image_parameters,
    get_finding_chart
)
from .candidate import grab_query_results_page

SOURCES_PER_PAGE = 100


class SourceHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        single:
          description: Retrieve a source
          parameters:
            - in: path
              name: obj_id
              required: false
              schema:
                type: string
          responses:
            200:
              content:
                application/json:
                  schema: SingleObj
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all sources
          parameters:
          - in: query
            name: ra
            nullable: true
            schema:
              type: number
            description: RA for spatial filtering
          - in: query
            name: dec
            nullable: true
            schema:
              type: number
            description: Declination for spatial filtering
          - in: query
            name: radius
            nullable: true
            schema:
              type: number
            description: Radius for spatial filtering if ra & dec are provided
          - in: query
            name: sourceID
            nullable: true
            schema:
              type: string
            description: Portion of ID to filter on
          - in: query
            name: simbadClass
            nullable: true
            schema:
              type: string
            description: Simbad class to filter on
          - in: query
            name: hasTNSname
            nullable: true
            schema:
              type: boolean
            description: If true, return only those matches with TNS names
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of sources to return per paginated request. Defaults to 100. Max 1000.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1
          - in: query
            name: totalMatches
            nullable: true
            schema:
              type: integer
            description: |
              Used only in the case of paginating query results - if provided, this
              allows for avoiding a potentially expensive query.count() call.
          - in: query
            name: startDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              last_detected >= startDate
          - in: query
            name: endDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              last_detected <= endDate
          responses:
            200:
              content:
                application/json:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: object
                        properties:
                          data:
                            type: object
                            properties:
                              sources:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Obj'
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              lastPage:
                                type: boolean
                              numberingStart:
                                type: integer
                              numberingEnd:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """
        page_number = self.get_query_argument('pageNumber', None)
        num_per_page = min(
            int(self.get_query_argument("numPerPage", SOURCES_PER_PAGE)), 1000
        )
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
        if obj_id:
            if is_token_request:
                # Logic determining whether to register front-end request as view lives in front-end
                register_source_view(obj_id=obj_id,
                                     username_or_token_id=self.current_user.id,
                                     is_token=True)
            s = Source.get_obj_if_owned_by(
                obj_id, self.current_user,
                options=[joinedload(Source.obj)
                         .joinedload(Obj.followup_requests)
                         .joinedload(FollowupRequest.requester),
                         joinedload(Source.obj)
                         .joinedload(Obj.followup_requests)
                         .joinedload(FollowupRequest.instrument),
                         joinedload(Source.obj)
                         .joinedload(Obj.thumbnails)
                         .joinedload(Thumbnail.photometry)
                         .joinedload(Photometry.instrument)
                         .joinedload(Instrument.telescope)])
            if s is None:
                return self.error("Invalid source ID.")
            s.comments = s.get_comments_owned_by(self.current_user)
            s.classifications = s.get_classifications_owned_by(self.current_user)
            source_info = s.to_dict()
            source_info["last_detected"] = s.last_detected
            source_info["groups"] = Group.query.filter(
                Group.id.in_(
                    DBSession().query(Source.group_id).filter(
                        Source.obj_id == obj_id
                    )
                )
            ).all()

            return self.success(data=source_info)
        if page_number:
            try:
                page = int(page_number)
            except ValueError:
                return self.error("Invalid page number value.")
            q = Obj.query.filter(Obj.id.in_(DBSession().query(
                Source.obj_id).filter(Source.group_id.in_(
                    [g.id for g in self.current_user.groups]))))
            if sourceID:
                q = q.filter(Obj.id.contains(sourceID.strip()))
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
                other = ha.Point(ra=ra, dec=dec)
                q = q.filter(Obj.within(other, radius))
            if start_date:
                start_date = arrow.get(start_date.strip())
                q = q.filter(Obj.last_detected >= start_date)
            if end_date:
                end_date = arrow.get(end_date.strip())
                q = q.filter(Obj.last_detected <= end_date)
            if simbad_class:
                q = q.filter(func.lower(Obj.altdata['simbad']['class'].astext)
                             == simbad_class.lower())
            if has_tns_name in ['true', True]:
                q = q.filter(Obj.altdata['tns']['name'].isnot(None))

            try:
                query_results = grab_query_results_page(
                    q, total_matches, page, num_per_page, "sources"
                )
            except ValueError as e:
                if "Page number out of range" in str(e):
                    return self.error("Page number out of range.")
                raise
            source_list = []
            for source in query_results["sources"]:
                source.comments = source.get_comments_owned_by(self.current_user)
                source_list.append(source.to_dict())
                source_list[-1]["last_detected"] = source.last_detected
            query_results["sources"] = source_list
            return self.success(data=query_results)

        sources = Obj.query.filter(Obj.id.in_(
            DBSession().query(Source.obj_id).filter(Source.group_id.in_(
                [g.id for g in self.current_user.groups]
            ))
        )).all()
        source_list = []
        for source in sources:
            source.comments = source.get_comments_owned_by(self.current_user)
            source_list.append(source.to_dict())
            source_list[-1]["last_detected"] = source.last_detected
        return self.success(data={"sources": source_list})

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Add a new source
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/Obj'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of associated group IDs. If not specified, all of the
                          user or token's groups will be used.
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: string
                              description: New source ID
        """
        data = self.get_json()
        schema = Obj.__schema__()
        user_group_ids = [g.id for g in self.current_user.groups]
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        if not user_group_ids:
            return self.error("You must belong to one or more groups before "
                              "you can add sources.")
        try:
            group_ids = [int(id) for id in data.pop('group_ids')
                         if int(id) in user_accessible_group_ids]
        except KeyError:
            group_ids = user_group_ids
        if not group_ids:
            return self.error("Invalid group_ids field. Please specify at least "
                              "one valid group ID that you belong to.")
        try:
            obj = schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        groups = Group.query.filter(Group.id.in_(group_ids)).all()
        if not groups:
            return self.error("Invalid group_ids field. Please specify at least "
                              "one valid group ID that you belong to.")
        DBSession().add(obj)
        DBSession().add_all([Source(obj=obj, group=group) for group in groups])
        DBSession().commit()

        self.push_all(action="skyportal/FETCH_SOURCES")
        self.push_all(action="skyportal/FETCH_CANDIDATES")
        return self.success(data={"id": obj.id})

    @permissions(['Manage sources'])
    def put(self, obj_id):
        """
        ---
        description: Update a source
        parameters:
          - in: path
            name: obj_id
            required: True
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema: ObjNoID
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
        s = Source.get_obj_if_owned_by(obj_id, self.current_user)
        data = self.get_json()
        data['id'] = obj_id

        schema = Obj.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success(action='skyportal/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def delete(self, obj_id, group_id):
        """
        ---
        description: Delete a source
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
          - in: path
            name: group_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        if group_id not in [g.id for g in self.current_user.accessible_groups]:
            return self.error("Inadequate permissions.")
        s = (DBSession().query(Source).filter(Source.obj_id == obj_id)
             .filter(Source.group_id == group_id).first())
        s.active = False
        s.unsaved_by = self.current_user
        DBSession().commit()

        return self.success(action='skyportal/FETCH_SOURCES')


class SourceOffsetsHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve offset stars to aid in spectroscopy
        parameters:
        - in: path
          name: obj_id
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
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
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
        source = Source.get_obj_if_owned_by(obj_id, self.current_user)
        if source is None:
            return self.error('Invalid source ID.')

        facility = self.get_query_argument('facility', 'Keck')
        how_many = self.get_query_argument('how_many', '3')
        obstime = self.get_query_argument(
            'obstime', datetime.datetime.utcnow().isoformat()
        )
        if not isinstance(isoparse(obstime), datetime.datetime):
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
                get_nearby_offset_stars(
                    source.ra, source.dec,
                    obj_id,
                    how_many=how_many,
                    radius_degrees=radius_degrees,
                    mag_limit=mag_limit,
                    min_sep_arcsec=min_sep_arcsec,
                    starlist_type=facility,
                    mag_min=mag_min,
                    obstime=obstime,
                    allowed_queries=2
                )

        except ValueError:
            return self.error('Error while querying for nearby offset stars')

        starlist_str = \
            "\n".join([x["str"].replace(" ", "&nbsp;") for x in starlist_info])
        return self.success(
            data={
                'facility': facility,
                'starlist_str': starlist_str,
                'starlist_info': starlist_info,
                'ra': source.ra,
                'dec': source.dec,
                'noffsets': noffsets,
                'queries_issued': queries_issued,
                'query': query_string
            }
        )


class SourceFinderHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Generate a PDF finding chart to aid in spectroscopy
        parameters:
        - in: path
          name: obj_id
          required: true
          schema:
            type: string
        - in: query
          name: imsize
          schema:
            type: float
            minimum: 2
            maximum: 15
          description: Image size in arcmin (square)
        - in: query
          name: facility
          nullable: true
          schema:
            type: string
            enum: [Keck, Shane, P200]
        - in: query
          name: image_source
          nullable: true
          schema:
            type: string
            enum: [desi, dss, ztfref]
          description: Source of the image used in the finding chart
        - in: query
          name: obstime
          nullable: True
          schema:
            type: string
          description: |
            datetime of observation in isoformat (e.g. 2020-12-30T12:34:10)
        responses:
          200:
            description: A PDF finding chart file
            content:
              application/pdf:
                schema:
                  type: string
                  format: binary
          400:
            content:
              application/json:
                schema: Error
        """
        source = Source.get_obj_if_owned_by(obj_id, self.current_user)
        if source is None:
            return self.error('Invalid source ID.')

        imsize = self.get_query_argument('imsize', '4.0')
        try:
            imsize = float(imsize)
        except ValueError:
            # could not handle inputs
            return self.error('Invalid argument for `imsize`')

        if imsize < 2.0 or imsize > 15.0:
            return \
                self.error('The value for `imsize` is outside the allowed range')

        facility = self.get_query_argument('facility', 'Keck')
        image_source = self.get_query_argument('image_source', 'desi')

        how_many = 3
        obstime = self.get_query_argument(
            'obstime', datetime.datetime.utcnow().isoformat()
        )
        if not isinstance(isoparse(obstime), datetime.datetime):
            return self.error('obstime is not valid isoformat')

        if facility not in facility_parameters:
            return self.error('Invalid facility')

        if image_source not in source_image_parameters:
            return self.error('Invalid source image')

        radius_degrees = facility_parameters[facility]["radius_degrees"]
        mag_limit = facility_parameters[facility]["mag_limit"]
        min_sep_arcsec = facility_parameters[facility]["min_sep_arcsec"]
        mag_min = facility_parameters[facility]["mag_min"]

        rez = get_finding_chart(
            source.ra, source.dec, obj_id,
            image_source=image_source,
            output_format='pdf',
            imsize=imsize,
            how_many=how_many,
            radius_degrees=radius_degrees,
            mag_limit=mag_limit,
            mag_min=mag_min,
            min_sep_arcsec=min_sep_arcsec,
            starlist_type=facility,
            obstime=obstime,
            use_source_pos_in_starlist=True,
            allowed_queries=2,
            queries_issued=0
        )

        filename = rez["name"]
        image = rez["data"]

        # do not send result via `.success`, since that creates a JSON
        self.set_status(200)
        self.set_header("Content-Type", "application/pdf; charset='utf-8'")
        self.set_header("Content-Disposition",
                        f"attachment; filename={filename}")
        self.set_header('Cache-Control',
                        'no-store, no-cache, must-revalidate, max-age=0')

        return self.write(image)
