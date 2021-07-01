from copy import deepcopy

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from validate_email import validate_email
from sqlalchemy.exc import IntegrityError

from baselayer.app.access import auth_or_token
from baselayer.app.config import recursive_update
from ...base import BaseHandler
from ....models import User


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
                            permissions:
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
        user = (
            User.query_records_accessible_by(self.current_user)
            .filter(User.username == self.current_user.username)
            .first()
        )
        user_roles = sorted([role.id for role in user.roles])
        user_acls = sorted([acl.id for acl in user.acls])
        user_permissions = sorted(user.permissions)
        user_tokens = [
            {
                "id": token.id,
                "name": token.name,
                "acls": sorted([acl.id for acl in token.acls]),
                "created_at": token.created_at,
            }
            for token in user.tokens
        ]
        user_info = user.to_dict()
        user_info["roles"] = user_roles
        user_info["permissions"] = user_permissions
        user_info["acls"] = user_acls
        user_info["tokens"] = user_tokens
        user_info["gravatar_url"] = user.gravatar_url or None
        user_info["preferences"] = user.preferences or {}
        user_info["groupAdmissionRequests"] = user.group_admission_requests
        self.verify_and_commit()
        return self.success(data=user_info)

    @auth_or_token
    def patch(self):
        """
        ---
        description: Update user preferences
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  username:
                    type: string
                    description: |
                      User's preferred user name
                  first_name:
                    type: string
                    description: |
                      User's preferred first name
                  last_name:
                    type: string
                    description: |
                       User's preferred last name
                  contact_email:
                    type: string
                    description: |
                       User's preferred email address
                  contact_phone:
                    type: string
                    description: |
                       User's preferred (international) phone number
                  preferences:
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
        user = User.get_if_accessible_by(
            self.associated_user_object.id, self.current_user, mode="update"
        )

        if data.get("username") is not None:
            username = data.pop("username").strip()
            if username == "":
                return self.error("Invalid username.")
            if len(username) < 5:
                return self.error("Username must be at least five characters long.")
            user.username = username

        if data.get("first_name") is not None:
            user.first_name = data.pop("first_name")

        if data.get("last_name") is not None:
            user.last_name = data.pop("last_name")

        if data.get("contact_phone") is not None:
            phone = data.pop("contact_phone")
            if phone not in [None, ""]:
                try:
                    if not phonenumbers.is_possible_number(
                        phonenumbers.parse(phone, "US")
                    ):
                        return self.error("Phone number given is not valid")
                except NumberParseException:
                    return self.error("Could not parse input as a phone number")
                user.contact_phone = phone
            else:
                user.contact_phone = None

        if data.get("contact_email") is not None:
            email = data.pop("contact_email")
            if email not in [None, ""]:
                if not validate_email(
                    email_address=email,
                    check_regex=True,
                    check_mx=False,
                    use_blacklist=True,
                    debug=False,
                ):
                    return self.error("Email does not appear to be valid")
                user.contact_email = email
            else:
                user.contact_email = None

        preferences = data.get("preferences", {})

        # Do not save blank fields (empty strings)
        for k, v in preferences.items():
            if isinstance(v, dict):
                preferences[k] = {key: val for key, val in v.items() if val != ""}
        user_prefs = deepcopy(user.preferences)
        if not user_prefs:
            user_prefs = preferences
        else:
            user_prefs = recursive_update(user_prefs, preferences)
        user.preferences = user_prefs

        try:
            self.verify_and_commit()
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e):
                return self.error(
                    "Username already exists. Please try another username."
                )
            raise
        if "newsFeed" in preferences:
            self.push(action="skyportal/FETCH_NEWSFEED")
        if "topSources" in preferences:
            self.push(action="skyportal/FETCH_TOP_SOURCES")
        if "recentGcnEvents" in preferences:
            self.push(action="skyportal/FETCH_RECENT_GCNEVENTS")
        if "recentSources" in preferences:
            self.push(action="skyportal/FETCH_RECENT_SOURCES")
        if "sourceCounts" in preferences:
            self.push(action="skyportal/FETCH_SOURCE_COUNTS")
        return self.success(action="skyportal/FETCH_USER_PROFILE")
