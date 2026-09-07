import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import AssistantMessage
from ...utils.assistant import is_enabled, post_to_assistant
from ..base import BaseHandler

_, cfg = load_env()


class AssistantMessagePostBody(BaseModel):
    """Request body for asking the assistant something."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(description="Message body")
    channel: str | None = Field(
        default=None,
        description="Conversation the message belongs to; the default one if unset.",
    )
    context_type: str | None = Field(
        default=None,
        description="Kind of resource the user is looking at, e.g. source or gcn_event.",
    )
    context_id: str | None = Field(
        default=None, description="ID of the resource the user is looking at."
    )


class AssistantChannelQuery(BaseModel):
    """Query parameters naming a conversation."""

    model_config = ConfigDict(extra="forbid")

    channel: str | None = Field(
        default=None,
        description="Conversation name. The one with no name when omitted.",
    )


class AssistantConversationPatchBody(BaseModel):
    """Request body for renaming a conversation."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="New name for the conversation")


def _mine(user_id, channel=None):
    return [
        AssistantMessage.user_id == user_id,
        AssistantMessage.channel == channel
        if channel
        else AssistantMessage.channel.is_(None),
    ]


class AssistantMessageHandler(BaseHandler):
    @auth_or_token
    async def get(self, *, query: AssistantChannelQuery = None):
        """
        ---
        summary: Read a conversation with the assistant
        description: Retrieve the requesting user's messages in one conversation.
        tags:
          - assistant
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        query = self.parse_query(AssistantChannelQuery)

        async with self.AsyncSession() as session:
            messages = await session.scalars(
                AssistantMessage.select(session.user_or_token)
                .where(*_mine(self.associated_user_object.id, query.channel))
                .order_by(AssistantMessage.created_at)
            )
            return self.success(data=[message.to_dict() for message in messages])

    @auth_or_token
    async def post(self, *, body: AssistantMessagePostBody = None):
        """
        ---
        summary: Ask the assistant something
        description: >
            Post a message to the assistant. The answer is written back into the
            same conversation out of band, once the assistant has worked it out.
        tags:
          - assistant
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(AssistantMessagePostBody)

        if not is_enabled(cfg):
            return self.error("No assistant is configured on this instance.")
        if not body.text.strip():
            return self.error("`text` must not be empty")

        async with self.AsyncSession() as session:
            message = AssistantMessage(
                user_id=self.associated_user_object.id,
                text=body.text,
                channel=body.channel or None,
                context_type=body.context_type,
                context_id=body.context_id,
            )
            session.add(message)
            await session.commit()

            message_id = message.id
            posted = await IOLoop.current().run_in_executor(
                None, lambda: post_to_assistant(cfg, message_id)
            )
            if not posted:
                # Nothing else will ever answer it, so do not leave it waiting.
                await session.delete(message)
                await session.commit()
                return self.error("The assistant is not responding right now.")
            return self.success(data={"id": message_id})


class AssistantConversationHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: List the requesting user's conversations with the assistant
        description: >
            Retrieve the names of the user's named conversations. A conversation
            exists as soon as a message carries its name.
        tags:
          - assistant
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        async with self.AsyncSession() as session:
            channels = await session.scalars(
                AssistantMessage.select(
                    session.user_or_token, columns=[AssistantMessage.channel]
                )
                .where(
                    AssistantMessage.user_id == self.associated_user_object.id,
                    AssistantMessage.channel.isnot(None),
                )
                .distinct()
            )
            return self.success(data=sorted(channels.all()))

    @auth_or_token
    async def patch(
        self,
        *,
        query: AssistantChannelQuery = None,
        body: AssistantConversationPatchBody = None,
    ):
        """
        ---
        summary: Rename a conversation with the assistant
        description: Rename a conversation and every message it holds.
        tags:
          - assistant
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        query = self.parse_query(AssistantChannelQuery)
        body = self.parse_body(AssistantConversationPatchBody)
        name = body.name.strip()
        if not query.channel:
            return self.error("`channel` must be provided")
        if not name:
            return self.error("`name` must not be empty")
        if name == query.channel:
            return self.success()

        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            taken = await session.scalar(
                sa.select(AssistantMessage.id).where(*_mine(user_id, name)).limit(1)
            )
            if taken is not None:
                return self.error(f'A conversation named "{name}" already exists')

            renamed = await session.execute(
                sa.update(AssistantMessage)
                .where(*_mine(user_id, query.channel))
                .values(channel=name)
            )
            if renamed.rowcount == 0:
                return self.error("Invalid channel")
            await session.commit()
            return self.success()

    @auth_or_token
    async def delete(self, *, query: AssistantChannelQuery = None):
        """
        ---
        summary: Delete a conversation with the assistant
        description: Delete a named conversation and every message it holds.
        tags:
          - assistant
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        query = self.parse_query(AssistantChannelQuery)
        if not query.channel:
            return self.error("`channel` must be provided")

        async with self.AsyncSession() as session:
            deleted = await session.execute(
                sa.delete(AssistantMessage).where(
                    *_mine(self.associated_user_object.id, query.channel)
                )
            )
            if deleted.rowcount == 0:
                return self.error("Invalid channel")
            await session.commit()
            return self.success()
