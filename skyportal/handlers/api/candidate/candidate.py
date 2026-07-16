import datetime
import json
import operator
import re
import time
import uuid
from copy import copy

import arrow
import astropy.units as u
import healpix_alchemy as ha
import numpy as np
import sqlalchemy as sa
from astropy.time import Time
from marshmallow.exceptions import ValidationError
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload  # noqa: F401
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.sql import Values, bindparam, column, text
from sqlalchemy.sql.expression import case, cast, func
from sqlalchemy.types import Boolean, Float, Integer, String

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from skyportal.log import make_log

from ....models import (
    Allocation,
    Annotation,
    AnnotationOnPhotometry,
    Candidate,
    Classification,
    Comment,
    Filter,
    FollowupRequest,
    Group,
    Listing,
    Localization,
    LocalizationTile,
    Obj,
    ObjToSuperObj,
    Photometry,
    PhotStat,
    Source,
    Spectrum,
    SuperObj,
)
from ....utils.cache import Cache, array_to_bytes
from ....utils.calculations import great_circle_distance
from ....utils.data_access import (
    accessible_group_and_filter_ids,
    accessible_group_ids_async,
)
from ....utils.parse import get_page_and_n_per_page
from ....utils.sizeof import SIZE_WARNING_THRESHOLD, sizeof
from ...base import BaseHandler
from .candidate_filter import (
    get_subquery_for_saved_status,
)

MAX_NUM_DAYS_USING_LOCALIZATION = 31 * 12 * 10  # 10 years

_, cfg = load_env()
cache_dir = "cache/candidates_queries"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_candidate_query_cache"] * 60,
)
log = make_log("api/candidate")


def update_summary_history_if_relevant(results_data, obj, user):
    if "summary" in results_data:
        summary_history = copy(obj.summary_history) if obj.summary_history else []
        summary_params = {
            "set_by_user_id": user.id,
            "set_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "summary": results_data["summary"],
            "is_bot": results_data.get("is_bot", False),
            "analysis_id": results_data.get("analysis_id"),
        }

        if "summary_origin" in results_data:
            summary_params["origin"] = results_data["summary_origin"]

        summary_history.insert(0, summary_params)
        obj.summary = results_data["summary"]
        obj.summary_history = summary_history


def update_redshift_history_if_relevant(request_data, obj, user):
    if "redshift" in request_data:
        redshift_history = copy(obj.redshift_history) if obj.redshift_history else []
        history_params = {
            "set_by_user_id": user.id,
            "set_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "value": request_data["redshift"],
            "uncertainty": request_data.get("redshift_error"),
        }

        origin = request_data.get("redshift_origin")
        if isinstance(origin, str) and origin.strip():
            history_params["origin"] = origin

        redshift_history.append(history_params)
        obj.redshift_history = redshift_history


def update_healpix_if_relevant(request_data, obj):
    # first check if the ra and dec is being updated
    ra = request_data.get("ra")
    dec = request_data.get("dec")

    if ra is not None and dec is not None:
        # This adds a healpix index for a new object being created
        obj.healpix = ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)
        return

    # otherwise make sure healpix is correct
    if obj.ra is not None and obj.dec is not None:
        obj.healpix = ha.constants.HPX.lonlat_to_healpix(
            obj.ra * u.deg, obj.dec * u.deg
        )


def create_photometry_annotations_query(
    session,
    photometry_annotations_filter_origin=None,
    photometry_annotations_filter_before=None,
    photometry_annotations_filter_after=None,
):
    photometry_annotations_query = AnnotationOnPhotometry.select(
        session.user_or_token,
        columns=[
            AnnotationOnPhotometry.obj_id.label("obj_id"),
            func.count(AnnotationOnPhotometry.obj_id).label("count"),
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


async def fetch_obj_data(model, options, obj_id, session):
    """Async fetch of all rows of ``model`` for ``obj_id``."""
    result = await session.scalars(
        model.select(session.user_or_token, options=options).where(
            model.obj_id == obj_id
        )
    )
    return result.unique().all()


async def include_requested_obj_data(
    obj_id, candidate, get_query_argument, session, include_phot_annotations
):
    """Add object data to the candidate dictionary based on the query
    parameters. Async equivalent of the previous sync version — uses
    ``selectinload`` to avoid lazy loads on the merged objects.

    Parameters
    ----------
    obj_id : str
        The object ID
    candidate : dict
        The candidate dictionary
    get_query_argument : func
        The function to get query arguments
    session : ``sqlalchemy.ext.asyncio.AsyncSession``
    include_phot_annotations : bool
        Whether to include photometry annotations

    Returns
    -------
    dict
        The updated candidate dictionary
    """
    if get_query_argument("includePhotometry", False):
        phot_options = [selectinload(Photometry.instrument)]

        if include_phot_annotations:
            phot_options.append(selectinload(Photometry.annotations))
            candidate["photometry"] = await fetch_obj_data(
                Photometry, phot_options, obj_id, session
            )
            candidate["photometry"] = [
                {
                    **phot.to_dict(),
                    "annotations": [
                        annotation.to_dict() for annotation in phot.annotations
                    ],
                }
                for phot in candidate["photometry"]
            ]
        else:
            candidate["photometry"] = await fetch_obj_data(
                Photometry, phot_options, obj_id, session
            )

    if get_query_argument("includeSpectra", False):
        candidate["spectra"] = await fetch_obj_data(
            Spectrum, [selectinload(Spectrum.instrument)], obj_id, session
        )

    if get_query_argument("includeComments", False):
        candidate["comments"] = sorted(
            await fetch_obj_data(
                Comment, [selectinload(Comment.author)], obj_id, session
            ),
            key=lambda x: x.created_at,
            reverse=True,
        )
    if get_query_argument("includeFollowupRequests", False):
        candidate["followup_requests"] = await fetch_obj_data(
            FollowupRequest,
            [
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.group,
                ),
                selectinload(FollowupRequest.requester),
            ],
            obj_id,
            session,
        )

    if get_query_argument("includeAssociatedObjs", True):
        # For each associated obj, we include the same info as for duplicates
        # (obj_id, ra, dec, separation), plus super_obj_{id,name}.
        super_objs_result = await session.scalars(
            sa.select(SuperObj)
            .options(selectinload(SuperObj.objs))
            .where(SuperObj.objs.any(Obj.id == obj_id))
        )
        super_objs = super_objs_result.unique().all()
        associated_objs = []
        for super_obj in super_objs:
            super_obj_id = super_obj.id
            super_obj_name = super_obj.name
            for obj in super_obj.objs:
                if obj.id == obj_id:
                    continue
                associated_objs.append(
                    {
                        "obj_id": obj.id,
                        "ra": obj.ra,
                        "dec": obj.dec,
                        "separation": great_circle_distance(
                            candidate["ra"], candidate["dec"], obj.ra, obj.dec
                        )
                        * 3600,
                        "super_obj_id": super_obj_id,
                        "super_obj_name": super_obj_name,
                    }
                )
        candidate["associated_objs"] = sorted(
            associated_objs, key=lambda x: x["separation"]
        )

    candidate["annotations"] = sorted(
        await fetch_obj_data(
            Annotation, [selectinload(Annotation.groups)], obj_id, session
        ),
        key=lambda x: x.origin,
    )
    return candidate


def add_computed_fields(candidate_info, obj):
    if obj.photstats and obj.photstats[-1].last_detected_mjd is not None:
        candidate_info["last_detected_at"] = Time(
            obj.photstats[-1].last_detected_mjd, format="mjd"
        ).datetime
    else:
        candidate_info["last_detected_at"] = None
    candidate_info["gal_lon"] = obj.gal_lon_deg
    candidate_info["gal_lat"] = obj.gal_lat_deg
    candidate_info["luminosity_distance"] = obj.luminosity_distance
    candidate_info["dm"] = obj.dm
    candidate_info["angular_diameter_distance"] = obj.angular_diameter_distance


class CandidateHandler(BaseHandler):
    @auth_or_token
    async def head(self, obj_id=None):
        """
        ---
        single:
          summary: Check if a Candidate exists
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
        async with self.AsyncSession() as session:
            query_params = [bindparam("objID", value=obj_id, type_=sa.String)]
            stmt = "SELECT id FROM candidates WHERE obj_id = :objID"
            if not self.associated_user_object.is_admin:
                query_params.append(
                    bindparam(
                        "userID", value=self.associated_user_object.id, type_=sa.Integer
                    )
                )
                stmt += " AND filter_id IN (SELECT DISTINCT(filters.id) FROM filters INNER JOIN group_users ON filters.group_id = group_users.group_id WHERE group_users.user_id = :userID)"
            stmt += " LIMIT 1"

            stmt = text(stmt).bindparams(*query_params).columns(id=sa.Integer)
            result = await session.execute(stmt)
            if result.fetchone():
                return self.success()
            return self.error(
                message=f"No candidate with object ID {obj_id}", status=404
            )

    @auth_or_token
    async def get(self, obj_id: str = None):
        """
        ---
        single:
          summary: Get a candidate
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
              name: includeFollowupRequests
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated follow-up requests. Defaults to false.
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
          summary: Retrieve multiple candidates
          description: Retrieve all candidates
          tags:
            - candidates
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
            name: classificationsReject
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
                Comma-separated string of classification(s) to filter OUT candidates matching
                with any of those classification(s).
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
          - in: query
            name: localizationDateobs
            schema:
              type: string
            description: |
                Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
                Each localization is associated with a specific GCNEvent by
                the date the event happened, and this date is used as a unique
                identifier. It can be therefore found as Localization.dateobs,
                queried from the /api/localization endpoint or dateobs in the
                GcnEvent page table.
          - in: query
            name: localizationName
            schema:
              type: string
            description: |
                Name of localization / skymap to use.
                Can be found in Localization.localization_name queried from
                /api/localization endpoint or skymap name in GcnEvent page
                table.
          - in: query
            name: localizationCumprob
            schema:
              type: number
            description: |
              Cumulative probability up to which to include sources
          - in: query
            name: firstDetectionAfter
            schema:
              type: string
            description: |
              Only return sources that were first detected after this UTC datetime.
          - in: query
            name: lastDetectionBefore
            schema:
              type: string
            description: |
              Only return sources that were last detected before this UTC datetime.
          - in: query
            name: numberDetections
            schema:
              type: integer
            description: |
              Only return sources that have been detected at least this many times.
          - in: query
            name: requireDetections
            schema:
              type: boolean
            description: |
              Require firstDetectionAfter, lastDetectionBefore, and numberDetections to be set when querying candidates in a localization. Defaults to True.
          - in: query
            name: excludeForcedPhotometry
            schema:
              type: boolean
            description: |
              If true, ignore forced photometry when applying firstDetectionAfter, lastDetectionBefore, and numberDetections. Defaults to False.

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

        include_alerts = self.get_query_argument("includeAlerts", False)

        if obj_id is not None:
            async with self.AsyncSession() as session:
                query_options = [
                    selectinload(Obj.thumbnails),
                    selectinload(Obj.photstats),
                ]

                c = await session.scalar(
                    Obj.select(session.user_or_token, options=query_options).where(
                        Obj.id == obj_id
                    )
                )
                if c is None:
                    return self.error("Invalid ID")
                candidate_info = recursive_to_dict(c)

                if include_alerts:
                    accessible_candidates_result = await session.scalars(
                        Candidate.select(session.user_or_token).where(
                            Candidate.obj_id == obj_id
                        )
                    )
                    accessible_candidates = accessible_candidates_result.unique().all()
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

                candidate_info = await include_requested_obj_data(
                    obj_id,
                    candidate_info,
                    self.get_query_argument,
                    session,
                    include_phot_annotations=True,
                )

                stmt = Source.select(session.user_or_token).where(
                    Source.obj_id == obj_id
                )
                count_stmt = sa.select(func.count()).select_from(
                    stmt.distinct().subquery()
                )
                candidate_info["is_source"] = await session.scalar(count_stmt)
                if candidate_info["is_source"]:
                    source_subquery = (
                        Source.select(session.user_or_token)
                        .where(Source.obj_id == obj_id)
                        .where(Source.active.is_(True))
                        .subquery()
                    )
                    saved_groups_result = await session.scalars(
                        Group.select(session.user_or_token).join(
                            source_subquery, Group.id == source_subquery.c.group_id
                        )
                    )
                    candidate_info["saved_groups"] = saved_groups_result.unique().all()
                    classifications_result = await session.scalars(
                        Classification.select(session.user_or_token).where(
                            Classification.obj_id == obj_id
                        )
                    )
                    candidate_info["classifications"] = (
                        classifications_result.unique().all()
                    )
                add_computed_fields(candidate_info, c)
                candidate_info = recursive_to_dict(candidate_info)

                query_size = sizeof(candidate_info)
                if query_size >= SIZE_WARNING_THRESHOLD:
                    end = time.time()
                    duration = end - start
                    log.info(
                        f"User {self.associated_user_object.id} candidate query for object {obj_id} returned {query_size} bytes in {duration} seconds"
                    )

                return self.success(data=candidate_info)

        page_number = self.get_query_argument("pageNumber", 1)
        n_per_page = self.get_query_argument("numPerPage", 25)

        # Lightweight autocomplete for the toolbar quick-search: return candidate
        # obj_ids matching a partial name, skipping the heavy scanning-page query.
        name_only = self.get_query_argument("nameOnly", "false").lower() == "true"
        obj_id_partial = self.get_query_argument("objID", None)
        if name_only and obj_id_partial:
            async with self.AsyncSession() as session:
                group_ids = await accessible_group_ids_async(
                    session.user_or_token, session
                )
                matches = await session.scalars(
                    sa.select(Candidate.obj_id)
                    .join(Filter, Filter.id == Candidate.filter_id)
                    .where(
                        Candidate.obj_id.ilike(f"{obj_id_partial}%"),
                        Filter.group_id.in_(group_ids),
                    )
                    .distinct()
                    .order_by(Candidate.obj_id)
                    .limit(int(n_per_page))
                )
                return self.success(
                    data={"candidates": [{"id": oid} for oid in matches.all()]}
                )
        # Not documented in API docs as this is for frontend-only usage & will confuse
        # users looking through the API docs
        query_id = self.get_query_argument("queryID", None)
        saved_status = self.get_query_argument("savedStatus", "all")
        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        group_ids = self.get_query_argument("groupIDs", None)
        filter_ids = self.get_query_argument("filterIDs", None)
        sort_by_origin = self.get_query_argument("sortByAnnotationOrigin", None)
        annotation_filter_list = self.get_query_argument("annotationFilterList", None)
        classifications = self.get_query_argument("classifications", None)
        classifications_reject = self.get_query_argument("classificationsReject", None)
        min_redshift = self.get_query_argument("minRedshift", None)
        max_redshift = self.get_query_argument("maxRedshift", None)
        list_name = self.get_query_argument("listName", None)
        list_name_reject = self.get_query_argument("listNameReject", None)
        autosave = self.get_query_argument("autosave", False)
        autosave_group_ids = self.get_query_argument("autosaveGroupIds", None)
        photometry_annotations_filter = self.get_query_argument(
            "photometryAnnotationsFilter", None
        )
        photometry_annotations_filter_origin = self.get_query_argument(
            "photometryAnnotationsFilterOrigin", None
        )
        photometry_annotations_filter_after = self.get_query_argument(
            "photometryAnnotationsFilterAfter", None
        )
        photometry_annotations_filter_before = self.get_query_argument(
            "photometryAnnotationsFilterBefore", None
        )
        # Parse to naive datetimes so the query compares against the timestamp
        # column rather than a string (Postgres has no timestamp >= text op).
        if photometry_annotations_filter_after is not None:
            try:
                photometry_annotations_filter_after = arrow.get(
                    photometry_annotations_filter_after
                ).naive
            except Exception:
                return self.error(
                    f"Invalid photometryAnnotationsFilterAfter: "
                    f"{photometry_annotations_filter_after}"
                )
        if photometry_annotations_filter_before is not None:
            try:
                photometry_annotations_filter_before = arrow.get(
                    photometry_annotations_filter_before
                ).naive
            except Exception:
                return self.error(
                    f"Invalid photometryAnnotationsFilterBefore: "
                    f"{photometry_annotations_filter_before}"
                )
        photometry_annotations_filter_min_count = self.get_query_argument(
            "photometryAnnotationsFilterMinCount", 1
        )

        first_detected_date = self.get_query_argument("firstDetectionAfter", None)
        last_detected_date = self.get_query_argument("lastDetectionBefore", None)
        number_of_detections = self.get_query_argument("numberDetections", None)
        require_detections = self.get_query_argument("requireDetections", True)
        exclude_forced_photometry = self.get_query_argument(
            "excludeForcedPhotometry", False
        )
        localization_dateobs = self.get_query_argument("localizationDateobs", None)
        localization_name = self.get_query_argument("localizationName", None)
        localization_cumprob = self.get_query_argument(
            "localizationCumprob", 0.95, type=float
        )

        if localization_dateobs is not None:
            try:
                localization_dateobs = arrow.get(localization_dateobs).naive
            except Exception:
                return self.error(
                    f"Invalid localizationDateobs: {localization_dateobs}"
                )

        if (localization_dateobs or localization_name) and require_detections:
            if (
                not first_detected_date
                or not last_detected_date
                or number_of_detections is None
            ):
                return self.error(
                    "must specify startDate, endDate and numberDetections when requireDetections is True and "
                    "filtering by localizationDateobs or localizationName"
                )
            try:
                first_detected_date = arrow.get(first_detected_date).datetime
                last_detected_date = arrow.get(last_detected_date).datetime
            except Exception:
                return self.error(
                    "firstDetectionAfter and lastDetectionBefore must be valid UTC dates"
                )
            if first_detected_date > last_detected_date:
                return self.error(
                    "startDate must be before endDate when filtering by localizationDateobs or localizationName",
                )
            if (
                last_detected_date - first_detected_date
            ).days > MAX_NUM_DAYS_USING_LOCALIZATION:
                return self.error(
                    "startDate and endDate must be less than 10 years apart when filtering by localizationDateobs or localizationName",
                )

        try:
            page_number, n_per_page = get_page_and_n_per_page(page_number, n_per_page)
        except ValueError as e:
            return self.error(str(e))

        async with self.AsyncSession() as session:
            # first, we get the list of group IDs and filter IDs
            # that the user has access to
            group_ids, filter_ids = await accessible_group_and_filter_ids(
                session,
                session.user_or_token,
                group_ids,
                filter_ids,
            )

            # since we verified filter and group IDs already, we can safely
            # query the candidates table without applying data access rules
            # i.e. sa.select(Candidate) instead of Candidate.select(session.user_or_token)
            # this will simplify the query generated by sqlalchemy and improve performance
            candidate_query = sa.select(Candidate).where(
                Candidate.filter_id.in_(filter_ids)
            )
            if start_date and start_date.strip().lower() not in {
                "",
                "null",
                "undefined",
            }:
                try:
                    start_date = arrow.get(start_date).datetime
                except Exception as e:
                    return self.error(f"Invalid startDate value: {e}")
                candidate_query = candidate_query.where(
                    Candidate.passed_at >= start_date
                )
            if end_date and end_date.strip().lower() not in {"", "null", "undefined"}:
                try:
                    end_date = arrow.get(end_date).datetime
                except Exception as e:
                    return self.error(f"Invalid endDate value: {e}")
                candidate_query = candidate_query.where(Candidate.passed_at <= end_date)
            candidate_subquery = candidate_query.subquery()
            # We'll join in the nested data for Obj (like photometry) later
            q = sa.select(Obj.id).join(
                candidate_subquery, Obj.id == candidate_subquery.c.obj_id
            )
            if sort_by_origin is not None or annotation_filter_list is not None:
                q = q.outerjoin(Annotation)

            if isinstance(classifications, str):
                if "," in classifications:
                    classifications = [c.strip() for c in classifications.split(",")]
                else:
                    classifications = [classifications]
                q = q.join(Classification).where(
                    Classification.classification.in_(classifications)
                )
            elif classifications is not None:
                return self.error(
                    "Invalid classifications value -- must provide at least one string value"
                )
            if isinstance(classifications_reject, str):
                if "," in classifications_reject:
                    classifications_reject = [
                        c.strip() for c in classifications_reject.split(",")
                    ]
                else:
                    classifications_reject = [classifications_reject]
                # here we want to keep candidates that:
                #   1. have no classification
                #   2. do not have one of the classifications_reject as a classification
                # first create a subquery to get the classifications we are trying to avoid
                classifications_reject_subquery = (
                    Classification.select(
                        session.user_or_token, columns=[Classification.obj_id]
                    )
                    .where(Classification.classification.in_(classifications_reject))
                    .subquery()
                )
                # then left outer join on that subquery
                q = q.outerjoin(
                    classifications_reject_subquery,
                    Obj.id == classifications_reject_subquery.c.obj_id,
                ).where(classifications_reject_subquery.c.obj_id.is_(None))
            elif classifications_reject is not None:
                return self.error(
                    "Invalid classificationsReject value -- must provide at least one string value"
                )

            if sort_by_origin is None:
                # Don't apply the order by just yet. Save it so we can pass it to
                # the LIMIT/OFFSET helper function down the line once other query
                # params are set.
                order_by = [candidate_subquery.c.passed_at.desc().nullslast(), Obj.id]

            q = get_subquery_for_saved_status(
                session, q, saved_status, group_ids, session.user_or_token
            )

            if q is None:
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

            if self.get_query_argument(
                "annotationExcludeOrigin", None
            ) or self.get_query_argument("annotationExcludeOutdatedDate", None):
                return self.error(
                    "annotationExcludeOrigin and annotationExcludeOutdatedDate parameters are no longer supported"
                )

            if list_name is not None:
                listing_subquery = (
                    Obj.select(session.user_or_token, columns=[Obj.id])
                    .join(Listing)
                    .where(
                        Listing.list_name == list_name,
                        Listing.user_id == self.associated_user_object.id,
                    )
                    .subquery()
                )
                q = q.join(listing_subquery, Obj.id == listing_subquery.c.id)
            if list_name_reject is not None:
                right = (
                    Obj.select(session.user_or_token, columns=[Obj.id])
                    .join(Listing)
                    .where(
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
                        return self.error(
                            f'Invalid annotation filter list item {item}: "origin" is required.'
                        )

                    if "key" not in new_filter:
                        return self.error(
                            f'Invalid annotation filter list item {item}: "key" is required.'
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
                            q = q.where(
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
                            f'Invalid annotation filter list item: {item}. Should have either "value" or "min" and "max"'
                        )

            if sort_by_origin is not None:
                sort_by_key = self.get_query_argument("sortByAnnotationKey", None)
                sort_by_order = self.get_query_argument("sortByAnnotationOrder", None)
                # Define a custom sort order to have annotations from the correct origin first, all others afterward
                origin_sort_order = case(
                    (Annotation.origin == sort_by_origin, 1),
                    else_=None,
                )
                annotation_sort_criterion = (
                    Annotation.data[sort_by_key].desc().nullslast()
                    if sort_by_order == "desc"
                    else Annotation.data[sort_by_key].nullslast()
                )
                # Don't apply the order by just yet. Save it so we can pass it to
                # the LIMIT/OFFSET helper function.
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
                    return self.error(
                        "Invalid annotationsFilter value -- must provide at least one string value"
                    )
            if photometry_annotations_filter_origin is not None:
                if isinstance(photometry_annotations_filter_origin, str):
                    photometry_annotations_filter_origin = [
                        c.strip()
                        for c in photometry_annotations_filter_origin.split(",")
                    ]
                else:
                    return self.error(
                        "Invalid annotationsFilterOrigin value -- must provide at least one string value"
                    )

            if (
                photometry_annotations_filter_origin is not None
                or photometry_annotations_filter_before is not None
                or photometry_annotations_filter_after is not None
                or photometry_annotations_filter is not None
            ):
                photometry_annotations_query = create_photometry_annotations_query(
                    session,
                    photometry_annotations_filter_origin=photometry_annotations_filter_origin,
                    photometry_annotations_filter_before=photometry_annotations_filter_before,
                    photometry_annotations_filter_after=photometry_annotations_filter_after,
                )
                if photometry_annotations_filter is not None:
                    for ann_filt in photometry_annotations_filter:
                        ann_split = ann_filt.split(":")
                        if len(ann_split) not in (1, 3):
                            return self.error(
                                "Invalid photometryAnnotationsFilter value -- annotation filter must have 1 or 3 values"
                            )
                        name = ann_split[0].strip()

                        if len(ann_split) == 3:
                            value = ann_split[1].strip()
                            try:
                                value = float(value)
                            except ValueError as e:
                                return self.error(
                                    f"Invalid annotation filter value: {e}"
                                )
                            op = ann_split[2].strip()
                            if op not in {"lt", "le", "eq", "ne", "ge", "gt"}:
                                return self.error(f"Invalid operator: {op}")
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

                photometry_annotations_subquery = (
                    photometry_annotations_query.subquery()
                )
                obj_photometry_annotations_query = sa.select(Obj.id).join(
                    photometry_annotations_subquery,
                    sa.and_(
                        photometry_annotations_subquery.c.count
                        >= photometry_annotations_filter_min_count,
                        photometry_annotations_subquery.c.obj_id == Obj.id,
                    ),
                )
                obj_photometry_annotations_subquery = (
                    obj_photometry_annotations_query.subquery()
                )

                q = q.join(
                    obj_photometry_annotations_subquery,
                    Obj.id == obj_photometry_annotations_subquery.c.id,
                )
            if require_detections:
                photstat_subquery_columns = [PhotStat.obj_id]
                photstat_subquery_conditions = []
                if first_detected_date is not None:
                    column = (
                        PhotStat.first_detected_no_forced_phot_mjd
                        if exclude_forced_photometry
                        else PhotStat.first_detected_mjd
                    )
                    photstat_subquery_columns.append(column)
                    photstat_subquery_conditions.append(
                        column >= Time(first_detected_date).mjd
                    )
                if last_detected_date is not None:
                    column = (
                        PhotStat.last_detected_no_forced_phot_mjd
                        if exclude_forced_photometry
                        else PhotStat.last_detected_mjd
                    )
                    photstat_subquery_columns.append(column)
                    photstat_subquery_conditions.append(
                        column <= Time(last_detected_date).mjd
                    )
                if number_of_detections is not None:
                    try:
                        number_of_detections = int(number_of_detections)
                    except ValueError:
                        return self.error(
                            "Invalid numberDetections value -- must be an integer"
                        )
                    column = (
                        PhotStat.num_det_no_forced_phot_global
                        if exclude_forced_photometry
                        else PhotStat.num_det_global
                    )
                    photstat_subquery_columns.append(column)
                    photstat_subquery_conditions.append(column >= number_of_detections)

                if photstat_subquery_conditions:
                    photstat_subquery = (
                        PhotStat.select(
                            session.user_or_token, columns=photstat_subquery_columns
                        )
                        .where(sa.and_(*photstat_subquery_conditions))
                        .subquery()
                    )
                    q = q.join(
                        photstat_subquery,
                        Obj.id == photstat_subquery.c.obj_id,
                    )
            if localization_dateobs is not None:
                if localization_name is None:
                    localization = await session.scalar(
                        Localization.select(self.associated_user_object)
                        .where(Localization.dateobs == localization_dateobs)
                        .order_by(Localization.created_at.desc())
                    )
                else:
                    localization = await session.scalar(
                        Localization.select(self.associated_user_object)
                        .where(Localization.dateobs == localization_dateobs)
                        .where(Localization.localization_name == localization_name)
                        .order_by(Localization.modified.desc())
                    )
                if localization is None:
                    if localization_name is not None:
                        return self.error(
                            f"Localization {localization_dateobs} with name {localization_name} not found",
                        )
                    else:
                        return self.error(
                            f"Localization {localization_dateobs} not found",
                        )

                try:
                    partition_key = arrow.get(localization.dateobs).datetime
                except Exception as e:
                    return self.error(f"Invalid localization dateobs value: {e}")
                localizationtile_partition_name = (
                    f"{partition_key.year}_{partition_key.month:02d}"
                )
                localizationtilescls = LocalizationTile.partitions.get(
                    localizationtile_partition_name, None
                )
                if localizationtilescls is None:
                    localizationtilescls = LocalizationTile.partitions.get(
                        "def", LocalizationTile
                    )
                else:
                    existing_tile = await session.scalar(
                        localizationtilescls.select(session.user_or_token).where(
                            localizationtilescls.localization_id == localization.id
                        )
                    )
                    if not existing_tile:
                        localizationtilescls = LocalizationTile.partitions.get(
                            "def", LocalizationTile
                        )

                cum_prob = (
                    sa.func.sum(
                        localizationtilescls.probdensity
                        * localizationtilescls.healpix.area
                    )
                    .over(order_by=localizationtilescls.probdensity.desc())
                    .label("cum_prob")
                )

                localizationtile_subquery = (
                    sa.select(localizationtilescls.probdensity, cum_prob).where(
                        localizationtilescls.localization_id == localization.id
                    )
                ).subquery()

                min_probdensity = (
                    sa.select(
                        sa.func.min(localizationtile_subquery.columns.probdensity)
                    ).where(
                        localizationtile_subquery.columns.cum_prob
                        <= localization_cumprob
                    )
                ).scalar_subquery()

                tile_ids_result = await session.scalars(
                    sa.select(localizationtilescls.id).where(
                        localizationtilescls.localization_id == localization.id,
                        localizationtilescls.probdensity >= min_probdensity,
                    )
                )
                tile_ids = tile_ids_result.all()

                tiles_subquery = (
                    sa.select(Obj.id)
                    .where(
                        localizationtilescls.id.in_(tile_ids),
                        localizationtilescls.healpix.contains(Obj.healpix),
                    )
                    .subquery()
                )
                q = q.join(
                    tiles_subquery,
                    Obj.id == tiles_subquery.c.id,
                )

            try:
                query_results = await grab_query_results(
                    session,
                    q,
                    page_number,
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

            matching_source_ids_result = await session.scalars(
                Source.select(session.user_or_token, columns=[Source.obj_id]).where(
                    Source.obj_id.in_(
                        [obj.id for (obj,) in query_results["candidates"]]
                    )
                )
            )
            matching_source_ids = matching_source_ids_result.unique().all()
            candidate_list = []
            if autosave:
                from ..source import post_source_async

            for (obj,) in query_results["candidates"]:
                # AsyncSession.no_autoflush is a property; use the proxy.
                with session.sync_session.no_autoflush:
                    obj.is_source = obj.id in matching_source_ids
                    if obj.is_source:
                        source_subquery = (
                            Source.select(session.user_or_token)
                            .where(Source.obj_id == obj.id)
                            .where(Source.active.is_(True))
                            .subquery()
                        )
                        saved_groups_result = await session.scalars(
                            Group.select(session.user_or_token).join(
                                source_subquery, Group.id == source_subquery.c.group_id
                            )
                        )
                        obj.saved_groups = saved_groups_result.unique().all()
                        classifications_result = await session.scalars(
                            Classification.select(self.current_user).where(
                                Classification.obj_id == obj.id
                            )
                        )
                        # Direct assignment would lazy-load the existing
                        # `Obj.classifications` collection before replace,
                        # which trips MissingGreenlet under async. Use
                        # set_committed_value to set it without trigger.
                        set_committed_value(
                            obj,
                            "classifications",
                            classifications_result.unique().all(),
                        )
                    candidate_filter_ids_result = await session.scalars(
                        Candidate.select(
                            session.user_or_token,
                            columns=[Candidate.filter_id],
                        ).where(Candidate.obj_id == obj.id)
                    )
                    candidate_filter_ids = candidate_filter_ids_result.all()
                    passing_filters_result = await session.scalars(
                        Filter.select(session.user_or_token).where(
                            Filter.id.in_(candidate_filter_ids)
                        )
                    )
                    passing_filters = passing_filters_result.all()
                    obj.passing_group_ids = [f.group_id for f in passing_filters]
                    if autosave:
                        source = {
                            "id": obj.id,
                            "group_ids": autosave_group_ids,
                        }
                        await post_source_async(
                            source,
                            self.associated_user_object.id,
                            session,
                        )

                    candidate_list.append(recursive_to_dict(obj))
                    candidate_list[-1] = await include_requested_obj_data(
                        obj.id,
                        candidate_list[-1],
                        self.get_query_argument,
                        session,
                        include_phot_annotations=False,
                    )

                    selected_groups_annotations = []
                    other_annotations = []
                    for annotation in candidate_list[-1]["annotations"]:
                        if set(group_ids).intersection(
                            {group.id for group in annotation.groups}
                        ):
                            selected_groups_annotations.append(annotation)
                        else:
                            other_annotations.append(annotation)
                    candidate_list[-1]["annotations"] = (
                        selected_groups_annotations + other_annotations
                    )
                    add_computed_fields(candidate_list[-1], obj)

            query_results["candidates"] = candidate_list
            query_results = recursive_to_dict(query_results)

            query_size = sizeof(query_results)
            if query_size >= SIZE_WARNING_THRESHOLD:
                end = time.time()
                duration = end - start
                log.info(
                    f"User {self.associated_user_object.id} candidate query returned {query_size} bytes in {duration} seconds"
                )

            return self.success(data=query_results)

    @permissions(["Upload data"])
    async def post(self):
        """
        ---
        summary: Create new candidate(s)
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

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == data["id"])
            )
            obj_already_exists = obj is not None
            schema = Obj.__schema__()

            if data.get("ra") is None and not obj_already_exists:
                return self.error("RA must not be null for a new Obj")

            if data.get("dec") is None and not obj_already_exists:
                return self.error("Dec must not be null for a new Obj")

            passing_alert_id = data.pop("passing_alert_id", None)
            passed_at = data.pop("passed_at", None)
            if passed_at is None:
                return self.error("Missing required parameter: `passed_at`.")
            try:
                passed_at = arrow.get(passed_at).datetime
            except Exception as e:
                return self.error(f"Invalid passedAt value: {e}")
            try:
                filter_ids = data.pop("filter_ids")
            except KeyError:
                return self.error("Missing required filter_ids parameter.")

            if not obj_already_exists:
                try:
                    obj = schema.load(data)
                except ValidationError as e:
                    return self.error(
                        f"Invalid/missing parameters: {e.normalized_messages()}"
                    )
                session.add(obj)
                await session.flush()

            filters_result = await session.scalars(
                Filter.select(session.user_or_token).where(Filter.id.in_(filter_ids))
            )
            filters = filters_result.unique().all()
            if not filters:
                return self.error("At least one valid filter ID must be provided.")

            update_redshift_history_if_relevant(data, obj, self.associated_user_object)
            update_healpix_if_relevant(data, obj)

            # Capture obj.id BEFORE the commit attempt so that we can still
            # build an error message after a rollback (which detaches obj).
            obj_id_str = obj.id

            candidates = [
                Candidate(
                    obj_id=obj_id_str,
                    filter_id=filter.id,
                    passing_alert_id=passing_alert_id,
                    passed_at=passed_at,
                    uploader_id=self.associated_user_object.id,
                )
                for filter in filters
            ]
            session.add_all(candidates)
            try:
                await session.commit()
                ids = [c.id for c in candidates]
            except IntegrityError as e:
                await session.rollback()
                return self.error(
                    f"Failed to post candidate for object {obj_id_str}: {e.args[0]}"
                )

            return self.success(data={"ids": ids})

    @permissions(["Upload data"])
    async def delete(self, obj_id: str, filter_id: int):
        """
        ---
        summary: Delete candidate(s)
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Success'
        """

        async with self.AsyncSession() as session:
            result = await session.scalars(
                Candidate.select(session.user_or_token, mode="delete")
                .where(Candidate.obj_id == obj_id)
                .where(Candidate.filter_id == filter_id)
            )
            cands_to_delete = result.all()
            if not cands_to_delete:
                return self.error(
                    "Invalid (obj_id, filter_id) pairing - no matching candidates"
                )
            for cand in cands_to_delete:
                await session.delete(cand)
            await session.commit()
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
        .data([(obj_id, idx) for idx, obj_id in enumerate(obj_ids)])
        .alias("values_table")
    )
    return values_table


async def grab_query_results(
    session,
    q,
    page,
    n_items_per_page,
    items_name,
    order_by=None,
    include_thumbnails=True,
    include_detection_stats=False,
    query_id=None,
    use_cache=False,
):
    """
    Returns a SQLAlchemy Query object (which is iterable) for the sorted Obj IDs desired.
    If there are no matching Objs, an empty list [] is returned instead.
    include_detection_stats is added to the pagination query directly here.
    """
    row = func.row_number().over(order_by=order_by).label("row_num")
    full_query = q.add_columns(row)

    info = {}
    full_query = full_query.subquery()
    ids_with_row_nums = (
        sa.select(full_query.c.id, full_query.c.row_num)
        .distinct(full_query.c.id)
        .order_by(full_query.c.id, full_query.c.row_num)
        .subquery()
    )
    ordered_ids = sa.select(
        ids_with_row_nums.c.id,
    ).order_by(ids_with_row_nums.c.row_num)

    if page:
        if use_cache:
            cache_filename = cache[query_id]
            if cache_filename is not None:
                all_ids = np.load(cache_filename)
            else:
                query_id = str(uuid.uuid4())
                all_result = await session.scalars(ordered_ids)
                all_ids = all_result.unique().all()
                cache[query_id] = array_to_bytes(all_ids)
            total_matches = len(all_ids)
            obj_ids_in_page = all_ids[
                ((page - 1) * n_items_per_page) : (page * n_items_per_page)
            ]
            info["queryID"] = query_id
        else:
            count_stmt = sa.select(func.count()).select_from(ordered_ids.subquery())
            total_matches = await session.scalar(count_stmt)
            page_result = await session.scalars(
                ordered_ids.limit(n_items_per_page).offset(
                    (page - 1) * n_items_per_page
                )
            )
            obj_ids_in_page = page_result.unique().all()
        info["pageNumber"] = page
        info["numPerPage"] = n_items_per_page
    else:
        count_stmt = sa.select(func.count()).select_from(ordered_ids.subquery())
        total_matches = await session.scalar(count_stmt)
        page_result = await session.execute(ordered_ids)
        obj_ids_in_page = page_result.unique().all()

    info["totalMatches"] = total_matches

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
        options.append(selectinload(Obj.thumbnails))
    if include_detection_stats:
        options.append(selectinload(Obj.photstats))

    items = []
    if len(obj_ids_in_page) > 0:
        obj_ids_values = get_obj_id_values(obj_ids_in_page)

        items_result = await session.execute(
            sa.select(Obj)
            .options(*options)
            .join(obj_ids_values, obj_ids_values.c.id == Obj.id)
            .order_by(obj_ids_values.c.ordering)
        )
        items = items_result.unique().all()

    info[items_name] = items
    return info


class BulkDeleteCandidatesHandler(BaseHandler):
    @permissions(["System admin"])
    def post(self):
        """
        ---
        summary: Bulk-delete old, unsaved candidates
        description: |
          Delete objects that appear as candidates, are not currently saved as
          an active source in any group, and whose most recent candidate
          `passed_at` is older than `maxAgeMonths`. Deleting the object cascades
          to its candidates, photometry, annotations, thumbnails, etc. System
          admin only. Intended to be driven periodically via the Recurring API.
        tags:
          - candidates
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  maxAgeMonths:
                    type: integer
                    description: |
                      Delete objects whose most recent candidate `passed_at` is
                      older than this many months. Defaults to 6.
                  batchSize:
                    type: integer
                    description: |
                      Maximum number of objects to delete in this call (deleted
                      oldest-first). Defaults to 1000.
                  dryRun:
                    type: boolean
                    description: |
                      If true, only report how many objects would be deleted,
                      without deleting anything. Defaults to false.
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
                            deleted:
                              type: integer
                              description: Number of objects deleted in this call.
                            remaining:
                              type: integer
                              description: Number of matching objects still to delete.
                            dryRun:
                              type: boolean
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        try:
            max_age_months = int(data.get("maxAgeMonths", 6))
        except (TypeError, ValueError):
            return self.error("maxAgeMonths must be an integer.")
        try:
            batch_size = int(data.get("batchSize", 1000))
        except (TypeError, ValueError):
            return self.error("batchSize must be an integer.")
        dry_run = bool(data.get("dryRun", False))

        if max_age_months < 1:
            return self.error("maxAgeMonths must be a positive integer.")
        if not (1 <= batch_size <= 10000):
            return self.error("batchSize must be between 1 and 10000.")

        cutoff = arrow.utcnow().shift(months=-max_age_months).naive

        # Objects that are candidates, are not currently saved as an active
        # source anywhere, and have no candidate activity at/after the cutoff
        # (i.e. their most recent passed_at is older than maxAgeMonths).
        criteria = sa.and_(
            Obj.id.in_(sa.select(Candidate.obj_id)),
            Obj.id.notin_(sa.select(Source.obj_id).where(Source.active.is_(True))),
            Obj.id.notin_(
                sa.select(Candidate.obj_id).where(Candidate.passed_at >= cutoff)
            ),
        )

        with self.Session() as session:
            count_stmt = sa.select(func.count()).select_from(Obj).where(criteria)

            if dry_run:
                total = int(session.scalar(count_stmt) or 0)
                return self.success(
                    data={"deleted": 0, "remaining": total, "dryRun": True}
                )

            objs = session.scalars(
                sa.select(Obj)
                .where(criteria)
                .order_by(Obj.created_at)
                .limit(batch_size)
            ).all()

            # Per-row delete so ORM cascades and the Obj `before_delete` event
            # (on-disk thumbnail cleanup) fire, rather than a bulk DELETE.
            n = len(objs)
            for obj in objs:
                session.delete(obj)
            session.commit()

            remaining = int(session.scalar(count_stmt) or 0)
            log.info(
                f"Bulk-deleted {n} unsaved candidate object(s) older than "
                f"{max_age_months} months; {remaining} remaining."
            )
            return self.success(
                data={"deleted": n, "remaining": remaining, "dryRun": False}
            )
