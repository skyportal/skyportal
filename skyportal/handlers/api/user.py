import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from validate_email import validate_email


from ..base import BaseHandler
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from ...models import (
    DBSession,
    User,
    Group,
    GroupUser,
    StreamUser,
    UserRole,
    Role,
    UserACL,
    ACL,
    Stream,
)


env, cfg = load_env()


def add_user_and_setup_groups(
    username,
    first_name=None,
    last_name=None,
    contact_phone=None,
    contact_email=None,
    roles=[],
    group_ids_and_admin=[],
    oauth_uid=None,
):
    # Add user
    user = User(
        username=username.lower(),
        role_ids=roles,
        first_name=first_name,
        last_name=last_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        oauth_uid=oauth_uid,
    )
    DBSession().add(user)
    DBSession().flush()

    # Add user to specified groups & associated streams
    for group_id, admin in group_ids_and_admin:
        DBSession().add(GroupUser(user_id=user.id, group_id=group_id, admin=admin))
        group = Group.query.get(group_id)
        if group.streams:
            for stream in group.streams:
                DBSession().add(StreamUser(user_id=user.id, stream_id=stream.id))

    # Add user to sitewide public group
    public_group = Group.query.filter(
        Group.name == cfg["misc"]["public_group_name"]
    ).first()
    if public_group is not None:
        DBSession().add(GroupUser(group_id=public_group.id, user_id=user.id))
    return user.id


class UserHandler(BaseHandler):
    @auth_or_token
    def get(self, user_id=None):
        """
        ---
        single:
          description: Retrieve a user
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
          parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of candidates to return per paginated request. Defaults to 25
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
                            type: array
                            items:
                              $ref: '#/components/schemas/User'
                            description: List of users
            400:
              content:
                application/json:
                  schema: Error
        """
        if user_id is not None:
            user = User.query.get(int(user_id))
            if user is None:
                return self.error(f"Invalid user ID ({user_id}).")
            user_info = user.to_dict()

            # return the phone number so it can be serialized
            if user_info.get("contact_phone"):
                user_info["contact_phone"] = user_info["contact_phone"].e164

            user_info["permissions"] = sorted(user.permissions)
            user_info["roles"] = sorted([role.id for role in user.roles])
            user_info["acls"] = sorted([acl.id for acl in user.acls])
            return self.success(data=user_info)

        page_number = self.get_query_argument("pageNumber", None) or 1
        n_per_page = self.get_query_argument("numPerPage", None) or 25
        first_name = self.get_query_argument("firstName", None)
        last_name = self.get_query_argument("lastName", None)
        username = self.get_query_argument("username", None)
        email_address = self.get_query_argument("email", None)
        role = self.get_query_argument("role", None)
        acl = self.get_query_argument("acl", None)
        group = self.get_query_argument("group", None)
        stream = self.get_query_argument("stream", None)

        try:
            page_number = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            n_per_page = int(n_per_page)
        except ValueError:
            return self.error("Invalid numPerPage value.")

        query = User.query.order_by(User.username)

        if first_name is not None:
            query = query.filter(User.first_name.contains(first_name))
        if last_name is not None:
            query = query.filter(User.last_name.contains(last_name))
        if username is not None:
            query = query.filter(User.username.contains(username))
        if email_address is not None:
            query = query.filter(User.contact_email.contains(email_address))
        if role is not None:
            query = query.join(UserRole).join(Role).filter(Role.id == role)
        if acl is not None:
            query = query.join(UserACL).join(ACL).filter(ACL.id == acl)
        if group is not None:
            query = query.join(GroupUser).join(Group).filter(Group.name == group)
        if stream is not None:
            query = query.join(StreamUser).join(Stream).filter(Stream.name == stream)

        total_matches = query.count()
        query = query.limit(n_per_page).offset((page_number - 1) * n_per_page)
        info = {}
        return_values = []
        for user in query.all():
            return_values.append(user.to_dict())
            del return_values[-1]["preferences"]
            return_values[-1]["permissions"] = sorted(user.permissions)
            return_values[-1]["roles"] = sorted([role.id for role in user.roles])
            return_values[-1]["acls"] = sorted([acl.id for acl in user.acls])
            if user.contact_phone:
                return_values[-1]["contact_phone"] = user.contact_phone.e164
            return_values[-1]["contact_email"] = user.contact_email
            # Only Sys admins can see other users' group memberships
            if "System admin" in self.associated_user_object.permissions:
                return_values[-1]["groups"] = user.groups
                return_values[-1]["streams"] = user.streams

        info["users"] = return_values
        info["totalMatches"] = int(total_matches)
        return self.success(data=info)

    @permissions(["Manage users"])
    def post(self):
        """
        ---
        description: Add a new user
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
        roles = data.get("roles", ["Full user"])
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
            if not validate_email(
                email_address=email,
                check_regex=True,
                check_mx=False,
                use_blacklist=True,
                debug=False,
            ):
                return self.error("Email does not appear to be valid")
            contact_email = email
        else:
            contact_email = None

        user_id = add_user_and_setup_groups(
            username=data["username"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            contact_phone=contact_phone,
            contact_email=contact_email,
            oauth_uid=data.get("oauth_uid"),
            roles=roles,
            group_ids_and_admin=group_ids_and_admin,
        )
        DBSession().commit()
        return self.success(data={"id": user_id})

    @permissions(["Manage users"])
    def delete(self, user_id=None):
        """
        ---
        description: Delete a user
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
        user = User.query.get(user_id)
        DBSession().delete(user)
        DBSession().commit()
        return self.success()
