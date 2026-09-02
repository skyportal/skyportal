import json

import arrow
from marshmallow.exceptions import ValidationError
from skyportal_py_models.recurring_apis import (
    RecurringAPIPostBody,
    RecurringAPIPostResponse,
)

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from baselayer.log import make_log

from ...models import (
    RecurringAPI,
)
from ..base import BaseHandler

log = make_log("app/recurring_api")

_, cfg = load_env()

ALLOWED_RECURRING_API_METHODS = ["POST", "GET"]


class RecurringAPIHandler(BaseHandler):
    """Handler for recurring APIs."""

    @permissions(["Manage Recurring APIs"])
    async def post(
        self, *, body: RecurringAPIPostBody = None
    ) -> RecurringAPIPostResponse:
        """
        ---
        summary: Create a new Recurring API
        description: POST a new Recurring APIs.
        tags:
          - recurring apis
        """
        body = self.parse_body(RecurringAPIPostBody)
        data = body.model_dump(exclude_none=True)

        try:
            data["next_call"] = str(
                arrow.get(body.next_call).datetime.replace(tzinfo=None)
            )
        except arrow.ParserError:
            return self.error(f"Invalid input for parameter next_call:{body.next_call}")

        data["method"] = body.method.upper()
        if data["method"] not in ALLOWED_RECURRING_API_METHODS:
            return self.error(
                f"method must be in {','.join(ALLOWED_RECURRING_API_METHODS)}"
            )

        try:
            json.loads(body.payload)
        except json.JSONDecodeError:
            return self.error("payload must be a valid JSON string")

        async with self.AsyncSession() as session:
            schema = RecurringAPI.__schema__()
            try:
                recurring_api = schema.load(data)
            except ValidationError as exc:
                return self.error(
                    f"Invalid/missing parameters: {exc.normalized_messages()}"
                )
            recurring_api.owner_id = self.associated_user_object.id
            session.add(recurring_api)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_RECURRING_APIS")
            return self.success(data={"id": recurring_api.id})

    @auth_or_token
    async def get(self, recurring_api_id: int | None = None):
        """
        ---
        single:
          summary: Retrieve a Recurring API
          description: Retrieve an Recurring API by id
          tags:
            - recurring apis
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
        if recurring_api_id is not None:
            try:
                recurring_api_id = int(recurring_api_id)
            except (TypeError, ValueError):
                return self.error(f"Invalid recurring_api_id: {recurring_api_id}")
        async with self.AsyncSession() as session:
            if recurring_api_id is not None:
                s = await session.scalar(
                    RecurringAPI.select(session.user_or_token).where(
                        RecurringAPI.id == recurring_api_id
                    )
                )
                if s is None:
                    return self.error("Cannot access this Recurring API.", status=403)

                recurring_api_dict = recursive_to_dict(s)
                return self.success(data=recurring_api_dict)

            # retrieve multiple services
            list_result = await session.scalars(
                RecurringAPI.select(session.user_or_token)
            )
            recurring_apis = list_result.all()

            ret_array = []
            for a in recurring_apis:
                recurring_api_dict = recursive_to_dict(a)
                if isinstance(a.payload, str):
                    recurring_api_dict["payload"] = json.loads(a.payload)
                elif isinstance(a.payload, dict):
                    recurring_api_dict["payload"] = a.payload
                else:
                    return self.error(message="payload must be dictionary or string")
                ret_array.append(recurring_api_dict)

            return self.success(data=ret_array)

    @permissions(["Manage Recurring APIs"])
    async def delete(self, recurring_api_id: int):
        """
        ---
        summary: Delete a Recurring API
        description: Delete an Recurring API.
        tags:
          - recurring apis
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        async with self.AsyncSession() as session:
            recurring_api = await session.scalar(
                RecurringAPI.select(session.user_or_token, mode="delete").where(
                    RecurringAPI.id == recurring_api_id
                )
            )
            if recurring_api is None:
                return self.error("Cannot delete this Recurring API.", status=403)
            await session.delete(recurring_api)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_RECURRING_APIS")
            return self.success()
