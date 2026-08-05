from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token

from ....model_util import create_token
from ....models import ACL, Token, User
from ...base import BaseHandler


class TokenPostBody(BaseModel):
    """Request body for creating a new API token."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Name of the token")
    acls: list[str] = Field(description="List of ACL IDs to grant the token")
    user_id: int | None = Field(
        default=None,
        description="ID of the user to create the token for; defaults to the requesting user",
    )


class TokenPostResponse(BaseModel):
    """ID of the newly created token."""

    token_id: str = Field(description="Token ID")


class TokenPutBody(BaseModel):
    """Request body for updating a token."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="New name of the token")
    acls: list[str] | None = Field(
        default=None, description="New list of ACL IDs for the token"
    )
    user_id: int | None = Field(
        default=None,
        description="ID of the user whose permissions the new ACLs are checked against; defaults to the requesting user",
    )


class TokenHandler(BaseHandler):
    @auth_or_token
    async def post(self, *, body: TokenPostBody = None) -> TokenPostResponse:
        """
        ---
        description: Generate new token (limit 1 per user)
        """
        body = self.parse_body(TokenPostBody)

        async with self.AsyncSession() as session:
            if body.user_id is not None:
                user_id = body.user_id
                user = await session.scalar(
                    User.select(session.user_or_token)
                    .options(
                        selectinload(User.acls),
                        selectinload(User.roles),
                    )
                    .where(User.id == user_id)
                )
            else:
                user = self.associated_user_object
                user_id = user.id

            token_acls = set(body.acls)
            if not all(acl_id in user.permissions for acl_id in token_acls):
                return self.error(
                    "User has attempted to grant token ACLs they do not have "
                    "access to. Please try again."
                )
            existing_result = await session.scalars(
                Token.select(session.user_or_token).where(
                    Token.created_by_id == user_id
                )
            )
            existing_tokens = existing_result.all()
            if len(existing_tokens) > 0 and not self.associated_user_object.is_admin:
                return self.error(
                    "You have reached the maximum number of tokens "
                    "allowed for your account type."
                )
            token_name = body.name
            existing_name = await session.scalar(
                Token.select(session.user_or_token).where(Token.name == token_name)
            )
            if existing_name:
                return self.error("Duplicate token name.")
            # create_token operates on its own sync DBSession; safe to call
            # from async here. The async session above never sees the new
            # token's row until we read it back below.
            token_id = create_token(ACLs=token_acls, user_id=user_id, name=token_name)
            self.push(
                action="baselayer/SHOW_NOTIFICATION",
                payload={"note": f'Token "{token_name}" created.', "type": "info"},
            )
            return self.success(
                data={"token_id": token_id}, action="skyportal/FETCH_USER_PROFILE"
            )

    @auth_or_token
    async def get(self, token_id: str | None = None):
        """
        ---
        single:
          description: Retrieve a token
          tags:
            - tokens
          parameters:
            - in: path
              name: token_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleToken
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all tokens
          tags:
            - tokens
          parameters:
            - in: query
              name: userID
              schema:
                type: integer
              description: Filter by user ID
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfTokens
            400:
              content:
                application/json:
                  schema: Error
        """

        user_id = self.get_query_argument("userID", None, type=int)

        async with self.AsyncSession() as session:
            if token_id is not None:
                t = await session.scalar(
                    Token.select(session.user_or_token).where(Token.id == token_id)
                )
                if t is None:
                    return self.error(f"Could not load token with ID {token_id}")
                return self.success(data=t)

            stmt = Token.select(session.user_or_token)
            if user_id is not None:
                stmt = stmt.where(Token.created_by_id == user_id)
            result = await session.scalars(stmt)
            return self.success(data=result.all())

    @auth_or_token
    async def put(self, token_id: str, *, body: TokenPutBody = None):
        """
        ---
        description: Update token
        tags:
          - tokens
        parameters:
          - in: path
            name: token_id
            required: true
            schema:
              type: integer
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
        body = self.parse_body(TokenPutBody)

        async with self.AsyncSession() as session:
            try:
                token = await session.scalar(
                    Token.select(session.user_or_token, mode="update").where(
                        Token.id == token_id
                    )
                )
                if token is None:
                    return self.error(
                        "Either the specified token does not exist, "
                        "or the user does not have the necessary "
                        "permissions to update it."
                    )

                if body.user_id is not None:
                    user_id = body.user_id
                    user = await session.scalar(
                        User.select(session.user_or_token)
                        .options(
                            selectinload(User.acls),
                            selectinload(User.roles),
                        )
                        .where(User.id == user_id)
                    )
                else:
                    user = self.associated_user_object
                    user_id = user.id

                if body.name is not None:
                    token.name = body.name

                if body.acls is not None:
                    token_acls = set(body.acls)
                    if not all(acl_id in user.permissions for acl_id in token_acls):
                        return self.error(
                            "User has attempted to grant token ACLs they do not have "
                            "access to. Please try again."
                        )

                    new_acl_ids = list(set(token_acls))
                    valid_ids_result = await session.scalars(
                        ACL.select(session.user_or_token, columns=[ACL.id]).where(
                            ACL.id.in_(new_acl_ids)
                        )
                    )
                    valid_ids = set(valid_ids_result.all())
                    if set(new_acl_ids) != valid_ids:
                        return self.error(
                            "Improperly formatted parameter aclIds; must be an array of strings corresponding to valid ACLs."
                        )
                    if len(new_acl_ids) == 0:
                        return self.error(f"No new ACLs to add to token {token_id}")

                    new_acls_result = await session.scalars(
                        ACL.select(session.user_or_token).where(ACL.id.in_(new_acl_ids))
                    )
                    new_acls = new_acls_result.unique().all()

                    token.acls = new_acls
                    session.add(token)

                await session.commit()
                self.push(
                    action="skyportal/FETCH_USER_PROFILE",
                )

                return self.success()
            except Exception as e:
                return self.error(f"Could not update token: {e}")

    @auth_or_token
    async def delete(self, token_id: str):
        """
        ---
        description: Delete a token
        parameters:
          - in: path
            name: token_id
            required: true
            schema:
              type: integer
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

        async with self.AsyncSession() as session:
            token = await session.scalar(
                Token.select(session.user_or_token, mode="delete").where(
                    Token.id == token_id
                )
            )
            if token is None:
                return self.error(
                    "Either the specified token does not exist, "
                    "or the user does not have the necessary "
                    "permissions to delete it."
                )
            token_name = token.name
            await session.delete(token)
            await session.commit()

            self.push(
                action="baselayer/SHOW_NOTIFICATION",
                payload={"note": f'Token "{token_name}" deleted.', "type": "info"},
            )
            return self.success(action="skyportal/FETCH_USER_PROFILE")
