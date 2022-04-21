from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ..base import BaseHandler
from ...models import (
    FollowupRequest,
)

log = make_log('api/photometry_request')


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

        try:
            followup_request = FollowupRequest.get_if_accessible_by(
                request_id, self.current_user, mode="read", raise_if_none=True
            )

            api = followup_request.instrument.api_class
            if not api.implements()['get']:
                return self.error('Cannot retrieve requests on this instrument.')

            followup_request.last_modified_by_id = self.associated_user_object.id
            internal_key = followup_request.obj.internal_key

            api.get(followup_request)
            self.verify_and_commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": internal_key},
            )
            return self.success()
        except Exception as e:
            log(f"Unable to get photometry: {e}")
            return self.error(e.args[0])
