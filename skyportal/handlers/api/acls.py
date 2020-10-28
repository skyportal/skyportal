from baselayer.app.access import auth_or_token, permissions

from ..base import BaseHandler
from ...models import DBSession, ACL, User, UserACL


class ACLHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        description: Retrieve list of all ACL IDs (strings)
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
                            type: string
                          description: List of all ACL IDs.
        """
        return self.success(data=ACL.query.all())


class UserACLHandler(BaseHandler):
    @permissions(["Manage users"])
    def post(self, user_id, *ignored_args):
        """
        ---
        description: Grant new ACL(s) to a user
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
                  aclIds:
                    type: array
                    items:
                      type: string
                    description: Array of ACL IDs (strings) to be granted to user
                required:
                  - aclIds
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        new_acl_ids = data.get("aclIds")
        if new_acl_ids is None:
            return self.error("Missing required parameter aclIds")
        if (not isinstance(new_acl_ids, (list, tuple))) or (
            not all([ACL.query.get(acl_id) is not None for acl_id in new_acl_ids])
        ):
            return self.error(
                "Improperly formatted parameter aclIds; " "must be an array of strings."
            )
        user = User.query.get(user_id)
        if user is None:
            return self.error("Invalid user_id parameter.")
        new_acls = ACL.query.filter(ACL.id.in_(new_acl_ids)).all()
        user.acls = list(set(user.acls).union(set(new_acls)))
        DBSession().commit()
        self.push_all(action="skyportal/FETCH_USERS")
        return self.success()

    @permissions(["Manage users"])
    def delete(self, user_id, acl_id):
        """
        ---
        description: Remove ACL from user permissions
        parameters:
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
          - in: path
            name: acl_id
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
        acl = ACL.query.get("acl_id")
        if acl is None:
            return self.error("Invalid acl_id")
        (
            UserACL.query.filter(UserACL.user_id == user_id)
            .filter(UserACL.acl_id == acl_id)
            .delete()
        )
        DBSession().commit()
        self.push_all(action="skyportal/FETCH_USERS")
        return self.success()
