import sqlalchemy as sa
from skyportal_py_models.discussions import (
    CommentThreadListResponse,
    DiscussionListResponse,
    DiscussionMemberListResponse,
    DiscussionMembershipPatchBody,
    DiscussionMembersPostBody,
    DiscussionMessageListQuery,
    DiscussionMessageListResponse,
    DiscussionMessagePostBody,
    DiscussionPatchBody,
    DiscussionPostBody,
    DiscussionPostResponse,
)
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token

from ...models import (
    Comment,
    CommentOnEarthquake,
    CommentOnGCN,
    CommentOnShift,
    CommentOnSpectrum,
    Discussion,
    DiscussionMember,
    DiscussionMessage,
    EarthquakeEvent,
    GcnEvent,
    Group,
    GroupUser,
    Shift,
    User,
)
from ...utils.naive_datetime import utcnow_naive
from ..base import BaseHandler

MAX_COMMENT_THREADS = 200


def user_dict(user):
    return {
        field: getattr(user, field)
        for field in (
            "id",
            "username",
            "first_name",
            "last_name",
            "gravatar_url",
            "is_bot",
        )
    }


def message_dict(message):
    return {
        "id": message.id,
        "discussion_id": message.discussion_id,
        "text": message.text,
        "created_at": message.created_at,
        "modified": message.modified,
        "author": user_dict(message.author),
    }


async def participant_ids(session, discussion):
    if discussion.group_id is None:
        stmt = sa.select(DiscussionMember.user_id).where(
            DiscussionMember.discussion_id == discussion.id
        )
    else:
        stmt = sa.select(GroupUser.user_id).where(
            GroupUser.group_id == discussion.group_id
        )
    return set((await session.scalars(stmt)).all())


async def own_membership(session, discussion, user_id):
    member = await session.scalar(
        sa.select(DiscussionMember).where(
            DiscussionMember.discussion_id == discussion.id,
            DiscussionMember.user_id == user_id,
        )
    )
    if member is None and discussion.group_id is not None:
        member = DiscussionMember(discussion_id=discussion.id, user_id=user_id)
        session.add(member)
    return member


class DiscussionBaseHandler(BaseHandler):
    async def get_discussion(self, session, discussion_id, mode="read"):
        discussion = await session.scalar(
            Discussion.select(session.user_or_token, mode=mode).where(
                Discussion.id == discussion_id
            )
        )
        if discussion is None:
            self.error("Invalid discussion ID")
        return discussion

    def push_refresh(self, user_ids, discussion_id):
        for user_id in user_ids:
            self.flow.push(
                user_id,
                "skyportal/REFRESH_DISCUSSIONS",
                {"discussion_id": discussion_id},
            )


class DiscussionHandler(DiscussionBaseHandler):
    @auth_or_token
    async def get(self, discussion_id: int | None = None) -> DiscussionListResponse:
        """
        ---
        summary: Retrieve your discussions
        description: >
            The direct messages and group discussions the requesting user takes
            part in, latest activity first, with their unread message count.
        tags:
          - discussions
        """
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            stmt = Discussion.select(
                session.user_or_token,
                options=[
                    selectinload(Discussion.group),
                    selectinload(Discussion.members).selectinload(
                        DiscussionMember.user
                    ),
                ],
            )
            if discussion_id is not None:
                stmt = stmt.where(Discussion.id == discussion_id)
            discussions = (await session.scalars(stmt)).unique().all()
            if discussion_id is not None and not discussions:
                return self.error("Invalid discussion ID")
            ids = [d.id for d in discussions]

            last_messages = {
                message.discussion_id: message
                for message in await session.scalars(
                    sa.select(DiscussionMessage)
                    .options(selectinload(DiscussionMessage.author))
                    .where(DiscussionMessage.discussion_id.in_(ids))
                    .order_by(
                        DiscussionMessage.discussion_id,
                        DiscussionMessage.created_at.desc(),
                    )
                    .distinct(DiscussionMessage.discussion_id)
                )
            }

            own = sa.and_(
                DiscussionMember.discussion_id == DiscussionMessage.discussion_id,
                DiscussionMember.user_id == user_id,
            )
            unread = dict(
                (
                    await session.execute(
                        sa.select(DiscussionMessage.discussion_id, sa.func.count())
                        .outerjoin(DiscussionMember, own)
                        .where(
                            DiscussionMessage.discussion_id.in_(ids),
                            DiscussionMessage.author_id != user_id,
                            sa.or_(
                                DiscussionMember.last_read_at.is_(None),
                                DiscussionMessage.created_at
                                > DiscussionMember.last_read_at,
                            ),
                        )
                        .group_by(DiscussionMessage.discussion_id)
                    )
                ).all()
            )

            group_sizes = dict(
                (
                    await session.execute(
                        sa.select(GroupUser.group_id, sa.func.count())
                        .where(
                            GroupUser.group_id.in_(
                                {d.group_id for d in discussions if d.group_id}
                            )
                        )
                        .group_by(GroupUser.group_id)
                    )
                ).all()
            )

            data = []
            for discussion in discussions:
                mine = next(
                    (m for m in discussion.members if m.user_id == user_id), None
                )
                last = last_messages.get(discussion.id)
                members = (
                    []
                    if discussion.group_id
                    else [user_dict(m.user) for m in discussion.members]
                )
                data.append(
                    {
                        "id": discussion.id,
                        "name": discussion.name,
                        "is_direct": discussion.is_direct,
                        "creator_id": discussion.creator_id,
                        "created_at": discussion.created_at,
                        "group": {
                            "id": discussion.group.id,
                            "name": discussion.group.name,
                        }
                        if discussion.group
                        else None,
                        "members": members,
                        "member_count": group_sizes.get(discussion.group_id, 0)
                        if discussion.group_id
                        else len(members),
                        "muted": bool(mine and mine.muted),
                        "unread": unread.get(discussion.id, 0),
                        "last_message": message_dict(last) if last else None,
                    }
                )
            data.sort(
                key=lambda d: (
                    d["last_message"]["created_at"]
                    if d["last_message"]
                    else d["created_at"]
                ),
                reverse=True,
            )
            return self.success(data={"discussions": data})

    @auth_or_token
    async def post(self, *, body: DiscussionPostBody = None) -> DiscussionPostResponse:
        """
        ---
        summary: Start a discussion
        description: >
            Start a group discussion with chosen users, or with every member of
            a group you belong to, or a direct message with one user (the one
            you already have with them is returned if it exists).
        tags:
          - discussions
        """
        body = self.parse_body(DiscussionPostBody)
        user_id = self.associated_user_object.id
        name = (body.name or "").strip() or None

        async with self.AsyncSession() as session:
            if body.group_id is not None:
                if body.user_ids or body.direct:
                    return self.error("Choose either users or a group, not both")
                group = await session.scalar(
                    Group.select(session.user_or_token).where(Group.id == body.group_id)
                )
                member = await session.scalar(
                    sa.select(GroupUser.id).where(
                        GroupUser.group_id == body.group_id,
                        GroupUser.user_id == user_id,
                    )
                )
                if group is None or member is None or group.single_user_group:
                    return self.error("You can only start a discussion in your groups")
                discussion = Discussion(
                    name=name, creator_id=user_id, group_id=group.id
                )
                session.add(discussion)
                await session.commit()
                self.push_refresh(
                    await participant_ids(session, discussion), discussion.id
                )
                return self.success(data={"id": discussion.id})

            others = set(body.user_ids) - {user_id}
            if not others:
                return self.error("Choose at least one other user")
            found = set(
                (
                    await session.scalars(
                        User.select(session.user_or_token, columns=[User.id]).where(
                            User.id.in_(others)
                        )
                    )
                ).all()
            )
            if found != others:
                return self.error(f"Invalid user IDs: {sorted(others - found)}")

            if body.direct:
                if len(others) != 1:
                    return self.error("A direct message is with exactly one user")
                (other,) = others
                existing = await session.scalar(
                    sa.select(Discussion.id)
                    .join(DiscussionMember)
                    .where(
                        Discussion.is_direct.is_(True),
                        DiscussionMember.user_id.in_([user_id, other]),
                    )
                    .group_by(Discussion.id)
                    .having(sa.func.count(sa.distinct(DiscussionMember.user_id)) == 2)
                )
                if existing is not None:
                    return self.success(data={"id": existing})

            discussion = Discussion(
                name=None if body.direct else name,
                is_direct=body.direct,
                creator_id=user_id,
                members=[
                    DiscussionMember(user_id=member_id)
                    for member_id in {user_id, *others}
                ],
            )
            session.add(discussion)
            await session.commit()
            self.push_refresh({user_id, *others}, discussion.id)
            return self.success(data={"id": discussion.id})

    @auth_or_token
    async def patch(self, discussion_id: int, *, body: DiscussionPatchBody = None):
        """
        ---
        summary: Rename a discussion
        tags:
          - discussions
        """
        body = self.parse_body(DiscussionPatchBody)
        async with self.AsyncSession() as session:
            discussion = await self.get_discussion(session, discussion_id, "update")
            if discussion is None:
                return
            if discussion.is_direct:
                return self.error("A direct message has no name")
            discussion.name = body.name.strip()
            await session.commit()
            self.push_refresh(await participant_ids(session, discussion), discussion.id)
            return self.success()

    @auth_or_token
    async def delete(self, discussion_id: int):
        """
        ---
        summary: Delete a discussion
        description: Delete a discussion and all its messages. Restricted to whoever started it.
        tags:
          - discussions
        """
        async with self.AsyncSession() as session:
            discussion = await self.get_discussion(session, discussion_id)
            if discussion is None:
                return
            if discussion.creator_id != self.associated_user_object.id:
                return self.error(
                    "Only the user who started this discussion can delete it",
                    status=403,
                )
            recipients = await participant_ids(session, discussion)
            await session.delete(discussion)
            await session.commit()
            self.push_refresh(recipients, discussion_id)
            return self.success()


class DiscussionMessageHandler(DiscussionBaseHandler):
    @auth_or_token
    async def get(
        self,
        discussion_id: int,
        *ignored_args,
        query: DiscussionMessageListQuery = None,
    ) -> DiscussionMessageListResponse:
        """
        ---
        summary: Read a discussion
        description: >
            The latest messages of a discussion, oldest first. Pass the ID of
            the oldest one received as `before` to get the ones preceding it.
        tags:
          - discussions
        """
        query = self.parse_query(DiscussionMessageListQuery)
        async with self.AsyncSession() as session:
            if await self.get_discussion(session, discussion_id) is None:
                return
            stmt = DiscussionMessage.select(
                session.user_or_token,
                options=[selectinload(DiscussionMessage.author)],
            ).where(DiscussionMessage.discussion_id == discussion_id)
            if query.before is not None:
                stmt = stmt.where(DiscussionMessage.id < query.before)
            messages = (
                await session.scalars(
                    stmt.order_by(DiscussionMessage.id.desc()).limit(query.limit + 1)
                )
            ).all()
            page = messages[: query.limit]
            return self.success(
                data={
                    "messages": [message_dict(m) for m in reversed(page)],
                    "has_more": len(messages) > query.limit,
                }
            )

    @auth_or_token
    async def post(
        self,
        discussion_id: int,
        *ignored_args,
        body: DiscussionMessagePostBody = None,
    ) -> DiscussionPostResponse:
        """
        ---
        summary: Send a message
        description: >
            Post a message in a discussion. Participants are notified according
            to their preferences, unless they muted the discussion.
        tags:
          - discussions
        """
        body = self.parse_body(DiscussionMessagePostBody)
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            discussion = await self.get_discussion(session, discussion_id)
            if discussion is None:
                return
            message = DiscussionMessage(
                discussion_id=discussion.id, author_id=user_id, text=body.text
            )
            session.add(message)
            member = await own_membership(session, discussion, user_id)
            member.last_read_at = utcnow_naive()
            await session.commit()
            self.push_refresh(await participant_ids(session, discussion), discussion.id)
            return self.success(data={"id": message.id})

    @auth_or_token
    async def patch(
        self,
        discussion_id: int,
        message_id: int,
        *,
        body: DiscussionMessagePostBody = None,
    ):
        """
        ---
        summary: Edit a message
        description: Restricted to the author of the message.
        tags:
          - discussions
        """
        body = self.parse_body(DiscussionMessagePostBody)
        async with self.AsyncSession() as session:
            message = await session.scalar(
                DiscussionMessage.select(session.user_or_token, mode="update").where(
                    DiscussionMessage.id == message_id,
                    DiscussionMessage.discussion_id == discussion_id,
                )
            )
            if message is None:
                return self.error("Invalid message ID")
            message.text = body.text
            await session.commit()
            discussion = await session.get(Discussion, discussion_id)
            self.push_refresh(await participant_ids(session, discussion), discussion_id)
            return self.success()

    @auth_or_token
    async def delete(self, discussion_id: int, message_id: int):
        """
        ---
        summary: Delete a message
        description: Restricted to the author of the message.
        tags:
          - discussions
        """
        async with self.AsyncSession() as session:
            message = await session.scalar(
                DiscussionMessage.select(session.user_or_token, mode="delete").where(
                    DiscussionMessage.id == message_id,
                    DiscussionMessage.discussion_id == discussion_id,
                )
            )
            if message is None:
                return self.error("Invalid message ID")
            discussion = await session.get(Discussion, discussion_id)
            recipients = await participant_ids(session, discussion)
            await session.delete(message)
            await session.commit()
            self.push_refresh(recipients, discussion_id)
            return self.success()


class DiscussionMemberHandler(DiscussionBaseHandler):
    @auth_or_token
    async def get(
        self, discussion_id: int, *ignored_args
    ) -> DiscussionMemberListResponse:
        """
        ---
        summary: List the members of a discussion
        description: The chosen members, or every member of the discussion's group.
        tags:
          - discussions
        """
        async with self.AsyncSession() as session:
            discussion = await self.get_discussion(session, discussion_id)
            if discussion is None:
                return
            members = await session.scalars(
                sa.select(User)
                .where(User.id.in_(await participant_ids(session, discussion)))
                .order_by(User.first_name, User.last_name, User.username)
            )
            return self.success(data={"members": [user_dict(m) for m in members]})

    @auth_or_token
    async def post(
        self,
        discussion_id: int,
        *ignored_args,
        body: DiscussionMembersPostBody = None,
    ):
        """
        ---
        summary: Add users to a discussion
        description: Any member can add users to a discussion between chosen users.
        tags:
          - discussions
        """
        body = self.parse_body(DiscussionMembersPostBody)
        async with self.AsyncSession() as session:
            discussion = await self.get_discussion(session, discussion_id)
            if discussion is None:
                return
            if discussion.is_direct or discussion.group_id is not None:
                return self.error(
                    "Users can only be added to a discussion between chosen users"
                )
            current = await participant_ids(session, discussion)
            new = set(body.user_ids) - current
            found = set(
                (
                    await session.scalars(
                        User.select(session.user_or_token, columns=[User.id]).where(
                            User.id.in_(new)
                        )
                    )
                ).all()
            )
            if found != new:
                return self.error(f"Invalid user IDs: {sorted(new - found)}")
            session.add_all(
                DiscussionMember(discussion_id=discussion.id, user_id=member_id)
                for member_id in new
            )
            await session.commit()
            self.push_refresh(current | new, discussion.id)
            return self.success()

    @auth_or_token
    async def delete(self, discussion_id: int, user_id: int):
        """
        ---
        summary: Remove a user from a discussion
        description: >
            Leave a discussion between chosen users, or remove someone from one
            you started. The discussion is deleted when its last member leaves.
        tags:
          - discussions
        """
        async with self.AsyncSession() as session:
            discussion = await self.get_discussion(session, discussion_id)
            if discussion is None:
                return
            if discussion.is_direct or discussion.group_id is not None:
                return self.error("Only a discussion between chosen users can be left")
            member = await session.scalar(
                DiscussionMember.select(session.user_or_token, mode="delete").where(
                    DiscussionMember.discussion_id == discussion.id,
                    DiscussionMember.user_id == user_id,
                )
            )
            if member is None:
                return self.error("Cannot remove this user", status=403)
            recipients = await participant_ids(session, discussion)
            if recipients == {user_id}:
                await session.execute(
                    sa.delete(Discussion).where(Discussion.id == discussion.id)
                )
            else:
                await session.delete(member)
            await session.commit()
            self.push_refresh(recipients, discussion.id)
            return self.success()


class DiscussionMembershipHandler(DiscussionBaseHandler):
    @auth_or_token
    async def patch(
        self, discussion_id: int, *, body: DiscussionMembershipPatchBody = None
    ):
        """
        ---
        summary: Mark a discussion as read, or mute it
        tags:
          - discussions
        """
        body = self.parse_body(DiscussionMembershipPatchBody)
        async with self.AsyncSession() as session:
            discussion = await self.get_discussion(session, discussion_id)
            if discussion is None:
                return
            member = await own_membership(
                session, discussion, self.associated_user_object.id
            )
            if member is None:
                return self.error("You are not a member of this discussion")
            if body.muted is not None:
                member.muted = body.muted
            if body.read:
                member.last_read_at = utcnow_naive()
            await session.commit()
            return self.success()


THREAD_TABLES = [
    ("sources", Comment, "obj_id", True),
    ("sources", CommentOnSpectrum, "obj_id", False),
    ("gcn_event", CommentOnGCN, "gcn_id", True),
    ("earthquake", CommentOnEarthquake, "earthquake_id", True),
    ("shift", CommentOnShift, "shift_id", True),
]


class CommentThreadHandler(BaseHandler):
    @auth_or_token
    async def get(self) -> CommentThreadListResponse:
        """
        ---
        summary: Retrieve the comment threads you are involved in
        description: >
            The comment threads, on sources, GCN events, earthquakes and shifts,
            where the requesting user wrote, latest activity first. Comments
            posted through the API (bots) are left out.
        tags:
          - comments
        """
        user_id = self.associated_user_object.id
        threads = {}
        async with self.AsyncSession() as session:
            for resource_type, table, column, threaded in THREAD_TABLES:
                accessible = table.select(
                    session.user_or_token,
                    columns=[
                        table.id,
                        getattr(table, column),
                        table.channel,
                        table.author_id,
                        table.bot,
                    ],
                ).subquery()
                resource = accessible.c[column]
                thread_columns = (
                    [resource, accessible.c.channel] if threaded else [resource]
                )

                involved = {
                    (resource_id, channel if threaded else None)
                    for resource_id, channel in await session.execute(
                        sa.select(resource, accessible.c.channel)
                        .where(
                            accessible.c.bot.is_(False),
                            accessible.c.author_id == user_id,
                        )
                        .distinct()
                    )
                }
                if not involved:
                    continue

                latest_ids = (
                    sa.select(sa.func.max(accessible.c.id))
                    .where(
                        accessible.c.bot.is_(False),
                        resource.in_({resource_id for resource_id, _ in involved}),
                    )
                    .group_by(*thread_columns)
                )
                for comment in await session.scalars(
                    sa.select(table)
                    .options(selectinload(table.author))
                    .where(table.id.in_(latest_ids))
                ):
                    thread = comment.channel if threaded else None
                    key = (getattr(comment, column), thread)
                    if key not in involved:
                        continue
                    thread_key = (resource_type, *key)
                    known = threads.get(thread_key)
                    if known and known["last_comment"].created_at > comment.created_at:
                        continue
                    threads[thread_key] = {
                        "resource_type": resource_type,
                        "resource_id": key[0],
                        "channel": thread,
                        "last_comment": comment,
                    }

            selected = sorted(
                threads.values(),
                key=lambda t: t["last_comment"].created_at,
                reverse=True,
            )[:MAX_COMMENT_THREADS]

            def ids_of(resource_type):
                return {
                    t["resource_id"]
                    for t in selected
                    if t["resource_type"] == resource_type
                }

            dateobs = dict(
                (
                    await session.execute(
                        sa.select(GcnEvent.id, GcnEvent.dateobs).where(
                            GcnEvent.id.in_(ids_of("gcn_event"))
                        )
                    )
                ).all()
            )
            event_ids = dict(
                (
                    await session.execute(
                        sa.select(EarthquakeEvent.id, EarthquakeEvent.event_id).where(
                            EarthquakeEvent.id.in_(ids_of("earthquake"))
                        )
                    )
                ).all()
            )
            shift_names = dict(
                (
                    await session.execute(
                        sa.select(Shift.id, Shift.name).where(
                            Shift.id.in_(ids_of("shift"))
                        )
                    )
                ).all()
            )

            data = []
            for thread in selected:
                resource_type, resource_id = (
                    thread["resource_type"],
                    thread["resource_id"],
                )
                extra = {}
                if resource_type == "sources":
                    label, url = resource_id, f"/source/{resource_id}"
                elif resource_type == "gcn_event":
                    if resource_id not in dateobs:
                        continue
                    iso = dateobs[resource_id].isoformat()
                    label, url = iso, f"/gcn_events/{iso}"
                    extra["dateobs"] = iso
                elif resource_type == "earthquake":
                    if resource_id not in event_ids:
                        continue
                    label = event_ids[resource_id]
                    url = f"/earthquakes/{label}"
                    extra["event_id"] = label
                else:
                    label = shift_names.get(resource_id) or f"Shift {resource_id}"
                    url = f"/shifts/{resource_id}"
                comment = thread["last_comment"]
                data.append(
                    {
                        "resource_type": resource_type,
                        "resource_id": str(resource_id),
                        "label": label,
                        "url": url,
                        "channel": thread["channel"],
                        "last_comment": {
                            "id": comment.id,
                            "text": comment.text,
                            "created_at": comment.created_at,
                            "author": user_dict(comment.author),
                        },
                        **extra,
                    }
                )
            return self.success(data={"threads": data})
