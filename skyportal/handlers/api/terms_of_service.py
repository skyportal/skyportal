from sqlalchemy.exc import IntegrityError

from baselayer.app.access import auth_or_token

from ...models import TermsOfServiceAcceptance
from ...utils.terms_of_service import has_accepted, terms_of_service
from ..base import BaseHandler


class TermsOfServiceHandler(BaseHandler):
    terms_of_service_exempt = ("GET", "POST")

    @auth_or_token
    async def get(self):
        """
        ---
        summary: Retrieve the terms of service and whether they are accepted
        description: |
          Returns the instance's configured terms of service, along with
          whether the requesting user has already accepted this version.
          `required` is false when the instance configures no terms.
        tags:
          - system_info
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
                            required:
                              type: boolean
                              description: |
                                Whether this user still needs to accept.
                            version:
                              type: string
                            title:
                              type: string
                            text:
                              type: string
        """
        terms = terms_of_service()
        if terms is None:
            return self.success(data={"required": False})

        # The anonymous account is shared, an acceptance would speak for everyone.
        if getattr(self, "is_anonymous_user", False):
            return self.success(data={"required": False})

        user = self.associated_user_object
        required = not has_accepted(user.id, terms["version"])
        return self.success(data={**terms, "required": required})

    @auth_or_token
    async def post(self):
        """
        ---
        summary: Accept the current terms of service
        description: |
          Records that the requesting user accepted the version of the terms
          currently configured. Accepting twice is a no-op.
        tags:
          - system_info
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
        terms = terms_of_service()
        if terms is None:
            return self.error("This instance has no terms of service.")

        if getattr(self, "is_anonymous_user", False):
            return self.error("Only a signed-in user can accept the terms.")

        user = self.associated_user_object

        async with self.AsyncSession() as session:
            acceptance = TermsOfServiceAcceptance(
                user_id=user.id, version=terms["version"]
            )
            try:
                # A double submit hits the unique constraint; already accepted.
                async with session.begin_nested():
                    session.add(acceptance)
                    await session.flush()
            except IntegrityError:
                return self.success()

            await session.commit()

        return self.success()
