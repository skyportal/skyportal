from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token

from ...models import (
    Obj,
    SourceLabel,
)
from ..base import BaseHandler


class SourceLabelsPostBody(BaseModel):
    """Request body for labelling a source."""

    model_config = ConfigDict(extra="forbid")

    groupIds: list[int] = Field(
        description="List of IDs of groups to indicate labelling for"
    )


class SourceLabelsDeleteBody(BaseModel):
    """Request body for deleting source labels."""

    model_config = ConfigDict(extra="forbid")

    groupIds: list[int] = Field(
        description="List of IDs of groups to indicate scanning for"
    )


class SourceLabelsHandler(BaseHandler):
    @auth_or_token
    async def post(self, obj_id: str, *, body: SourceLabelsPostBody = None):
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
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(SourceLabelsPostBody)
        group_ids = body.groupIds

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error("Invalid objId")

            for group_id in group_ids:
                source_label = await session.scalar(
                    SourceLabel.select(session.user_or_token)
                    .where(SourceLabel.obj_id == obj_id)
                    .where(SourceLabel.group_id == group_id)
                    .where(SourceLabel.labeller_id == self.associated_user_object.id)
                )
                if source_label is None:
                    label = SourceLabel(
                        obj_id=obj_id,
                        labeller_id=self.associated_user_object.id,
                        group_id=group_id,
                    )
                    session.add(label)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            return self.success()

    @auth_or_token
    async def delete(self, obj_id: str, *, body: SourceLabelsDeleteBody = None):
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
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(SourceLabelsDeleteBody)
        group_ids = body.groupIds

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error("Invalid objId")

            for group_id in group_ids:
                source_label = await session.scalar(
                    SourceLabel.select(session.user_or_token, mode="delete")
                    .where(SourceLabel.obj_id == obj_id)
                    .where(SourceLabel.group_id == group_id)
                    .where(SourceLabel.labeller_id == self.associated_user_object.id)
                )
                if source_label is not None:
                    await session.delete(source_label)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )

            return self.success()
