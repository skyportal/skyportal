import arrow
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Instrument, Source, FollowupRequest


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
        followup_request = FollowupRequest(**data)
        DBSession.add(followup_request)
        DBSession.commit()

        self.push_all(action="skyportal/REFRESH_SOURCE",
                      payload={"source_id": followup_request.source_id})
        return self.success(data={"id": followup_request.id})
