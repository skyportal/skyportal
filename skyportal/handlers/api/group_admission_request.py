from baselayer.app.access import auth_or_token, permissions
from baselayer.app.custom_exceptions import AccessError

from ...models import Group, GroupAdmissionRequest, GroupUser, User, UserNotification
from ..base import BaseHandler


class GroupAdmissionRequestHandler(BaseHandler):
    @auth_or_token
    def get(self, admission_request_id=None):
        """
        ---
        single:
          summary: Get a group admission request
          description: Retrieve a group admission request
          tags:
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
          summary: Get all group admission requests
          description: Retrieve all group admission requests
          tags:
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

        with self.Session() as session:
            if admission_request_id is not None:
                admission_request = session.scalars(
                    GroupAdmissionRequest.select(session.user_or_token).where(
                        GroupAdmissionRequest.id == admission_request_id
                    )
                ).first()
                if admission_request is None:
                    return self.error(
                        f"Could not find an admission request with the ID: {admission_request_id}."
                    )
                group = session.scalars(
                    Group.select(session.user_or_token).where(
                        Group.id == admission_request.group_id
                    )
                ).first()
                if group is None:
                    return self.error("Invalid group ID")
                admins = session.scalars(
                    GroupUser.select(session.user_or_token)
                    .where(GroupUser.group_id == admission_request.group_id)
                    .where(GroupUser.admin.is_(True))
                ).all()
                admin_ids = [admin.user.id for admin in admins]

                if (admission_request.user.id != self.current_user.created_by.id) and (
                    self.current_user.created_by.id not in admin_ids
                ):
                    return self.error(
                        "User must be group admin or requester to see request"
                    )

                response_data = {
                    **admission_request.to_dict(),
                    "user": admission_request.user,
                }
                response_data["user"] = admission_request.user
                return self.success(data=response_data)

            q = GroupAdmissionRequest.select(session.user_or_token)
            if group_id is not None:
                q = q.where(GroupAdmissionRequest.group_id == group_id)
            admission_requests = session.scalars(q).unique().all()
            response_data = [
                {**admission_request.to_dict(), "user": admission_request.user}
                for admission_request in admission_requests
            ]
            return self.success(data=response_data)

    @auth_or_token
    def post(self):
        """
        ---
        summary: Create a group admission request
        description: Create a new group admission request
        tags:
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

        with self.Session() as session:
            group = session.scalars(
                Group.select(session.user_or_token).where(Group.id == group_id)
            ).first()
            if group is None or group.single_user_group:
                return self.error("Invalid group ID")
            requesting_user = session.scalars(
                User.select(session.user_or_token).where(User.id == user_id)
            ).first()
            if requesting_user is None:
                return self.error("Invalid user ID")

            if hasattr(self.current_user, "created_by"):
                if requesting_user.id != self.current_user.created_by.id:
                    return self.error(
                        "Group admission request cannot be made on behalf of others."
                    )
            else:
                if requesting_user.id != self.current_user.id:
                    return self.error(
                        "Group admission request cannot be made on behalf of others."
                    )

            # Ensure user is not already a member of target group
            gu = session.scalars(
                GroupUser.select(session.user_or_token)
                .where(GroupUser.group_id == group_id)
                .where(GroupUser.user_id == user_id)
            ).first()
            if gu is not None:
                return self.error(
                    f"User {user_id} is already a member of group {group_id}"
                )
            # Ensure user has sufficient stream access for target group
            if group.streams:
                missing_streams = [
                    stream
                    for stream in group.streams
                    if stream not in requesting_user.accessible_streams
                ]
                if missing_streams:
                    stream_names = ", ".join(missing_streams)
                    return self.error(
                        f"User {user_id} does not have access to the following streams: {stream_names},"
                        f"required to be added to group {group_id}."
                    )
            admission_request = GroupAdmissionRequest(
                user_id=user_id, group_id=group_id, status="pending"
            )
            session.add(admission_request)

            try:
                session.commit()
            except AccessError as e:
                return self.error(
                    "Insufficient permissions: group admission requests cannot be made "
                    f"on behalf of others. (Original exception: {e})"
                )

            self.push(action="skyportal/FETCH_USER_PROFILE")
            return self.success(data={"id": admission_request.id})

    @permissions(["Upload data"])
    def patch(self, admission_request_id):
        """
        ---
        summary: Update a group admission request status
        description: Update a group admission request's status
        tags:
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

        with self.Session() as session:
            admission_request = session.scalars(
                GroupAdmissionRequest.select(
                    session.user_or_token, mode="update"
                ).where(GroupAdmissionRequest.id == admission_request_id)
            ).first()
            if admission_request is None:
                return self.error(
                    "Insufficient permissions: group admission request status can "
                    "only be changed by group admins."
                )

            admission_request.status = status
            session.add(
                UserNotification(
                    user=admission_request.user,
                    text=f"Your admission request to group *{admission_request.group.name}* has been *{status}*",
                    url="/groups",
                )
            )

            session.commit()
            self.flow.push(
                admission_request.user_id, "skyportal/FETCH_NOTIFICATIONS", {}
            )
            return self.success()

    @permissions(["Upload data"])
    def delete(self, admission_request_id):
        """
        ---
        summary: Delete a group admission request
        description: Delete a group admission request
        tags:
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

        with self.Session() as session:
            admission_request = session.scalars(
                GroupAdmissionRequest.select(
                    session.user_or_token, mode="delete"
                ).where(GroupAdmissionRequest.id == admission_request_id)
            ).first()
            if admission_request is None:
                return self.error(
                    "Insufficient permissions: only the requester can delete a "
                    "group admission request."
                )
            session.delete(admission_request)
            session.commit()
            self.push(action="skyportal/FETCH_USER_PROFILE")
            return self.success()
