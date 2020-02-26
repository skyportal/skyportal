import json
from copy import deepcopy
from baselayer.app.access import auth_or_token
from baselayer.app.config import recursive_update
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
        return self.success(data={
            'username': self.current_user.username,
            'roles': user_roles,
            'acls': user_acls,
            'tokens': user_tokens,
            'preferences': self.current_user.preferences or {}
        })

    def put(self):
        """
        ---
        description: Update user preferences
        requestBody:
          content:
            application/json:
              schema: UpdateUserPreferencesRequestJSON
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
        if 'preferences' not in data:
            return self.error('Invalid request body: missing required "preferences" parameter')
        preferences = data['preferences']
        # Do not save blank fields (empty strings)
        for k, v in preferences.items():
            if isinstance(v, dict):
                preferences[k] = {key: val for key, val in v.items() if val != ''}
        user_prefs = deepcopy(self.current_user.preferences)
        if not user_prefs:
            user_prefs = preferences
        else:
            user_prefs = recursive_update(user_prefs, preferences)
        self.current_user.preferences = user_prefs
        DBSession.add(self.current_user)
        DBSession.commit()
        if 'newsFeed' in preferences:
            self.push(action='skyportal/FETCH_NEWSFEED')
        if 'topSources' in preferences:
            self.push(action='skyportal/FETCH_TOP_SOURCES')
        return self.success(action="skyportal/FETCH_USER_PROFILE")
