from ..base import BaseHandler
from baselayer.app.access import permissions
from ...models import DBSession, User, Group, GroupUser, cfg
from ...model_util import role_acls

from sqlalchemy.orm import joinedload


class UserHandler(BaseHandler):
    @permissions(['Manage users'])
    def get(self, user_id=None):
        """
        ---
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
        """
        user = User.query.get(int(user_id))
        if user is None:
            return self.error(f'Invalid user ID ({user_id}).')
        else:
            return self.success(data=user)

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

        # Add user
        user = User(username=data["username"], role_ids=roles)
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
        DBSession().commit()
        return self.success(data={"id": user.id})

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
