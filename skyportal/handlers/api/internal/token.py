from marshmallow.exceptions import ValidationError

from ...base import BaseHandler
from baselayer.app.access import auth_or_token
from ....models import ACL, Token, User
from ....model_util import create_token


class TokenHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Generate new token (limit 1 per user)
        requestBody:
          content:
            application/json:
              schema: Token
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
                            token_id:
                              type: string
                              description: Token ID
        """
        data = self.get_json()

        with self.Session() as session:
            if 'user_id' in data:
                user_id = data['user_id']
                user = session.scalars(
                    User.select(session.user_or_token).where(User.id == user_id)
                ).first()
            else:
                user = self.associated_user_object
                user_id = user.id

            token_acls = set(data['acls'])
            if not all([acl_id in user.permissions for acl_id in token_acls]):
                return self.error(
                    "User has attempted to grant token ACLs they do not have "
                    "access to. Please try again."
                )
            existing_tokens = session.scalars(
                Token.select(session.user_or_token).where(
                    Token.created_by_id == user_id
                )
            ).all()
            if len(existing_tokens) > 0 and not self.associated_user_object.is_admin:
                return self.error(
                    "You have reached the maximum number of tokens "
                    "allowed for your account type."
                )
            token_name = data['name']
            if session.scalars(
                Token.select(session.user_or_token).where(Token.name == token_name)
            ).first():
                return self.error("Duplicate token name.")
            token_id = create_token(ACLs=token_acls, user_id=user_id, name=token_name)
            session.commit()
            self.push(
                action='baselayer/SHOW_NOTIFICATION',
                payload={'note': f'Token "{token_name}" created.', 'type': 'info'},
            )
            return self.success(
                data={'token_id': token_id}, action='skyportal/FETCH_USER_PROFILE'
            )

    @auth_or_token
    def get(self, token_id=None):
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
                type: int
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

        user_id = self.get_query_argument("userID", None)

        with self.Session() as session:
            if token_id is not None:
                t = session.scalars(
                    Token.select(session.user_or_token).where(Token.id == token_id)
                ).first()
                if t is None:
                    return self.error(f"Could not load token with ID {token_id}")
                return self.success(data=t)

            stmt = Token.select(session.user_or_token)
            if user_id is not None:
                stmt = stmt.where(Token.created_by == user_id)
            data = session.scalars(stmt).all()
            return self.success(data=data)

    @auth_or_token
    def put(self, token_id):
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
        requestBody:
          content:
            application/json:
              schema: Token
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

        with self.Session() as session:
            try:
                token = session.scalars(
                    Token.select(session.user_or_token, mode="update").where(
                        Token.id == token_id
                    )
                ).first()
                if token is None:
                    return self.error(
                        'Either the specified token does not exist, '
                        'or the user does not have the necessary '
                        'permissions to update it.'
                    )

                data = self.get_json()
                data['id'] = token_id

                if 'user_id' in data:
                    user_id = data['user_id']
                    user = session.scalars(
                        User.select(session.user_or_token).where(User.id == user_id)
                    ).first()
                else:
                    user = self.associated_user_object
                    user_id = user.id

                schema = Token.__schema__()
                try:
                    schema.load(data, partial=True)
                except ValidationError as e:
                    return self.error(
                        'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                    )
                if 'name' in data:
                    token.name = data['name']

                if 'acls' in data:
                    token_acls = set(data['acls'])
                    if not all([acl_id in user.permissions for acl_id in token_acls]):
                        return self.error(
                            "User has attempted to grant token ACLs they do not have "
                            "access to. Please try again."
                        )

                    new_acl_ids = list(set(token_acls))
                    if not all(
                        [
                            session.scalars(
                                ACL.select(session.user_or_token).where(
                                    ACL.id == acl_id
                                )
                            ).first()
                            is not None
                            for acl_id in new_acl_ids
                        ]
                    ):
                        return self.error(
                            "Improperly formatted parameter aclIds; must be an array of strings corresponding to valid ACLs."
                        )
                    if len(new_acl_ids) == 0:
                        return self.error(f'No new ACLs to add to token {token_id}')

                    new_acls = (
                        session.scalars(
                            ACL.select(session.user_or_token).where(
                                ACL.id.in_(new_acl_ids)
                            )
                        )
                        .unique()
                        .all()
                    )

                    token.acls = new_acls
                    session.add(token)

                session.commit()
                self.push(
                    action='skyportal/FETCH_USER_PROFILE',
                )

                return self.success()
            except Exception as e:
                return self.error(f'Could not update token: {e}')

    @auth_or_token
    def delete(self, token_id):
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

        with self.Session() as session:
            token = session.scalars(
                Token.select(session.user_or_token, mode="delete").where(
                    Token.id == token_id
                )
            ).first()
            if token is None:
                return self.error(
                    'Either the specified token does not exist, '
                    'or the user does not have the necessary '
                    'permissions to delete it.'
                )

            session.delete(token)
            session.commit()

            self.push(
                action='baselayer/SHOW_NOTIFICATION',
                payload={'note': f'Token "{token.name}" deleted.', 'type': 'info'},
            )
            return self.success(action='skyportal/FETCH_USER_PROFILE')
