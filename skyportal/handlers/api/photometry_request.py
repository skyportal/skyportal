from skyportal.models import ThreadSession
from baselayer.app.access import auth_or_token

from ..base import BaseHandler
from ...models import (
    FollowupRequest,
)


class PhotometryRequestHandler(BaseHandler):
    @auth_or_token
    def get(self, request_id):
        """
        ---
        description: Get photometry request.
        tags:
          - followup_requests
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

        refresh_source = self.get_query_argument("refreshSource", True)
        refresh_requests = self.get_query_argument("refreshRequests", False)

        with ThreadSession() as session:
            try:
                followup_request = session.query(FollowupRequest).get(request_id)

                api = followup_request.instrument.api_class
                if not api.implements()['get']:
                    return self.error('Cannot retrieve requests on this instrument.')

                followup_request.last_modified_by_id = self.associated_user_object.id
                internal_key = followup_request.obj.internal_key

                api.get(
                    followup_request,
                    session,
                    refresh_source=refresh_source,
                    refresh_requests=refresh_requests,
                )
                self.verify_and_commit()

                self.push_all(
                    action="skyportal/REFRESH_SOURCE",
                    payload={"obj_key": internal_key},
                )
                return self.success()
            except Exception as e:
                session.rollback()
                return self.error(f'Error retrieving photometry request: {e}')
