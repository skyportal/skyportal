import datetime
import arrow
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Photometry,
    Thumbnail,
    Instrument,
    Group,
    Source,
    GroupSource,
    GroupCandidate,
)


CANDIDATES_PER_PAGE = 25


class CandidateHandler(BaseHandler):
    @auth_or_token
    def get(self, candidate_id=None):
        """
        ---
        single:
          description: Retrieve a candidate
          parameters:
            - in: path
              name: candidate_id
              required: true
              schema:
                type: string
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
          description: Retrieve all candidates
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
        if candidate_id is not None:
            c = Source.get_if_owned_by(
                candidate_id,
                self.current_user,
                groups_attr="candidate_groups",
                options=[
                    joinedload(Source.candidate_comments),
                    joinedload(Source.candidate_groups),
                    joinedload(Source.thumbnails)
                    .joinedload(Thumbnail.photometry)
                    .joinedload(Photometry.instrument)
                    .joinedload(Instrument.telescope),
                ],
            )
            if (c is None) or (not c.is_candidate):
                return self.error("Invalid candidate ID")
            return self.success(data={"candidates": c})

        page_number = self.get_query_argument("pageNumber", None) or 1
        unsaved_only = self.get_query_argument("unsavedOnly", False)
        total_matches = self.get_query_argument("totalMatches", None)
        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        group_ids = self.get_query_argument("groupIDs", None)
        info = {}
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
            Source.query.options(
                [
                    joinedload(Source.candidate_comments),
                    joinedload(Source.candidate_groups),
                    joinedload(Source.thumbnails)
                    .joinedload(Thumbnail.photometry)
                    .joinedload(Photometry.instrument)
                    .joinedload(Instrument.telescope),
                ]
            )
            .filter(
                Source.id.in_(
                    DBSession.query(GroupCandidate.source_id).filter(
                        GroupCandidate.group_id.in_(group_ids)
                    )
                )
            )
            .order_by(Source.last_detected.desc().nullslast(), Source.id)
            .filter(Source.is_candidate.is_(True))
        )
        if unsaved_only == "true":
            q = q.filter(Source.is_source.is_(False))
        if start_date is not None and start_date.strip() != "":
            start_date = arrow.get(start_date.strip())
            q = q.filter(Source.last_detected >= start_date)
        if end_date is not None and end_date.strip() != "":
            end_date = arrow.get(end_date.strip())
            q = q.filter(Source.last_detected <= end_date)
        if total_matches:
            info["totalMatches"] = int(total_matches)
        else:
            info["totalMatches"] = q.count()
        if (
            (
                (
                    info["totalMatches"] < (page - 1) * CANDIDATES_PER_PAGE
                    and info["totalMatches"] % CANDIDATES_PER_PAGE != 0
                )
                or (
                    info["totalMatches"] < page * CANDIDATES_PER_PAGE
                    and info["totalMatches"] % CANDIDATES_PER_PAGE == 0
                )
                and info["totalMatches"] != 0
            )
            or page <= 0
            or (info["totalMatches"] == 0 and page != 1)
        ):
            return self.error("Page number out of range.")
        info["candidates"] = (
            q.limit(CANDIDATES_PER_PAGE).offset((page - 1) * CANDIDATES_PER_PAGE).all()
        )

        info["pageNumber"] = page
        info["lastPage"] = info["totalMatches"] <= page * CANDIDATES_PER_PAGE
        info["candidateNumberingStart"] = (page - 1) * CANDIDATES_PER_PAGE + 1
        info["candidateNumberingEnd"] = min(
            info["totalMatches"], page * CANDIDATES_PER_PAGE
        )
        if info["totalMatches"] == 0:
            info["candidateNumberingStart"] = 0

        return self.success(data=info)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Upload a candidate. If group_ids is not specified, the user or token's groups will be used.
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
                          description: New candidate ID
        """
        data = self.get_json()
        data["is_candidate"] = True
        saved_as_source_by_id = data.pop("saved_as_source_by_id", None)
        schema = Source.__schema__()
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
            c = schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        groups = Group.query.filter(Group.id.in_(group_ids)).all()
        if not groups:
            return self.error(
                "Invalid group_ids field. Please specify at least "
                "one valid group ID that you belong to."
            )
        c.candidate_groups = groups
        if saved_as_source_by_id is None:
            saved_as_source_by_id = self.current_user.id
        # TODO - create GroupSources with appropriate fields
        DBSession.add(c)
        DBSession().commit()

        self.push_all(action="skyportal/FETCH_CANDIDATES")
        return self.success(data={"id": c.id})

    @permissions(["Manage sources"])
    def patch(self, candidate_id):
        """
        ---
        description: Update a candidate
        parameters:
          - in: path
            name: candidate_id
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
        # Ensure user has access to candidate
        c = Source.get_if_owned_by(
            candidate_id, self.current_user, groups_attr="candidate_groups"
        )
        if c is None:
            return self.error("Invalid ID or inadequate permssions.")
        data = self.get_json()
        data["id"] = candidate_id

        save_as_source = data.pop("saveAsSource", False)
        if save_as_source:
            group_ids = data.get("groupIDs", None)
            if group_ids is None:
                return self.error("Required groupIDs field missing.")
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if len(groups) == 0:
                return self.error("Invalid group ID(s).")
            c.is_source = True
            c.source_groups = groups
            for g in groups:
                gs = (
                    GroupSource.query.filter(GroupSource.group_id == g.id)
                    .filter(GroupSource.source_id == c.id)
                    .first()
                )
                if gs is None:
                    gs = GroupSource(
                        group_id=g.id,
                        source_id=c.id,
                        saved_as_source_by_id=self.current_user.id,
                        saved_as_source_at_time=arrow.now(),
                    )
                    DBSession.add(gs)
                else:
                    gs.saved_as_source_by_id = self.current_user.id
                    gs.saved_as_source_at_time = arrow.now()
            DBSession.commit()
            self.push_all("skyportal/FETCH_SOURCES")
            return self.success(
                data={"candidate": c}, action="skyportal/FETCH_CANDIDATES"
            )

        schema = Source.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        DBSession().commit()

        self.push_all(action="skyportal/FETCH_CANDIDATES")
        return self.success()

    @permissions(["Manage sources"])
    def delete(self, candidate_id):
        """
        ---
        description: Delete a candidate
        parameters:
          - in: path
            name: candidate_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        _ = Source.get_if_owned_by(
            candidate_id, self.current_user, groups_attr="candidate_groups"
        )
        DBSession.query(Source).filter(Source.id == candidate_id).delete()
        DBSession().commit()

        return self.success(action="skyportal/FETCH_CANDIDATES")
