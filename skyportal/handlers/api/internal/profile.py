import json
from copy import deepcopy
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import User, DBSession


class ProfileHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve user profile
        responses:
          200:
            content:
              application/json:
                schema: SingleUser
        """
        user = (User.query.filter(User.username == self.current_user.username)
                    .first())
        user_roles = [role.id for role in user.roles]
        user_acls = [acl.id for acl in user.acls]
        user_tokens = [{'id': token.id,
                        'name': token.name,
                        'acls': [acl.id for acl in token.acls],
                        'created_at': token.created_at}
                       for token in user.tokens]
        return self.success(data={'username': self.current_user.username,
                                  'roles': user_roles,
                                  'acls': user_acls,
                                  'tokens': user_tokens,
                                  'preferences': self.current_user.preferences})

    def put(self):
        """
        ---
        description: Update user preferences
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  preferences:
                    type: object
                    description: JSON describing updates to user preferences dict
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
        data = self.get_json()
        user_prefs = deepcopy(self.current_user.preferences)
        if not user_prefs:
            user_prefs = data['preferences']
        else:
            user_prefs.update(data['preferences'])
        self.current_user.preferences = user_prefs
        DBSession.add(self.current_user)
        DBSession.commit()
        if "newsFeed" in data['preferences']:
            self.push(action='skyportal/FETCH_NEWSFEED')
        return self.success(action="skyportal/FETCH_USER_PROFILE")
