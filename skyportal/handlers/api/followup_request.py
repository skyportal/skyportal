import arrow
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Instrument, Source, FollowupRequest, Token


class FollowupRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Submit follow-up request.
        requestBody:
          content:
            application/json:
              schema: FollowupRequest
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
                          description: New follow-up request ID
        """
        data = self.get_json()
        _ = Source.get_if_owned_by(data["source_id"], self.current_user)
        data["start_date"] = arrow.get(data["start_date"]).datetime
        data["end_date"] = arrow.get(data["end_date"]).datetime
        data["requester_id"] = self.current_user.id
        if isinstance(data["filters"], str):
            data["filters"] = [data["filters"]]
        followup_request = FollowupRequest(**data)
        DBSession.add(followup_request)
        DBSession.commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"source_id": followup_request.source_id},
        )
        return self.success(data={"id": followup_request.id})

    @auth_or_token
    def delete(self, request_id):
        """
        ---
        description: Delete follow-up request.
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        followup_request = FollowupRequest.query.get(int(request_id))
        if hasattr(self.current_user, "roles"):
            if not (
                "Super admin" in [role.id for role in self.current_user.roles]
                or "Group admin" in [role.id for role in self.current_user.roles]
                or followup_request.requester.username == self.current_user.username
            ):
                return self.error("Insufficient permissions.")
        elif isinstance(self.current_user, Token):
            if self.current_user.created_by_id != followup_request.requester.id:
                return self.error("Insufficient permissions.")
        DBSession.delete(followup_request)
        DBSession.commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"source_id": followup_request.source_id},
        )
        return self.success()
