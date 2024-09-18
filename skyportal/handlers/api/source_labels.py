from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    Obj,
    SourceLabel,
)


class SourceLabelsHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_id):
        """
        ---
        summary: Label a source
        description: Note that a source has been labelled.
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: |
              ID of object to indicate source labelling for
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  groupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups to indicate labelling for
                required:
                  - groupIds
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()
        group_ids = data.get("groupIds")
        if group_ids is None:
            return self.error("Missing required parameter: `groupIds`")

        try:
            group_ids = [int(gid) for gid in data["groupIds"]]
        except ValueError:
            return self.error(
                "Invalid value provided for `groupIDs`; unable to parse "
                "all list items to integers."
            )

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error("Invalid objId")

            for group_id in group_ids:
                source_label = session.scalars(
                    SourceLabel.select(session.user_or_token)
                    .where(SourceLabel.obj_id == obj_id)
                    .where(SourceLabel.group_id == group_id)
                    .where(SourceLabel.labeller_id == self.associated_user_object.id)
                ).first()
                if source_label is None:
                    label = SourceLabel(
                        obj_id=obj_id,
                        labeller_id=self.associated_user_object.id,
                        group_id=group_id,
                    )
                    session.add(label)
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            return self.success()

    @auth_or_token
    def delete(self, obj_id):
        """
        ---
        summary: Delete source labels
        description: Delete source labels
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  groupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups to indicate scanning for
                required:
                  - groupIds
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()
        group_ids = data.get("groupIds")
        if group_ids is None:
            return self.error("Missing required parameter: `groupIds`")

        try:
            group_ids = [int(gid) for gid in data["groupIds"]]
        except ValueError:
            return self.error(
                "Invalid value provided for `groupIDs`; unable to parse "
                "all list items to integers."
            )

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error("Invalid objId")

            for group_id in group_ids:
                source_label = session.scalars(
                    SourceLabel.select(session.user_or_token, mode="delete")
                    .where(SourceLabel.obj_id == obj_id)
                    .where(SourceLabel.group_id == group_id)
                    .where(SourceLabel.labeller_id == self.associated_user_object.id)
                ).first()
                if source_label is not None:
                    session.delete(source_label)
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )

            return self.success()
