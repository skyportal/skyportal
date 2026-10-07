from typing import Annotated

from pydantic import Field
from skyportal_py_models.sources import SourceLabelsDeleteBody, SourceLabelsPostBody

from baselayer.app.access import auth_or_token

from ...models import (
    Obj,
    SourceLabel,
)
from ..base import BaseHandler


async def add_source_labels(session, obj_id, group_ids, labeller_id):
    """Label the obj for each given group the labeller has not labelled it in yet.

    The groups are read in one query: a classification deleted from a dozen
    groups asked once per group, and the labels are few enough to compare in
    memory.
    """
    group_ids = list(dict.fromkeys(group_ids))
    if not group_ids:
        return
    labelled = {
        label.group_id
        for label in (
            await session.scalars(
                SourceLabel.select(session.user_or_token)
                .where(SourceLabel.obj_id == obj_id)
                .where(SourceLabel.group_id.in_(group_ids))
                .where(SourceLabel.labeller_id == labeller_id)
            )
        )
        .unique()
        .all()
    }
    for group_id in group_ids:
        if group_id not in labelled:
            session.add(
                SourceLabel(obj_id=obj_id, labeller_id=labeller_id, group_id=group_id)
            )


class SourceLabelsHandler(BaseHandler):
    @auth_or_token
    async def post(
        self,
        obj_id: Annotated[
            str, Field(description="ID of object to indicate source labelling for")
        ],
        *,
        body: SourceLabelsPostBody = None,
    ):
        """
        ---
        summary: Label a source
        description: Note that a source has been labelled.
        tags:
          - sources
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

            await add_source_labels(
                session, obj_id, group_ids, self.associated_user_object.id
            )
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
