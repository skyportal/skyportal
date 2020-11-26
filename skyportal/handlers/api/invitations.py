import uuid
import python_http_client.exceptions
from baselayer.app.access import permissions
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
)

_, cfg = load_env()


class InvitationHandler(BaseHandler):
    @permissions(["Manage users"])
    def post(self):
        """
        ---
        description: Invite a new user
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  userEmail:
                    type: string
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
                      status for respective specified group(s).
                required:
                  - userEmail
                  - groupIDs
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        if not cfg["invitations.enabled"]:
            return self.error("Invitations are not enabled in current deployment.")
        data = self.get_json()

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
        groups = DBSession().query(Group).filter(Group.id.in_(group_ids)).all()
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
            streams = DBSession().query(Stream).filter(Stream.id.in_(stream_ids)).all()
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
                DBSession()
                .query(Stream)
                .join(GroupStream)
                .filter(GroupStream.group_id.in_(group_ids))
                .all()
            )
        group_admin = data.get("groupAdmin", [False] * len(groups))
        admin_for_groups = [
            el in [True, "True", "true", "t", "T"] for el in group_admin
        ]
        if len(admin_for_groups) != len(groups):
            return self.error("groupAdmin and groupIDs must be the same length")

        invite_token = str(uuid.uuid4())
        DBSession().add(
            Invitation(
                token=invite_token,
                groups=groups,
                admin_for_groups=admin_for_groups,
                streams=streams,
                user_email=user_email,
                invited_by=self.associated_user_object,
            )
        )
        try:
            DBSession().commit()
        except python_http_client.exceptions.UnauthorizedError:
            return self.error(
                "Twilio Sendgrid authorization error. Please ensure "
                "valid Sendgrid API key is set in server environment as "
                "per their setup docs."
            )
        return self.success()

    @permissions(["Manage users"])
    def get(self):
        """
        ---
        description: Retrieve invitations
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

        query = Invitation.query
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
        return self.success(data=info)

    @permissions(["Manage users"])
    def patch(self, invitation_id):
        """
        ---
        description: Update a pending invitation
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
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        invitation = Invitation.query.get(invitation_id)
        group_ids = data.get("groupIDs")
        stream_ids = data.get("streamIDs")
        if group_ids is None and stream_ids is None:
            return self.error(
                "At least one of either groupIDs or streamIDs are requried."
            )
        if group_ids is not None:
            group_ids = [int(gid) for gid in group_ids]
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if set(group_ids).difference({g.id for g in groups}):
                return self.error(
                    "The following groupIDs elements are invalid: "
                    f"{set(group_ids).difference({g.id for g in groups})}"
                )
        else:
            groups = invitation.groups
        if stream_ids is not None:
            stream_ids = [int(sid) for sid in stream_ids]
            streams = Stream.query.filter(Stream.id.in_(stream_ids)).all()
            if set(stream_ids).difference({s.id for s in streams}):
                return self.error(
                    "The following streamIDs elements are invalid: "
                    f"{set(stream_ids).difference({s.id for s in streams})}"
                )
        else:
            streams = invitation.streams

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

        DBSession().commit()
        return self.success()

    @permissions(["Manage users"])
    def delete(self, invitation_id):
        """
        ---
        description: Delete an invitation
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
        invitation = DBSession().query(Invitation).get(invitation_id)
        if invitation is None:
            return self.error("Invalid invitation ID")
        DBSession().delete(invitation)
        DBSession().commit()
        return self.success()
