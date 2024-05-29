from copy import deepcopy

import phonenumbers
import sqlalchemy as sa
from phonenumbers.phonenumberutil import NumberParseException
from validate_email import validate_email
from sqlalchemy.exc import IntegrityError
from baselayer.app.access import auth_or_token
from baselayer.app.config import recursive_update
from ...base import BaseHandler
from ....models import (
    User,
    GroupUser,
    TNSRobotGroup,
    TNSRobotGroupAutoreporter,
    TNSRobotCoauthor,
)


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
        with self.Session() as session:
            user = session.scalars(
                User.select(session.user_or_token).where(
                    User.username == self.associated_user_object.username
                )
            ).first()
            user_roles = sorted(role.id for role in user.roles)
            user_acls = sorted(acl.id for acl in user.acls)
            user_permissions = sorted(user.permissions)
            user_tokens = [
                {
                    "id": token.id,
                    "name": token.name,
                    "acls": sorted(acl.id for acl in token.acls),
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
            return self.success(data=user_info)

    @auth_or_token
    def patch(self, user_id=None):
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
                  affiliations:
                    type: list
                    description: |
                      User's list of affiliations
                  contact_email:
                    type: string
                    description: |
                      User's preferred email address
                  contact_phone:
                    type: string
                    description: |
                      User's preferred (international) phone number
                  bio:
                    type: string
                    description: |
                      User's biography, or a short description of the user
                  is_bot:
                    type: boolean
                    description: |
                      Whether or not the user account should be flagged as a bot account
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

        with self.Session() as session:
            if user_id is None:
                user_id = self.associated_user_object.id
            user = session.scalars(
                User.select(session.user_or_token, mode="update").where(
                    User.id == user_id
                )
            ).first()
            if user is None:
                return self.error(f'Cannot find User with ID: {user_id}')

            if data.get("username") is not None:
                username = data.pop("username").strip()
                if len(username) < 5:
                    return self.error("Username must be at least five characters long.")
                user.username = username

            if data.get("first_name") is not None:
                user.first_name = data.pop("first_name")

            if data.get("last_name") is not None:
                user.last_name = data.pop("last_name")

            if data.get("affiliations") is not None:
                if isinstance(data.get("affiliations"), list):
                    user.affiliations = data.pop("affiliations")
                else:
                    return self.error(
                        "Invalid affiliations. Should be a list of strings."
                    )

            if data.get("bio") is not None and isinstance(data.get("bio"), str):
                bio = data.pop("bio")
                bio = str(bio).strip()

                # the bio is not empty, verify that it is valid
                if len(bio) > 0:
                    if len(bio) < 10:
                        return self.error("Bio must be at least 10 characters long.")
                    if len(bio) > 1000:
                        return self.error("Bio must be less than 1000 characters long.")

                    # capitalize the first letter of the bio
                    bio = bio[0].upper() + bio[1:]

                    # if it doesn't end in a period, exclamation point, or question mark, add a period
                    if bio[-1] not in [".", "!", "?"]:
                        bio += "."

                user.bio = bio

            if data.get("is_bot") not in [None, ""]:
                if str(data.get("is_bot")).lower() in ["true", "t", "1"]:
                    user.is_bot = True
                else:
                    user.is_bot = False

            if user.is_bot:
                # check that the bio is set and is between 10 and 1000 characters if the user is a bot
                if user.bio is None or len(user.bio) < 10 or len(user.bio) > 1000:
                    return self.error(
                        "Bot users must have a bio between 10 and 1000 characters long."
                    )

                # check that the user isn't in any groups that have auto-reporting enabled but bot autoreports are not allowed
                user_accessible_groups = [group.id for group in user.accessible_groups]
                tnsrobot_groups_no_bot_autoreports = session.scalars(
                    TNSRobotGroup.select(session.user_or_token).where(
                        TNSRobotGroup.group_id.in_(user_accessible_groups),
                        TNSRobotGroup.auto_report.is_(True),
                        TNSRobotGroup.auto_report_allow_bots.is_(False),
                    )
                ).all()
                for tnsrobot_group in tnsrobot_groups_no_bot_autoreports:
                    autoreporter = session.scalars(
                        sa.select(TNSRobotGroupAutoreporter).where(
                            TNSRobotGroupAutoreporter.tnsrobot_group_id
                            == tnsrobot_group.id,
                            TNSRobotGroupAutoreporter.group_user_id.in_(
                                sa.select(GroupUser.id).where(
                                    GroupUser.user_id == user.id,
                                    GroupUser.group_id == tnsrobot_group.group_id,
                                )
                            ),
                        )
                    ).first()
                    if autoreporter is not None:
                        return self.error(
                            "User is an autoreporter of a TNS robot group that does not allow bots to be autoreporters. Please remove the autoreporter status first, or allow bot autoreporting."
                        )

                # check that the user isn't a coauthor of any TNS bot, in which case they can't be a bot
                tns_bot_coauthor = session.scalars(
                    TNSRobotCoauthor.select(session.user_or_token).where(
                        TNSRobotCoauthor.user_id == user.id
                    )
                ).first()
                if tns_bot_coauthor is not None:
                    return self.error(
                        "User is a coauthor of a TNS robot and cannot be flagged as a bot."
                    )

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
                        check_blacklist=False,
                        check_dns=False,
                        check_smtp=False,
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
                if "classificationShortcuts" in preferences:
                    user_prefs["classificationShortcuts"] = preferences[
                        "classificationShortcuts"
                    ]
                if "photometryButtons" in preferences:
                    user_prefs["photometryButtons"] = preferences["photometryButtons"]
                if "spectroscopyButtons" in preferences:
                    user_prefs["spectroscopyButtons"] = preferences[
                        "spectroscopyButtons"
                    ]
                gcn_event_properties = (
                    preferences.get('notifications', {})
                    .get('gcn_events', {})
                    .get('properties', None)
                )
                if gcn_event_properties is not None:
                    user_prefs["notifications"]["gcn_events"][
                        "properties"
                    ] = gcn_event_properties
                user_prefs = recursive_update(user_prefs, preferences)
            user.preferences = user_prefs

            try:
                session.commit()
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
            if "topSavers" in preferences:
                self.push(action="skyportal/FETCH_TOP_SAVERS")
            if "recentGcnEvents" in preferences:
                self.push(action="skyportal/FETCH_RECENT_GCNEVENTS")
            if "recentSources" in preferences:
                self.push(action="skyportal/FETCH_RECENT_SOURCES")
            if "sourceCounts" in preferences:
                self.push(action="skyportal/FETCH_SOURCE_COUNTS")
            return self.success(action="skyportal/FETCH_USER_PROFILE")
