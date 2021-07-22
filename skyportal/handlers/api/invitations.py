import uuid
import smtplib
import python_http_client.exceptions
import arrow
from baselayer.app.access import permissions, AccessError
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    GroupStream,
    GroupInvitation,
    StreamInvitation,
    UserInvitation,
    User,
    Invitation,
    Stream,
    Role,
)

_, cfg = load_env()


class InvitationHandler(BaseHandler):
    @permissions(["Manage users"])
    def post(self):
        """
        ---
        description: Invite a new user
        tags:
          - invitations
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  userEmail:
                    type: string
                  role:
                    type: string
                    description: |
                      The role the new user will have in the system.
                      If provided, must be one of either "Full user" or "View only".
                      Defaults to "Full user".
                  streamIDs:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of streams invited user will be given access to. If
                      not provided, user will be granted access to all streams associated
                      with the groups specified by `groupIDs`.
                  groupIDs:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups invited user will be added to. If `streamIDs`
                      is not provided, invited user will be given accesss to all streams
                      associated with the groups specified by this field.
                  groupAdmin:
                    type: array
                    items:
                      type: boolean
                    description: |
                      List of booleans indicating whether user should be granted admin
                      status for respective specified group(s). Defaults to all false.
                  canSave:
                    type: array
                    items:
                      type: boolean
                    description: |
                      List of booleans indicating whether user should be able to save
                      sources to respective specified group(s). Defaults to all true.
                  userExpirationDate:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01). Set a user's expiration
                      date, after which the user's account will be deactivated and will be unable
                      to access the application.
                required:
                  - userEmail
                  - groupIDs
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
                              type: string
                              description: New invitation ID
        """
        if not cfg["invitations.enabled"]:
            return self.error("Invitations are not enabled in current deployment.")
        data = self.get_json()

        role_id = data.get("role", "Full user")
        if role_id not in ["Full user", "View only"]:
            return self.error(
                f"Unsupported value provided for parameter `role`: {role_id}. "
                "Must be one of either 'Full user' or 'View only'."
            )
        role = Role.query.get(role_id)
        if data.get("userEmail") in [None, "", "None", "null"]:
            return self.error("Missing required parameter `userEmail`")
        user_email = data["userEmail"].strip()

        if data.get("groupIDs") is None:
            return self.error("Missing required parameter `groupIDs`")
        try:
            group_ids = [int(gid) for gid in data["groupIDs"]]
        except ValueError:
            return self.error(
                "Invalid value provided for `groupIDs`; unable to parse "
                "all list items to integers."
            )
        groups = Group.get_if_accessible_by(group_ids, self.current_user)
        if set(group_ids).difference({g.id for g in groups}):
            return self.error(
                "The following groupIDs elements are invalid: "
                f"{set(group_ids).difference({g.id for g in groups})}"
            )

        if data.get("streamIDs") not in [None, "", "null", "None"]:
            try:
                stream_ids = [int(sid) for sid in data["streamIDs"]]
            except ValueError:
                return self.error(
                    "Invalid value provided for `streamIDs`; unable to parse "
                    "all list items to integers."
                )

            streams = Stream.get_if_accessible_by(stream_ids, self.current_user)
            if set(stream_ids).difference({s.id for s in streams}):
                return self.error(
                    "The following streamIDs elements are invalid: "
                    f"{set(stream_ids).difference({s.id for s in streams})}"
                )

            # Ensure specified groups are covered by specified streams
            if not all(
                [stream in streams for group in groups for stream in group.streams]
            ):
                return self.error(
                    "You have attempted to invite user to group(s) that "
                    "access streams that were not specified in provided "
                    "stream IDs list. Please try again."
                )
        else:
            streams = (
                Stream.query_records_accessible_by(self.current_user, mode="read")
                .join(GroupStream)
                .filter(GroupStream.group_id.in_(group_ids))
                .all()
            )
        admin_for_groups = data.get("groupAdmin", [False] * len(groups))
        if not all([isinstance(admin, bool) for admin in admin_for_groups]):
            return self.error(
                "Invalid value provided for `groupAdmin` parameter: "
                "all elements must be booleans"
            )
        can_save = data.get("canSave", [True] * len(groups))
        if not all([isinstance(can_save_el, bool) for can_save_el in can_save]):
            return self.error(
                "Invalid value provided for `canSave` parameter: "
                "all elements must be booleans"
            )
        user_expiration_date = data.get("userExpirationDate")
        if user_expiration_date is not None:
            try:
                user_expiration_date = arrow.get(user_expiration_date).datetime
            except arrow.parser.ParserError:
                return self.error("Unable to parse `userExpirationDate` parameter.")

        if len(admin_for_groups) != len(groups):
            return self.error("groupAdmin and groupIDs must be the same length")

        invite_token = str(uuid.uuid4())
        invitation = Invitation(
            token=invite_token,
            groups=groups,
            admin_for_groups=admin_for_groups,
            can_save_to_groups=can_save,
            streams=streams,
            user_email=user_email,
            role=role,
            invited_by=self.associated_user_object,
            user_expiration_date=user_expiration_date,
        )
        DBSession().add(invitation)
        try:
            self.verify_and_commit()
        except python_http_client.exceptions.UnauthorizedError:
            return self.error(
                "Twilio Sendgrid authorization error. Please ensure "
                "valid Sendgrid API key is set in server environment as "
                "per their setup docs."
            )
        except smtplib.SMTPAuthenticationError:
            return self.error(
                "SMTP authentication failed. Please ensure valid "
                "credentials are specified in the config file."
            )
        return self.success(data={"id": invitation.id})

    @permissions(["Manage users"])
    def get(self):
        """
        ---
        description: Retrieve invitations
        tags:
          - invitations
        parameters:
          - in: query
            name: includeUsed
            schema:
              type: boolean
            description: |
              Bool indicating whether to include used invitations.
              Defaults to false.
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of candidates to return per paginated request. Defaults to 25
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1
          - in: query
            name: email
            nullable: true
            schema:
              type: string
            description: Get invitations whose email contains this string.
          - in: query
            name: group
            nullable: true
            schema:
              type: string
            description: Get invitations part of the group with name given by this parameter.
          - in: query
            name: stream
            nullable: true
            schema:
              type: string
            description: Get invitations with access to the stream with name given by this parameter.
          - in: query
            name: invitedBy
            nullable: true
            schema:
              type: string
            description: Get invitations invited by users whose username contains this string.
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
                              invitations:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Invitation'
                              totalMatches:
                                type: integer
        """
        include_used = self.get_query_argument("includeUsed", False)
        email_address = self.get_query_argument("email", None)
        group = self.get_query_argument("group", None)
        stream = self.get_query_argument("stream", None)
        invited_by = self.get_query_argument("invitedBy", None)
        page_number = self.get_query_argument("pageNumber", None) or 1
        n_per_page = self.get_query_argument("numPerPage", None) or 25
        try:
            page_number = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            n_per_page = int(n_per_page)
        except ValueError:
            return self.error("Invalid numPerPage value.")

        query = Invitation.query_records_accessible_by(self.current_user, mode="read")
        if not include_used:
            query = query.filter(Invitation.used.is_(False))
        if email_address is not None:
            query = query.filter(Invitation.user_email.contains(email_address))
        if group is not None:
            query = query.join(GroupInvitation).join(Group).filter(Group.name == group)
        if stream is not None:
            query = (
                query.join(StreamInvitation).join(Stream).filter(Stream.name == stream)
            )
        if invited_by is not None:
            query = (
                query.join(UserInvitation)
                .join(User)
                .filter(User.username.contains(invited_by))
            )

        total_matches = query.count()
        query = query.limit(n_per_page).offset((page_number - 1) * n_per_page)
        invitations = query.all()
        info = {}
        return_data = [invitation.to_dict() for invitation in invitations]
        for idx, invite_dict in enumerate(return_data):
            invite_dict["streams"] = invitations[idx].streams
            invite_dict["groups"] = invitations[idx].groups
            invite_dict["invited_by"] = invitations[idx].invited_by

        info["invitations"] = return_data
        info["totalMatches"] = int(total_matches)
        self.verify_and_commit()
        return self.success(data=info)

    @permissions(["Manage users"])
    def patch(self, invitation_id):
        """
        ---
        description: Update a pending invitation
        tags:
          - invitations
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  groupIDs:
                    type: array
                    items:
                      type: integer
                  streamIDs:
                    type: array
                    items:
                      type: integer
                  role:
                    type: string
                  userExpirationDate:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01). Set a user's expiration
                      date, after which the user's account will be deactivated and will be unable
                      to access the application.
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        try:
            invitation = Invitation.get_if_accessible_by(
                invitation_id, self.current_user, raise_if_none=True, mode="update"
            )
        except AccessError as e:
            return self.error(
                "Insufficient permissions: Only the invitor may update an invitation. "
                f"(Original exception: {e})"
            )

        group_ids = data.get("groupIDs")
        stream_ids = data.get("streamIDs")
        role_id = data.get("role")
        user_expiration_date = data.get("userExpirationDate")
        if (
            group_ids is None
            and stream_ids is None
            and role_id is None
            and user_expiration_date is None
        ):
            return self.error(
                "At least one of `groupIDs`, `streamIDs`, `role`, or `userExpirationDate` is required."
            )
        if group_ids is not None:
            group_ids = [int(gid) for gid in group_ids]
            groups = Group.get_if_accessible_by(group_ids, self.current_user)
            if set(group_ids).difference({g.id for g in groups}):
                return self.error(
                    "The following groupIDs elements are invalid: "
                    f"{set(group_ids).difference({g.id for g in groups})}"
                )
        else:
            groups = (
                Group.query_records_accessible_by(self.current_user, mode="read")
                .join(GroupInvitation)
                .filter(GroupInvitation.invitation_id == invitation.id)
                .all()
            )
        if stream_ids is not None:
            stream_ids = [int(sid) for sid in stream_ids]
            streams = Stream.get_if_accessible_by(stream_ids, self.current_user)
            if set(stream_ids).difference({s.id for s in streams}):
                return self.error(
                    "The following streamIDs elements are invalid: "
                    f"{set(stream_ids).difference({s.id for s in streams})}"
                )
        else:
            streams = (
                Stream.query_records_accessible_by(self.current_user, mode="read")
                .join(StreamInvitation)
                .filter(StreamInvitation.invitation_id == invitation.id)
                .all()
            )

        if user_expiration_date is not None:
            try:
                user_expiration_date = arrow.get(user_expiration_date).datetime
            except arrow.parser.ParserError:
                return self.error("Unable to parse `userExpirationDate` parameter.")

        # Ensure specified groups are covered by specified streams
        if not all([stream in streams for group in groups for stream in group.streams]):
            return self.error(
                "You have attempted to invite user to group(s) that "
                "access streams that were not specified in provided "
                "stream IDs list. Please try again."
            )
        if group_ids is not None:
            invitation.groups = groups
        if stream_ids is not None:
            invitation.streams = streams
        if role_id is not None:
            invitation.role_id = role_id
        if user_expiration_date is not None:
            invitation.user_expiration_date = user_expiration_date

        self.verify_and_commit()
        return self.success()

    @permissions(["Manage users"])
    def delete(self, invitation_id):
        """
        ---
        description: Delete an invitation
        tags:
          - invitations
        parameters:
          - in: path
            name: invitation_id
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
            invitation = Invitation.get_if_accessible_by(
                invitation_id, self.current_user, raise_if_none=True, mode="delete"
            )
        except AccessError as e:
            return self.error(
                "Insufficient permissions: Only the invitor may delete an invitation. "
                f"(Original exception: {e})"
            )
        DBSession().delete(invitation)
        self.verify_and_commit()
        return self.success()
