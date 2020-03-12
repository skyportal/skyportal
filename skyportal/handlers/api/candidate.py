import datetime
import arrow
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Photometry,
    Candidate,
    Thumbnail,
    GroupCandidate,
    Instrument,
    Group,
    Source,
)


CANDIDATES_PER_PAGE = 25


class CandidateHandler(BaseHandler):
    @auth_or_token
    def get(self, candidate_id=None):
        if candidate_id is not None:
            c = Candidate.get_if_owned_by(
                candidate_id,
                self.current_user,
                options=[
                    joinedload(Candidate.comments),
                    joinedload(Candidate.thumbnails)
                    .joinedload(Thumbnail.photometry)
                    .joinedload(Photometry.instrument)
                    .joinedload(Instrument.telescope),
                ],
            )
            if c is None:
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
        q = Candidate.query.options(
            [
                joinedload(Candidate.comments),
                joinedload(Candidate.groups),
                joinedload(Candidate.thumbnails)
                .joinedload(Thumbnail.photometry)
                .joinedload(Photometry.instrument)
                .joinedload(Instrument.telescope)
            ]
        ).filter(
            Candidate.id.in_(
                DBSession.query(GroupCandidate.candidate_id).filter(
                    GroupCandidate.group_id.in_(group_ids)))
        ).order_by(Candidate.last_detected.desc().nullslast(), Candidate.id)
        if unsaved_only == "true":
            q = q.filter(Candidate.source_id.is_(None))
        if start_date is not None and start_date.strip() != "":
            start_date = arrow.get(start_date.strip())
            q = q.filter(Candidate.last_detected >= start_date)
        if end_date is not None and end_date.strip() != "":
            end_date = arrow.get(end_date.strip())
            q = q.filter(Candidate.last_detected <= end_date)
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
              schema: Candidate
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
        source_id = data.pop("source_id", None)
        saved_as_source_by_id = data.pop("saved_as_source_by_id", None)
        schema = Candidate.__schema__()
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
        c.groups = groups
        if source_id is not None:
            c.source_id = source_id
        if saved_as_source_by_id is not None:
            c.saved_as_source_by_id = saved_as_source_by_id
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
              schema: CandidateNoID
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
        c = Candidate.get_if_owned_by(candidate_id, self.current_user)
        data = self.get_json()
        data["id"] = candidate_id

        save_as_source = data.pop("saveAsSource", False)
        if save_as_source:
            s = Source.query.get(candidate_id)
            group_ids = data.get("groupIDs", None)
            if group_ids is None:
                return self.error("Required groupIDs field missing.")
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if len(groups) == 0:
                return self.error("Invalid group ID(s).")
            if s is not None:
                return self.error("Source with matching ID already exists.")
            s = Source()
            attrs = [
                k
                for k in dir(Candidate)
                if not callable(getattr(Candidate, k))
                and not k.startswith("_")
                and k != "query"
                and "url" not in k
            ]
            for attr in attrs:
                setattr(s, attr, getattr(c, attr))
            s.groups = groups
            s.photometry = c.photometry
            s.thumbnails = c.thumbnails
            s.spectra = c.spectra
            s.saved_as_source_by = self.current_user
            s.created_at = datetime.datetime.now()
            DBSession.add(s)
            DBSession.commit()
            c.source_id = s.id
            c.saved_as_source_by_id = self.current_user.id
            DBSession.add(c)
            DBSession.commit()
            self.push_all("skyportal/FETCH_SOURCES")
            return self.success(
                data={"candidate": c}, action="skyportal/FETCH_CANDIDATES"
            )

        schema = Candidate.__schema__()
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
        _ = Candidate.get_if_owned_by(candidate_id, self.current_user)
        DBSession.query(Candidate).filter(Candidate.id == candidate_id).delete()
        DBSession().commit()

        return self.success(action="skyportal/FETCH_CANDIDATES")
