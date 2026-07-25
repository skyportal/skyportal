import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import permissions
from baselayer.log import make_log

from ...models import Obj, Source
from ...utils.asynchronous import run_async
from ...utils.data_access import auto_source_publishing_async
from ...utils.naive_datetime import utcnow_naive
from ..base import BaseHandler

log = make_log("api/source_groups")


class SourceGroupsPostBody(BaseModel):
    """Request body for saving/unsaving a source to/from groups."""

    model_config = ConfigDict(extra="forbid")

    objId: str = Field(description="ID of the object in question.")
    inviteGroupIds: list[int] = Field(
        default_factory=list,
        description="List of group IDs to save or invite to save specified source.",
    )
    unsaveGroupIds: list[int] = Field(
        default_factory=list,
        description="List of group IDs from which specified source is to be unsaved.",
    )


class SourceGroupsPatchBody(BaseModel):
    """Request body for updating a Source table row."""

    model_config = ConfigDict(extra="forbid")

    groupID: int = Field(description="ID of the group whose Source row to update.")
    active: bool = Field(description="Whether the source is saved to the group.")
    requested: bool = Field(
        description="Whether the source is requested to be saved to the group."
    )


class SourceGroupsHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self, *, body: SourceGroupsPostBody = None):
        """
        ---
        summary: Save or unsave sources to/from groups
        description: Save or request group(s) to save source, and optionally unsave from group(s).
        tags:
          - sources
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(SourceGroupsPostBody)
        obj_id = body.objId
        # pydantic coerces string ids to int here — clients (and old code
        # paths) sometimes send these as strings, which then crashes the
        # Source.group_id comparison against an integer column.
        save_or_invite_group_ids = body.inviteGroupIds
        unsave_group_ids = body.unsaveGroupIds
        if not save_or_invite_group_ids and not unsave_group_ids:
            return self.error(
                "Missing required parameter: one of either unsaveGroupIds or inviteGroupIds must be provided"
            )

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if not obj:
                return self.error(f"Obj {obj_id} not found", status=404)

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
                source = await session.scalar(
                    Source.select(session.user_or_token)
                    .where(Source.obj_id == obj_id)
                    .where(Source.group_id == save_or_invite_group_id)
                )
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
                source = await session.scalar(
                    Source.select(session.user_or_token)
                    .where(Source.obj_id == obj_id)
                    .where(Source.group_id == unsave_group_id)
                )
                if source is None:
                    return self.error(
                        "Specified source is not saved to group from which it was to be unsaved."
                    )
                source.unsaved_by_id = self.associated_user_object.id
                source.active = False
                source.unsaved_at = utcnow_naive()

            if len(unsave_group_ids) > 0:
                from .public_pages.public_source_page import delete_auto_published_page

                groups_result = await session.scalars(
                    sa.select(Source.group_id).where(
                        Source.obj_id == obj_id,
                        Source.active.is_(True),
                        ~Source.group_id.in_(unsave_group_ids),
                    )
                )
                all_saved_groups = groups_result.all()
                run_async(
                    delete_auto_published_page,
                    source_id=obj_id,
                    remaining_group_ids=all_saved_groups,
                )
            await session.commit()

            # Shared mutable list to ensure publish_to target is triggered only once across all groups if needed
            publish_to = ["TNS", "Hermes", "Public page"]
            for group_id in saved_to_group_ids:
                await auto_source_publishing_async(
                    session=session,
                    saver=self.associated_user_object,
                    obj=obj,
                    group_id=group_id,
                    publish_to=publish_to,
                )

            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            return self.success()

    @permissions(["Upload data"])
    async def patch(
        self, obj_id: str, *ignored_args, body: SourceGroupsPatchBody = None
    ):
        """
        ---
        summary: Update a Source table row
        description: Update a Source table row
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(SourceGroupsPatchBody)
        group_id = body.groupID
        active = body.active
        requested = body.requested

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            source = await session.scalar(
                Source.select(session.user_or_token).where(
                    Source.obj_id == obj_id, Source.group_id == group_id
                )
            )
            previously_active = bool(source.active)
            source.active = active
            source.requested = requested
            if active and not previously_active:
                source.saved_by_id = self.associated_user_object.id

            await session.commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            self.push_all(
                action="skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
            )
            return self.success()
