import datetime
from copy import copy
import re
import json
import uuid
from astropy.time import Time
import astropy.units as u
import operator  # noqa: F401
import string
import arrow
import numpy as np
import time

from tornado.ioloop import IOLoop

import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql.expression import case, func, cast
from sqlalchemy.sql import column, Values
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import Float, Boolean, String, Integer
from sqlalchemy.exc import IntegrityError
from marshmallow.exceptions import ValidationError
import healpix_alchemy as ha

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.model_util import recursive_to_dict
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.custom_exceptions import AccessError
from baselayer.log import make_log

from ..base import BaseHandler
from ...models import (
    DBSession,
    AnnotationOnPhotometry,
    User,
    Obj,
    Candidate,
    Photometry,
    Spectrum,
    Source,
    Filter,
    Annotation,
    Group,
    Classification,
    Listing,
    Comment,
)
from ...utils.cache import Cache, array_to_bytes
from ...utils.sizeof import sizeof, SIZE_WARNING_THRESHOLD


_, cfg = load_env()
cache_dir = "cache/candidates_queries"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_candidate_query_cache"] * 60,
)
log = make_log('api/candidate')

Session = scoped_session(sessionmaker())


def add_linked_thumbnails_and_push_ws_msg(obj_id, user_id):

    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        user = session.query(User).get(user_id)
        if Obj.get_if_accessible_by(obj_id, user) is None:
            raise AccessError(
                f"Insufficient permissions for User {user_id} to read Obj {obj_id}"
            )
        obj = session.query(Obj).get(obj_id)
        obj.add_linked_thumbnails(session=session)
        flow = Flow()
        flow.push(
            '*', "skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
        )
        flow.push('*', "skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key})
    except Exception as e:
        log(f"Unable to add linked thumbnails to {obj_id}: {e}")
        session.rollback()
    finally:
        session.close()
        Session.remove()


def update_redshift_history_if_relevant(request_data, obj, user):
    if "redshift" in request_data:
        if obj.redshift_history is None:
            redshift_history = []
        else:
            redshift_history = copy(obj.redshift_history)

        history_params = {
            "set_by_user_id": user.id,
            "set_at_utc": datetime.datetime.utcnow().isoformat(),
            "value": request_data["redshift"],
            "uncertainty": request_data.get("redshift_error", None),
        }

        if "redshift_origin" in request_data:
            history_params["origin"] = request_data["redshift_origin"]

        redshift_history.append(history_params)
        obj.redshift_history = redshift_history


def update_healpix_if_relevant(request_data, obj):

    # first check if the ra and dec is being updated
    ra = request_data.get('ra', None)
    dec = request_data.get('dec', None)

    if (ra is not None) and (dec is not None):
        # This adds a healpix index for a new object being created
        obj.healpix = ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)
        return

    # otherwise make sure healpix is correct
    if (obj.ra is not None) and (obj.dec is not None):
        obj.healpix = ha.constants.HPX.lonlat_to_healpix(
            obj.ra * u.deg, obj.dec * u.deg
        )
        return


def create_photometry_annotations_query(
    session,
    photometry_annotations_filter_origin=None,
    photometry_annotations_filter_before=None,
    photometry_annotations_filter_after=None,
):
    photometry_annotations_query = AnnotationOnPhotometry.select(
        session.user_or_token,
        columns=[
            AnnotationOnPhotometry.obj_id.label('obj_id'),
            func.count(AnnotationOnPhotometry.obj_id).label('count'),
        ],
    ).group_by(AnnotationOnPhotometry.obj_id)
    if photometry_annotations_filter_origin is not None:
        photometry_annotations_query = photometry_annotations_query.where(
            AnnotationOnPhotometry.origin.in_(photometry_annotations_filter_origin)
        )
    if photometry_annotations_filter_before:
        photometry_annotations_query = photometry_annotations_query.where(
            AnnotationOnPhotometry.created_at <= photometry_annotations_filter_before
        )
    if photometry_annotations_filter_after:
        photometry_annotations_query = photometry_annotations_query.where(
            AnnotationOnPhotometry.created_at >= photometry_annotations_filter_after
        )

    return photometry_annotations_query


class CandidateHandler(BaseHandler):
    @auth_or_token
    def head(self, obj_id=None):
        """
        ---
        single:
          description: Check if a Candidate exists
          tags:
            - candidates
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
        with self.Session() as session:
            stmt = Candidate.select(session.user_or_token).where(
                Candidate.obj_id == obj_id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            num_c = session.execute(count_stmt).scalar()
            if num_c > 0:
                return self.success()
            else:
                return self.error(
                    message=f"No candidate with object ID {obj_id}", status=404
                )

    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        single:
          description: Retrieve a candidate
          tags:
            - candidates
          parameters:
            - in: path
              name: obj_id
              required: true
              schema:
                type: string
            - in: query
              name: includeComments
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated comments. Defaults to false.
            - in: query
              name: includeAlerts
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated alerts. Defaults to false.
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
          tags:
            - candidates
          description: Retrieve all candidates
          parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of candidates to return per paginated request. Defaults to 25.
              Capped at 500.
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
            name: autosave
            nullable: true
            schema:
                type: boolean
            description: Automatically save candidates passing query.
          - in: query
            name: autosaveGroupIds
            nullable: true
            schema:
                type: boolean
            description: Group ID(s) to save candidates to.
          - in: query
            name: savedStatus
            nullable: true
            schema:
                type: string
                enum: [all, savedToAllSelected, savedToAnySelected, savedToAnyAccessible, notSavedToAnyAccessible, notSavedToAnySelected, notSavedToAllSelected]
            description: |
                String indicating the saved status to filter candidate results for. Must be one of the enumerated values.
          - in: query
            name: startDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              Candidate.passed_at >= startDate
          - in: query
            name: endDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              Candidate.passed_at <= endDate
          - in: query
            name: groupIDs
            nullable: true
            schema:
              type: array
              items:
                type: integer
            explode: false
            style: simple
            description: |
              Comma-separated string of group IDs (e.g. "1,2"). Defaults to all of user's
              groups if filterIDs is not provided.
          - in: query
            name: filterIDs
            nullable: true
            schema:
              type: array
              items:
                type: integer
            explode: false
            style: simple
            description: |
              Comma-separated string of filter IDs (e.g. "1,2"). Defaults to all of user's
              groups' filters if groupIDs is not provided.
          - in: query
            name: annotationExcludeOrigin
            nullable: true
            schema:
              type: string
            description: |
              Only load objects that do not have annotations from this origin.
              If the annotationsExcludeOutdatedDate is also given, then annotations with
              this origin will still be loaded if they were modified before that date.
          - in: query
            name: annotationExcludeOutdatedDate
            nullable: true
            schema:
              type: string
            description: |
              An Arrow parseable string designating when an existing annotation is outdated.
              Only relevant if giving the annotationExcludeOrigin argument.
              Will treat objects with outdated annotations as if they did not have that annotation,
              so it will load an object if it doesn't have an annotation with the origin specified or
              if it does have it but the annotation modified date < annotationsExcludeOutdatedDate
          - in: query
            name: sortByAnnotationOrigin
            nullable: true
            schema:
              type: string
            description: |
              The origin of the Annotation to sort by
          - in: query
            name: sortByAnnotationKey
            nullable: true
            schema:
              type: string
            description: |
              The key of the Annotation data value to sort by
          - in: query
            name: sortByAnnotationOrder
            nullable: true
            schema:
              type: string
            description: |
              The sort order for annotations - either "asc" or "desc".
              Defaults to "asc".
          - in: query
            name: annotationFilterList
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
              Comma-separated string of JSON objects representing annotation filters.
              Filter objects are expected to have keys { origin, key, value } for
              non-numeric value types, or { origin, key, min, max } for numeric values.
          - in: query
            name: includePhotometry
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated photometry. Defaults to
              false.
          - in: query
            name: includeSpectra
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated spectra. Defaults to false.
          - in: query
            name: includeComments
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated comments. Defaults to false.
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
              Comma-separated string of classification(s) to filter for candidates matching
              that/those classification(s).
          - in: query
            name: minRedshift
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only candidates with a redshift of at least this value
          - in: query
            name: maxRedshift
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only candidates with a redshift of at most this value
          - in: query
            name: listName
            nullable: true
            schema:
              type: string
            description: |
              Get only candidates saved to the querying user's list, e.g., "favorites".
          - in: query
            name: listNameReject
            nullable: true
            schema:
              type: string
            description: |
              Get only candidates that ARE NOT saved to the querying user's list, e.g., "rejected_candidates".
          - in: query
            name: photometryAnnotationsFilter
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
              Comma-separated string of "annotation: value: operator" triplet(s) to filter for sources matching
              that/those photometry annotation(s), i.e. "drb: 0.5: lt"
          - in: query
            name: photometryAnnotationsFilterOrigin
            nullable: true
            schema:
              type: string
            description: Comma separated string of origins. Only photometry annotations from these origins are used when filtering with the photometryAnnotationsFilter.
          - in: query
            name: photometryAnnotationsFilterBefore
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that have photometry annotations before this UTC datetime.
          - in: query
            name: photometryAnnotationsFilterAfter
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that have photometry annotations after this UTC datetime.
          - in: query
            name: photometryAnnotationsFilterMinCount
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that have at least this number of photometry annotations passing the photometry annotations filtering criteria. Defaults to 1.
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
                              candidates:
                                type: array
                                items:
                                  allOf:
                                    - $ref: '#/components/schemas/Obj'
                                    - type: object
                                      properties:
                                        is_source:
                                          type: boolean
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

        start = time.time()

        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        include_photometry = self.get_query_argument("includePhotometry", False)
        include_spectra = self.get_query_argument("includeSpectra", False)
        include_comments = self.get_query_argument("includeComments", False)
        include_alerts = self.get_query_argument("includeAlerts", False)

        if obj_id is not None:
            with self.Session() as session:
                query_options = [joinedload(Obj.thumbnails), joinedload(Obj.photstats)]

                c = session.scalars(
                    Obj.select(session.user_or_token, options=query_options).where(
                        Obj.id == obj_id
                    )
                ).first()
                if c is None:
                    return self.error("Invalid ID")
                candidate_info = recursive_to_dict(c)

                if include_alerts:
                    accessible_candidates = session.scalars(
                        Candidate.select(session.user_or_token).where(
                            Candidate.obj_id == obj_id
                        )
                    ).all()
                    filter_ids = [cand.filter_id for cand in accessible_candidates]

                    passing_alerts = [
                        {
                            "filter_id": cand.filter_id,
                            "passing_alert_id": cand.passing_alert_id,
                            "passed_at": cand.passed_at,
                        }
                        for cand in accessible_candidates
                    ]
                    candidate_info["filter_ids"] = filter_ids
                    candidate_info["passing_alerts"] = passing_alerts

                if include_comments:
                    candidate_info["comments"] = sorted(
                        session.scalars(
                            Comment.select(session.user_or_token).where(
                                Comment.obj_id == obj_id
                            )
                        ).all(),
                        key=lambda x: x.created_at,
                        reverse=True,
                    )

                if include_photometry:
                    candidate_info['photometry'] = (
                        session.scalars(
                            Photometry.select(
                                session.user_or_token,
                                options=[
                                    joinedload(Photometry.instrument),
                                    joinedload(Photometry.annotations),
                                ],
                            ).where(Photometry.obj_id == obj_id)
                        )
                        .unique()
                        .all()
                    )
                    candidate_info['photometry'] = [
                        {
                            **phot.to_dict(),
                            'annotations': [
                                annotation.to_dict() for annotation in phot.annotations
                            ],
                        }
                        for phot in candidate_info['photometry']
                    ]
                if include_spectra:
                    candidate_info['spectra'] = session.scalars(
                        Spectrum.select(
                            session.user_or_token,
                            options=[joinedload(Spectrum.instrument)],
                        ).where(Spectrum.obj_id == obj_id)
                    ).all()

                candidate_info["annotations"] = sorted(
                    session.scalars(
                        Annotation.select(session.user_or_token).where(
                            Annotation.obj_id == obj_id
                        )
                    ).all(),
                    key=lambda x: x.origin,
                )
                stmt = Source.select(session.user_or_token).where(
                    Source.obj_id == obj_id
                )
                count_stmt = sa.select(func.count()).select_from(stmt.distinct())
                candidate_info["is_source"] = session.execute(count_stmt).scalar()
                if candidate_info["is_source"]:
                    source_subquery = (
                        Source.select(session.user_or_token)
                        .where(Source.obj_id == obj_id)
                        .where(Source.active.is_(True))
                        .subquery()
                    )
                    candidate_info["saved_groups"] = (
                        session.scalars(
                            Group.select(session.user_or_token).join(
                                source_subquery, Group.id == source_subquery.c.group_id
                            )
                        )
                        .unique()
                        .all()
                    )
                    candidate_info["classifications"] = (
                        session.scalars(
                            Classification.select(session.user_or_token).where(
                                Classification.obj_id == obj_id
                            )
                        )
                        .unique()
                        .all()
                    )
                if len(c.photstats) > 0:
                    if c.photstats[-1].last_detected_mjd is not None:
                        candidate_info["last_detected_at"] = Time(
                            c.photstats[-1].last_detected_mjd, format='mjd'
                        ).datetime
                    else:
                        candidate_info["last_detected_at"] = None
                else:
                    candidate_info["last_detected_at"] = None
                candidate_info["gal_lon"] = c.gal_lon_deg
                candidate_info["gal_lat"] = c.gal_lat_deg
                candidate_info["luminosity_distance"] = c.luminosity_distance
                candidate_info["dm"] = c.dm
                candidate_info[
                    "angular_diameter_distance"
                ] = c.angular_diameter_distance

                candidate_info = recursive_to_dict(candidate_info)

                query_size = sizeof(candidate_info)
                if query_size >= SIZE_WARNING_THRESHOLD:
                    end = time.time()
                    duration = end - start
                    log(
                        f'User {self.associated_user_object.id} candidate query for object {obj_id} returned {query_size} bytes in {duration} seconds'
                    )

                return self.success(data=candidate_info)

        page_number = self.get_query_argument("pageNumber", None) or 1
        n_per_page = self.get_query_argument("numPerPage", None) or 25
        # Not documented in API docs as this is for frontend-only usage & will confuse
        # users looking through the API docs
        query_id = self.get_query_argument("queryID", None)
        saved_status = self.get_query_argument("savedStatus", "all")
        total_matches = self.get_query_argument("totalMatches", None)
        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        group_ids = self.get_query_argument("groupIDs", None)
        filter_ids = self.get_query_argument("filterIDs", None)
        annotation_exclude_origin = self.get_query_argument(
            'annotationExcludeOrigin', None
        )
        annotation_exclude_date = self.get_query_argument(
            'annotationExcludeOutdatedDate', None
        )
        sort_by_origin = self.get_query_argument("sortByAnnotationOrigin", None)
        annotation_filter_list = self.get_query_argument("annotationFilterList", None)
        classifications = self.get_query_argument("classifications", None)
        min_redshift = self.get_query_argument("minRedshift", None)
        max_redshift = self.get_query_argument("maxRedshift", None)
        list_name = self.get_query_argument('listName', None)
        list_name_reject = self.get_query_argument('listNameReject', None)
        autosave = self.get_query_argument("autosave", False)
        autosave_group_ids = self.get_query_argument("autosaveGroupIds", None)
        photometry_annotations_filter = self.get_query_argument(
            "photometryAnnotationsFilter", None
        )
        photometry_annotations_filter_origin = self.get_query_argument(
            "photometryAnnotationsFilterOrigin", None
        )
        photometry_annotations_filter_after = self.get_query_argument(
            'photometryAnnotationsFilterAfter', None
        )
        photometry_annotations_filter_before = self.get_query_argument(
            'photometryAnnotationsFilterBefore', None
        )
        photometry_annotations_filter_min_count = self.get_query_argument(
            'photometryAnnotationsFilterMinCount', 1
        )

        if autosave:
            from .source import post_source

        with self.Session() as session:
            user_accessible_group_ids = [
                g.id for g in self.current_user.accessible_groups
            ]
            user_accessible_filter_ids = [
                filtr.id
                for g in self.current_user.accessible_groups
                for filtr in g.filters
                if g.filters is not None
            ]
            if group_ids is not None:
                if (
                    isinstance(group_ids, str)
                    and "," in group_ids
                    and set(group_ids).issubset(string.digits + ',')
                ):
                    group_ids = [int(g_id) for g_id in group_ids.split(",")]
                elif isinstance(group_ids, str) and group_ids.isdigit():
                    group_ids = [int(group_ids)]
                else:
                    return self.error(
                        "Invalid groupIDs value -- select at least one group"
                    )
                filters = session.scalars(
                    Filter.select(self.current_user).where(
                        Filter.group_id.in_(group_ids)
                    )
                ).all()
                filter_ids = [f.id for f in filters]
            elif filter_ids is not None:
                if "," in filter_ids and set(filter_ids) in set(string.digits + ','):
                    filter_ids = [int(f_id) for f_id in filter_ids.split(",")]
                elif filter_ids.isdigit():
                    filter_ids = [int(filter_ids)]
                else:
                    return self.error("Invalid filterIDs paramter value.")
                filters = session.scalars(
                    Filter.select(self.current_user).where(Filter.id.in_(filter_ids))
                ).all()
                group_ids = [f.group_id for f in filters]
            else:
                # If 'groupIDs' & 'filterIDs' params not present in request, use all user groups
                group_ids = user_accessible_group_ids
                filter_ids = user_accessible_filter_ids

        try:
            page = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            n_per_page = int(n_per_page)
        except ValueError:
            return self.error("Invalid numPerPage value.")
        n_per_page = min(n_per_page, 500)

        with self.Session() as session:
            candidate_query = Candidate.select(session.user_or_token).where(
                Candidate.filter_id.in_(filter_ids)
            )
            if start_date is not None and start_date.strip() not in [
                "",
                "null",
                "undefined",
            ]:
                start_date = arrow.get(start_date).datetime
                candidate_query = candidate_query.where(
                    Candidate.passed_at >= start_date
                )
            if end_date is not None and end_date.strip() not in [
                "",
                "null",
                "undefined",
            ]:
                end_date = arrow.get(end_date).datetime
                candidate_query = candidate_query.where(Candidate.passed_at <= end_date)
            candidate_subquery = candidate_query.subquery()
            # We'll join in the nested data for Obj (like photometry) later
            q = Obj.select(session.user_or_token).join(
                candidate_subquery, Obj.id == candidate_subquery.c.obj_id
            )
            if sort_by_origin is not None or annotation_filter_list is not None:
                q = q.outerjoin(Annotation)

            if classifications is not None:
                if isinstance(classifications, str) and "," in classifications:
                    classifications = [c.strip() for c in classifications.split(",")]
                elif isinstance(classifications, str):
                    classifications = [classifications]
                else:
                    return self.error(
                        "Invalid classifications value -- must provide at least one string value"
                    )
                q = q.join(Classification).where(
                    Classification.classification.in_(classifications)
                )
            if sort_by_origin is None:
                # Don't apply the order by just yet. Save it so we can pass it to
                # the LIMT/OFFSET helper function down the line once other query
                # params are set.
                order_by = [candidate_subquery.c.passed_at.desc().nullslast(), Obj.id]

            if saved_status in [
                "savedToAllSelected",
                "savedToAnySelected",
                "savedToAnyAccessible",
                "notSavedToAnyAccessible",
                "notSavedToAnySelected",
                "notSavedToAllSelected",
            ]:
                notin = False
                active_sources = Source.select(
                    session.user_or_token, columns=[Source.obj_id]
                ).where(Source.active.is_(True))
                if saved_status == "savedToAllSelected":
                    # Retrieve objects that have as many active saved groups that are
                    # in 'group_ids' as there are items in 'group_ids'
                    subquery = (
                        active_sources.where(Source.group_id.in_(group_ids))
                        .group_by(Source.obj_id)
                        .having(func.count(Source.group_id) == len(group_ids))
                    )
                elif saved_status == "savedToAnySelected":
                    subquery = active_sources.where(Source.group_id.in_(group_ids))
                elif saved_status == "savedToAnyAccessible":
                    subquery = active_sources.where(
                        Source.group_id.in_(user_accessible_group_ids)
                    )
                elif saved_status == "notSavedToAnyAccessible":
                    subquery = active_sources.where(
                        Source.group_id.in_(user_accessible_group_ids)
                    )
                    notin = True
                elif saved_status == "notSavedToAnySelected":
                    subquery = active_sources.where(Source.group_id.in_(group_ids))
                    notin = True
                elif saved_status == "notSavedToAllSelected":
                    # Retrieve objects that have as many active saved groups that are
                    # in 'group_ids' as there are items in 'group_ids', and select
                    # the objects not in that set
                    subquery = (
                        active_sources.where(Source.group_id.in_(group_ids))
                        .group_by(Source.obj_id)
                        .having(func.count(Source.group_id) == len(group_ids))
                    )
                    notin = True
                q = (
                    q.where(Obj.id.notin_(subquery))
                    if notin
                    else q.where(Obj.id.in_(subquery))
                )
            elif saved_status != "all":
                return self.error(
                    f"Invalid savedStatus: {saved_status}. Must be one of the enumerated options."
                )

            if min_redshift is not None:
                try:
                    min_redshift = float(min_redshift)
                except ValueError:
                    return self.error(
                        "Invalid values for minRedshift - could not convert to float"
                    )
                q = q.where(Obj.redshift >= min_redshift)
            if max_redshift is not None:
                try:
                    max_redshift = float(max_redshift)
                except ValueError:
                    return self.error(
                        "Invalid values for maxRedshift - could not convert to float"
                    )
                q = q.where(Obj.redshift <= max_redshift)

            if annotation_exclude_origin is not None:
                if annotation_exclude_date is None:
                    right = (
                        Obj.select(session.user_or_token, columns=[Obj.id])
                        .join(Annotation)
                        .where(Annotation.origin == annotation_exclude_origin)
                        .subquery()
                    )
                else:
                    expire_date = arrow.get(annotation_exclude_date).datetime
                    right = (
                        Obj.select(session.user_or_token, columns=[Obj.id])
                        .join(Annotation)
                        .where(
                            Annotation.origin == annotation_exclude_origin,
                            Annotation.modified >= expire_date,
                        )
                        .subquery()
                    )

                q = q.outerjoin(right, Obj.id == right.c.id).where(right.c.id.is_(None))

            if list_name is not None:
                q = q.where(
                    Listing.list_name == list_name,
                    Listing.user_id == self.associated_user_object.id,
                )
            if list_name_reject is not None:
                right = (
                    Obj.select(session.user_or_token, columns=[Obj.id])
                    .join(Listing)
                    .filter(
                        Listing.list_name == list_name_reject,
                        Listing.user_id == self.associated_user_object.id,
                    )
                    .subquery()
                )

                q = q.outerjoin(right, Obj.id == right.c.id).where(right.c.id.is_(None))

            if annotation_filter_list is not None:
                # Parse annotation filter list objects from the query string
                # and apply the filters to the query

                for item in re.split(r",(?={)", annotation_filter_list):
                    try:
                        new_filter = json.loads(item)
                    except json.decoder.JSONDecodeError:
                        return self.error(
                            "Could not parse JSON objects for annotation filtering"
                        )

                    if "origin" not in new_filter:
                        self.error(
                            f"Invalid annotation filter list item {item}: \"origin\" is required."
                        )

                    if "key" not in new_filter:
                        self.error(
                            f"Invalid annotation filter list item {item}: \"key\" is required."
                        )

                    if "value" in new_filter:
                        value = new_filter["value"]
                        if isinstance(value, bool):
                            q = q.where(
                                Annotation.origin == new_filter["origin"],
                                Annotation.data[new_filter["key"]].astext.cast(Boolean)
                                == value,
                            )
                        else:
                            # Test if the value is a nested object
                            try:
                                value = json.loads(value)
                                # If a nested object, we put the value through the
                                # JSON loads/dumps pipeline to get a string formatted
                                # like Postgres will for its JSONB ->> text operation
                                # For some reason, for example, not doing this will
                                # have value = { "key": "value" } (with the extra
                                # spaces around the braces) and cause the filter to
                                # fail.
                                value = json.dumps(value)
                            except json.decoder.JSONDecodeError:
                                # If not, this is just a string field and we don't
                                # need the string formatting above
                                pass
                            q = q.filter(
                                Annotation.origin == new_filter["origin"],
                                Annotation.data[new_filter["key"]].astext == value,
                            )
                    elif "min" in new_filter and "max" in new_filter:
                        try:
                            min_value = float(new_filter["min"])
                            max_value = float(new_filter["max"])
                            q = q.where(
                                Annotation.origin == new_filter["origin"],
                                Annotation.data[new_filter["key"]].cast(Float)
                                >= min_value,
                                Annotation.data[new_filter["key"]].cast(Float)
                                <= max_value,
                            )
                        except ValueError:
                            return self.error(
                                f"Invalid annotation filter list item: {item}. The min/max provided is not a valid number."
                            )
                    else:
                        return self.error(
                            f"Invalid annotation filter list item: {item}. Should have either \"value\" or \"min\" and \"max\""
                        )

            if sort_by_origin is not None:
                sort_by_key = self.get_query_argument("sortByAnnotationKey", None)
                sort_by_order = self.get_query_argument("sortByAnnotationOrder", None)
                # Define a custom sort order to have annotations from the correct
                # origin first, all others afterwards
                origin_sort_order = case(
                    {sort_by_origin: 1},
                    value=Annotation.origin,
                    else_=None,
                )
                annotation_sort_criterion = (
                    Annotation.data[sort_by_key].desc().nullslast()
                    if sort_by_order == "desc"
                    else Annotation.data[sort_by_key].nullslast()
                )
                # Don't apply the order by just yet. Save it so we can pass it to
                # the LIMT/OFFSET helper function.
                order_by = [
                    origin_sort_order.nullslast(),
                    annotation_sort_criterion,
                    candidate_subquery.c.passed_at.desc().nullslast(),
                    Obj.id,
                ]

            if photometry_annotations_filter is not None:
                if isinstance(photometry_annotations_filter, str):
                    photometry_annotations_filter = [
                        c.strip() for c in photometry_annotations_filter.split(",")
                    ]
                else:
                    raise ValueError(
                        "Invalid annotationsFilter value -- must provide at least one string value"
                    )
            if photometry_annotations_filter_origin is not None:
                if isinstance(photometry_annotations_filter_origin, str):
                    photometry_annotations_filter_origin = [
                        c.strip()
                        for c in photometry_annotations_filter_origin.split(",")
                    ]
                else:
                    raise ValueError(
                        "Invalid annotationsFilterOrigin value -- must provide at least one string value"
                    )

            if (
                (photometry_annotations_filter_origin is not None)
                or (photometry_annotations_filter_before is not None)
                or (photometry_annotations_filter_after is not None)
                or (photometry_annotations_filter is not None)
            ):
                if photometry_annotations_filter is not None:
                    for ann_filt in photometry_annotations_filter:
                        ann_split = ann_filt.split(":")
                        if not (len(ann_split) == 1 or len(ann_split) == 3):
                            raise ValueError(
                                "Invalid photometryAnnotationsFilter value -- annotation filter must have 1 or 3 values"
                            )
                        name = ann_split[0].strip()

                        photometry_annotations_query = create_photometry_annotations_query(
                            session,
                            photometry_annotations_filter_origin=photometry_annotations_filter_origin,
                            photometry_annotations_filter_before=photometry_annotations_filter_before,
                            photometry_annotations_filter_after=photometry_annotations_filter_after,
                        )

                        if len(ann_split) == 3:
                            value = ann_split[1].strip()
                            try:
                                value = float(value)
                            except ValueError as e:
                                raise ValueError(
                                    f"Invalid annotation filter value: {e}"
                                )
                            op = ann_split[2].strip()
                            op_options = ["lt", "le", "eq", "ne", "ge", "gt"]
                            if op not in op_options:
                                raise ValueError(f"Invalid operator: {op}")
                            comp_function = getattr(operator, op)

                            photometry_annotations_query = (
                                photometry_annotations_query.where(
                                    comp_function(
                                        AnnotationOnPhotometry.data[name],
                                        cast(value, JSONB),
                                    )
                                )
                            )
                        else:
                            photometry_annotations_query = (
                                photometry_annotations_query.where(
                                    AnnotationOnPhotometry.data[name].astext.is_not(
                                        None
                                    )
                                )
                            )

                else:
                    photometry_annotations_query = create_photometry_annotations_query(
                        session,
                        photometry_annotations_filter_origin=photometry_annotations_filter_origin,
                        photometry_annotations_filter_before=photometry_annotations_filter_before,
                        photometry_annotations_filter_after=photometry_annotations_filter_after,
                    )

                photometry_annotations_subquery = (
                    photometry_annotations_query.subquery()
                )
                obj_photometry_annotations_query = sa.select(Obj.id)
                obj_photometry_annotations_query = (
                    obj_photometry_annotations_query.join(
                        photometry_annotations_subquery,
                        sa.and_(
                            photometry_annotations_subquery.c.count
                            >= photometry_annotations_filter_min_count,
                            photometry_annotations_subquery.c.obj_id == Obj.id,
                        ),
                    )
                )
                obj_photometry_annotations_subquery = (
                    obj_photometry_annotations_query.subquery()
                )

                q = q.join(
                    obj_photometry_annotations_subquery,
                    Obj.id == obj_photometry_annotations_subquery.c.id,
                )

            try:
                query_results = grab_query_results(
                    session,
                    q,
                    total_matches,
                    page,
                    n_per_page,
                    "candidates",
                    order_by=order_by,
                    query_id=query_id,
                    use_cache=True,
                    include_detection_stats=True,
                )
            except ValueError as e:
                if "Page number out of range" in str(e):
                    return self.error("Page number out of range.")
                raise

            matching_source_ids = (
                session.scalars(
                    Source.select(session.user_or_token, columns=[Source.obj_id]).where(
                        Source.obj_id.in_(
                            [obj.id for obj, in query_results["candidates"]]
                        )
                    )
                )
                .unique()
                .all()
            )
            candidate_list = []
            for (obj,) in query_results["candidates"]:
                with session.no_autoflush:
                    obj.is_source = obj.id in matching_source_ids
                    if obj.is_source:
                        source_subquery = (
                            Source.select(session.user_or_token)
                            .where(Source.obj_id == obj.id)
                            .where(Source.active.is_(True))
                            .subquery()
                        )
                        obj.saved_groups = session.scalars(
                            Group.select(session.user_or_token).join(
                                source_subquery, Group.id == source_subquery.c.group_id
                            )
                        ).all()
                        obj.classifications = session.scalars(
                            Classification.select(self.current_user).where(
                                Classification.obj_id == obj.id
                            )
                        ).all()
                    obj.passing_group_ids = [
                        f.group_id
                        for f in session.scalars(
                            Filter.select(session.user_or_token).where(
                                Filter.id.in_(
                                    session.scalars(
                                        Candidate.select(
                                            session.user_or_token,
                                            columns=[Candidate.filter_id],
                                        ).where(Candidate.obj_id == obj.id)
                                    ).all()
                                )
                            )
                        ).all()
                    ]
                    if autosave:
                        source = {
                            'id': obj.id,
                            'group_ids': autosave_group_ids,
                        }
                        post_source(source, self.associated_user_object.id, session)
                    candidate_list.append(recursive_to_dict(obj))
                    if include_photometry:
                        candidate_list[-1]["photometry"] = (
                            session.scalars(
                                Photometry.select(
                                    session.user_or_token,
                                    options=[joinedload(Photometry.instrument)],
                                ).where(Photometry.obj_id == obj.id)
                            )
                            .unique()
                            .all()
                        )

                    if include_spectra:
                        candidate_list[-1]["spectra"] = session.scalars(
                            Spectrum.select(
                                session.user_or_token,
                                options=[joinedload(Spectrum.instrument)],
                            ).where(Spectrum.obj_id == obj.id)
                        ).all()

                    if include_comments:
                        candidate_list[-1]["comments"] = sorted(
                            session.scalars(
                                Comment.select(session.user_or_token).where(
                                    Comment.obj_id == obj.id
                                )
                            )
                            .unique()
                            .all(),
                            key=lambda x: x.created_at,
                            reverse=True,
                        )
                    unordered_annotations = sorted(
                        session.scalars(
                            Annotation.select(self.current_user).where(
                                Annotation.obj_id == obj.id
                            )
                        ).all(),
                        key=lambda x: x.origin,
                    )
                    selected_groups_annotations = []
                    other_annotations = []
                    for annotation in unordered_annotations:
                        if set(group_ids).intersection(
                            {group.id for group in annotation.groups}
                        ):
                            selected_groups_annotations.append(annotation)
                        else:
                            other_annotations.append(annotation)
                    candidate_list[-1]["annotations"] = (
                        selected_groups_annotations + other_annotations
                    )
                    if len(obj.photstats) > 0:
                        if obj.photstats[-1].last_detected_mjd is not None:
                            candidate_list[-1]["last_detected_at"] = Time(
                                obj.photstats[-1].last_detected_mjd, format='mjd'
                            ).datetime
                        else:
                            candidate_list[-1]["last_detected_at"] = None
                    else:
                        candidate_list[-1]["last_detected_at"] = None
                    candidate_list[-1]["gal_lat"] = obj.gal_lat_deg
                    candidate_list[-1]["gal_lon"] = obj.gal_lon_deg
                    candidate_list[-1]["luminosity_distance"] = obj.luminosity_distance
                    candidate_list[-1]["dm"] = obj.dm
                    candidate_list[-1][
                        "angular_diameter_distance"
                    ] = obj.angular_diameter_distance

            query_results["candidates"] = candidate_list
            query_results = recursive_to_dict(query_results)
            self.verify_and_commit()

            query_size = sizeof(query_results)
            if query_size >= SIZE_WARNING_THRESHOLD:
                end = time.time()
                duration = end - start
                log(
                    f'User {self.associated_user_object.id} candidate query returned {query_size} bytes in {duration} seconds'
                )

            return self.success(data=query_results)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Create new candidate(s) (one per filter).
        tags:
          - candidates
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ObjPost'
                  - type: object
                    properties:
                      filter_ids:
                        type: array
                        items:
                          type: integer
                        description: List of associated filter IDs
                      passing_alert_id:
                        type: integer
                        description: ID of associated filter that created candidate
                        nullable: true
                      passed_at:
                        type: string
                        description: Arrow-parseable datetime string indicating when passed filter.
                        nullable: true
                    required:
                      - filter_ids
                      - passed_at
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
                            ids:
                              type: array
                              items:
                                type: integer
                              description: List of new candidate IDs
        """
        data = self.get_json()

        with self.Session() as session:

            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == data["id"])
            ).first()
            if obj is None:
                obj_already_exists = False
            else:
                obj_already_exists = True
            schema = Obj.__schema__()

            ra = data.get('ra', None)
            dec = data.get('dec', None)

            if ra is None and not obj_already_exists:
                return self.error("RA must not be null for a new Obj")

            if dec is None and not obj_already_exists:
                return self.error("Dec must not be null for a new Obj")

            passing_alert_id = data.pop("passing_alert_id", None)
            passed_at = data.pop("passed_at", None)
            if passed_at is None:
                return self.error("Missing required parameter: `passed_at`.")
            passed_at = arrow.get(passed_at).datetime
            try:
                filter_ids = data.pop("filter_ids")
            except KeyError:
                return self.error("Missing required filter_ids parameter.")

            if not obj_already_exists:
                try:
                    obj = schema.load(data)
                except ValidationError as e:
                    return self.error(
                        "Invalid/missing parameters: " f"{e.normalized_messages()}"
                    )
                session.add(obj)

            filters = session.scalars(
                Filter.select(session.user_or_token).where(Filter.id.in_(filter_ids))
            )
            if not filters:
                return self.error("At least one valid filter ID must be provided.")

            update_redshift_history_if_relevant(data, obj, self.associated_user_object)
            update_healpix_if_relevant(data, obj)

            candidates = [
                Candidate(
                    obj=obj,
                    filter=filter,
                    passing_alert_id=passing_alert_id,
                    passed_at=passed_at,
                    uploader_id=self.associated_user_object.id,
                )
                for filter in filters
            ]
            session.add_all(candidates)
            try:
                session.commit()
            except IntegrityError as e:
                session.rollback()
                return self.error(
                    f"Failed to post candidate for object {obj.id}: {e.args[0]}"
                )

            obj_id = obj.id
            calling_user_id = self.associated_user_object.id
            if not obj_already_exists:
                IOLoop.current().run_in_executor(
                    None,
                    lambda: add_linked_thumbnails_and_push_ws_msg(
                        obj_id, calling_user_id
                    ),
                )

            return self.success(data={"ids": [c.id for c in candidates]})

    @permissions(["Upload data"])
    def delete(self, obj_id, filter_id):
        """
        ---
        description: Delete candidate(s)
        tags:
          - candidates
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
          - in: path
            name: filter_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            cands_to_delete = session.scalars(
                Candidate.select(session.user_or_token, mode="delete")
                .where(Candidate.obj_id == obj_id)
                .where(Candidate.filter_id == filter_id)
            ).all()
            if len(cands_to_delete) == 0:
                return self.error(
                    "Invalid (obj_id, filter_id) pairing - no matching candidates"
                )
            for cand in cands_to_delete:
                session.delete(cand)
            session.commit()

            return self.success()


def get_obj_id_values(obj_ids):
    """Return a Postgres VALUES representation of ordered list of Obj IDs
    to be returned by the Candidates/Sources query.

    Parameters
    ----------
    obj_ids: `list`
        List of Obj IDs

    Returns
    -------
    values_table: `sqlalchemy.sql.expression.FromClause`
        The VALUES representation of the Obj IDs list.
    """
    values_table = (
        Values(
            column("id", String),
            column("ordering", Integer),
        )
        .data(
            [
                (
                    obj_id,
                    idx,
                )
                for idx, obj_id in enumerate(obj_ids)
            ]
        )
        .alias("values_table")
    )
    return values_table


def grab_query_results(
    session,
    q,
    total_matches,
    page,
    n_items_per_page,
    items_name,
    order_by=None,
    include_thumbnails=True,
    include_detection_stats=False,
    query_id=None,
    use_cache=False,
    current_user=None,
):
    """
    Returns a SQLAlchemy Query object (which is iterable) for the sorted Obj IDs desired.
    If there are no matching Objs, an empty list [] is returned instead.
    include_detection_stats is added to the pagination query directly here.
    """
    # The query will return multiple rows per candidate object if it has multiple
    # annotations associated with it, with rows appearing at the end of the query
    # for any annotations with origins not equal to the one being sorted on (if applicable).
    # We want to essentially grab only the candidate objects as they first appear
    # in the query results, and ignore these other irrelevant annotation entries.

    # Add a "row_num" column to the desire query that explicitly encodes the ordering
    # of the query results - remember that these query rows are essentially
    # (Obj, Annotation) tuples, so the earliest row numbers for a given Obj is
    # the one we want to adhere to (and the later ones are annotation records for
    # the candidate that are not being sorted/filtered on right now)
    #
    # The row number must be preserved like this in order to remember the desired
    # ordering info even while using the passed in query as a subquery to select
    # from. This is because subqueries provide a set of results to query from,
    # losing any order_by information.
    row = func.row_number().over(order_by=order_by).label("row_num")
    full_query = q.add_columns(row)

    info = {}
    full_query = full_query.subquery()
    # Using the PostgreSQL DISTINCT ON keyword, we grab the candidate Obj ids
    # in the order that they first appear in the query (per the row_num values)
    # NOTE: It is probably possible to grab the full Obj records here instead of
    # just the ID values, but querying "full_query" here means we lost the original
    # ORM mappings, so we would have to explicity re-label the columns here.
    # It is much more straightforward to just get an ordered list of Obj ID
    # values here and get the corresponding n_items_per_page full Obj objects
    # at the end, I think, for minimal additional overhead.
    ids_with_row_nums = (
        sa.select(full_query.c.id, full_query.c.row_num)
        .distinct(full_query.c.id)
        .order_by(full_query.c.id, full_query.c.row_num)
        .subquery()
    )
    # Grouping and getting the first distinct obj_id above messed up the order
    # in the query set, so re-order by the row_num we used to remember the
    # original ordering
    ordered_ids = sa.select(
        ids_with_row_nums.c.id,
    ).order_by(ids_with_row_nums.c.row_num)

    if page:
        if use_cache:
            cache_filename = cache[query_id]
            if cache_filename is not None:
                all_ids = np.load(cache_filename)
            else:
                # Cache expired/removed/non-existent; create new cache file
                query_id = str(uuid.uuid4())
                all_ids = session.scalars(ordered_ids).unique().all()
                cache[query_id] = array_to_bytes(all_ids)
            totalMatches = len(all_ids)
            obj_ids_in_page = all_ids[
                ((page - 1) * n_items_per_page) : (page * n_items_per_page)
            ]
            info["queryID"] = query_id
        else:
            count_stmt = sa.select(func.count()).select_from(ordered_ids)
            totalMatches = session.execute(count_stmt).scalar()
            obj_ids_in_page = (
                session.scalars(
                    ordered_ids.limit(n_items_per_page).offset(
                        (page - 1) * n_items_per_page
                    )
                )
                .unique()
                .all()
            )
        info["pageNumber"] = page
        info["numPerPage"] = n_items_per_page
    else:
        count_stmt = sa.select(func.count()).select_from(ordered_ids)
        totalMatches = session.execute(count_stmt).scalar()
        obj_ids_in_page = session.execute(ordered_ids).unique().all()

    info["totalMatches"] = totalMatches

    if page:
        if (
            (
                (
                    info["totalMatches"] < (page - 1) * n_items_per_page
                    and info["totalMatches"] % n_items_per_page != 0
                )
                or (
                    info["totalMatches"] < page * n_items_per_page
                    and info["totalMatches"] % n_items_per_page == 0
                )
                and info["totalMatches"] != 0
            )
            or page <= 0
            or (info["totalMatches"] == 0 and page != 1)
        ):
            raise ValueError("Page number out of range.")

    options = []
    if include_thumbnails:
        options.append(joinedload(Obj.thumbnails))
    if include_detection_stats:
        options.append(joinedload(Obj.photstats))

    items = []
    if len(obj_ids_in_page) > 0:
        # If there are no values, the VALUES statement above will cause a syntax error,
        # so only filter on the values if they exist
        obj_ids_values = get_obj_id_values(obj_ids_in_page)

        items = (
            session.execute(
                sa.select(Obj)
                .options(*options)
                .join(obj_ids_values, obj_ids_values.c.id == Obj.id)
                .order_by(obj_ids_values.c.ordering)
            )
            .unique()
            .all()
        )

    info[items_name] = items
    return info
