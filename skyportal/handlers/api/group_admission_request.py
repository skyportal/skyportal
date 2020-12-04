from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    User,
    GroupAdmissionRequest,
)


class GroupAdmissionRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Create a new group admission request
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  groupID:
                    type: integer
                  userID:
                    type: integer
                required:
                  - groupID
                  - userID
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
                              description: New group admission request ID
        """
        data = self.get_json()
        user_id = data.get("userID")
        group_id = data.get("groupID")
        if user_id is None:
            return self.error("Missing required parameter `userID`")
        if group_id is None:
            return self.error("Missing required parameter `groupID`")
        try:
            user_id = int(user_id)
        except ValueError:
            return self.error("Invalid `userID` parameter; unable to parse to int")
        try:
            group_id = int(group_id)
        except ValueError:
            return self.error("Invalid `groupID` parameter; unable to parse to int")
        # Ensure that requesting user is either sysadmin or is the user in question
        if (
            self.associated_user_object.id != user_id
            and not self.current_user.is_system_admin
        ):
            return self.error("Insufficient permissions")
        if Group.query.get(group_id) is None:
            return self.error("Invalid group ID")
        if User.query.get(user_id) is None:
            return self.error("Invalid user ID")
        admission_request = GroupAdmissionRequest(
            user_id=user_id, group_id=group_id, status="pending"
        )
        DBSession().add(admission_request)
        DBSession().commit()
        self.push(action="skyportal/FETCH_USER_PROFILE")
        return self.success(data={"id": admission_request.id})

    @auth_or_token
    def delete(self, admission_request_id):
        """
        ---
        description: Delete a group admission request
        parameters:
          - in: path
            name: admission_request_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        admission_request = GroupAdmissionRequest.query.get(admission_request_id)
        if admission_request is None:
            return self.error("Invalid admission request ID")
        # Ensure that requesting user is either sysadmin or is the user in question
        if (
            self.associated_user_object.id != admission_request.user_id
            and not self.current_user.is_system_admin
        ):
            return self.error("Insufficient permissions")
        DBSession().delete(admission_request)
        DBSession().commit()
        self.push(action="skyportal/FETCH_USER_PROFILE")
        return self.success()
