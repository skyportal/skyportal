from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    User,
    GroupAdmissionRequest,
)
from .group import has_admin_access_for_group


class GroupAdmissionRequestHandler(BaseHandler):
    @auth_or_token
    def get(self, admission_request_id=None):
        """
        ---
        single:
          description: Retrieve a group admission request
          parameters:
            - in: path
              name: admission_request_id
              required: false
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleGroupAdmissionRequest
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all group admission requests
          parameters:
          - in: query
            name: groupID
            nullable: true
            schema:
              type: integer
            description: ID of group for which admission requests are desired
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfGroupAdmissionRequests
            400:
              content:
                application/json:
                  schema: Error
        """
        group_id = self.get_query_argument("groupID", None)
        if admission_request_id is not None:
            admission_request = GroupAdmissionRequest.query.get(admission_request_id)
            if admission_request is None:
                return self.error("Invalid admission request ID.")

            response_data = admission_request.to_json()
            response_data["user"] = admission_request.user

            return self.success(data=response_data)

        q = GroupAdmissionRequest.query
        if group_id is not None:
            q = q.filter(GroupAdmissionRequest.group_id == group_id)
        admission_requests = q.all()
        response_data = [
            {**admission_request.to_dict(), "user": admission_request.user}
            for admission_request in admission_requests
        ]
        return self.success(data=response_data)

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
    def patch(self, admission_request_id):
        """
        ---
        description: Update an admission request's status
        parameters:
          - in: path
            name: admission_request_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    description: One of either 'accepted', 'declined', or 'pending'.
                required:
                  - status
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        status = data.get("status")
        if status is None:
            return self.error("Missing required parameter `status`")
        if status not in ["pending", "accepted", "declined"]:
            return self.error(
                "Invalid 'status' value - should be one of either 'accepted', 'declined', or 'pending'"
            )
        admission_request = GroupAdmissionRequest.query.get(admission_request_id)
        if admission_request is None:
            return self.error("Invalid admission request ID.")
        if not has_admin_access_for_group(
            self.current_user, admission_request.group_id
        ):
            return self.error("Insufficient permissions.")
        admission_request.status = status
        DBSession().commit()
        return self.success()

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
