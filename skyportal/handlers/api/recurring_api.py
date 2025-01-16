import arrow
import json

from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.model_util import recursive_to_dict

from baselayer.log import make_log
from baselayer.app.env import load_env

from ..base import BaseHandler

from ...models import (
    RecurringAPI,
)

log = make_log('app/recurring_api')

_, cfg = load_env()

ALLOWED_RECURRING_API_METHODS = ['POST', 'GET']
MAX_RETRIES = 10


class RecurringAPIHandler(BaseHandler):
    """Handler for recurring APIs."""

    @permissions(["Manage Recurring APIs"])
    def post(self):
        """
        ---
        summary: Create a new Recurring API
        description: POST a new Recurring APIs.
        tags:
          - recurring apis
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  endpoint:
                    type: string
                    description: Endpoint of the API call.
                  method:
                    type: string
                    description: HTTP method of the API call.
                  next_call:
                    type: datetime
                    description: Time of the next API call.
                  call_delay:
                    type: number
                    description: Delay until next API call in days.
                  number_of_retries:
                    type: integer
                    description: Number of retries before service is deactivated.
                  payload:
                    type: object
                    description: Payload of the API call.
                required:
                  - endpoint
                  - method
                  - next_call
                  - call_delay
                  - payload
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
                              type: integer
                              description: New RecurringAPI ID
        """
        data = self.get_json()

        try:
            data['next_call'] = str(
                arrow.get(data.get('next_call')).datetime.replace(tzinfo=None)
            )
        except arrow.ParserError:
            return self.error(
                f"Invalid input for parameter next_call:{data.get('next_call')}"
            )

        if 'method' in data:
            data['method'] = data['method'].upper()
            if not data['method'] in ALLOWED_RECURRING_API_METHODS:
                return self.error(
                    'method must be in {",".join(ALLOWED_RECURRING_API_METHODS)}'
                )

        if 'number_of_retries' in data:
            if data['number_of_retries'] > MAX_RETRIES:
                return self.error(f'number_of_retries must be <= {MAX_RETRIES}')

        if 'payload' in data:
            try:
                json.loads(data['payload'])
            except json.JSONDecodeError:
                return self.error('payload must be a valid JSON string')

        with self.Session() as session:
            schema = RecurringAPI.__schema__()
            try:
                recurring_api = schema.load(data)
            except ValidationError as exc:
                return self.error(
                    'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
                )
            recurring_api.owner_id = self.associated_user_object.id
            session.add(recurring_api)
            session.commit()

            self.push_all(action='skyportal/REFRESH_RECURRING_APIS')
            return self.success(data={"id": recurring_api.id})

    @auth_or_token
    def get(self, recurring_api_id=None):
        """
        ---
        single:
          summary: Retrieve a Recurring API
          description: Retrieve an Recurring API by id
          tags:
            - recurring apis
          parameters:
            - in: path
              name: recurring_api_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleRecurringAPI
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Retrieve all Recurring APIs
          description: Retrieve all Recurring APIs
          tags:
            - recurring apis
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfRecurringAPIs
            400:
              content:
                application/json:
                  schema: Error
        """
        with self.Session() as session:
            if recurring_api_id is not None:
                s = session.scalars(
                    RecurringAPI.select(session.user_or_token).where(
                        RecurringAPI.id == recurring_api_id
                    )
                ).first()
                if s is None:
                    return self.error('Cannot access this Recurring API.', status=403)

                recurring_api_dict = recursive_to_dict(s)
                return self.success(data=recurring_api_dict)

            # retrieve multiple services
            recurring_apis = session.scalars(
                RecurringAPI.select(session.user_or_token)
            ).all()

            ret_array = []
            for a in recurring_apis:
                recurring_api_dict = recursive_to_dict(a)
                if isinstance(a.payload, str):
                    recurring_api_dict["payload"] = json.loads(a.payload)
                elif isinstance(a.payload, dict):
                    recurring_api_dict["payload"] = a.payload
                else:
                    return self.error(message='payload must be dictionary or string')
                ret_array.append(recurring_api_dict)

            return self.success(data=ret_array)

    @permissions(["Manage Recurring APIs"])
    def delete(self, recurring_api_id):
        """
        ---
        summary: Delete a Recurring API
        description: Delete an Recurring API.
        tags:
          - recurring apis
        parameters:
          - in: path
            name: recurring_api_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            recurring_api = session.scalars(
                RecurringAPI.select(session.user_or_token, mode="delete").where(
                    RecurringAPI.id == recurring_api_id
                )
            ).first()
            if recurring_api is None:
                return self.error('Cannot delete this Recurring API.', status=403)
            session.delete(recurring_api)
            session.commit()

            self.push_all(action='skyportal/REFRESH_RECURRING_APIS')
            return self.success()
