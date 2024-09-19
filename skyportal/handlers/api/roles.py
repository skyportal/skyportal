from baselayer.app.access import auth_or_token, permissions

from ..base import BaseHandler
from ...models import Role, User, UserRole


class RoleHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        summary: Get all roles
        description: Retrieve list of all Role IDs (strings)
        tags:
          - roles
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
                            $ref: '#/components/schemas/Role'
                          description: List of all Roles.
        """
        roles = Role.query.all()
        for i, role in enumerate(roles):
            roles[i] = role.to_dict()
            roles[i]['acls'] = [acl.id for acl in role.acls]
        self.verify_and_commit()
        return self.success(data=roles)


class UserRoleHandler(BaseHandler):
    @permissions(["Manage users"])
    def post(self, user_id, *ignored_args):
        """
        ---
        summary: Grant new Role(s) to a user
        description: Grant new Role(s) to a user
        tags:
          - roles
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
                  roleIds:
                    type: array
                    items:
                      type: string
                    description: Array of Role IDs (strings) to be granted to user
                required:
                  - roleIds
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        new_role_ids = data.get("roleIds")
        if new_role_ids is None:
            return self.error("Missing required parameter roleIds")
        if (not isinstance(new_role_ids, (list, tuple))) or (
            not all([Role.query.get(role_id) is not None for role_id in new_role_ids])
        ):
            return self.error(
                "Improperly formatted parameter roleIds; must be an array of strings."
            )
        user = User.query.get(user_id)
        if user is None:
            return self.error("Invalid user_id parameter.")
        new_roles = Role.query.filter(Role.id.in_(new_role_ids)).all()
        user.roles = list(set(user.roles).union(set(new_roles)))
        self.verify_and_commit()
        return self.success()

    @permissions(["Manage users"])
    def delete(self, user_id, role_id):
        """
        ---
        summary: Delete user role
        description: Delete user role
        tags:
          - roles
        parameters:
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
          - in: path
            name: role_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        user = User.query.get(user_id)
        if user is None:
            return self.error("Invalid user_id")
        role = Role.query.get(role_id)
        if role is None:
            return self.error("Invalid role_id")
        (
            UserRole.query.filter(UserRole.user_id == user_id)
            .filter(UserRole.role_id == role_id)
            .delete()
        )
        self.verify_and_commit()
        return self.success()
