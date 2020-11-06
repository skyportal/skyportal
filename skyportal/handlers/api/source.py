import datetime
from json.decoder import JSONDecodeError
import python_http_client.exceptions
from twilio.base.exceptions import TwilioException
import tornado
from tornado.ioloop import IOLoop
import io
import math
from dateutil.parser import isoparse
from sqlalchemy.orm import joinedload
from sqlalchemy import func, or_
import arrow
from marshmallow.exceptions import ValidationError
import functools
import healpix_alchemy as ha
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    Allocation,
    Instrument,
    Photometry,
    Obj,
    Source,
    Token,
    Group,
    FollowupRequest,
    ClassicalAssignment,
    ObservingRun,
    SourceNotification,
)
from .internal.source_views import register_source_view
from ...utils import (
    get_nearby_offset_stars,
    facility_parameters,
    source_image_parameters,
    get_finding_chart,
    _calculate_best_position_for_offset_stars,
)
from .candidate import grab_query_results_page, update_redshift_history_if_relevant


SOURCES_PER_PAGE = 100

_, cfg = load_env()


def add_ps1_thumbnail_and_push_ws_msg(obj, request_handler):
    try:
        obj.add_ps1_thumbnail()
    except (ValueError, ConnectionError) as e:
        return request_handler.error(f"Unable to generate PS1 thumbnail URL: {e}")
    request_handler.push_all(
        action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
    )


class SourceHandler(BaseHandler):
    @auth_or_token
    def head(self, obj_id=None):
        """
        ---
        single:
          description: Check if a Source exists
          parameters:
            - in: path
              name: obj_id
              required: true
              schema:
                type: string
          responses:
            200:
              content:
                application/json:
                  schema: Success
            404:
              content:
                application/json:
                  schema: Error
        """
        user_group_ids = [g.id for g in self.associated_user_object.accessible_groups]
        num_s = (
            DBSession()
            .query(Source)
            .filter(Source.obj_id == obj_id)
            .filter(Source.group_id.in_(user_group_ids))
            .count()
        )
        if num_s > 0:
            return self.success()
        else:
            self.set_status(404)
            self.finish()

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
          - in: query
            name: group_ids
            nullable: true
            schema:
              type: list
              items:
                type: integer
            description: |
               If provided, filter only sources saved to one of these group IDs.
          - in: query
            name: includePhotometry
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated photometry. Defaults to
              false.
          - in: query
            name: includeRequested
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include requested saves. Defaults to
              false.
          - in: query
            name: pendingOnly
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to only include requested/pending saves.
              Defaults to false.
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
                              numPerPage:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """
        page_number = self.get_query_argument('pageNumber', None)
        num_per_page = min(
            int(self.get_query_argument("numPerPage", SOURCES_PER_PAGE)), 100
        )
        ra = self.get_query_argument('ra', None)
        dec = self.get_query_argument('dec', None)
        radius = self.get_query_argument('radius', None)
        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        sourceID = self.get_query_argument('sourceID', None)  # Partial ID to match
        include_photometry = self.get_query_argument("includePhotometry", False)
        include_requested = self.get_query_argument("includeRequested", False)
        requested_only = self.get_query_argument("pendingOnly", False)

        # parse the group ids:
        group_ids = self.get_query_argument('group_ids', None)
        if group_ids is not None:
            try:
                group_ids = [int(gid) for gid in group_ids.split(',')]
            except ValueError:
                return self.error(
                    f'Invalid group ids field ({group_ids}; Could not parse all elements to integers'
                )

        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]

        simbad_class = self.get_query_argument('simbadClass', None)
        has_tns_name = self.get_query_argument('hasTNSname', None)
        total_matches = self.get_query_argument('totalMatches', None)
        is_token_request = isinstance(self.current_user, Token)
        if obj_id is not None:
            query_options = [
                joinedload(Source.obj)
                .joinedload(Obj.followup_requests)
                .joinedload(FollowupRequest.requester),
                joinedload(Source.obj)
                .joinedload(Obj.followup_requests)
                .joinedload(FollowupRequest.allocation)
                .joinedload(Allocation.instrument),
                joinedload(Source.obj)
                .joinedload(Obj.assignments)
                .joinedload(ClassicalAssignment.run)
                .joinedload(ObservingRun.instrument)
                .joinedload(Instrument.telescope),
                joinedload(Source.obj).joinedload(Obj.thumbnails),
                joinedload(Source.obj)
                .joinedload(Obj.followup_requests)
                .joinedload(FollowupRequest.allocation)
                .joinedload(Allocation.group),
            ]
            if include_photometry:
                query_options.append(
                    joinedload(Source.obj)
                    .joinedload(Obj.photometry)
                    .joinedload(Photometry.instrument)
                )
            if is_token_request:
                # Logic determining whether to register front-end request as view lives in front-end
                register_source_view(
                    obj_id=obj_id,
                    username_or_token_id=self.current_user.id,
                    is_token=True,
                )
                self.push_all(action="skyportal/FETCH_TOP_SOURCES")
            s = Source.get_obj_if_owned_by(
                obj_id, self.current_user, options=query_options,
            )
            if s is None:
                return self.error("Source not found", status=404)
            if "ps1" not in [thumb.type for thumb in s.thumbnails]:
                IOLoop.current().add_callback(
                    lambda: add_ps1_thumbnail_and_push_ws_msg(s, self)
                )
            comments = s.get_comments_owned_by(self.current_user)
            source_info = s.to_dict()
            source_info["comments"] = sorted(
                [c.to_dict() for c in comments],
                key=lambda x: x["created_at"],
                reverse=True,
            )
            for comment in source_info["comments"]:
                comment["author"] = comment["author"].to_dict()
                del comment["author"]["preferences"]
            source_info["annotations"] = sorted(
                s.get_annotations_owned_by(self.current_user), key=lambda x: x.origin,
            )
            source_info["classifications"] = s.get_classifications_owned_by(
                self.current_user
            )
            source_info["last_detected"] = s.last_detected
            source_info["gal_lat"] = s.gal_lat_deg
            source_info["gal_lon"] = s.gal_lon_deg
            source_info["luminosity_distance"] = s.luminosity_distance
            source_info["dm"] = s.dm
            source_info["angular_diameter_distance"] = s.angular_diameter_distance

            source_info["followup_requests"] = [
                f for f in source_info['followup_requests'] if f.status != 'deleted'
            ]
            query = (
                DBSession()
                .query(Group)
                .join(Source)
                .filter(
                    Source.obj_id == source_info["id"],
                    Group.id.in_(user_accessible_group_ids),
                )
            )
            if include_requested:
                query = query.filter(
                    or_(Source.requested.is_(True), Source.active.is_(True))
                )
            elif not requested_only:
                query = query.filter(Source.active.is_(True))
            if requested_only:
                query = query.filter(Source.active.is_(False)).filter(
                    Source.requested.is_(True)
                )
            source_info["groups"] = [g.to_dict() for g in query.all()]
            for group in source_info["groups"]:
                source_table_row = Source.query.filter(
                    Source.obj_id == s.id, Source.group_id == group["id"]
                ).first()
                group["active"] = source_table_row.active
                group["requested"] = source_table_row.requested
                group["saved_at"] = source_table_row.saved_at
                group["saved_by"] = (
                    source_table_row.saved_by.to_dict()
                    if source_table_row.saved_by is not None
                    else None
                )

            # add the date(s) this source was saved to each of these groups
            for i, g in enumerate(source_info["groups"]):
                saved_at = (
                    DBSession()
                    .query(Source.saved_at)
                    .filter(
                        Source.obj_id == source_info["id"], Source.group_id == g["id"]
                    )
                    .first()
                    .saved_at
                )
                source_info["groups"][i]['saved_at'] = saved_at

            return self.success(data=source_info)

        # Fetch multiple sources
        query_options = [joinedload(Obj.thumbnails)]
        if include_photometry:
            query_options.append(
                joinedload(Obj.photometry).joinedload(Photometry.instrument)
            )
        source_filter_condition = (
            or_(Source.requested.is_(True), Source.active.is_(True))
            if include_requested
            else Source.active.is_(True)
        )
        q = (
            DBSession()
            .query(Obj)
            .join(Source)
            .filter(
                source_filter_condition,
                Source.group_id.in_(
                    user_accessible_group_ids
                ),  # only give sources the user has access to
            )
            .options(query_options)
        )

        if sourceID:
            q = q.filter(Obj.id.contains(sourceID.strip()))
        if any([ra, dec, radius]):
            if not all([ra, dec, radius]):
                return self.error(
                    "If any of 'ra', 'dec' or 'radius' are "
                    "provided, all three are required."
                )
            try:
                ra = float(ra)
                dec = float(dec)
                radius = float(radius)
            except ValueError:
                return self.error(
                    "Invalid values for ra, dec or radius - could not convert to float"
                )
            other = ha.Point(ra=ra, dec=dec)
            q = q.filter(Obj.within(other, radius))
        if start_date:
            start_date = arrow.get(start_date.strip())
            q = q.filter(Obj.last_detected >= start_date)
        if end_date:
            end_date = arrow.get(end_date.strip())
            q = q.filter(Obj.last_detected <= end_date)
        if simbad_class:
            q = q.filter(
                func.lower(Obj.altdata['simbad']['class'].astext)
                == simbad_class.lower()
            )
        if has_tns_name in ['true', True]:
            q = q.filter(Obj.altdata['tns']['name'].isnot(None))
        if group_ids is not None:
            if not all(gid in user_accessible_group_ids for gid in group_ids):
                return self.error(
                    f"One of the requested groups in '{group_ids}' is inaccessible to user."
                )
            q = q.filter(Source.group_id.in_(group_ids))
            if include_requested:
                q = q.filter(or_(Source.requested.is_(True), Source.active.is_(True)))
            elif not requested_only:
                q = q.filter(Source.active.is_(True))
            if requested_only:
                q = q.filter(Source.active.is_(False)).filter(
                    Source.requested.is_(True)
                )

        if page_number:
            try:
                page = int(page_number)
            except ValueError:
                return self.error("Invalid page number value.")
            try:
                query_results = grab_query_results_page(
                    q,
                    total_matches,
                    page,
                    num_per_page,
                    "sources",
                    include_photometry=include_photometry,
                )
            except ValueError as e:
                if "Page number out of range" in str(e):
                    return self.error("Page number out of range.")
                raise
        else:
            query_results = {"sources": q.all()}

        source_list = []
        for source in query_results["sources"]:
            source_list.append(source.to_dict())
            source_list[-1]["comments"] = sorted(
                [s.to_dict() for s in source.get_comments_owned_by(self.current_user)],
                key=lambda x: x["created_at"],
                reverse=True,
            )
            for comment in source_list[-1]["comments"]:
                comment["author"] = comment["author"].to_dict()
                del comment["author"]["preferences"]
            source_list[-1]["classifications"] = source.get_classifications_owned_by(
                self.current_user
            )
            source_list[-1]["annotations"] = sorted(
                source.get_annotations_owned_by(self.current_user),
                key=lambda x: x.origin,
            )
            source_list[-1]["last_detected"] = source.last_detected
            source_list[-1]["gal_lon"] = source.gal_lon_deg
            source_list[-1]["gal_lat"] = source.gal_lat_deg
            source_list[-1]["luminosity_distance"] = source.luminosity_distance
            source_list[-1]["dm"] = source.dm
            source_list[-1][
                "angular_diameter_distance"
            ] = source.angular_diameter_distance
            source_list[-1]["groups"] = [
                g.to_dict()
                for g in (
                    DBSession()
                    .query(Group)
                    .join(Source)
                    .filter(
                        Source.obj_id == source_list[-1]["id"],
                        source_filter_condition,
                        Group.id.in_(user_accessible_group_ids),
                    )
                    .all()
                )
            ]
            for group in source_list[-1]["groups"]:
                source_table_row = Source.query.filter(
                    Source.obj_id == source.id, Source.group_id == group["id"]
                ).first()
                group["active"] = source_table_row.active
                group["requested"] = source_table_row.requested
                group["saved_at"] = source_table_row.saved_at
                group["saved_by"] = (
                    source_table_row.saved_by.to_dict()
                    if source_table_row.saved_by is not None
                    else None
                )

            # add the date(s) this source was saved to each of these groups
            for i, g in enumerate(source_list[-1]["groups"]):
                saved_at = (
                    DBSession()
                    .query(Source.saved_at)
                    .filter(
                        Source.obj_id == source_list[-1]["id"],
                        Source.group_id == g["id"],
                    )
                    .first()
                    .saved_at
                )
                source_list[-1]["groups"][i]['saved_at'] = saved_at

        query_results["sources"] = source_list

        return self.success(data=query_results)

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
        obj_already_exists = Obj.query.get(data["id"]) is not None
        schema = Obj.__schema__()

        ra = data.get('ra', None)
        dec = data.get('dec', None)

        if ra is None and not obj_already_exists:
            return self.error("RA must not be null for a new Obj")

        if dec is None and not obj_already_exists:
            return self.error("Dec must not be null for a new Obj")

        user_group_ids = [g.id for g in self.current_user.groups]
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        if not user_group_ids:
            return self.error(
                "You must belong to one or more groups before " "you can add sources."
            )
        try:
            group_ids = [
                int(id)
                for id in data.pop('group_ids')
                if int(id) in user_accessible_group_ids
            ]
        except KeyError:
            group_ids = user_group_ids
        if not group_ids:
            return self.error(
                "Invalid group_ids field. Please specify at least "
                "one valid group ID that you belong to."
            )
        try:
            obj = schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        previously_saved = Source.query.filter(Source.obj_id == obj.id).first()

        groups = Group.query.filter(Group.id.in_(group_ids)).all()
        if not groups:
            return self.error(
                "Invalid group_ids field. Please specify at least "
                "one valid group ID that you belong to."
            )

        update_redshift_history_if_relevant(data, obj, self.associated_user_object)

        DBSession().add(obj)
        DBSession().add_all(
            [
                Source(obj=obj, group=group, saved_by_id=self.associated_user_object.id)
                for group in groups
            ]
        )
        DBSession().commit()
        if not obj_already_exists:
            obj.add_linked_thumbnails()

        self.push_all(action="skyportal/FETCH_SOURCES")
        # If we're updating a source
        if previously_saved is not None:
            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )

        self.push_all(
            action="skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
        )
        self.push_all(action="skyportal/FETCH_RECENT_SOURCES")
        return self.success(data={"id": obj.id})

    @permissions(['Upload data'])
    def patch(self, obj_id):
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
        # Permissions check
        _ = Source.get_obj_if_owned_by(obj_id, self.current_user)
        data = self.get_json()
        data['id'] = obj_id

        schema = Obj.__schema__()
        try:
            obj = schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        update_redshift_history_if_relevant(data, obj, self.associated_user_object)
        DBSession().commit()
        self.push_all(
            action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key},
        )

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
        s = (
            DBSession()
            .query(Source)
            .filter(Source.obj_id == obj_id)
            .filter(Source.group_id == group_id)
            .first()
        )
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
          name: num_offset_stars
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
        - in: query
          name: use_ztfref
          required: false
          schema:
            type: boolean
          description: |
            Use ZTFref catalog for offset star positions, otherwise Gaia DR2
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
        source = Source.get_obj_if_owned_by(
            obj_id,
            self.current_user,
            options=[joinedload(Source.obj).joinedload(Obj.photometry)],
        )
        if source is None:
            return self.error('Source not found', status=404)

        initial_pos = (source.ra, source.dec)

        try:
            best_ra, best_dec = _calculate_best_position_for_offset_stars(
                source.photometry,
                fallback=(initial_pos[0], initial_pos[1]),
                how="snr2",
            )
        except JSONDecodeError:
            self.push_notification(
                'Source position using photometry points failed.'
                ' Reverting to discovery position.'
            )
            best_ra, best_dec = initial_pos[0], initial_pos[1]

        facility = self.get_query_argument('facility', 'Keck')
        num_offset_stars = self.get_query_argument('num_offset_stars', '3')
        use_ztfref = self.get_query_argument('use_ztfref', True)
        if isinstance(use_ztfref, str):
            use_ztfref = use_ztfref in ['t', 'True', 'true', 'yes', 'y']

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
            num_offset_stars = int(num_offset_stars)
        except ValueError:
            # could not handle inputs
            return self.error('Invalid argument for `num_offset_stars`')

        try:
            (
                starlist_info,
                query_string,
                queries_issued,
                noffsets,
                used_ztfref,
            ) = get_nearby_offset_stars(
                best_ra,
                best_dec,
                obj_id,
                how_many=num_offset_stars,
                radius_degrees=radius_degrees,
                mag_limit=mag_limit,
                min_sep_arcsec=min_sep_arcsec,
                starlist_type=facility,
                mag_min=mag_min,
                obstime=obstime,
                allowed_queries=2,
                use_ztfref=use_ztfref,
            )
        except ValueError:
            return self.error('Error while querying for nearby offset stars')

        starlist_str = "\n".join(
            [x["str"].replace(" ", "&nbsp;") for x in starlist_info]
        )

        return self.success(
            data={
                'facility': facility,
                'starlist_str': starlist_str,
                'starlist_info': starlist_info,
                'ra': source.ra,
                'dec': source.dec,
                'noffsets': noffsets,
                'queries_issued': queries_issued,
                'query': query_string,
            }
        )


class SourceFinderHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id):
        """
        ---
        description: Generate a PDF/PNG finding chart to aid in spectroscopy
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
          name: use_ztfref
          required: false
          schema:
            type: boolean
          description: |
            Use ZTFref catalog for offset star positions, otherwise DR2
        - in: query
          name: obstime
          nullable: True
          schema:
            type: string
          description: |
            datetime of observation in isoformat (e.g. 2020-12-30T12:34:10)
        - in: query
          name: type
          nullable: true
          schema:
            type: string
            enum: [png, pdf]
          description: |
            output type
        - in: query
          name: num_offset_stars
          schema:
            type: integer
            minimum: 0
            maximum: 4
          description: |
            output desired number of offset stars [0,5] (default: 3)
        responses:
          200:
            description: A PDF/PNG finding chart file
            content:
              application/pdf:
                schema:
                  type: string
                  format: binary
              image/png:
                schema:
                  type: string
                  format: binary
          400:
            content:
              application/json:
                schema: Error
        """
        source = Source.get_obj_if_owned_by(
            obj_id,
            self.current_user,
            options=[joinedload(Source.obj).joinedload(Obj.photometry)],
        )
        if source is None:
            return self.error('Source not found', status=404)

        output_type = self.get_query_argument('type', 'pdf')
        if output_type not in ["png", "pdf"]:
            return self.error(f'Invalid argument for `type`: {output_type}')

        imsize = self.get_query_argument('imsize', '4.0')
        try:
            imsize = float(imsize)
        except ValueError:
            # could not handle inputs
            return self.error('Invalid argument for `imsize`')

        if imsize < 2.0 or imsize > 15.0:
            return self.error('The value for `imsize` is outside the allowed range')

        initial_pos = (source.ra, source.dec)
        try:
            best_ra, best_dec = _calculate_best_position_for_offset_stars(
                source.photometry,
                fallback=(initial_pos[0], initial_pos[1]),
                how="snr2",
            )
        except JSONDecodeError:
            self.push_notification(
                'Source position using photometry points failed.'
                ' Reverting to discovery position.'
            )
            best_ra, best_dec = initial_pos[0], initial_pos[1]

        facility = self.get_query_argument('facility', 'Keck')
        image_source = self.get_query_argument('image_source', 'ztfref')
        use_ztfref = self.get_query_argument('use_ztfref', True)
        if isinstance(use_ztfref, str):
            use_ztfref = use_ztfref in ['t', 'True', 'true', 'yes', 'y']

        num_offset_stars = self.get_query_argument('num_offset_stars', '3')
        try:
            num_offset_stars = int(num_offset_stars)
        except ValueError:
            # could not handle inputs
            return self.error('Invalid argument for `num_offset_stars`')

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

        finder = functools.partial(
            get_finding_chart,
            best_ra,
            best_dec,
            obj_id,
            image_source=image_source,
            output_format=output_type,
            imsize=imsize,
            how_many=num_offset_stars,
            radius_degrees=radius_degrees,
            mag_limit=mag_limit,
            mag_min=mag_min,
            min_sep_arcsec=min_sep_arcsec,
            starlist_type=facility,
            obstime=obstime,
            use_source_pos_in_starlist=True,
            allowed_queries=2,
            queries_issued=0,
            use_ztfref=use_ztfref,
        )

        self.push_notification(
            'Finding chart generation in progress. Download will start soon.'
        )
        rez = await IOLoop.current().run_in_executor(None, finder)

        filename = rez["name"]
        image = io.BytesIO(rez["data"])

        # Adapted from
        # https://bhch.github.io/posts/2017/12/serving-large-files-with-tornado-safely-without-blocking/
        mb = 1024 * 1024 * 1
        chunk_size = 1 * mb
        max_file_size = 15 * mb
        if not (image.getbuffer().nbytes < max_file_size):
            return self.error(
                f"Refusing to send files larger than {max_file_size / mb:.2f} MB"
            )

        # do not send result via `.success`, since that creates a JSON
        self.set_status(200)
        if output_type == "pdf":
            self.set_header("Content-Type", "application/pdf; charset='utf-8'")
            self.set_header("Content-Disposition", f"attachment; filename={filename}")
        else:
            self.set_header("Content-type", f"image/{output_type}")

        self.set_header(
            'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'
        )

        for i in range(math.ceil(max_file_size / chunk_size)):
            chunk = image.read(chunk_size)
            if not chunk:
                break
            try:
                self.write(chunk)  # write the chunk to response
                await self.flush()  # send the chunk to client
            except tornado.iostream.StreamClosedError:
                # this means the client has closed the connection
                # so break the loop
                break
            finally:
                # deleting the chunk is very important because
                # if many clients are downloading files at the
                # same time, the chunks in memory will keep
                # increasing and will eat up the RAM
                del chunk

                # pause the coroutine so other handlers can run
                await tornado.gen.sleep(1e-9)  # 1 ns


class SourceNotificationHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Send out a new source notification
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  additionalNotes:
                    type: string
                    description: |
                      Notes to append to the message sent out
                  groupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups whose members should get the notification (if they've opted in)
                  sourceId:
                    type: string
                    description: |
                      The ID of the Source's Obj the notification is being sent about
                  level:
                    type: string
                    description: |
                      Either 'soft' or 'hard', determines whether to send an email or email+SMS notification
                required:
                  - groupIds
                  - sourceId
                  - level
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
                              description: New SourceNotification ID
        """
        if not cfg["notifications.enabled"]:
            return self.error("Notifications are not enabled in current deployment.")
        data = self.get_json()

        additional_notes = data.get("additionalNotes")
        if isinstance(additional_notes, str):
            additional_notes = data["additionalNotes"].strip()
        else:
            if additional_notes is not None:
                return self.error(
                    "Invalid parameter `additionalNotes`: should be a string"
                )

        if data.get("groupIds") is None:
            return self.error("Missing required parameter `groupIds`")
        try:
            group_ids = [int(gid) for gid in data["groupIds"]]
        except ValueError:
            return self.error(
                "Invalid value provided for `groupIDs`; unable to parse "
                "all list items to integers."
            )

        groups = DBSession().query(Group).filter(Group.id.in_(group_ids)).all()

        if data.get("sourceId") is None:
            return self.error("Missing required parameter `sourceId`")

        source = Source.get_obj_if_owned_by(data["sourceId"], self.current_user)
        if source is None:
            return self.error('Source not found', status=404)

        source_id = data["sourceId"]

        source_group_ids = [
            row[0]
            for row in DBSession()
            .query(Source.group_id)
            .filter(Source.obj_id == source_id)
            .all()
        ]

        if bool(set(group_ids).difference(set(source_group_ids))):
            forbidden_groups = list(set(group_ids) - set(source_group_ids))
            return self.error(
                "Insufficient recipient group access permissions. Not a member of "
                f"group IDs: {forbidden_groups}."
            )

        if data.get("level") is None:
            return self.error("Missing required parameter `level`")
        if data["level"] not in ["soft", "hard"]:
            return self.error(
                "Invalid value provided for `level`: should be either 'soft' or 'hard'"
            )
        level = data["level"]

        new_notification = SourceNotification(
            source_id=source_id,
            groups=groups,
            additional_notes=additional_notes,
            sent_by=self.associated_user_object,
            level=level,
        )
        DBSession().add(new_notification)
        try:
            DBSession().commit()
        except python_http_client.exceptions.UnauthorizedError:
            return self.error(
                "Twilio Sendgrid authorization error. Please ensure "
                "valid Sendgrid API key is set in server environment as "
                "per their setup docs."
            )
        except TwilioException:
            return self.error(
                "Twilio Communication SMS API authorization error. Please ensure "
                "valid Twilio API key is set in server environment as "
                "per their setup docs."
            )

        return self.success(data={'id': new_notification.id})
