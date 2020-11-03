import uuid
import python_http_client.exceptions
from baselayer.app.access import permissions
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    GroupStream,
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

        if data.get("streamIDs") not in [None, "", "null", "None"]:
            try:
                stream_ids = [int(sid) for sid in data["streamIDs"]]
            except ValueError:
                return self.error(
                    "Invalid value provided for `streamIDs`; unable to parse "
                    "all list items to integers."
                )
            streams = DBSession().query(Stream).filter(Stream.id.in_(stream_ids)).all()

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
                              type: array
                              items:
                                $ref: '#/components/schemas/Invitation'
        """
        include_used = self.get_query_argument("includeUsed", False)
        query = Invitation.query
        if not include_used:
            query = query.filter(Invitation.used.is_(False))
        invitations = query.all()
        return_data = [invitation.to_dict() for invitation in invitations]
        for idx, invite_dict in return_data:
            invite_dict["streams"] = invitations[idx].streams
            invite_dict["groups"] = invitations[idx].groups

        return self.success(data=return_data)

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
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if len(groups) != len(group_ids):
                return self.error(
                    "Invalid groupIDs paramter: at least one "
                    "invalid group ID provided."
                )
        else:
            groups = invitation.groups
        if stream_ids is not None:
            streams = Stream.query.filter(Stream.id.in_(stream_ids)).all()
            if len(streams) != len(stream_ids):
                return self.error(
                    "Invalid streamIDs paramter: at least one "
                    "invalid stream ID provided."
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
