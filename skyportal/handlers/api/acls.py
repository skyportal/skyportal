from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions

from ...models import ACL, User, UserACL
from ..base import BaseHandler


class ACLHandler(BaseHandler):
    @auth_or_token
    async def get(self):
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
        async with self.AsyncSession() as session:
            result = await session.scalars(
                ACL.select(session.user_or_token, columns=[ACL.id])
            )
            acls = result.all()
            return self.success(data=acls)


class UserACLHandler(BaseHandler):
    @permissions(["Manage users"])
    async def post(self, user_id: int, *ignored_args):
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
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid user_id: {user_id}")
        data = self.get_json()
        new_acl_ids = data.get("aclIds")
        if new_acl_ids is None:
            return self.error("Missing required parameter aclIds")
        if not isinstance(new_acl_ids, list | tuple):
            return self.error(
                "Improperly formatted parameter aclIds; must be an array of strings."
            )
        async with self.AsyncSession() as session:
            # Validate every supplied ACL id exists/is accessible in a single
            # round trip rather than one query per id.
            existing_result = await session.scalars(
                ACL.select(session.user_or_token, columns=[ACL.id]).where(
                    ACL.id.in_(new_acl_ids)
                )
            )
            existing_ids = set(existing_result.all())
            if existing_ids != set(new_acl_ids):
                return self.error(
                    "Improperly formatted parameter aclIds; must be an array of strings."
                )
            user_result = await session.scalars(
                User.select(session.user_or_token)
                .options(selectinload(User.acls))
                .where(User.id == user_id)
            )
            user = user_result.first()
            if user is None:
                return self.error("Invalid user_id parameter.")
            new_acls_result = await session.scalars(
                ACL.select(session.user_or_token).where(ACL.id.in_(new_acl_ids))
            )
            new_acls = new_acls_result.unique().all()
            user.acls = list(set(user.acls).union(set(new_acls)))
            await session.commit()
            return self.success()

    @permissions(["Manage users"])
    async def delete(self, user_id: int, acl_id: str):
        # Path arg comes in as a string; the column is integer.
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
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid user_id: {user_id}")
        async with self.AsyncSession() as session:
            user_result = await session.scalars(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            user = user_result.first()
            if user is None:
                return self.error("Invalid user_id")
            acl_result = await session.scalars(
                ACL.select(session.user_or_token).where(ACL.id == acl_id)
            )
            acl = acl_result.first()
            if acl is None:
                return self.error("Invalid acl_id")
            user_acl_result = await session.scalars(
                UserACL.select(session.user_or_token, mode="delete")
                .where(UserACL.user_id == user_id)
                .where(UserACL.acl_id == acl_id)
            )
            user_acl = user_acl_result.first()
            await session.delete(user_acl)
            await session.commit()
            return self.success()
