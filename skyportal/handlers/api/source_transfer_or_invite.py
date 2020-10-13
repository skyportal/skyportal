import datetime

from baselayer.app.access import permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Obj,
    Source,
)


class SourceTransferOrInviteHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Request group(s) to save source, and optionally unsave from group(s).
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
                      List of group IDs to invite to save specified source.
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
        obj = Obj.get_if_owned_by(obj_id, self.associated_user_object)
        if obj is None:
            return self.error("Invalid objId")
        invite_group_ids = data.get("inviteGroupIds", [])
        unsave_group_ids = data.get("unsaveGroupIds", [])
        if not invite_group_ids and not unsave_group_ids:
            return self.error(
                "Missing required parameter: one of either unsaveGroupIds or inviteGroupIds must be provided"
            )
        for invite_group_id in invite_group_ids:
            source = (
                DBSession()
                .query(Source)
                .filter(Source.obj_id == obj_id)
                .filter(Source.group_id == invite_group_id)
                .first()
            )
            if source is None:
                DBSession().add(
                    Source(
                        obj_id=obj_id,
                        group_id=invite_group_id,
                        active=True,
                        requested=True,
                        saved_by_id=self.associated_user_object.id,
                    )
                )
            else:
                source.active = True
        for unsave_group_id in unsave_group_ids:
            source = (
                DBSession()
                .query(Source)
                .filter(Source.obj_id == obj_id)
                .filter(Source.group_id == unsave_group_id)
                .first()
            )
            if source is None:
                return self.error(
                    "Specified source is not saved to group from which it was to be unsaved."
                )
            source.unsaved_by_id = self.associated_user_object.id
            source.active = False
            source.unsaved_at = datetime.datetime.utcnow()

        DBSession().commit()
        self.push_all(action="skyportal/FETCH_SOURCES")
        self.push_all(
            action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
        )
        self.push_all(action="skyportal/FETCH_RECENT_SOURCES")
        return self.success()
