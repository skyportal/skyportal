from ..base import BaseHandler
from baselayer.app.access import permissions
from baselayer.app.env import load_env
from ...models import DBSession, User, Group, GroupUser


env, cfg = load_env()


def add_user_and_setup_groups(username, roles, group_ids_and_admin):
    # Add user
    user = User(username=username.lower(), role_ids=roles)
    DBSession().add(user)
    DBSession().flush()

    # Add user to specified groups
    for group_id, admin in group_ids_and_admin:
        DBSession.add(GroupUser(user_id=user.id, group_id=group_id, admin=admin))

    # Create single-user group
    DBSession().add(Group(name=user.username, users=[user], single_user_group=True))

    # Add user to sitewide public group
    public_group = Group.query.filter(
        Group.name == cfg["misc"]["public_group_name"]
    ).first()
    if public_group is not None:
        DBSession().add(GroupUser(group_id=public_group.id, user_id=user.id))
    return user.id


class UserHandler(BaseHandler):
    @permissions(['Manage users'])
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
                return self.error(f'Invalid user ID ({user_id}).')
            user_info = user.to_dict()

            # return the phone number so it can be serialized
            if user_info.get("contact_phone"):
                user_info["contact_phone"] = user_info["contact_phone"].e164

            user_info['acls'] = sorted(user.acls, key=lambda a: a.id)
            return self.success(data=user_info)
        users = User.query.all()
        for user in users:
            if user.get("contact_phone"):
                user["contact_phone"] = user["contact_phone"].e164
        return self.success(data=users)

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
                    description: User's email address
                  first_name:
                    type: string
                  last_name:
                    type: string
                  contact_email:
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

        user_id = add_user_and_setup_groups(
            username=data["username"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            contact_phone=data.get("contact_phone"),
            contact_email=data.get("contact_email"),
            roles=roles,
            group_ids_and_admin=group_ids_and_admin
        )
        DBSession().commit()
        return self.success(data={"id": user_id})

    @permissions(['Manage users'])
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
        single_user_group = Group.query.filter(Group.name == user.username).first()
        if single_user_group is not None:
            DBSession().delete(single_user_group)
        DBSession().commit()
        return self.success()
