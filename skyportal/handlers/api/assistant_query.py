import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token

from ...models import AssistantQuery, AssistantQuerySubscription, GroupUser
from ..base import BaseHandler


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
    context_type: str = Field(
        default="source", description="Resource the query runs on."
    )
    active: bool = Field(default=True, description="Whether the query runs.")
    dry_run: bool = Field(default=False, description="Run but notify no one.")


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
            query = AssistantQuery(
                owner_id=user_id,
                group_id=body.group_id,
                name=body.name,
                description=body.description,
                prompt=body.prompt,
                analysis_service_match=body.analysis_service_match,
                notify_groups=body.notify_groups,
                context_type=body.context_type,
                active=body.active,
                dry_run=body.dry_run,
            )
            session.add(query)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_ASSISTANT_QUERIES")
            return self.success(data={"id": query.id})

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
