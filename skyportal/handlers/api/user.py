import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from email_validator import validate_email, EmailNotValidError
import arrow
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import func

from ..base import BaseHandler
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log
from ...models import (
    User,
    Role,
    UserRole,
    UserACL,
    ACL,
    Group,
    GroupUser,
    StreamUser,
    Stream,
)

from skyportal.model_util import role_acls, all_acl_ids

log = make_log("api/user")
env, cfg = load_env()


def set_default_role(user, session):
    """
    Set the default role for a user.
    The default role can be set in the config file.
    This method does not commit the session,
    so the session needs to be committed after calling this method.
    If the default role from the config does not exist,
    an exception is raised, and can be caught by the caller (i.e., in a handler).
    """
    default_role = cfg['user.default_role']
    if isinstance(default_role, str) and default_role in role_acls:
        role = session.scalars(sa.select(Role).where(Role.id == default_role)).first()
        if role is None:
            # raise an error:
            raise Exception(
                f"Invalid default_role configuration value: {default_role} does not exist"
            )
        else:
            session.add(UserRole(user_id=user.id, role_id=role.id))


def set_default_acls(user, session):
    """
    Set the default acls for a user.
    The default acls can be set in the config file.
    This method does not commit the session,
    so the session needs to be committed after calling this method.
    If the default acl from the config does not exist,
    an exception is raised, and can be caught by the caller (i.e., in a handler).
    """
    for acl_id in cfg['user.default_acls']:
        if acl_id not in all_acl_ids:
            raise Exception(
                f"Invalid default_acl configuration value: {acl_id} does not exist"
            )
    for acl_id in cfg['user.default_acls']:
        session.add(UserACL(user_id=user.id, acl_id=acl_id))


def set_default_group(user, session):
    """
    Set the default groups for a user.
    The default groups can be set in the config file.
    This method does not commit the session,
    so the session needs to be committed after calling this method.
    If the default group from the config does not exist,
    an exception is raised, and can be caught by the caller (i.e., in a handler).
    """
    default_groups = []
    if cfg['misc.public_group_name'] is not None:
        default_groups.append(cfg['misc.public_group_name'])
    default_groups.extend(cfg['user.default_groups'])
    default_groups = list(set(default_groups))
    for default_group_name in default_groups:
        group = session.scalars(
            sa.select(Group).where(Group.name == default_group_name)
        ).first()
        if group is None:
            raise Exception(
                f"Invalid default_group configuration value: {default_group_name} does not exist"
            )
        else:
            session.add(GroupUser(user_id=user.id, group_id=group.id, admin=False))
            if group.streams:
                for stream in group.streams:
                    session.add(StreamUser(stream_id=stream.id, user_id=user.id))


def add_user_and_setup_groups(
    session,
    username,
    first_name=None,
    last_name=None,
    affiliations=None,
    contact_phone=None,
    contact_email=None,
    role_ids=[],
    group_ids_and_admin=[],
    oauth_uid=None,
    expiration_date=None,
):
    try:
        # the roles come from the association_proxy
        # in baselayer/app/models.py line 1851
        # they are queried from a different session
        # in the "creator" lambda. Until we figure out
        # how to do this in the same session, this should
        # solve the problem.
        roles = session.scalars(sa.select(Role).where(Role.id.in_(role_ids))).all()
        user = User(
            username=username.lower(),
            roles=roles,
            first_name=first_name,
            last_name=last_name,
            affiliations=affiliations,
            contact_phone=contact_phone,
            contact_email=contact_email,
            oauth_uid=oauth_uid,
            expiration_date=expiration_date,
        )
        session.add(user)
        session.flush()

        if role_ids == []:
            set_default_role(user, session)

        if group_ids_and_admin == []:
            set_default_group(user, session)
        else:
            for group_id, admin in group_ids_and_admin:
                session.add(GroupUser(user_id=user.id, group_id=group_id, admin=admin))
                group = session.scalars(
                    sa.select(Group).where(Group.id == group_id)
                ).first()
                if group.streams:
                    for stream in group.streams:
                        session.add(StreamUser(stream_id=stream.id, user_id=user.id))

            # Add user to sitewide public group
            if cfg["misc.public_group_name"] is not None:
                public_group = session.scalars(
                    sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
                ).first()
                if public_group is not None:
                    session.add(GroupUser(group_id=public_group.id, user_id=user.id))

        set_default_acls(user, session)
        session.commit()
    except Exception as e:
        session.rollback()
        log(str(e))
        raise e
    return user.id


class UserHandler(BaseHandler):
    @auth_or_token
    def get(self, user_id=None):
        """
        ---
        single:
          description: Retrieve a user
          tags:
            - users
          parameters:
            - in: path
              name: user_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleUser
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all users
          tags:
            - users
          parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of candidates to return per paginated request. Defaults to all users
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1
          - in: query
            name: firstName
            nullable: true
            schema:
              type: string
            description: Get users whose first name contains this string.
          - in: query
            name: lastName
            nullable: true
            schema:
              type: string
            description: Get users whose last name contains this string.
          - in: query
            name: username
            nullable: true
            schema:
              type: string
            description: Get users whose username contains this string.
          - in: query
            name: email
            nullable: true
            schema:
              type: string
            description: Get users whose email contains this string.
          - in: query
            name: role
            nullable: true
            schema:
              type: string
            description: Get users with the role.
          - in: query
            name: acl
            nullable: true
            schema:
              type: string
            description: Get users with this ACL.
          - in: query
            name: group
            nullable: true
            schema:
              type: string
            description: Get users part of the group with name given by this parameter.
          - in: query
            name: stream
            nullable: true
            schema:
              type: string
            description: Get users with access to the stream with name given by this parameter.
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
                              users:
                                type: array
                                items:
                                  $ref: '#/components/schemas/User'
                                description: List of users
                              totalMatches:
                                type: integer
                                description: The total number of users matching the query
            400:
              content:
                application/json:
                  schema: Error
        """
        if user_id is not None:
            try:
                user_id = int(user_id)
            except ValueError:
                return self.error(f"Invalid user_id {user_id}")

            with self.Session() as session:
                user = session.scalars(
                    User.select(self.current_user).where(User.id == user_id)
                ).first()
                if user is None:
                    return self.error(f"Cannot find user with ID {user_id}.")
                user_info = user.to_dict()

                # return the phone number so it can be serialized
                if user_info.get("contact_phone"):
                    user_info["contact_phone"] = user_info["contact_phone"].e164

                user_info["permissions"] = sorted(user.permissions)
                user_info["roles"] = sorted(role.id for role in user.roles)
                user_info["acls"] = sorted(acl.id for acl in user.acls)

                return self.success(data=user_info)

        # get users by query parameters
        page_number = self.get_query_argument("pageNumber", None) or 1
        n_per_page = self.get_query_argument("numPerPage", None)
        first_name = self.get_query_argument("firstName", None)
        last_name = self.get_query_argument("lastName", None)
        username = self.get_query_argument("username", None)
        email_address = self.get_query_argument("email", None)
        role = self.get_query_argument("role", None)
        acl = self.get_query_argument("acl", None)
        group = self.get_query_argument("group", None)
        stream = self.get_query_argument("stream", None)
        include_expired = self.get_query_argument("includeExpired", False)

        try:
            page_number = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            if n_per_page is not None:
                n_per_page = int(n_per_page)
        except ValueError:
            return self.error("Invalid numPerPage value.")

        with self.Session() as session:
            stmt = User.select(self.current_user).order_by(User.username)

            if not include_expired:
                stmt = stmt.where(
                    sa.or_(
                        User.expiration_date >= datetime.now(),
                        User.expiration_date.is_(None),
                    )
                )

            if first_name is not None:
                stmt = stmt.where(User.first_name.contains(first_name))
            if last_name is not None:
                stmt = stmt.where(User.last_name.contains(last_name))
            if username is not None:
                stmt = stmt.where(User.username.contains(username))
            if email_address is not None:
                stmt = stmt.where(User.contact_email.contains(email_address))
            if role is not None:
                stmt = stmt.join(UserRole).join(Role).where(Role.id == role)
            if acl is not None:
                stmt = stmt.join(UserACL).join(ACL).where(ACL.id == acl)
            if group is not None:
                stmt = stmt.join(GroupUser).join(Group).where(Group.name == group)
            if stream is not None:
                stmt = stmt.join(StreamUser).join(Stream).where(Stream.name == stream)

            total_matches = session.execute(
                sa.select(func.count()).select_from(stmt)
            ).scalar()

            if n_per_page is not None:
                stmt = stmt.limit(n_per_page).offset((page_number - 1) * n_per_page)
            info = {}
            return_values = []
            user_accessible_group_ids = {
                g.id
                for g in self.current_user.accessible_groups
                if not g.single_user_group
            }

            for user in session.scalars(stmt).all():
                return_values.append(user.to_dict())
                return_values[-1]["permissions"] = sorted(user.permissions)
                return_values[-1]["roles"] = sorted(role.id for role in user.roles)
                return_values[-1]["acls"] = sorted(acl.id for acl in user.acls)
                if user.contact_phone:
                    return_values[-1]["contact_phone"] = user.contact_phone.e164
                return_values[-1]["contact_email"] = user.contact_email
                return_values[-1]["gravatar_url"] = user.gravatar_url
                # Only Sys admins can see other users' group memberships for all groups and stream access
                # if not sys admin, restrict to only the groups the current user is a member of
                if self.current_user.is_system_admin:
                    return_values[-1]["groups"] = user.groups
                    return_values[-1]["streams"] = user.streams
                else:
                    return_values[-1]["groups"] = [
                        g for g in user.groups if g.id in user_accessible_group_ids
                    ]

            info["users"] = return_values
            info["totalMatches"] = int(total_matches)

            return self.success(data=info)

    @permissions(["Manage users"])
    def post(self):
        """
        ---
        description: Add a new user
        tags:
          - users
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  username:
                    type: string
                  first_name:
                    type: string
                  last_name:
                    type: string
                  affiliations:
                    type: array
                    items:
                      type: string
                  contact_email:
                    type: string
                  oauth_uid:
                    type: string
                  contact_phone:
                    type: string
                  roles:
                    type: array
                    items:
                      type: string
                    enum: {list(role_acls)}
                    description: |
                      List of user roles. Defaults to `[Full user]`. Will be overridden
                      by `groupIDsAndAdmin` on a per-group basis.
                  groupIDsAndAdmin:
                    type: array
                    items:
                      type: array
                    description: |
                      Array of 2-element arrays `[groupID, admin]` where `groupID`
                      is the ID of a group that the new user will be added to and
                      `admin` is a boolean indicating whether they will be an admin in
                      that group, e.g. `[[group_id_1, true], [group_id_2, false]]`
                required:
                  - username
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
                            id:
                              type: integer
                              description: New user ID
        """
        data = self.get_json()
        role_ids = data.get("roles", [])
        group_ids_and_admin = data.get("groupIDsAndAdmin", [])

        phone = data.get("contact_phone")
        if phone not in [None, ""]:
            try:
                if not phonenumbers.is_possible_number(phonenumbers.parse(phone, "US")):
                    return self.error("Phone number given is not valid")
            except NumberParseException:
                return self.error("Could not parse input as a phone number")
            contact_phone = phone
        else:
            contact_phone = None

        email = data.get("contact_email")
        if email not in [None, ""]:
            try:
                emailinfo = validate_email(email, check_deliverability=False)
            except EmailNotValidError as e:
                return self.error(f"Email does not appear to be valid: {str(e)}")
            contact_email = emailinfo.normalized
        else:
            contact_email = None

        affiliations = data.get("affiliations")
        # check if the affiliations are a list
        if affiliations is not None and not isinstance(affiliations, list):
            return self.error("Affiliations must be a list of strings")
        with self.Session() as session:
            try:
                user_id = add_user_and_setup_groups(
                    session=session,
                    username=data["username"],
                    first_name=data.get("first_name"),
                    last_name=data.get("last_name"),
                    affiliations=affiliations,
                    contact_phone=contact_phone,
                    contact_email=contact_email,
                    oauth_uid=data.get("oauth_uid"),
                    role_ids=role_ids,
                    group_ids_and_admin=group_ids_and_admin,
                )
            except Exception as e:
                session.rollback()
                return self.error(str(e))

            session.commit()

        return self.success(data={"id": user_id})

    @permissions(["Manage users"])
    def patch(self, user_id):
        """
        ---
        description: Update a User record
        tags:
          - users
        parameters:
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  expirationDate:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01). Set a user's expiration
                      date, after which the user's account will be deactivated and will be unable
                      to access the application.
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()

        if user_id is not None:
            try:
                user_id = int(user_id)
            except ValueError:
                return self.error(f"Invalid user ID {user_id}")

            with self.Session() as session:
                user = session.scalars(
                    User.select(self.current_user, mode='update').where(
                        User.id == user_id
                    )
                ).first()
                if user is None:
                    return self.error(f'Cannot find user with ID {user_id}')
                expiration_date = data.get("expirationDate")
                if expiration_date is not None:
                    try:
                        user.expiration_date = arrow.get(
                            expiration_date.strip()
                        ).datetime
                    except arrow.parser.ParserError:
                        return self.error("Unable to parse `expirationDate` parameter.")

                for k in data:
                    if k != 'expiration_date':
                        setattr(user, k, data[k])

                session.commit()
                self.push_all(action="skyportal/FETCH_USERS")
                return self.success()
        else:
            return self.error("User ID must be provided")

    @permissions(["Manage users"])
    def delete(self, user_id=None):
        """
        ---
        description: Delete a user
        tags:
          - users
        parameters:
          - in: path
            name: user_id
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
            user = session.scalars(
                User.select(self.current_user, mode='delete').where(User.id == user_id)
            ).first()
            if user is None:
                return self.error(f"Cannot find/delete user with ID {user_id}")
            session.delete(user)
            session.commit()

        return self.success()
