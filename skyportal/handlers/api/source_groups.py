import datetime

import sqlalchemy as sa

from baselayer.app.access import permissions
from baselayer.log import make_log
from ..base import BaseHandler
from ...models import (
    Obj,
    Source,
    TNSRobotGroup,
    TNSRobotGroupAutoreporter,
    TNSRobotSubmission,
    GroupUser,
)

log = make_log('api/source_groups')


class SourceGroupsHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Save or request group(s) to save source, and optionally unsave from group(s).
        tags:
          - sources
          - groups
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  objId:
                    type: string
                    description: ID of the object in question.
                  inviteGroupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs to save or invite to save specified source.
                  unsaveGroupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs from which specified source is to be unsaved.
                required:
                  - objId
                  - inviteGroupIds
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        obj_id = data.get("objId")
        if obj_id is None:
            return self.error("Missing required parameter: objId")

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error("Invalid objId")
            save_or_invite_group_ids = data.get("inviteGroupIds", [])
            unsave_group_ids = data.get("unsaveGroupIds", [])
            if not save_or_invite_group_ids and not unsave_group_ids:
                return self.error(
                    "Missing required parameter: one of either unsaveGroupIds or inviteGroupIds must be provided"
                )

            saved_to_group_ids = []
            for save_or_invite_group_id in save_or_invite_group_ids:
                if int(save_or_invite_group_id) in [
                    g.id for g in self.current_user.accessible_groups
                ]:
                    active = True
                    requested = False
                    saved_to_group_ids.append(save_or_invite_group_id)
                else:
                    active = False
                    requested = True
                source = session.scalars(
                    Source.select(session.user_or_token)
                    .where(Source.obj_id == obj_id)
                    .where(Source.group_id == save_or_invite_group_id)
                ).first()
                if source is None:
                    session.add(
                        Source(
                            obj_id=obj_id,
                            group_id=save_or_invite_group_id,
                            active=active,
                            requested=requested,
                            saved_by_id=self.associated_user_object.id,
                        )
                    )
                elif not source.active:
                    source.active = active
                    source.requested = requested
                else:
                    return self.error(
                        f"Source already saved to group w/ ID {save_or_invite_group_id}"
                    )
            for unsave_group_id in unsave_group_ids:
                source = session.scalars(
                    Source.select(session.user_or_token)
                    .where(Source.obj_id == obj_id)
                    .where(Source.group_id == unsave_group_id)
                ).first()
                if source is None:
                    return self.error(
                        "Specified source is not saved to group from which it was to be unsaved."
                    )
                source.unsaved_by_id = self.associated_user_object.id
                source.active = False
                source.unsaved_at = datetime.datetime.utcnow()

            session.commit()

            for group_id in saved_to_group_ids:
                # see if there is a tnsrobot_group set up for autosubmission
                # and if the user has autosubmission set up
                tnsrobot_group_with_autoreporter = session.scalars(
                    TNSRobotGroup.select(session.user_or_token)
                    .join(
                        TNSRobotGroupAutoreporter,
                        TNSRobotGroup.id == TNSRobotGroupAutoreporter.tnsrobot_group_id,
                    )
                    .where(
                        TNSRobotGroup.group_id == group_id,
                        TNSRobotGroup.auto_report,
                        TNSRobotGroupAutoreporter.group_user_id.in_(
                            sa.select(GroupUser.id).where(
                                GroupUser.user_id == self.current_user.id,
                                GroupUser.group_id == group_id,
                            )
                        ),
                    )
                ).first()

                if tnsrobot_group_with_autoreporter is not None:
                    # add a request to submit to TNS for only the first group we save to
                    # that has access to TNSRobot and auto_report is True
                    #
                    # but first, check if there is already an auto-submission request
                    # for this object and tnsrobot that is:
                    # 1. pending
                    # 2. processing
                    # 3. submitted
                    # 4. complete
                    # if so, do not add another request
                    stmt = TNSRobotSubmission.select(session.user_or_token).where(
                        TNSRobotSubmission.obj_id == obj.id,
                        TNSRobotSubmission.tnsrobot_id
                        == tnsrobot_group_with_autoreporter.tnsrobot_id,
                        sa.or_(
                            TNSRobotSubmission.status == "pending",
                            TNSRobotSubmission.status == "processing",
                            TNSRobotSubmission.status.like("submitted%"),
                            TNSRobotSubmission.status.like("complete%"),
                        ),
                    )
                    if self.associated_user_object.is_bot:
                        stmt = stmt.where(
                            TNSRobotGroup.auto_report_allow_bots.is_(True)
                        )
                    existing_submission_request = session.scalars(stmt).first()
                    if existing_submission_request is not None:
                        log(
                            f"Submission request already exists for obj_id {obj.id} and tnsrobot_id {tnsrobot_group_with_autoreporter.tnsrobot_id}"
                        )
                    else:
                        submission_request = TNSRobotSubmission(
                            obj_id=obj.id,
                            tnsrobot_id=tnsrobot_group_with_autoreporter.tnsrobot_id,
                            user_id=self.current_user.id,
                            auto_submission=True,
                        )
                        session.add(submission_request)
                        session.commit()
                        log(
                            f"Added TNSRobotSubmission request for obj_id {obj.id} saved to group {group_id} with tnsrobot_id {tnsrobot_group_with_autoreporter.tnsrobot_id} for user_id {self.current_user.id}"
                        )
                        break

            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            # self.push_all(
            #    action="skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
            # )
            return self.success()

    @permissions(['Upload data'])
    def patch(self, obj_id, *ignored_args):
        """
        ---
        description: Update a Source table row
        tags:
          - sources
          - groups
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  groupID:
                    type: integer
                  active:
                    type: boolean
                  requested:
                    type: boolean
                required:
                  - groupID
                  - active
                  - requested
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        group_id = data.get("groupID")
        if group_id is None:
            return self.error("Missing required parameter: groupID")
        active = data.get("active")
        requested = data.get("requested")

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            source = session.scalars(
                Source.select(session.user_or_token).where(
                    Source.obj_id == obj_id, Source.group_id == group_id
                )
            ).first()
            previously_active = bool(source.active)
            source.active = active
            source.requested = requested
            if active and not previously_active:
                source.saved_by_id = self.associated_user_object.id

            session.commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            self.push_all(
                action="skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
            )
            return self.success()
