from baselayer.app.handlers import BaseHandler
from baselayer.app.access import auth_or_token
from marshmallow.exceptions import ValidationError

from ...models import Token, FacilityMessage


class FollowupRequestResponseHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Post a message from a remote facility
        requestBody:
          content:
            application/json:
              schema: FollowupRequestHTTPRequestNoID
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

        token = self.current_user
        if not isinstance(token, Token):
            return self.error("This method can only be called with an API token.")

        instrument = token.created_by_instrument
        if instrument is None:
            return self.error("API token is not associated with a Listener API.")

        data = self.get_json()

        try:
            response = FacilityMessage.__schema__().load(data)
        except ValidationError as e:
            return self.error(
                f'Error parsing message from facility: {e.normalized_messages()}'
            )

        instrument.listener_class.receive_message(response)
