import datetime
from copy import copy
import re
import json

import arrow

from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import case, func
from sqlalchemy.types import Float, Boolean
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Obj,
    Candidate,
    Photometry,
    Source,
    Filter,
    Annotation,
    Group,
)


def update_redshift_history_if_relevant(request_data, obj, user):
    if "redshift" in request_data:
        if obj.redshift_history is None:
            redshift_history = []
        else:
            redshift_history = copy(obj.redshift_history)
        redshift_history.append(
            {
                "set_by_user_id": user.id,
                "set_at_utc": datetime.datetime.utcnow().isoformat(),
                "value": float(request_data["redshift"]),
            }
        )
        obj.redshift_history = redshift_history


class CandidateHandler(BaseHandler):
    @auth_or_token
    def head(self, obj_id=None):
        """
        ---
        single:
          description: Check if a Candidate exists
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
            400:
              content:
                application/json:
                  schema: Error
        """
        user_group_ids = [g.id for g in self.associated_user_object.accessible_groups]
        num_c = (
            DBSession()
            .query(Candidate)
            .join(Filter)
            .filter(Candidate.obj_id == obj_id, Filter.group_id.in_(user_group_ids))
            .count()
        )
        if num_c > 0:
            return self.success()
        else:
            self.set_status(404)
            self.finish()

    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        single:
          description: Retrieve a candidate
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
                  schema: SingleObj
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all candidates
          parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of candidates to return per paginated request. Defaults to 25
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
            name: unsavedOnly
            nullable: true
            schema:
              type: boolean
            description: Boolean indicating whether to return only unsaved candidates
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
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        include_photometry = self.get_query_argument("includePhotometry", False)

        if obj_id is not None:
            query_options = [joinedload(Candidate.obj).joinedload(Obj.thumbnails)]
            if include_photometry:
                query_options.append(
                    joinedload(Candidate.obj)
                    .joinedload(Obj.photometry)
                    .joinedload(Photometry.instrument)
                )
            c = Candidate.get_obj_if_owned_by(
                obj_id, self.current_user, options=query_options,
            )
            if c is None:
                return self.error("Invalid ID")
            accessible_candidates = (
                DBSession()
                .query(Candidate)
                .join(Filter)
                .filter(
                    Candidate.obj_id == obj_id,
                    Filter.group_id.in_(
                        [g.id for g in self.current_user.accessible_groups]
                    ),
                )
                .all()
            )
            filter_ids = [cand.filter_id for cand in accessible_candidates]

            passing_alerts = [
                {
                    "filter_id": cand.filter_id,
                    "passing_alert_id": cand.passing_alert_id,
                    "passed_at": cand.passed_at,
                }
                for cand in accessible_candidates
            ]

            candidate_info = c.to_dict()
            candidate_info["filter_ids"] = filter_ids
            candidate_info["passing_alerts"] = passing_alerts
            candidate_info["comments"] = sorted(
                [cmt.to_dict() for cmt in c.get_comments_owned_by(self.current_user)],
                key=lambda x: x["created_at"],
                reverse=True,
            )
            for comment in candidate_info["comments"]:
                comment["author"] = comment["author"].to_dict()
                del comment["author"]["preferences"]
            candidate_info["annotations"] = sorted(
                c.get_annotations_owned_by(self.current_user), key=lambda x: x.origin,
            )
            candidate_info["is_source"] = len(c.sources) > 0
            if candidate_info["is_source"]:
                candidate_info["saved_groups"] = (
                    DBSession()
                    .query(Group)
                    .join(Source)
                    .filter(Source.obj_id == obj_id)
                    .filter(Group.id.in_(user_accessible_group_ids))
                    .all()
                )
                candidate_info["classifications"] = c.get_classifications_owned_by(
                    self.current_user
                )
            candidate_info["last_detected"] = c.last_detected
            candidate_info["gal_lon"] = c.gal_lon_deg
            candidate_info["gal_lat"] = c.gal_lat_deg
            candidate_info["luminosity_distance"] = c.luminosity_distance
            candidate_info["dm"] = c.dm
            candidate_info["angular_diameter_distance"] = c.angular_diameter_distance

            return self.success(data=candidate_info)

        page_number = self.get_query_argument("pageNumber", None) or 1
        n_per_page = self.get_query_argument("numPerPage", None) or 25
        unsaved_only = self.get_query_argument("unsavedOnly", False)
        total_matches = self.get_query_argument("totalMatches", None)
        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        group_ids = self.get_query_argument("groupIDs", None)
        filter_ids = self.get_query_argument("filterIDs", None)
        sort_by_origin = self.get_query_argument("sortByAnnotationOrigin", None)
        annotation_filter_list = self.get_query_argument("annotationFilterList", None)
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        user_accessible_filter_ids = [
            filtr.id
            for g in self.current_user.accessible_groups
            for filtr in g.filters
            if g.filters is not None
        ]
        if group_ids is not None:
            if isinstance(group_ids, str) and "," in group_ids:
                group_ids = [int(g_id) for g_id in group_ids.split(",")]
            elif isinstance(group_ids, str) and group_ids.isdigit():
                group_ids = [int(group_ids)]
            else:
                return self.error("Invalid groupIDs value -- select at least one group")
            filter_ids = [
                f.id for f in Filter.query.filter(Filter.group_id.in_(group_ids))
            ]
        elif filter_ids is not None:
            if "," in filter_ids:
                filter_ids = [int(f_id) for f_id in filter_ids.split(",")]
            elif filter_ids.isdigit():
                filter_ids = [int(filter_ids)]
            else:
                return self.error("Invalid filterIDs paramter value.")
            group_ids = [
                f.group_id for f in Filter.query.filter(Filter.id.in_(filter_ids))
            ]
        else:
            # If 'groupIDs' & 'filterIDs' params not present in request, use all user groups
            group_ids = user_accessible_group_ids
            filter_ids = user_accessible_filter_ids

        # Ensure user has access to specified groups/filters
        if not (
            all([gid in user_accessible_group_ids for gid in group_ids])
            and all([fid in user_accessible_filter_ids for fid in filter_ids])
        ):
            return self.error(
                "Insufficient permissions - you must only specify "
                "groups/filters that you have access to."
            )
        try:
            page = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            n_per_page = int(n_per_page)
        except ValueError:
            return self.error("Invalid numPerPage value.")

        # We'll join in the nested data for Obj (like photometry) later
        q = Obj.query.filter(
            Obj.id.in_(
                DBSession()
                .query(Candidate.obj_id)
                .filter(Candidate.filter_id.in_(filter_ids))
            )
        ).outerjoin(
            Annotation
        )  # Join in annotations info for sort/filter
        if sort_by_origin is None:
            # Don't apply the order by just yet. Save it so we can pass it to
            # the LIMT/OFFSET helper function down the line once other query
            # params are set.
            order_by = [Obj.last_detected.desc().nullslast(), Obj.id]
        if unsaved_only == "true":
            q = q.filter(
                Obj.id.notin_(
                    DBSession()
                    .query(Source.obj_id)
                    .filter(Source.group_id.in_(group_ids))
                )
            )
        if start_date is not None and start_date.strip() not in [
            "",
            "null",
            "undefined",
        ]:
            start_date = arrow.get(start_date).datetime
            q = q.filter(Obj.last_detected >= start_date)
        if end_date is not None and end_date.strip() not in ["", "null", "undefined"]:
            end_date = arrow.get(end_date).datetime
            q = q.filter(Obj.last_detected <= end_date)
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
                        q = q.filter(
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
                        q = q.filter(
                            Annotation.origin == new_filter["origin"],
                            Annotation.data[new_filter["key"]].cast(Float) >= min_value,
                            Annotation.data[new_filter["key"]].cast(Float) <= max_value,
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
                value=Annotation.origin, whens={sort_by_origin: 1}, else_=None,
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
                Obj.last_detected.desc().nullslast(),
                Obj.id,
            ]
        try:
            query_results = grab_query_results_page(
                q,
                total_matches,
                page,
                n_per_page,
                "candidates",
                order_by=order_by,
                include_photometry=include_photometry,
            )
        except ValueError as e:
            if "Page number out of range" in str(e):
                return self.error("Page number out of range.")
            raise
        matching_source_ids = (
            DBSession()
            .query(Source.obj_id)
            .filter(Source.group_id.in_(user_accessible_group_ids))
            .filter(Source.obj_id.in_([obj.id for obj in query_results["candidates"]]))
            .all()
        )
        candidate_list = []
        for obj in query_results["candidates"]:
            obj.is_source = (obj.id,) in matching_source_ids
            if obj.is_source:
                obj.saved_groups = (
                    DBSession()
                    .query(Group)
                    .join(Source)
                    .filter(Source.obj_id == obj_id)
                    .filter(Group.id.in_(user_accessible_group_ids))
                    .all()
                )
                obj.classifications = obj.get_classifications_owned_by(
                    self.current_user
                )
            obj.passing_group_ids = [
                f.group_id
                for f in (
                    DBSession()
                    .query(Filter)
                    .filter(Filter.id.in_(user_accessible_filter_ids))
                    .filter(
                        Filter.id.in_(
                            DBSession()
                            .query(Candidate.filter_id)
                            .filter(Candidate.obj_id == obj.id)
                        )
                    )
                    .all()
                )
            ]
            candidate_list.append(obj.to_dict())
            candidate_list[-1]["comments"] = sorted(
                [cmt.to_dict() for cmt in obj.get_comments_owned_by(self.current_user)],
                key=lambda x: x["created_at"],
                reverse=True,
            )
            for comment in candidate_list[-1]["comments"]:
                comment["author"] = comment["author"].to_dict()
                del comment["author"]["preferences"]
            candidate_list[-1]["annotations"] = sorted(
                obj.get_annotations_owned_by(self.current_user), key=lambda x: x.origin,
            )
            candidate_list[-1]["last_detected"] = obj.last_detected
            candidate_list[-1]["gal_lat"] = obj.gal_lat_deg
            candidate_list[-1]["gal_lon"] = obj.gal_lon_deg
            candidate_list[-1]["luminosity_distance"] = obj.luminosity_distance
            candidate_list[-1]["dm"] = obj.dm
            candidate_list[-1][
                "angular_diameter_distance"
            ] = obj.angular_diameter_distance

        query_results["candidates"] = candidate_list
        return self.success(data=query_results)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Create a new candidate.
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/Obj'
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
                              description: New candidate ID
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

        passing_alert_id = data.pop("passing_alert_id", None)
        passed_at = data.pop("passed_at", None)
        if passed_at is not None:
            passed_at = arrow.get(passed_at).datetime
        try:
            filter_ids = data.pop("filter_ids")
        except KeyError:
            return self.error("Missing required filter_ids parameter.")
        user_accessible_filter_ids = [
            filtr.id
            for g in self.current_user.accessible_groups
            for filtr in g.filters
            if g.filters is not None
        ]
        if not all([fid in user_accessible_filter_ids for fid in filter_ids]):
            return self.error(
                "Insufficient permissions - you must only specify "
                "filters that you have access to."
            )

        try:
            obj = schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        filters = Filter.query.filter(Filter.id.in_(filter_ids)).all()
        if not filters:
            return self.error("At least one valid filter ID must be provided.")

        update_redshift_history_if_relevant(data, obj, self.associated_user_object)

        DBSession().add(obj)
        DBSession().add_all(
            [
                Candidate(
                    obj=obj,
                    filter=filter,
                    passing_alert_id=passing_alert_id,
                    passed_at=passed_at,
                )
                for filter in filters
            ]
        )
        DBSession().commit()
        if not obj_already_exists:
            obj.add_linked_thumbnails()

        return self.success(data={"id": obj.id})

    @permissions(["Manage sources"])
    def put(self, obj_id):
        """
        ---
        description: Update a candidate
        parameters:
          - in: path
            name: obj_id
            required: True
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
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
                    description: Arrow-parseable datetime string indicating when alert passed filter.
                    nullable: true
                required:
                  - filter_ids
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
        data["obj_id"] = obj_id

        # Ensure user has access to candidate
        if (
            DBSession().query(Candidate).filter(Candidate.obj_id == obj_id).first()
            is None
        ):
            return self.error("Invalid ID.")

        passing_alert_id = data.pop("passing_alert_id", None)
        passed_at = data.pop("passed_at", None)
        if passed_at is not None:
            passed_at = arrow.get(passed_at).datetime
        try:
            filter_ids = data.pop("filter_ids")
        except KeyError:
            return self.error("Missing required filter_ids parameter.")
        user_accessible_filter_ids = [
            filtr.id
            for g in self.current_user.accessible_groups
            for filtr in g.filters
            if g.filters is not None
        ]
        if not all([fid in user_accessible_filter_ids for fid in filter_ids]):
            return self.error(
                "Insufficient permissions - you must only specify "
                "filters that you have access to."
            )

        filters = Filter.query.filter(Filter.id.in_(filter_ids)).all()
        if not filters:
            return self.error("At least one valid filter ID must be provided.")

        candidates = (
            DBSession()
            .query(Candidate)
            .filter(Candidate.obj_id == obj_id, Candidate.filter_id.in_(filter_ids))
            .all()
        )

        for candidate in candidates:
            candidate.passed_at = passed_at
            candidate.passing_alert_id = passing_alert_id

        DBSession().commit()

        self.push_all(action="skyportal/FETCH_CANDIDATES")
        return self.success()

    # TODO Do we need a delete handler? If so, what should it do? Old, unsaved
    # candidates will automatically be deleted by cron job.


def grab_query_results_page(
    q,
    total_matches,
    page,
    n_items_per_page,
    items_name,
    order_by=None,
    include_photometry=False,
):
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
    full_query = q.add_column(row)

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
        DBSession()
        .query(full_query.c.id, full_query.c.row_num)
        .distinct(full_query.c.id)
        .order_by(full_query.c.id, full_query.c.row_num)
        .subquery()
    )
    # Grouping and getting the first distinct obj_id above messed up the order
    # in the query set, so re-order by the row_num we used to remember the
    # original ordering
    ordered_ids = (
        DBSession().query(ids_with_row_nums.c.id).order_by(ids_with_row_nums.c.row_num)
    )

    if total_matches:
        info["totalMatches"] = int(total_matches)
    else:
        info["totalMatches"] = ordered_ids.count()
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

    # Now bring in the full Obj info for the candidates
    page_ids = (
        ordered_ids.limit(n_items_per_page).offset((page - 1) * n_items_per_page).all()
    )
    items = []
    query_options = [joinedload(Obj.thumbnails)]
    if include_photometry:
        query_options.append(
            joinedload(Obj.photometry).joinedload(Photometry.instrument)
        )
    for item_id in page_ids:
        items.append(Obj.query.options(query_options).get(item_id))
    info[items_name] = items
    info["pageNumber"] = page
    info["lastPage"] = info["totalMatches"] <= page * n_items_per_page
    info["numberingStart"] = (page - 1) * n_items_per_page + 1
    info["numberingEnd"] = min(info["totalMatches"], page * n_items_per_page)
    if info["totalMatches"] == 0:
        info["numberingStart"] = 0
    return info
