from ...base import BaseHandler
from baselayer.app.access import auth_or_token
from ....models import Token, DBSession
from ....model_util import create_token

import tornado.web


class TokenHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        """
        ---
        description: Generate new token
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

        user = self.associated_user_object
        token_acls = set(data['acls'])
        if not all([acl_id in user.permissions for acl_id in token_acls]):
            return self.error(
                "User has attempted to grant token ACLs they do not have "
                "access to. Please try again."
            )
        token_name = data['name']
        if Token.query.filter(Token.name == token_name).first():
            return self.error("Duplicate token name.")
        token_id = create_token(ACLs=token_acls, user_id=user.id, name=token_name)
        self.verify_and_commit()
        self.push(
            action='baselayer/SHOW_NOTIFICATION',
            payload={'note': f'Token "{token_name}" created.', 'type': 'info'},
        )
        return self.success(
            data={'token_id': token_id}, action='skyportal/FETCH_USER_PROFILE'
        )

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
        token = Token.get_if_accessible_by(token_id, self.current_user, mode="delete")
        if token is not None:
            DBSession.delete(token)
            self.verify_and_commit()

            self.push(
                action='baselayer/SHOW_NOTIFICATION',
                payload={'note': f'Token "{token.name}" deleted.', 'type': 'info'},
            )
            return self.success(action='skyportal/FETCH_USER_PROFILE')
        else:
            return self.error(
                'Either the specified token does not exist, '
                'or the user does not have the necessary '
                'permissions to delete it.'
            )
