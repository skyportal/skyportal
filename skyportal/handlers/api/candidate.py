import arrow

from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Obj,
    Candidate,
    Thumbnail,
    Photometry,
    Instrument,
    Source,
    Filter,
    Group,
)


class CandidateHandler(BaseHandler):
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

        if obj_id is not None:
            c = Candidate.get_obj_if_owned_by(
                obj_id,
                self.current_user,
                options=[
                    joinedload(Candidate.obj)
                    .joinedload(Obj.thumbnails)
                    .joinedload(Thumbnail.photometry)
                    .joinedload(Photometry.instrument)
                    .joinedload(Instrument.telescope)
                ],
            )
            if c is None:
                return self.error("Invalid ID")
            candidate_info = c.to_dict()
            candidate_info["comments"] = sorted(
                c.get_comments_owned_by(self.current_user),
                key=lambda x: x.created_at,
                reverse=True,
            )
            candidate_info["is_source"] = len(c.sources) > 0
            if candidate_info["is_source"]:
                candidate_info["saved_groups"] = [
                    g
                    for g in (
                        DBSession()
                        .query(Group)
                        .join(Source)
                        .filter(Source.obj_id == obj_id)
                        .filter(Group.id.in_(user_accessible_group_ids),)
                    )
                ]
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
        q = (
            Obj.query.options(
                [
                    joinedload(Obj.thumbnails)
                    .joinedload(Thumbnail.photometry)
                    .joinedload(Photometry.instrument)
                    .joinedload(Instrument.telescope),
                ]
            )
            .filter(
                Obj.id.in_(
                    DBSession()
                    .query(Candidate.obj_id)
                    .filter(Candidate.filter_id.in_(filter_ids))
                )
            )
            .order_by(Obj.last_detected.desc().nullslast(), Obj.id)
        )
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
        try:
            query_results = grab_query_results_page(
                q, total_matches, page, n_per_page, "candidates"
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
                obj.saved_groups = [
                    g
                    for g in (
                        DBSession()
                        .query(Group)
                        .join(Source)
                        .filter(Source.obj_id == obj.id)
                        .filter(Group.id.in_(user_accessible_group_ids),)
                    )
                ]
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
                obj.get_comments_owned_by(self.current_user),
                key=lambda x: x.created_at,
                reverse=True,
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
        schema = Obj.__schema__()

        passing_alert_id = data.pop("passing_alert_id", None)
        passed_at = data.pop("passed_at", None)
        if passed_at is not None:
            passed_at = arrow.get(passed_at)
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

        return self.success(data={"id": obj.id})

    @permissions(["Manage sources"])
    def patch(self, obj_id):
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
        # Ensure user has access to candidate
        c = Candidate.get_obj_if_owned_by(obj_id, self.current_user)
        if c is None:
            return self.error("Invalid ID.")
        data = self.get_json()
        data["id"] = obj_id

        schema = Obj.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        DBSession().commit()

        self.push_all(action="skyportal/FETCH_CANDIDATES")
        return self.success()

    # TODO Do we need a delete handler? If so, what should it do? Old, unsaved
    # candidates will automatically be deleted by cron job.


def grab_query_results_page(q, total_matches, page, n_items_per_page, items_name):
    info = {}
    if total_matches:
        info["totalMatches"] = int(total_matches)
    else:
        info["totalMatches"] = q.count()
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
    info[items_name] = (
        q.limit(n_items_per_page).offset((page - 1) * n_items_per_page).all()
    )

    info["pageNumber"] = page
    info["lastPage"] = info["totalMatches"] <= page * n_items_per_page
    info["numberingStart"] = (page - 1) * n_items_per_page + 1
    info["numberingEnd"] = min(info["totalMatches"], page * n_items_per_page)
    if info["totalMatches"] == 0:
        info["numberingStart"] = 0
    return info
