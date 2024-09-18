from baselayer.app.access import auth_or_token, permissions

from ..base import BaseHandler
from ...models import ACL, User, UserACL


class ACLHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        summary: Get all ACL IDs
        description: Retrieve list of all ACL IDs (strings)
        tags:
          - acls
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
        with self.Session() as session:
            acls = session.scalars(
                ACL.select(session.user_or_token, columns=[ACL.id])
            ).all()
            return self.success(data=acls)


class UserACLHandler(BaseHandler):
    @permissions(["Manage users"])
    def post(self, user_id, *ignored_args):
        """
        ---
        summary: Grant ACLs to a user
        description: Grant new ACL(s) to a user
        tags:
          - acls
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
        with self.Session() as session:
            if (not isinstance(new_acl_ids, (list, tuple))) or (
                not all(
                    [
                        session.scalars(
                            ACL.select(session.user_or_token).where(ACL.id == acl_id)
                        ).first()
                        is not None
                        for acl_id in new_acl_ids
                    ]
                )
            ):
                return self.error(
                    "Improperly formatted parameter aclIds; must be an array of strings."
                )
            user = session.scalars(
                User.select(session.user_or_token).where(User.id == user_id)
            ).first()
            if user is None:
                return self.error("Invalid user_id parameter.")
            new_acls = (
                session.scalars(
                    ACL.select(session.user_or_token).where(ACL.id.in_(new_acl_ids))
                )
                .unique()
                .all()
            )
            user.acls = list(set(user.acls).union(set(new_acls)))
            session.commit()
            return self.success()

    @permissions(["Manage users"])
    def delete(self, user_id, acl_id):
        """
        ---
        summary: Remove ACL from a user
        description: Remove ACL from user permissions
        tags:
          - acls
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
        with self.Session() as session:
            user = session.scalars(
                User.select(session.user_or_token).where(User.id == user_id)
            ).first()
            if user is None:
                return self.error("Invalid user_id")
            acl = session.scalars(
                ACL.select(session.user_or_token).where(ACL.id == acl_id)
            ).first()
            if acl is None:
                return self.error("Invalid acl_id")
            user_acl = session.scalars(
                UserACL.select(session.user_or_token, mode="delete")
                .where(UserACL.user_id == user_id)
                .where(UserACL.acl_id == acl_id)
            ).first()
            session.delete(user_acl)
            session.commit()
            return self.success()
