import json
from copy import deepcopy

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from validate_email import validate_email

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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            username:
                              type: string
                            first_name:
                              type: string
                            last_name:
                              type: string
                            contact_email:
                              type: string
                            contact_phone:
                              type: string
                            gravatar_url:
                              type: string
                            acls:
                              type: array
                              items:
                                type: string
                            roles:
                              type: array
                              items:
                                type: string
                            tokens:
                              type: array
                              items:
                                type: object
                                properties:
                                  id:
                                    type: string
                                  name:
                                    type: string
                                  acls:
                                    type: array
                                    items:
                                      type: string
                                  created_at:
                                    type: string
                            preferences:
                              type: object
        """
        user = (User.query.filter(User.username == self.current_user.username)
                    .first())
        user_roles = sorted([role.id for role in user.roles])
        user_acls = sorted([acl.id for acl in user.acls])
        user_tokens = [{'id': token.id,
                        'name': token.name,
                        'acls': sorted([acl.id for acl in token.acls]),
                        'created_at': token.created_at}
                       for token in user.tokens]
        return self.success(data={
            'username': self.current_user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'contact_email': user.contact_email,
            'contact_phone': (
              None if user.contact_phone is None else user.contact_phone.e164
            ),
            'gravatar_url': user.gravatar_url,
            'roles': user_roles,
            'acls': user_acls,
            'tokens': user_tokens,
            'preferences': self.current_user.preferences or {}
        })

    @auth_or_token
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

        user = (User.query.filter(User.username == self.current_user.username)
                    .first())

        if 'preferences' not in data:
            return self.error(
                              'Invalid request body: missing required '
                              '"preferences" parameter'
                             )
        preferences = data['preferences']
        if preferences.get("first_name") is not None:
            user.first_name = preferences.pop("first_name")

        if preferences.get("last_name") is not None:
            user.last_name = preferences.pop("last_name")

        if preferences.get("contact_phone") is not None:
            phone = preferences.pop("contact_phone")
            if phone not in [None, ""]:
                try:
                    if not phonenumbers.is_possible_number(
                            phonenumbers.parse(phone, "US")):
                        return self.error(
                                  'Phone number given is not valid'
                                 )
                except NumberParseException:
                    return self.error(
                                  'Could not parse input as a phone number'
                                 )
                user.contact_phone = phone
            else:
                user.contact_phone = None

        if preferences.get("contact_email") is not None:
            email = preferences.pop("contact_email")
            if email not in [None, ""]:
                if not validate_email(
                       email_address=email,
                        check_regex=True,
                        check_mx=False,
                        use_blacklist=True,
                        debug=False):
                    return self.error(
                              'Email does not appear to be valid'
                             )
                user.contact_email = email
            else:
                user.contact_email = None

        # Do not save blank fields (empty strings)
        for k, v in preferences.items():
            if isinstance(v, dict):
                preferences[k] = \
                  {key: val for key, val in v.items() if val != ''}
        user_prefs = deepcopy(user.preferences)
        if not user_prefs:
            user_prefs = preferences
        else:
            user_prefs = recursive_update(user_prefs, preferences)
        user.preferences = user_prefs

        DBSession.add(user)
        DBSession.commit()
        if 'newsFeed' in preferences:
            self.push(action='skyportal/FETCH_NEWSFEED')
        if 'topSources' in preferences:
            self.push(action='skyportal/FETCH_TOP_SOURCES')
        return self.success(action="skyportal/FETCH_USER_PROFILE")
