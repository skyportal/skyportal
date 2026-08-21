import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import TermsOfServiceAcceptance
from ..base import BaseHandler

_, cfg = load_env()


def terms_of_service():
    """The configured terms, or None when this instance prompts for none.

    Both switches matter: `enabled` is how a deployer turns the prompt on, and
    the text guard keeps an enabled-but-blank config from blocking everyone
    behind an empty dialog.
    """
    terms = cfg.get("app.terms_of_service") or {}
    text = (terms.get("text") or "").strip()
    if not terms.get("enabled") or not text:
        return None
    return {
        "version": str(terms.get("version", "1")),
        "title": terms.get("title") or "Terms of Service",
        "text": text,
    }


class TermsOfServiceHandler(BaseHandler):
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

        # Tokens and the anonymous account cannot hold an acceptance: prompting
        # is a browser-session concern, so treat them as satisfied.
        user = self.associated_user_object
        if user is None or getattr(user, "is_anonymous", False):
            return self.success(data={"required": False})

        async with self.AsyncSession() as session:
            accepted = await session.scalar(
                sa.select(TermsOfServiceAcceptance.id).where(
                    TermsOfServiceAcceptance.user_id == user.id,
                    TermsOfServiceAcceptance.version == terms["version"],
                )
            )

        return self.success(data={**terms, "required": accepted is None})

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

        user = self.associated_user_object
        if user is None or getattr(user, "is_anonymous", False):
            return self.error("Only a signed-in user can accept the terms.")

        async with self.AsyncSession() as session:
            acceptance = TermsOfServiceAcceptance(
                user_id=user.id, version=terms["version"]
            )
            try:
                # The unique constraint absorbs a double submit; the existing
                # row already records the acceptance, so this is not an error.
                async with session.begin_nested():
                    session.add(acceptance)
                    await session.flush()
            except IntegrityError:
                return self.success()

            await session.commit()

        return self.success()
