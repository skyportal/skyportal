from skyportal_py_models.feedback import (
    FeedbackListResponse,
    FeedbackPatchBody,
    FeedbackPostBody,
)
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions

from ...models import Feedback
from ..base import BaseHandler


def message_dict(message):
    return {
        "id": message.id,
        "category": message.category,
        "text": message.text,
        "resolved": message.resolved,
        "created_at": message.created_at,
        "author": {"id": message.author.id, "username": message.author.username},
    }


class FeedbackHandler(BaseHandler):
    @auth_or_token
    async def get(self, feedback_id: int | None = None) -> FeedbackListResponse:
        """
        ---
        summary: Retrieve messages left to the admins
        description: The requesting user's own messages, or every message for system admins.
        tags:
          - system info
        """
        async with self.AsyncSession() as session:
            stmt = Feedback.select(
                session.user_or_token, options=[selectinload(Feedback.author)]
            ).order_by(Feedback.created_at.desc())
            if feedback_id is not None:
                stmt = stmt.where(Feedback.id == feedback_id)
            messages = await session.scalars(stmt)
            return self.success(data={"messages": [message_dict(m) for m in messages]})

    @auth_or_token
    async def post(self, *, body: FeedbackPostBody = None):
        """
        ---
        summary: Leave a message to the admins
        description: Report a bug, request a change or say anything else. System admins are notified.
        tags:
          - system info
        """
        body = self.parse_body(FeedbackPostBody)
        async with self.AsyncSession() as session:
            message = Feedback(
                author_id=self.associated_user_object.id, **body.model_dump()
            )
            session.add(message)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_FEEDBACK")
            return self.success(data={"id": message.id})

    @permissions(["System admin"])
    async def patch(self, feedback_id: int, *, body: FeedbackPatchBody = None):
        """
        ---
        summary: Mark a message left to the admins as handled, or reopen it
        tags:
          - system info
        """
        body = self.parse_body(FeedbackPatchBody)
        async with self.AsyncSession() as session:
            message = await session.scalar(
                Feedback.select(session.user_or_token, mode="update").where(
                    Feedback.id == feedback_id
                )
            )
            if message is None:
                return self.error("Invalid feedback ID")
            message.resolved = body.resolved
            await session.commit()
            self.push_all(action="skyportal/REFRESH_FEEDBACK")
            return self.success()
