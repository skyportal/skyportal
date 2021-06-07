from baselayer.app.access import auth_or_token, permissions
from baselayer.app.custom_exceptions import AccessError
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    User,
    GroupUser,
    GroupAdmissionRequest,
    UserNotification,
)


class GroupAdmissionRequestHandler(BaseHandler):
    @auth_or_token
    def get(self, admission_request_id=None):
        """
        ---
        single:
          description: Retrieve a group admission request
          tags:
            - group_admission_requests
            - groups
            - users
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
          tags:
            - group_admission_requests
            - groups
            - users
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
            admission_request = GroupAdmissionRequest.get_if_accessible_by(
                admission_request_id, self.current_user, raise_if_none=True, mode="read"
            )
            response_data = {
                **admission_request.to_dict(),
                "user": admission_request.user,
            }
            response_data["user"] = admission_request.user
            self.verify_and_commit()
            return self.success(data=response_data)

        q = GroupAdmissionRequest.query_records_accessible_by(
            self.current_user, mode="read"
        )
        if group_id is not None:
            q = q.filter(GroupAdmissionRequest.group_id == group_id)
        admission_requests = q.all()
        response_data = [
            {**admission_request.to_dict(), "user": admission_request.user}
            for admission_request in admission_requests
        ]
        self.verify_and_commit()
        return self.success(data=response_data)

    @auth_or_token
    def post(self):
        """
        ---
        description: Create a new group admission request
        tags:
          - group_admission_requests
          - groups
          - users
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

        group = Group.query.get(group_id)
        if group is None or group.single_user_group:
            return self.error("Invalid group ID")
        requesting_user = User.query.get(user_id)
        if requesting_user is None:
            return self.error("Invalid user ID")
        # Ensure user is not already a member of target group
        gu = (
            GroupUser.query.filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .first()
        )
        if gu is not None:
            return self.error(f"User {user_id} is already a member of group {group_id}")
        # Ensure user has sufficient stream access for target group
        if group.streams:
            if not all(
                [
                    stream in requesting_user.accessible_streams
                    for stream in group.streams
                ]
            ):
                return self.error(
                    f"User {user_id} does not have sufficient stream access "
                    f"to be added to group {group_id}."
                )
        admission_request = GroupAdmissionRequest(
            user_id=user_id, group_id=group_id, status="pending"
        )
        DBSession().add(admission_request)

        group_admin_gu = (
            GroupUser.query.filter(GroupUser.group_id == group_id)
            .filter(GroupUser.admin.is_(True))
            .first()
        )
        group_admin = (
            User.query.get(group_admin_gu.user_id)
            if group_admin_gu is not None
            else None
        )
        if group_admin is not None:
            DBSession().add(
                UserNotification(
                    user=group_admin,
                    text=f"*@{requesting_user.username}* has requested to join *{group.name}*",
                    url=f"/group/{group_id}",
                )
            )

        try:
            self.verify_and_commit()
        except AccessError as e:
            return self.error(
                "Insufficient permissions: group admission requests cannot be made "
                f"on behalf of others. (Original exception: {e})"
            )

        self.push(action="skyportal/FETCH_USER_PROFILE")
        if group_admin is not None:
            self.flow.push(group_admin.id, "skyportal/FETCH_NOTIFICATIONS", {})
        return self.success(data={"id": admission_request.id})

    @permissions(["Upload data"])
    def patch(self, admission_request_id):
        """
        ---
        description: Update a group admission request's status
        tags:
          - group_admission_requests
          - groups
          - users
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

        try:
            admission_request = GroupAdmissionRequest.get_if_accessible_by(
                admission_request_id,
                self.current_user,
                raise_if_none=True,
                mode="update",
            )
        except AccessError as e:
            return self.error(
                "Insufficient permissions: group admission request status can "
                f"only be changed by group admins. (Original exception: {e})"
            )

        admission_request.status = status
        DBSession().add(
            UserNotification(
                user=admission_request.user,
                text=f"Your admission request to group *{admission_request.group.name}* has been *{status}*",
                url="/groups",
            )
        )

        self.verify_and_commit()
        self.flow.push(admission_request.user_id, "skyportal/FETCH_NOTIFICATIONS", {})
        return self.success()

    @permissions(["Upload data"])
    def delete(self, admission_request_id):
        """
        ---
        description: Delete a group admission request
        tags:
          - group_admission_requests
          - groups
          - users
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
        try:
            admission_request = GroupAdmissionRequest.get_if_accessible_by(
                admission_request_id,
                self.current_user,
                raise_if_none=True,
                mode="delete",
            )
        except AccessError as e:
            return self.error(
                "Insufficient permissions: only the requester can delete a "
                f"group admission request. (Original exception: {e})"
            )
        DBSession().delete(admission_request)
        self.verify_and_commit()
        self.push(action="skyportal/FETCH_USER_PROFILE")
        return self.success()
