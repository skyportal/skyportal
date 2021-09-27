import datetime
from json.decoder import JSONDecodeError
from dateutil.tz import UTC
import python_http_client.exceptions
from twilio.base.exceptions import TwilioException
import tornado
from tornado.ioloop import IOLoop
import io
import math
from dateutil.parser import isoparse
from sqlalchemy.orm import joinedload
from sqlalchemy import func, or_, distinct
import arrow
from marshmallow import Schema, fields
from marshmallow.exceptions import ValidationError
import functools
import healpix_alchemy as ha
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from ..base import BaseHandler
from ...models import (
    DBSession,
    Allocation,
    Annotation,
    Comment,
    Instrument,
    Obj,
    Source,
    Thumbnail,
    Token,
    Photometry,
    Group,
    FollowupRequest,
    ClassicalAssignment,
    ObservingRun,
    SourceNotification,
    Classification,
    Taxonomy,
    Listing,
    Spectrum,
    SourceView,
)
from ...utils.offset import (
    get_nearby_offset_stars,
    facility_parameters,
    source_image_parameters,
    get_finding_chart,
    _calculate_best_position_for_offset_stars,
)
from .candidate import grab_query_results, update_redshift_history_if_relevant
from .photometry import serialize
from .color_mag import get_color_mag

SOURCES_PER_PAGE = 100

_, cfg = load_env()


def apply_active_or_requested_filtering(query, include_requested, requested_only):
    if include_requested:
        query = query.filter(or_(Source.requested.is_(True), Source.active.is_(True)))
    elif not requested_only:
        query = query.filter(Source.active.is_(True))
    if requested_only:
        query = query.filter(Source.active.is_(False)).filter(
            Source.requested.is_(True)
        )
    return query


def add_ps1_thumbnail_and_push_ws_msg(obj_id, request_handler):
    try:
        obj = Obj.get_if_accessible_by(obj_id, request_handler.current_user)
        obj.add_ps1_thumbnail()
        request_handler.push_all(
            action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
        )
        request_handler.push_all(
            action="skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
        )
    except Exception as e:
        return request_handler.error(f"Unable to generate PS1 thumbnail URL: {e}")
    finally:
        DBSession.remove()


class SourceHandler(BaseHandler):
    @auth_or_token
    def head(self, obj_id=None):
        """
        ---
        single:
          description: Check if a Source exists
          tags:
            - sources
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
        self.verify_and_commit()
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
          tags:
            - sources
          parameters:
            - in: path
              name: obj_id
              required: false
              schema:
                type: string
            - in: query
              name: includePhotometry
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated photometry. Defaults to
                false.
            - in: query
              name: includeComments
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include comment metadata in response.
                Defaults to false.
            - in: query
              name: includePhotometryExists
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return if a source has any photometry points. Defaults to false.
            - in: query
              name: includeSpectrumExists
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return if a source has a spectra. Defaults to false.
            - in: query
              name: includeThumbnails
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated thumbnails. Defaults to false.
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
          tags:
            - sources
          parameters:
          - in: query
            name: ra
            nullable: true
            schema:
              type: number
            description: RA for spatial filtering (in decimal degrees)
          - in: query
            name: dec
            nullable: true
            schema:
              type: number
            description: Declination for spatial filtering (in decimal degrees)
          - in: query
            name: radius
            nullable: true
            schema:
              type: number
            description: Radius for spatial filtering if ra & dec are provided (in decimal degrees)
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
            name: alias
            nullable: true
            schema:
              type: array
              items:
                types: string
            description: additional name for the same object
          - in: query
            name: origin
            nullable: true
            schema:
              type: string
            description: who posted/discovered this source
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
              last_detected_at >= startDate
          - in: query
            name: endDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              last_detected_at <= endDate
          - in: query
            name: listName
            nullable: true
            schema:
              type: string
            description: |
              Get only sources saved to the querying user's list, e.g., "favorites".
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
            name: includeColorMagnitude
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include the color-magnitude data from Gaia.
              This will only include data for objects that have an annotation
              with the appropriate format: a key named Gaia that contains a dictionary
              with keys named Mag_G, Mag_Bp, Mag_Rp, and Plx
              (underscores and case are ignored when matching all the above keys).
              The result is saved in a field named 'color_magnitude'.
              If no data is available, returns an empty array.
              Defaults to false (do not search for nor include this info).
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
          - in: query
            name: savedBefore
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that were saved before this UTC datetime.
          - in: query
            name: savedAfter
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that were saved after this UTC datetime.
          - in: query
            name: saveSummary
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to only return the source save
              information in the response (defaults to false). If true,
              the response will contain a list of dicts with the following
              schema under `response['data']['sources']`:
              ```
                  {
                    "group_id": 2,
                    "created_at": "2020-11-13T22:11:25.910271",
                    "saved_by_id": 1,
                    "saved_at": "2020-11-13T22:11:25.910271",
                    "requested": false,
                    "unsaved_at": null,
                    "modified": "2020-11-13T22:11:25.910271",
                    "obj_id": "16fil",
                    "active": true,
                    "unsaved_by_id": null
                  }
              ```
          - in: query
            name: sortBy
            nullable: true
            schema:
              type: string
            description: |
              The field to sort by. Currently allowed options are ["id", "ra", "dec", "redshift", "saved_at"]
          - in: query
            name: sortOrder
            nullable: true
            schema:
              type: string
            description: |
              The sort order - either "asc" or "desc". Defaults to "asc"
          - in: query
            name: includeComments
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include comment metadata in response.
              Defaults to false.
          - in: query
            name: includePhotometryExists
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to return if a source has any photometry points. Defaults to false.
          - in: query
            name: includeSpectrumExists
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to return if a source has a spectra. Defaults to false.
          - in: query
            name: removeNested
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to remove nested output. Defaults to false.
          - in: query
            name: includeThumbnails
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated thumbnails. Defaults to false.
          - in: query
            name: includeDetectionStats
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include photometry detection statistics for each source
              (last detection and peak detection). Defaults to false.
          - in: query
            name: classifications
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
              Comma-separated string of "taxonomy: classification" pair(s) to filter for sources matching
              that/those classification(s), i.e. "Sitewide Taxonomy: Type II, Sitewide Taxonomy: AGN"
          - in: query
            name: minRedshift
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a redshift of at least this value
          - in: query
            name: maxRedshift
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a redshift of at most this value
          - in: query
            name: minPeakMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a peak photometry magnitude of at least this value
          - in: query
            name: maxPeakMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a peak photometry magnitude of at most this value
          - in: query
            name: minLatestMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources whose latest photometry magnitude is at least this value
          - in: query
            name: maxLatestMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources whose latest photometry magnitude is at most this value
          - in: query
            name: hasSpectrum
            nullable: true
            schema:
              type: boolean
            description: If true, return only those matches with at least one associated spectrum
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
        list_name = self.get_query_argument('listName', None)
        sourceID = self.get_query_argument('sourceID', None)  # Partial ID to match
        include_photometry = self.get_query_argument("includePhotometry", False)
        include_color_mag = self.get_query_argument("includeColorMagnitude", False)
        include_requested = self.get_query_argument("includeRequested", False)
        include_thumbnails = self.get_query_argument("includeThumbnails", False)
        requested_only = self.get_query_argument("pendingOnly", False)
        saved_after = self.get_query_argument('savedAfter', None)
        saved_before = self.get_query_argument('savedBefore', None)
        save_summary = self.get_query_argument('saveSummary', False)
        sort_by = self.get_query_argument("sortBy", None)
        sort_order = self.get_query_argument("sortOrder", "asc")
        include_comments = self.get_query_argument("includeComments", False)
        include_photometry_exists = self.get_query_argument(
            "includePhotometryExists", False
        )
        include_spectrum_exists = self.get_query_argument(
            "includeSpectrumExists", False
        )
        remove_nested = self.get_query_argument("removeNested", False)
        include_detection_stats = self.get_query_argument(
            "includeDetectionStats", False
        )
        classifications = self.get_query_argument("classifications", None)
        min_redshift = self.get_query_argument("minRedshift", None)
        max_redshift = self.get_query_argument("maxRedshift", None)
        min_peak_magnitude = self.get_query_argument("minPeakMagnitude", None)
        max_peak_magnitude = self.get_query_argument("maxPeakMagnitude", None)
        min_latest_magnitude = self.get_query_argument("minLatestMagnitude", None)
        max_latest_magnitude = self.get_query_argument("maxLatestMagnitude", None)
        has_spectrum = self.get_query_argument("hasSpectrum", False)

        # These are just throwaway helper classes to help with deserialization
        class UTCTZnaiveDateTime(fields.DateTime):
            """
            DateTime object that deserializes both timezone aware iso8601
            strings and naive iso8601 strings into naive datetime objects
            in utc

            See discussion in https://github.com/Scille/umongo/issues/44#issuecomment-244407236
            """

            def _deserialize(self, value, attr, data, **kwargs):
                value = super()._deserialize(value, attr, data, **kwargs)
                if value and value.tzinfo:
                    value = (value - value.utcoffset()).replace(tzinfo=None)
                return value

        class Validator(Schema):
            saved_after = UTCTZnaiveDateTime(required=False, missing=None)
            saved_before = UTCTZnaiveDateTime(required=False, missing=None)
            save_summary = fields.Boolean()
            remove_nested = fields.Boolean()
            include_thumbnails = fields.Boolean()

        validator_instance = Validator()
        params_to_be_validated = {}
        if saved_after is not None:
            params_to_be_validated['saved_after'] = saved_after
        if saved_before is not None:
            params_to_be_validated['saved_before'] = saved_before
        if save_summary is not None:
            params_to_be_validated['save_summary'] = save_summary
        if include_thumbnails is not None:
            params_to_be_validated['include_thumbnails'] = include_thumbnails
        if remove_nested is not None:
            params_to_be_validated['remove_nested'] = remove_nested

        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        saved_after = validated['saved_after']
        saved_before = validated['saved_before']
        save_summary = validated['save_summary']
        remove_nested = validated['remove_nested']
        include_thumbnails = validated['include_thumbnails']

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
        alias = self.get_query_argument('alias', None)
        origin = self.get_query_argument('origin', None)
        has_tns_name = self.get_query_argument('hasTNSname', None)
        total_matches = self.get_query_argument('totalMatches', None)
        is_token_request = isinstance(self.current_user, Token)
        if obj_id is not None:
            if include_thumbnails:
                s = Obj.get_if_accessible_by(
                    obj_id, self.current_user, options=[joinedload(Obj.thumbnails)]
                )
            else:
                s = Obj.get_if_accessible_by(obj_id, self.current_user)
            if s is None:
                return self.error("Source not found", status=404)
            source_info = s.to_dict()
            source_info["followup_requests"] = (
                FollowupRequest.query_records_accessible_by(
                    self.current_user,
                    options=[
                        joinedload(FollowupRequest.allocation).joinedload(
                            Allocation.instrument
                        ),
                        joinedload(FollowupRequest.allocation).joinedload(
                            Allocation.group
                        ),
                        joinedload(FollowupRequest.requester),
                    ],
                )
                .filter(FollowupRequest.obj_id == obj_id)
                .filter(FollowupRequest.status != "deleted")
                .all()
            )
            source_info["assignments"] = (
                ClassicalAssignment.query_records_accessible_by(
                    self.current_user,
                    options=[
                        joinedload(ClassicalAssignment.run)
                        .joinedload(ObservingRun.instrument)
                        .joinedload(Instrument.telescope)
                    ],
                )
                .filter(ClassicalAssignment.obj_id == obj_id)
                .all()
            )
            point = ha.Point(ra=s.ra, dec=s.dec)
            # Check for duplicates (within 4 arcsecs)
            duplicates = (
                Obj.query_records_accessible_by(self.current_user)
                .filter(Obj.within(point, 4 / 3600))
                .filter(Obj.id != s.id)
                .all()
            )
            if len(duplicates) > 0:
                source_info["duplicates"] = [dup.id for dup in duplicates]
            else:
                source_info["duplicates"] = None

            if is_token_request:
                # Logic determining whether to register front-end request as view lives in front-end
                sv = SourceView(
                    obj_id=obj_id,
                    username_or_token_id=self.current_user.id,
                    is_token=True,
                )
                DBSession.add(sv)
                # To keep loaded relationships from being cleared in verify_and_commit:
                source_info = recursive_to_dict(source_info)
                self.verify_and_commit()

            if include_thumbnails:
                if "ps1" not in [thumb.type for thumb in s.thumbnails]:
                    IOLoop.current().add_callback(
                        lambda: add_ps1_thumbnail_and_push_ws_msg(obj_id, self)
                    )
            if include_comments:
                comments = (
                    Comment.query_records_accessible_by(
                        self.current_user,
                        options=[
                            joinedload(Comment.author),
                            joinedload(Comment.groups),
                        ],
                    )
                    .filter(Comment.obj_id == obj_id)
                    .all()
                )
                source_info["comments"] = sorted(
                    [
                        {
                            **{
                                k: v
                                for k, v in c.to_dict().items()
                                if k != "attachment_bytes"
                            },
                            "author": {
                                **c.author.to_dict(),
                                "gravatar_url": c.author.gravatar_url,
                            },
                        }
                        for c in comments
                    ],
                    key=lambda x: x["created_at"],
                    reverse=True,
                )
            source_info["annotations"] = sorted(
                Annotation.query_records_accessible_by(
                    self.current_user, options=[joinedload(Annotation.author)]
                )
                .filter(Annotation.obj_id == obj_id)
                .all(),
                key=lambda x: x.origin,
            )
            readable_classifications = (
                Classification.query_records_accessible_by(self.current_user)
                .filter(Classification.obj_id == obj_id)
                .all()
            )

            readable_classifications_json = []
            for classification in readable_classifications:
                classification_dict = classification.to_dict()
                classification_dict['groups'] = [
                    g.to_dict() for g in classification.groups
                ]
                readable_classifications_json.append(classification_dict)

            source_info["classifications"] = readable_classifications_json
            if include_detection_stats:
                source_info["last_detected_at"] = s.last_detected_at(self.current_user)
                source_info["last_detected_mag"] = s.last_detected_mag(
                    self.current_user
                )
                source_info["peak_detected_at"] = s.peak_detected_at(self.current_user)
                source_info["peak_detected_mag"] = s.peak_detected_mag(
                    self.current_user
                )
            source_info["gal_lat"] = s.gal_lat_deg
            source_info["gal_lon"] = s.gal_lon_deg
            source_info["luminosity_distance"] = s.luminosity_distance
            source_info["dm"] = s.dm
            source_info["angular_diameter_distance"] = s.angular_diameter_distance

            if include_photometry:
                photometry = (
                    Photometry.query_records_accessible_by(self.current_user)
                    .filter(Photometry.obj_id == obj_id)
                    .all()
                )
                source_info["photometry"] = [
                    serialize(phot, 'ab', 'flux') for phot in photometry
                ]
            if include_photometry_exists:
                source_info["photometry_exists"] = (
                    len(
                        Photometry.query_records_accessible_by(self.current_user)
                        .filter(Photometry.obj_id == obj_id)
                        .all()
                    )
                    > 0
                )
            if include_spectrum_exists:
                source_info["spectrum_exists"] = (
                    len(
                        Spectrum.query_records_accessible_by(self.current_user)
                        .filter(Spectrum.obj_id == obj_id)
                        .all()
                    )
                    > 0
                )
            source_query = Source.query_records_accessible_by(self.current_user).filter(
                Source.obj_id == source_info["id"]
            )
            source_query = apply_active_or_requested_filtering(
                source_query, include_requested, requested_only
            )
            source_subquery = source_query.subquery()
            groups = (
                Group.query_records_accessible_by(self.current_user)
                .join(source_subquery, Group.id == source_subquery.c.group_id)
                .all()
            )
            source_info["groups"] = [g.to_dict() for g in groups]
            for group in source_info["groups"]:
                source_table_row = (
                    Source.query_records_accessible_by(self.current_user)
                    .filter(Source.obj_id == s.id, Source.group_id == group["id"])
                    .first()
                )
                if source_table_row is not None:
                    group["active"] = source_table_row.active
                    group["requested"] = source_table_row.requested
                    group["saved_at"] = source_table_row.saved_at
                    group["saved_by"] = (
                        source_table_row.saved_by.to_dict()
                        if source_table_row.saved_by is not None
                        else None
                    )
            if include_color_mag:
                source_info["color_magnitude"] = get_color_mag(
                    source_info["annotations"]
                )

            source_info = recursive_to_dict(source_info)
            self.verify_and_commit()
            return self.success(data=source_info)

        # Fetch multiple sources
        obj_query_options = (
            [joinedload(Obj.thumbnails)]
            if include_thumbnails and not remove_nested
            else []
        )

        obj_query = Obj.query_records_accessible_by(
            self.current_user, options=obj_query_options
        )
        source_query = Source.query_records_accessible_by(self.current_user)

        if sourceID:
            obj_query = obj_query.filter(Obj.id.contains(sourceID.strip()))
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
            obj_query = obj_query.filter(Obj.within(other, radius))
        if start_date:
            start_date = arrow.get(start_date.strip()).datetime
            obj_query = obj_query.filter(
                Obj.last_detected_at(self.current_user) >= start_date
            )
        if end_date:
            end_date = arrow.get(end_date.strip()).datetime
            obj_query = obj_query.filter(
                Obj.last_detected_at(self.current_user) <= end_date
            )
        if saved_before:
            source_query = source_query.filter(Source.saved_at <= saved_before)
        if saved_after:
            source_query = source_query.filter(Source.saved_at >= saved_after)
        if list_name:
            listing_subquery = (
                Listing.query_records_accessible_by(self.current_user)
                .filter(Listing.list_name == list_name)
                .filter(Listing.user_id == self.associated_user_object.id)
                .subquery()
            )
            obj_query = obj_query.join(
                listing_subquery, Obj.id == listing_subquery.c.obj_id
            )
        if simbad_class:
            obj_query = obj_query.filter(
                func.lower(Obj.altdata['simbad']['class'].astext)
                == simbad_class.lower()
            )
        if alias is not None:
            obj_query = obj_query.filter(Obj.alias.any(alias.strip()))
        if origin is not None:
            obj_query = obj_query.filter(Obj.origin.contains(origin.strip()))
        if has_tns_name in ['true', True]:
            obj_query = obj_query.filter(Obj.altdata['tns']['name'].isnot(None))
        if has_spectrum in ["true", True]:
            spectrum_subquery = Spectrum.query_records_accessible_by(
                self.current_user
            ).subquery()
            obj_query = obj_query.join(
                spectrum_subquery, Obj.id == spectrum_subquery.c.obj_id
            )
        if min_redshift is not None:
            try:
                min_redshift = float(min_redshift)
            except ValueError:
                return self.error(
                    "Invalid values for minRedshift - could not convert to float"
                )
            obj_query = obj_query.filter(Obj.redshift >= min_redshift)
        if max_redshift is not None:
            try:
                max_redshift = float(max_redshift)
            except ValueError:
                return self.error(
                    "Invalid values for maxRedshift - could not convert to float"
                )
            obj_query = obj_query.filter(Obj.redshift <= max_redshift)
        if min_peak_magnitude is not None:
            try:
                min_peak_magnitude = float(min_peak_magnitude)
            except ValueError:
                return self.error(
                    "Invalid values for minPeakMagnitude - could not convert to float"
                )
            obj_query = obj_query.filter(
                Obj.peak_detected_mag(self.current_user) >= min_peak_magnitude
            )
        if max_peak_magnitude is not None:
            try:
                max_peak_magnitude = float(max_peak_magnitude)
            except ValueError:
                return self.error(
                    "Invalid values for maxPeakMagnitude - could not convert to float"
                )
            obj_query = obj_query.filter(
                Obj.peak_detected_mag(self.current_user) <= max_peak_magnitude
            )
        if min_latest_magnitude is not None:
            try:
                min_latest_magnitude = float(min_latest_magnitude)
            except ValueError:
                return self.error(
                    "Invalid values for minLatestMagnitude - could not convert to float"
                )
            obj_query = obj_query.filter(
                Obj.last_detected_mag(self.current_user) >= min_latest_magnitude
            )
        if max_latest_magnitude is not None:
            try:
                max_latest_magnitude = float(max_latest_magnitude)
            except ValueError:
                return self.error(
                    "Invalid values for maxLatestMagnitude - could not convert to float"
                )
            obj_query = obj_query.filter(
                Obj.last_detected_mag(self.current_user) <= max_latest_magnitude
            )
        if classifications is not None or sort_by == "classification":
            if classifications is not None:
                if isinstance(classifications, str) and "," in classifications:
                    classifications = [c.strip() for c in classifications.split(",")]
                elif isinstance(classifications, str):
                    classifications = [classifications]
                else:
                    return self.error(
                        "Invalid classifications value -- must provide at least one string value"
                    )
                taxonomy_names, classifications = list(
                    zip(
                        *list(
                            map(
                                lambda c: (
                                    c.split(":")[0].strip(),
                                    c.split(":")[1].strip(),
                                ),
                                classifications,
                            )
                        )
                    )
                )
                classification_accessible_query = (
                    Classification.query_records_accessible_by(
                        self.current_user
                    ).subquery()
                )

                classification_query = (
                    DBSession()
                    .query(
                        distinct(Classification.obj_id).label("obj_id"),
                        Classification.classification,
                    )
                    .join(Taxonomy)
                    .filter(Classification.classification.in_(classifications))
                    .filter(Taxonomy.name.in_(taxonomy_names))
                )
                classification_subquery = classification_query.subquery()

                # We join in the classifications being filtered for first before
                # the filter for accessible classifications to speed up the query
                # (this way seems to help the query planner come to more optimal join
                # strategies)
                obj_query = obj_query.join(
                    classification_subquery,
                    Obj.id == classification_subquery.c.obj_id,
                )
                obj_query = obj_query.join(
                    classification_accessible_query,
                    Obj.id == classification_accessible_query.c.obj_id,
                )

            else:
                # Not filtering on classifications, but ordering on them
                classification_query = Classification.query_records_accessible_by(
                    self.current_user
                )
                classification_subquery = classification_query.subquery()

                # We need an outer join here when just sorting by classifications
                # to support sources with no classifications being sorted to the end
                obj_query = obj_query.join(
                    classification_subquery,
                    Obj.id == classification_subquery.c.obj_id,
                    isouter=True,
                )

        source_query = apply_active_or_requested_filtering(
            source_query, include_requested, requested_only
        )
        if group_ids is not None:
            if not all(gid in user_accessible_group_ids for gid in group_ids):
                return self.error(
                    f"One of the requested groups in '{group_ids}' is inaccessible to user."
                )
            source_query = source_query.filter(Source.group_id.in_(group_ids))

        source_subquery = source_query.subquery()
        query = obj_query.join(source_subquery, Obj.id == source_subquery.c.obj_id)
        order_by = None
        if sort_by is not None:
            if sort_by == "id":
                order_by = [Obj.id] if sort_order == "asc" else [Obj.id.desc()]
            elif sort_by == "alias":
                order_by = (
                    [Obj.alias.nullslast()]
                    if sort_order == "asc"
                    else [Obj.alias.desc().nullslast()]
                )
            elif sort_by == "origin":
                order_by = (
                    [Obj.origin.nullslast()]
                    if sort_order == "asc"
                    else [Obj.origin.desc().nullslast()]
                )
            elif sort_by == "ra":
                order_by = (
                    [Obj.ra.nullslast()]
                    if sort_order == "asc"
                    else [Obj.ra.desc().nullslast()]
                )
            elif sort_by == "dec":
                order_by = (
                    [Obj.dec.nullslast()]
                    if sort_order == "asc"
                    else [Obj.dec.desc().nullslast()]
                )
            elif sort_by == "redshift":
                order_by = (
                    [Obj.redshift.nullslast()]
                    if sort_order == "asc"
                    else [Obj.redshift.desc().nullslast()]
                )
            elif sort_by == "saved_at":
                order_by = (
                    [source_subquery.c.saved_at]
                    if sort_order == "asc"
                    else [source_subquery.c.saved_at.desc()]
                )
            elif sort_by == "classification":
                order_by = (
                    [classification_subquery.c.classification.nullslast()]
                    if sort_order == "asc"
                    else [classification_subquery.c.classification.desc().nullslast()]
                )

        if page_number:
            try:
                page_number = int(page_number)
            except ValueError:
                return self.error("Invalid page number value.")
            try:
                query_results = grab_query_results(
                    query,
                    total_matches,
                    page_number,
                    num_per_page,
                    "sources",
                    order_by=order_by,
                    # We'll join thumbnails in manually, as they lead to duplicate
                    # results downstream with the detection stats being added in
                    include_thumbnails=False,
                )
            except ValueError as e:
                if "Page number out of range" in str(e):
                    return self.error("Page number out of range.")
                raise
        elif save_summary:
            query_results = {"sources": source_query.all()}
        else:
            query_results = grab_query_results(
                query,
                total_matches,
                None,
                None,
                "sources",
                order_by=order_by,
                # We'll join thumbnails in manually, as they lead to duplicate
                # results downstream with the detection stats being added in
                include_thumbnails=False,
            )

        if not save_summary:
            # Records are Objs, not Sources
            obj_list = []

            # The query_results could be an empty list instead of a SQLAlchemy
            # Query object if there are no matching sources
            if query_results["sources"] != [] and include_detection_stats:
                # Load in all last_detected_at values at once
                last_detected_at = Obj.last_detected_at(self.current_user)
                query_results["sources"] = query_results["sources"].add_columns(
                    last_detected_at
                )

                # Load in all last_detected_mag values at once
                last_detected_mag = Obj.last_detected_mag(self.current_user)
                query_results["sources"] = query_results["sources"].add_columns(
                    last_detected_mag
                )

                # Load in all peak_detected_at values at once
                peak_detected_at = Obj.peak_detected_at(self.current_user)
                query_results["sources"] = query_results["sources"].add_columns(
                    peak_detected_at
                )

                # Load in all peak_detected_mag values at once
                peak_detected_mag = Obj.peak_detected_mag(self.current_user)
                query_results["sources"] = query_results["sources"].add_columns(
                    peak_detected_mag
                )

            for result in query_results["sources"]:
                if include_detection_stats:
                    (
                        obj,
                        last_detected_at,
                        last_detected_mag,
                        peak_detected_at,
                        peak_detected_mag,
                    ) = result
                else:
                    obj = result
                obj_list.append(obj.to_dict())

                if include_comments:
                    obj_list[-1]["comments"] = sorted(
                        [
                            {
                                k: v
                                for k, v in c.to_dict().items()
                                if k != "attachment_bytes"
                            }
                            for c in Comment.query_records_accessible_by(
                                self.current_user
                            )
                            .filter(Comment.obj_id == obj.id)
                            .all()
                        ],
                        key=lambda x: x["created_at"],
                        reverse=True,
                    )

                if include_thumbnails and not remove_nested:
                    obj_list[-1]["thumbnails"] = (
                        Thumbnail.query_records_accessible_by(self.current_user)
                        .filter(Thumbnail.obj_id == obj.id)
                        .all()
                    )

                if not remove_nested:
                    readable_classifications = (
                        Classification.query_records_accessible_by(self.current_user)
                        .filter(Classification.obj_id == obj.id)
                        .all()
                    )

                    readable_classifications_json = []
                    for classification in readable_classifications:
                        classification_dict = classification.to_dict()
                        classification_dict['groups'] = [
                            g.to_dict() for g in classification.groups
                        ]
                        readable_classifications_json.append(classification_dict)

                    obj_list[-1]["classifications"] = readable_classifications_json

                    obj_list[-1]["annotations"] = sorted(
                        Annotation.query_records_accessible_by(
                            self.current_user
                        ).filter(Annotation.obj_id == obj.id),
                        key=lambda x: x.origin,
                    )
                if include_detection_stats:
                    obj_list[-1]["last_detected_at"] = (
                        (last_detected_at - last_detected_at.utcoffset()).replace(
                            tzinfo=UTC
                        )
                        if last_detected_at
                        else None
                    )
                    obj_list[-1]["last_detected_mag"] = last_detected_mag
                    obj_list[-1]["peak_detected_at"] = (
                        (peak_detected_at - peak_detected_at.utcoffset()).replace(
                            tzinfo=UTC
                        )
                        if peak_detected_at
                        else None
                    )
                    obj_list[-1]["peak_detected_mag"] = peak_detected_mag

                obj_list[-1]["gal_lon"] = obj.gal_lon_deg
                obj_list[-1]["gal_lat"] = obj.gal_lat_deg
                obj_list[-1]["luminosity_distance"] = obj.luminosity_distance
                obj_list[-1]["dm"] = obj.dm
                obj_list[-1][
                    "angular_diameter_distance"
                ] = obj.angular_diameter_distance

                if include_photometry:
                    photometry = Photometry.query_records_accessible_by(
                        self.current_user
                    ).filter(Photometry.obj_id == obj.id)
                    obj_list[-1]["photometry"] = [
                        serialize(phot, 'ab', 'flux') for phot in photometry
                    ]
                if include_photometry_exists:
                    obj_list[-1]["photometry_exists"] = (
                        len(
                            Photometry.query_records_accessible_by(self.current_user)
                            .filter(Photometry.obj_id == obj.id)
                            .all()
                        )
                        > 0
                    )
                if include_spectrum_exists:
                    obj_list[-1]["spectrum_exists"] = (
                        len(
                            Spectrum.query_records_accessible_by(self.current_user)
                            .filter(Spectrum.obj_id == obj.id)
                            .all()
                        )
                        > 0
                    )

                if not remove_nested:
                    source_query = Source.query_records_accessible_by(
                        self.current_user
                    ).filter(Source.obj_id == obj_list[-1]["id"])
                    source_query = apply_active_or_requested_filtering(
                        source_query, include_requested, requested_only
                    )
                    source_subquery = source_query.subquery()
                    groups = (
                        Group.query_records_accessible_by(self.current_user)
                        .join(source_subquery, Group.id == source_subquery.c.group_id)
                        .all()
                    )
                    obj_list[-1]["groups"] = [g.to_dict() for g in groups]

                    for group in obj_list[-1]["groups"]:
                        source_table_row = (
                            Source.query_records_accessible_by(self.current_user)
                            .filter(
                                Source.obj_id == obj_list[-1]["id"],
                                Source.group_id == group["id"],
                            )
                            .first()
                        )
                        if source_table_row is not None:
                            group["active"] = source_table_row.active
                            group["requested"] = source_table_row.requested
                            group["saved_at"] = source_table_row.saved_at
                            group["saved_by"] = (
                                source_table_row.saved_by.to_dict()
                                if source_table_row.saved_by is not None
                                else None
                            )

                if include_color_mag:
                    obj_list[-1]["color_magnitude"] = get_color_mag(
                        obj_list[-1]["annotations"]
                    )
            query_results["sources"] = obj_list

        query_results = recursive_to_dict(query_results)
        self.verify_and_commit()
        return self.success(data=query_results)

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Add a new source
        tags:
          - sources
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ObjPost'
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
        obj_already_exists = (
            Obj.get_if_accessible_by(data["id"], self.current_user) is not None
        )
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

        groups = (
            Group.query_records_accessible_by(self.current_user)
            .filter(Group.id.in_(group_ids))
            .all()
        )
        if not groups:
            return self.error(
                "Invalid group_ids field. Please specify at least "
                "one valid group ID that you belong to."
            )

        update_redshift_history_if_relevant(data, obj, self.associated_user_object)

        DBSession().add(obj)
        for group in groups:
            source = (
                Source.query_records_accessible_by(self.current_user)
                .filter(Source.obj_id == obj.id)
                .filter(Source.group_id == group.id)
                .first()
            )
            if source is not None:
                source.active = True
                source.saved_by = self.associated_user_object
            else:
                DBSession().add(
                    Source(
                        obj=obj, group=group, saved_by_id=self.associated_user_object.id
                    )
                )
        self.verify_and_commit()
        if not obj_already_exists:
            obj.add_linked_thumbnails()
        self.push_all(
            action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
        )

        self.push_all(
            action="skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
        )
        return self.success(data={"id": obj.id})

    @permissions(['Upload data'])
    def patch(self, obj_id):
        """
        ---
        description: Update a source
        tags:
          - sources
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
        self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": obj.internal_key},
        )

        return self.success(action='skyportal/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def delete(self, obj_id, group_id):
        """
        ---
        description: Delete a source
        tags:
          - sources
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
            Source.query_records_accessible_by(self.current_user, mode="update")
            .filter(Source.obj_id == obj_id)
            .filter(Source.group_id == group_id)
            .first()
        )
        s.active = False
        s.unsaved_by = self.current_user
        self.verify_and_commit()

        return self.success(action='skyportal/FETCH_SOURCES')


class SourceOffsetsHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id):
        """
        ---
        description: Retrieve offset stars to aid in spectroscopy
        tags:
          - sources
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
        source = Obj.get_if_accessible_by(obj_id, self.current_user)
        if source is None:
            return self.error('Source not found', status=404)

        initial_pos = (source.ra, source.dec)

        try:
            best_ra, best_dec = _calculate_best_position_for_offset_stars(
                Photometry.query_records_accessible_by(self.current_user)
                .filter(Photometry.obj_id == source.id)
                .all(),
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

        offset_func = functools.partial(
            get_nearby_offset_stars,
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

        try:
            (
                starlist_info,
                query_string,
                queries_issued,
                noffsets,
                used_ztfref,
            ) = await IOLoop.current().run_in_executor(None, offset_func)
        except ValueError:
            return self.error("Error querying for nearby offset stars")

        starlist_str = "\n".join(
            [x["str"].replace(" ", "&nbsp;") for x in starlist_info]
        )

        self.verify_and_commit()
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
        tags:
          - sources
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
        source = Obj.get_if_accessible_by(obj_id, self.current_user)
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
                Photometry.query_records_accessible_by(self.current_user)
                .filter(Photometry.obj_id == source.id)
                .all(),
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

        self.verify_and_commit()

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
    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Send out a new source notification
        tags:
          - notifications
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

        groups = (
            Group.query_records_accessible_by(self.current_user)
            .filter(Group.id.in_(group_ids))
            .all()
        )

        if data.get("sourceId") is None:
            return self.error("Missing required parameter `sourceId`")

        source = Obj.get_if_accessible_by(data["sourceId"], self.current_user)
        if source is None:
            return self.error('Source not found', status=404)

        source_id = data["sourceId"]

        source_group_ids = [
            row[0]
            for row in Source.query_records_accessible_by(
                self.current_user, columns=[Source.group_id]
            )
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
            self.verify_and_commit()
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


class PS1ThumbnailHandler(BaseHandler):
    @auth_or_token  # We should allow these requests from view-only users (triggered on source page)
    def post(self):
        data = self.get_json()
        obj_id = data.get("objID")
        if obj_id is None:
            return self.error("Missing required paramter objID")
        IOLoop.current().add_callback(
            lambda: add_ps1_thumbnail_and_push_ws_msg(obj_id, self)
        )
        return self.success()
