from baselayer.app.access import auth_or_token, permissions

from ...models import Role, User, UserRole
from ..base import BaseHandler


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
        with self.Session() as session:
            roles = session.scalars(Role.select(self.associated_user_object)).all()
            output = []
            for role in roles:
                role_dict = role.to_dict()
                role_dict["acls"] = [acl.id for acl in role.acls]
                output.append(role_dict)
            return self.success(data=output)


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
        if not isinstance(new_role_ids, list) or not all(
            isinstance(role_id, str) for role_id in new_role_ids
        ):
            return self.error(
                "Improperly formatted parameter roleIds; must be an array of strings."
            )

        with self.Session() as session:
            user = session.scalar(
                User.select(self.associated_user_object).where(User.id == user_id)
            )
            if user is None:
                return self.error("Invalid user_id parameter.")
            # if some of the requested role IDs are invalid, return an error listing the invalid IDs
            valid_role_ids = set(
                session.scalars(
                    Role.select(self.associated_user_object, columns=[Role.id]).where(
                        Role.id.in_(new_role_ids)
                    )
                ).all()
            )
            invalid_role_ids = set(new_role_ids) - valid_role_ids
            if invalid_role_ids:
                return self.error(f"Invalid role_id(s): {', '.join(invalid_role_ids)}")
            new_roles = session.scalars(
                Role.select(self.associated_user_object).where(
                    Role.id.in_(new_role_ids)
                )
            ).all()
            user.roles = list(set(user.roles).union(set(new_roles)))
            session.commit()
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
        with self.Session() as session:
            user = session.scalar(
                User.select(self.associated_user_object).where(User.id == user_id)
            )
            if user is None:
                return self.error("Invalid user_id parameter.")
            user_role = session.scalar(
                UserRole.select(self.associated_user_object).where(
                    UserRole.user_id == user_id, UserRole.role_id == role_id
                )
            )
            if user_role is None:
                return self.error("User does not have specified role.")
            session.delete(user_role)
            session.commit()
            return self.success()
