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
              required: false
              schema:
                type: integer
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
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfObjs
            400:
              content:
                application/json:
                  schema: Error
        """
        if obj_id is not None:
            c = Candidate.get_if_owned_by(obj_id, self.current_user)
            if c is None:
                return self.error("Invalid ID")
            return self.success(data={"candidates": c})

        page_number = self.get_query_argument("pageNumber", None) or 1
        n_per_page = 25  # TODO grab this from URL param
        unsaved_only = self.get_query_argument("unsavedOnly", False)
        total_matches = self.get_query_argument("totalMatches", None)
        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        group_ids = self.get_query_argument("groupIDs", None)
        if group_ids is not None:
            if "," in group_ids:
                group_ids = [int(g_id) for g_id in group_ids.split(",")]
            elif group_ids.isdigit():
                group_ids = [int(group_ids)]
            else:
                return self.error("Invalid groupIDs value -- select at least one group")
        else:
            # If 'groupIDs' param not present in request, use all user groups
            group_ids = [g.id for g in self.current_user.groups]
        try:
            page = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        q = (
            Obj.query.options(
                [
                    joinedload(Obj.comments),
                    joinedload(Obj.thumbnails)
                    .joinedload(Thumbnail.photometry)
                    .joinedload(Photometry.instrument)
                    .joinedload(Instrument.telescope),
                ]
            )
            .filter(
                Obj.id.in_(
                    DBSession.query(Candidate.obj_id).filter(
                        Candidate.group_id.in_(group_ids)
                    )
                )
            )
            .order_by(Obj.last_detected.desc().nullslast(), Obj.id)
        )
        if unsaved_only == "true":
            q = q.filter(
                Obj.id.notin_(
                    DBSession.query(Source.obj_id).filter(
                        Source.group_id.in_(group_ids)
                    )
                )
            )
        if start_date is not None and start_date.strip() != "":
            start_date = arrow.get(start_date.strip())
            q = q.filter(Obj.last_detected >= start_date)
        if end_date is not None and end_date.strip() != "":
            end_date = arrow.get(end_date.strip())
            q = q.filter(Obj.last_detected <= end_date)
        try:
            query_results = grab_query_results_page(
                q, total_matches, page, n_per_page, "candidates"
            )
        except ValueError as e:
            if "Page number out of range" in str(e):
                return self.error("Page number out of range.")
            raise
        return self.success(data=query_results)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: POST a new candidate. If group_ids is not specified, the user or token's groups will be used.
        requestBody:
          content:
            application/json:
              schema: Obj
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
                          description: New candidate ID
        """
        data = self.get_json()
        schema = Obj.__schema__()
        user_group_ids = [g.id for g in self.current_user.groups]
        if not user_group_ids:
            return self.error(
                "You must belong to one or more groups before you can add candidates."
            )
        try:
            group_ids = [id for id in data.pop("group_ids") if id in user_group_ids]
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
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        filters = Filter.query.filter(Filter.group_id.in_(group_ids)).all()
        if not filters:
            return self.error("Invalid group/filter association -- please specify "
                              "at least one group associated with a valid filter.")

        DBSession.add(obj)
        DBSession.add_all([Candidate(obj=obj, filter=filter) for filter in filters])
        DBSession().commit()

        self.push_all(action="skyportal/FETCH_CANDIDATES")
        return self.success(data={"id": obj.id})

    @auth_or_token
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
        c = Candidate.get_if_owned_by(obj_id, self.current_user)
        if c is None:
            return self.error("Invalid ID.")
        data = self.get_json()
        data["id"] = obj_id

        schema = Obj.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        DBSession().commit()

        self.push_all(action="skyportal/FETCH_CANDIDATES")
        return self.success()


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
