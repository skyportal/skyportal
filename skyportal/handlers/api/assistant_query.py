from typing import Literal

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.models import new_async_session

from ...models import (
    AssistantMessage,
    AssistantQuery,
    AssistantQuerySubscription,
    GroupUser,
)
from ...utils.assistant import is_enabled
from ...utils.assistant_schedule import (
    dispatch_query_jobs,
    queue_query_task,
    saved_source,
    task_channel_prefix,
    update_schedule,
)
from ...utils.data_access import accessible_group_ids_async
from ...utils.naive_datetime import utcnow_naive
from ..base import BaseHandler

_, cfg = load_env()


class AssistantQueryPostBody(BaseModel):
    """Request body for creating a shared assistant query."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Short name shown in the query list.")
    group_id: int = Field(
        description="Group the query is tied to; its members subscribe."
    )
    prompt: str = Field(description="Instruction the assistant runs.")
    description: str | None = Field(default=None, description="What the query does.")
    analysis_service_match: str | None = Field(
        default=None,
        description="Substring of an analysis service name; a completed matching "
        "analysis triggers the query.",
    )
    notify_groups: list[int] | None = Field(
        default=None, description="Group ids always notified, besides the subscribers."
    )
    context_type: Literal["source", "gcn_event"] = Field(
        default="source", description="Resource the query runs on."
    )
    source_id: str | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    active: bool = Field(default=True, description="Whether the query runs.")
    dry_run: bool = Field(default=False, description="Run but notify no one.")


class AssistantQueryPatchBody(BaseModel):
    """Fields to update on a shared assistant query; only those sent are changed.
    The group a query is tied to is fixed (make a new query to move it)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    prompt: str | None = None
    analysis_service_match: str | None = None
    notify_groups: list[int] | None = None
    context_type: Literal["source", "gcn_event"] | None = None
    source_id: str | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    active: bool | None = None
    dry_run: bool | None = None


async def _can_notify(user_or_token, session, group_ids):
    if not group_ids:
        return True
    return set(group_ids) <= set(
        await accessible_group_ids_async(user_or_token, session)
    )


async def _validate_scope(session, query, check_source=True):
    if query.context_type == "gcn_event":
        if query.analysis_service_match or query.source_id:
            return "GRB queries use Run now or an interval."
    elif query.context_type == "source":
        if query.interval_minutes and not query.source_id:
            return "An interval requires a source saved to the query's group."
        if (
            check_source
            and query.source_id
            and not await session.scalar(saved_source(query.group_id, query.source_id))
        ):
            return "Select a source saved to the query's group."
    else:
        return "Select a valid query scope."
    return None


def _serialize(query, subscriber_ids, user_id):
    return {
        "id": query.id,
        "name": query.name,
        "description": query.description,
        "prompt": query.prompt,
        "group_id": query.group_id,
        "group_name": query.group.name if query.group else None,
        "owner_id": query.owner_id,
        "analysis_service_match": query.analysis_service_match,
        "notify_groups": query.notify_groups,
        "context_type": query.context_type,
        "source_id": query.source_id,
        "interval_minutes": query.interval_minutes,
        "next_run_at": query.next_run_at,
        "last_run_at": query.last_run_at,
        "last_run_count": query.last_run_count,
        "active": query.active,
        "dry_run": query.dry_run,
        "subscriber_count": len(subscriber_ids),
        "subscribed": user_id in subscriber_ids,
        "is_owner": query.owner_id == user_id,
    }


class AssistantQueryHandler(BaseHandler):
    @auth_or_token
    async def get(self, query_id: int | None = None):
        """
        ---
        single:
          summary: Retrieve one shared assistant query
          tags: [assistant]
          responses:
            200: {content: {application/json: {schema: Success}}}
        multiple:
          summary: List the shared assistant queries visible to the user
          description: Queries tied to a group the requesting user belongs to.
          tags: [assistant]
          responses:
            200: {content: {application/json: {schema: Success}}}
        """
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            stmt = AssistantQuery.select(session.user_or_token).options(
                sa.orm.selectinload(AssistantQuery.group)
            )
            if query_id is not None:
                stmt = stmt.where(AssistantQuery.id == query_id)
            queries = (await session.scalars(stmt)).unique().all()
            if query_id is not None and not queries:
                return self.error("Cannot access this query.", status=403)

            subs = {}
            if queries:
                rows = await session.execute(
                    sa.select(
                        AssistantQuerySubscription.query_id,
                        AssistantQuerySubscription.user_id,
                    ).where(
                        AssistantQuerySubscription.query_id.in_([q.id for q in queries])
                    )
                )
                for qid, uid in rows:
                    subs.setdefault(qid, set()).add(uid)

            data = [_serialize(q, subs.get(q.id, set()), user_id) for q in queries]
            if query_id is not None:
                return self.success(data=data[0])
            return self.success(data=data)

    @auth_or_token
    async def post(self, *, body: AssistantQueryPostBody = None):
        """
        ---
        summary: Create a shared assistant query
        description: The creator must be a member of the query's group.
        tags: [assistant]
        responses:
          200: {content: {application/json: {schema: Success}}}
        """
        body = self.parse_body(AssistantQueryPostBody)
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            member = await session.scalar(
                sa.select(GroupUser.id).where(
                    GroupUser.user_id == user_id, GroupUser.group_id == body.group_id
                )
            )
            if member is None:
                return self.error(
                    "You must be a member of the group to create a query in it.",
                    status=403,
                )
            if not await _can_notify(self.current_user, session, body.notify_groups):
                return self.error(
                    "You can only notify groups you are a member of.", status=403
                )
            query = AssistantQuery(
                owner_id=user_id,
                group_id=body.group_id,
                name=body.name,
                description=body.description,
                prompt=body.prompt,
                analysis_service_match=body.analysis_service_match,
                notify_groups=body.notify_groups,
                context_type=body.context_type,
                source_id=body.source_id,
                interval_minutes=body.interval_minutes,
                active=body.active,
                dry_run=body.dry_run,
            )
            if error := await _validate_scope(session, query):
                return self.error(error)
            update_schedule(query, utcnow_naive())
            session.add(query)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_ASSISTANT_QUERIES")
            return self.success(data={"id": query.id})

    @auth_or_token
    async def patch(self, query_id: int):
        """
        ---
        summary: Update a shared assistant query
        description: Only the query's owner may edit it; only the sent fields change.
        tags: [assistant]
        responses:
          200: {content: {application/json: {schema: Success}}}
        """
        updates = self.parse_body(AssistantQueryPatchBody).model_dump(
            exclude_unset=True
        )
        async with self.AsyncSession() as session:
            query = await session.scalar(
                AssistantQuery.select(session.user_or_token, mode="update")
                .where(AssistantQuery.id == query_id)
                .with_for_update(of=AssistantQuery)
            )
            if query is None:
                return self.error("Cannot update this query.", status=403)
            if not await _can_notify(
                self.current_user, session, updates.get("notify_groups")
            ):
                return self.error(
                    "You can only notify groups you are a member of.", status=403
                )
            reschedule = any(
                updates[key] != getattr(query, key)
                for key in ("active", "interval_minutes")
                if key in updates
            )
            rescoped = any(
                updates[key] != getattr(query, key)
                for key in ("source_id", "context_type", "group_id")
                if key in updates
            )
            for field, value in updates.items():
                setattr(query, field, value)
            if error := await _validate_scope(session, query, check_source=rescoped):
                return self.error(error)
            if reschedule:
                update_schedule(query, utcnow_naive())
            await session.commit()
            self.push_all(action="skyportal/REFRESH_ASSISTANT_QUERIES")
            return self.success()

    @auth_or_token
    async def delete(self, query_id: int):
        """
        ---
        summary: Delete a shared assistant query
        description: Only the query's owner may delete it.
        tags: [assistant]
        responses:
          200: {content: {application/json: {schema: Success}}}
        """
        async with self.AsyncSession() as session:
            query = await session.scalar(
                AssistantQuery.select(session.user_or_token, mode="delete").where(
                    AssistantQuery.id == query_id
                )
            )
            if query is None:
                return self.error("Cannot delete this query.", status=403)
            await session.delete(query)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_ASSISTANT_QUERIES")
            return self.success()


class AssistantQueryRunHandler(BaseHandler):
    @auth_or_token
    async def post(self, query_id: int):
        """
        ---
        summary: Run a saved assistant query now
        description: The owner may run the saved query without changing its schedule.
        tags: [assistant]
        responses:
          200: {content: {application/json: {schema: Success}}}
        """
        async with new_async_session() as session:
            query = await session.scalar(
                sa.select(AssistantQuery)
                .where(
                    AssistantQuery.id == query_id,
                    AssistantQuery.owner_id == self.associated_user_object.id,
                )
                .with_for_update()
            )
            if query is None:
                return self.error("Only the query owner can run it.", status=403)
            if not is_enabled(cfg):
                return self.error("No assistant is configured on this instance.")
            try:
                jobs = await queue_query_task(
                    session, query, utcnow_naive(), cfg["misc.public_group_name"]
                )
            except ValueError as exc:
                return self.error(str(exc))
            await session.commit()
            dispatched = await dispatch_query_jobs(session, cfg, jobs)
        self.push_all(action="skyportal/REFRESH_ASSISTANT_QUERIES")
        return self.success(
            data={"queued": dispatched, "failed": len(jobs) - dispatched}
        )

    @auth_or_token
    async def get(self, query_id: int):
        """
        ---
        summary: List recent interval and manual runs of an assistant query
        description: Results, including previews, are visible to the query owner.
        tags: [assistant]
        responses:
          200: {content: {application/json: {schema: Success}}}
        """
        async with self.AsyncSession() as session:
            query = await session.scalar(
                AssistantQuery.select(session.user_or_token).where(
                    AssistantQuery.id == query_id,
                    AssistantQuery.owner_id == self.associated_user_object.id,
                )
            )
            if query is None:
                return self.error("Only the query owner can view runs.", status=403)
            reply = sa.orm.aliased(AssistantMessage)
            attempt = sa.orm.aliased(AssistantMessage)
            next_attempt_id = (
                sa.select(sa.func.min(attempt.id))
                .where(
                    attempt.channel == AssistantMessage.channel,
                    attempt.id > AssistantMessage.id,
                    attempt.system.is_(False),
                )
                .correlate(AssistantMessage)
                .scalar_subquery()
            )
            reply_text = (
                sa.select(reply.text)
                .where(
                    reply.channel == AssistantMessage.channel,
                    reply.user_id == AssistantMessage.user_id,
                    reply.system.is_(True),
                    reply.id > AssistantMessage.id,
                    (next_attempt_id.is_(None) | (reply.id < next_attempt_id)),
                )
                .order_by(reply.id.desc())
                .limit(1)
                .scalar_subquery()
            )
            runs = await session.execute(
                sa.select(
                    AssistantMessage.id,
                    AssistantMessage.context_id,
                    AssistantMessage.created_at,
                    AssistantMessage.run_status,
                    reply_text.label("result"),
                )
                .where(
                    AssistantMessage.channel.startswith(task_channel_prefix(query.id)),
                    AssistantMessage.run_status.is_not(None),
                    AssistantMessage.system.is_(False),
                )
                .order_by(AssistantMessage.id.desc())
                .limit(10)
            )
            return self.success(data=[dict(run._mapping) for run in runs])


class AssistantQuerySubscriptionHandler(BaseHandler):
    @auth_or_token
    async def post(self, query_id: int):
        """
        ---
        summary: Subscribe the requesting user to a query's notifications
        description: Allowed only for a query the user can see (in its group).
        tags: [assistant]
        responses:
          200: {content: {application/json: {schema: Success}}}
        """
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            query = await session.scalar(
                AssistantQuery.select(session.user_or_token).where(
                    AssistantQuery.id == query_id
                )
            )
            if query is None:
                return self.error("Cannot access this query.", status=403)
            existing = await session.scalar(
                sa.select(AssistantQuerySubscription).where(
                    AssistantQuerySubscription.query_id == query_id,
                    AssistantQuerySubscription.user_id == user_id,
                )
            )
            if existing is None:
                session.add(
                    AssistantQuerySubscription(query_id=query_id, user_id=user_id)
                )
                await session.commit()
            self.push_all(action="skyportal/REFRESH_ASSISTANT_QUERIES")
            return self.success()

    @auth_or_token
    async def delete(self, query_id: int):
        """
        ---
        summary: Unsubscribe the requesting user from a query's notifications
        tags: [assistant]
        responses:
          200: {content: {application/json: {schema: Success}}}
        """
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            existing = await session.scalar(
                sa.select(AssistantQuerySubscription).where(
                    AssistantQuerySubscription.query_id == query_id,
                    AssistantQuerySubscription.user_id == user_id,
                )
            )
            if existing is not None:
                await session.delete(existing)
                await session.commit()
            self.push_all(action="skyportal/REFRESH_ASSISTANT_QUERIES")
            return self.success()
