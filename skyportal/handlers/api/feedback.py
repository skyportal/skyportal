from skyportal_py_models.feedback import (
    FeedbackListResponse,
    FeedbackPatchBody,
    FeedbackPostBody,
    FeedbackReplyPostBody,
)
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions

from ...models import Feedback, FeedbackReply, User
from ...utils.gitlog import normalize_pr_url, running_pr_urls, tracked_pr_url_bases
from ..base import BaseHandler


def user_dict(author):
    return {
        "id": author.id,
        "username": author.username,
        "first_name": author.first_name,
        "last_name": author.last_name,
        "gravatar_url": author.gravatar_url,
    }


def message_dict(message, deployed):
    return {
        "id": message.id,
        "category": message.category,
        "text": message.text,
        "resolved": message.resolved,
        "created_at": message.created_at,
        "author": user_dict(message.author),
        "assignee": message.assignee and user_dict(message.assignee),
        "pull_requests": [
            {"url": url, "deployed": url in deployed} for url in message.pr_urls
        ],
        "deployed_at": message.deployed_at,
        "replies": [
            {
                "id": reply.id,
                "text": reply.text,
                "created_at": reply.created_at,
                "author": user_dict(reply.author),
            }
            for reply in message.replies
        ],
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
                session.user_or_token,
                options=[
                    selectinload(Feedback.author),
                    selectinload(Feedback.assignee),
                    selectinload(Feedback.replies).selectinload(FeedbackReply.author),
                ],
            ).order_by(Feedback.created_at.desc(), Feedback.id.desc())
            if feedback_id is not None:
                stmt = stmt.where(Feedback.id == feedback_id)
            messages = await session.scalars(stmt)
            deployed = running_pr_urls()
            return self.success(
                data={"messages": [message_dict(m, deployed) for m in messages]}
            )

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
        summary: Mark a message left to the admins as handled, reopen it, assign it, or link its fixes
        description: Once all the linked pull requests are deployed, the message is resolved and its author notified.
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
            if body.resolved is not None:
                message.resolved = body.resolved
            if "assignee_id" in body.model_fields_set:
                if body.assignee_id is not None and not await session.get(
                    User, body.assignee_id
                ):
                    return self.error("Invalid assignee ID")
                message.assignee_id = body.assignee_id
            if body.pr_urls is not None:
                bases = tracked_pr_url_bases(running_pr_urls())
                if body.pr_urls and not bases:
                    return self.error(
                        "This instance has no git history, so pull requests cannot be tracked"
                    )
                pr_urls = []
                for url in body.pr_urls:
                    normalized = normalize_pr_url(url)
                    if normalized is None:
                        return self.error(f"Not a GitHub pull request URL: {url}")
                    if not normalized.startswith(tuple(bases)):
                        repos = sorted(
                            base.removeprefix("https://github.com/").removesuffix(
                                "/pull/"
                            )
                            for base in bases
                        )
                        return self.error(
                            f"Only pull requests of {', '.join(repos)} can be tracked"
                        )
                    if normalized not in pr_urls:
                        pr_urls.append(normalized)
                message.pr_urls = pr_urls
            await session.commit()
            self.push_all(action="skyportal/REFRESH_FEEDBACK")
            return self.success()


class FeedbackReplyHandler(BaseHandler):
    @auth_or_token
    async def post(self, feedback_id: int, *, body: FeedbackReplyPostBody = None):
        """
        ---
        summary: Reply to a message left to the admins
        description: Admins can reply to any message, users to their own. The other side is notified.
        tags:
          - system info
        """
        body = self.parse_body(FeedbackReplyPostBody)
        async with self.AsyncSession() as session:
            message = await session.scalar(
                Feedback.select(session.user_or_token).where(Feedback.id == feedback_id)
            )
            if message is None:
                return self.error("Invalid feedback ID")
            reply = FeedbackReply(
                feedback_id=feedback_id,
                author_id=self.associated_user_object.id,
                text=body.text,
            )
            session.add(reply)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_FEEDBACK")
            return self.success(data={"id": reply.id})
