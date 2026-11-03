from collections import defaultdict
from datetime import UTC

import sqlalchemy as sa
from skyportal_py_models.topics import (
    TopicFeedQuery,
    TopicFeedResponse,
    TopicIdResponse,
    TopicListResponse,
    TopicPatchBody,
    TopicPostBody,
    TopicSourcePostBody,
)
from sqlalchemy.orm import load_only, selectinload

from baselayer.app.access import auth_or_token

from ...models import (
    Classification,
    Comment,
    Obj,
    ObjTag,
    ObjTagOption,
    Spectrum,
    Topic,
    TopicSource,
    TopicSubscription,
    basic_user_display_info,
)
from ..base import BaseHandler

HUMAN_CLASSIFICATION = (
    Classification.ml.is_(False),
    sa.or_(Classification.probability.is_(None), Classification.probability > 0),
)


def human_classifications(user_or_token, columns, names):
    return Classification.select(user_or_token, columns=columns).where(
        Classification.classification.in_(names), *HUMAN_CLASSIFICATION
    )


def author_dict(user):
    return basic_user_display_info(user) if user is not None else None


async def tag_options(session, tag_ids):
    if not tag_ids:
        return {}
    return {
        option.id: option
        for option in await session.scalars(
            ObjTagOption.select(session.user_or_token).where(
                ObjTagOption.id.in_(tag_ids)
            )
        )
    }


async def topic_dicts(session, topics, user_id):
    ids = [t.id for t in topics]
    counts = dict(
        (
            await session.execute(
                sa.select(TopicSubscription.topic_id, sa.func.count())
                .where(TopicSubscription.topic_id.in_(ids))
                .group_by(TopicSubscription.topic_id)
            )
        ).all()
    )
    subscribed = set(
        (
            await session.scalars(
                sa.select(TopicSubscription.topic_id).where(
                    TopicSubscription.topic_id.in_(ids),
                    TopicSubscription.user_id == user_id,
                )
            )
        ).all()
    )
    tags = await tag_options(session, {i for t in topics for i in t.tag_ids})
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "creator": author_dict(t.creator),
            "created_at": t.created_at,
            "classifications": t.classifications,
            "tags": [
                {"id": i, "name": tags[i].name, "color": tags[i].color}
                for i in t.tag_ids
                if i in tags
            ],
            "subscriber_count": counts.get(t.id, 0),
            "subscribed": t.id in subscribed,
        }
        for t in topics
    ]


async def rules_error(session, topic_id, name, tag_ids):
    if name is not None:
        taken = await session.scalar(
            sa.select(Topic.id).where(
                sa.func.lower(Topic.name) == name.lower(), Topic.id != topic_id
            )
        )
        if taken is not None:
            return f"A topic named {name} already exists"
    if tag_ids:
        missing = set(tag_ids) - set(await tag_options(session, tag_ids))
        if missing:
            return f"Invalid tag IDs: {sorted(missing)}"


def clean_classifications(classifications):
    return sorted({c.strip() for c in classifications if c.strip()})


class TopicBaseHandler(BaseHandler):
    async def get_topic(self, session, topic_id, mode="read"):
        topic = await session.scalar(
            Topic.select(session.user_or_token, mode=mode).where(Topic.id == topic_id)
        )
        if topic is None:
            self.error("Invalid topic ID")
        return topic


class TopicHandler(TopicBaseHandler):
    @auth_or_token
    async def get(self, topic_id: int | None = None) -> TopicListResponse:
        """
        ---
        summary: Retrieve topics
        description: >
            Every topic, most followed first, with whether the requesting user
            is subscribed to it.
        tags:
          - topics
        """
        async with self.AsyncSession() as session:
            stmt = Topic.select(
                session.user_or_token, options=[selectinload(Topic.creator)]
            )
            if topic_id is not None:
                stmt = stmt.where(Topic.id == topic_id)
            topics = (await session.scalars(stmt)).all()
            if topic_id is not None and not topics:
                return self.error("Invalid topic ID")
            data = await topic_dicts(session, topics, self.associated_user_object.id)
            data.sort(key=lambda t: (-t["subscriber_count"], t["name"].lower()))
            return self.success(data={"topics": data})

    @auth_or_token
    async def post(self, *, body: TopicPostBody = None) -> TopicIdResponse:
        """
        ---
        summary: Create a topic
        description: >
            Sources join the topic when they are posted to it, or when they get
            one of its classifications or object tags. Its creator is
            subscribed to it.
        tags:
          - topics
        """
        body = self.parse_body(TopicPostBody)
        user_id = self.associated_user_object.id
        name = body.name.strip()
        if not name:
            return self.error("A topic needs a name")
        async with self.AsyncSession() as session:
            if error := await rules_error(session, None, name, body.tag_ids):
                return self.error(error)
            topic = Topic(
                name=name,
                description=(body.description or "").strip() or None,
                creator_id=user_id,
                classifications=clean_classifications(body.classifications),
                tag_ids=sorted(set(body.tag_ids)),
                subscriptions=[TopicSubscription(user_id=user_id)],
            )
            session.add(topic)
            await session.commit()
            return self.success(data={"id": topic.id})

    @auth_or_token
    async def patch(self, topic_id: int, *, body: TopicPatchBody = None):
        """
        ---
        summary: Edit a topic
        description: Restricted to the user who created it.
        tags:
          - topics
        """
        body = self.parse_body(TopicPatchBody)
        name = body.name.strip() if body.name is not None else None
        if name == "":
            return self.error("A topic needs a name")
        async with self.AsyncSession() as session:
            topic = await self.get_topic(session, topic_id, "update")
            if topic is None:
                return
            if error := await rules_error(session, topic.id, name, body.tag_ids):
                return self.error(error)
            if name is not None:
                topic.name = name
            if "description" in body.model_fields_set:
                topic.description = (body.description or "").strip() or None
            if body.classifications is not None:
                topic.classifications = clean_classifications(body.classifications)
            if body.tag_ids is not None:
                topic.tag_ids = sorted(set(body.tag_ids))
            await session.commit()
            return self.success()

    @auth_or_token
    async def delete(self, topic_id: int):
        """
        ---
        summary: Delete a topic
        description: Restricted to the user who created it.
        tags:
          - topics
        """
        async with self.AsyncSession() as session:
            topic = await self.get_topic(session, topic_id, "delete")
            if topic is None:
                return
            await session.delete(topic)
            await session.commit()
            return self.success()


class TopicSubscriptionHandler(TopicBaseHandler):
    @auth_or_token
    async def post(self, topic_id: int):
        """
        ---
        summary: Subscribe to a topic
        tags:
          - topics
        """
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            if await self.get_topic(session, topic_id) is None:
                return
            existing = await session.scalar(
                sa.select(TopicSubscription.id).where(
                    TopicSubscription.topic_id == topic_id,
                    TopicSubscription.user_id == user_id,
                )
            )
            if existing is None:
                session.add(TopicSubscription(topic_id=topic_id, user_id=user_id))
                await session.commit()
            return self.success()

    @auth_or_token
    async def delete(self, topic_id: int):
        """
        ---
        summary: Unsubscribe from a topic
        tags:
          - topics
        """
        async with self.AsyncSession() as session:
            await session.execute(
                sa.delete(TopicSubscription).where(
                    TopicSubscription.topic_id == topic_id,
                    TopicSubscription.user_id == self.associated_user_object.id,
                )
            )
            await session.commit()
            return self.success()


class TopicSourceHandler(TopicBaseHandler):
    @auth_or_token
    async def post(
        self, topic_id: int, *ignored_args, body: TopicSourcePostBody = None
    ) -> TopicIdResponse:
        """
        ---
        summary: Post a source to a topic
        tags:
          - topics
        """
        body = self.parse_body(TopicSourcePostBody)
        obj_id = body.obj_id.strip()
        async with self.AsyncSession() as session:
            if await self.get_topic(session, topic_id) is None:
                return
            obj = await session.scalar(
                Obj.select(session.user_or_token, columns=[Obj.id]).where(
                    Obj.id == obj_id
                )
            )
            if obj is None:
                return self.error(f"Invalid source ID: {obj_id}")
            existing = await session.scalar(
                sa.select(TopicSource.id).where(
                    TopicSource.topic_id == topic_id, TopicSource.obj_id == obj_id
                )
            )
            if existing is not None:
                return self.error(f"{obj_id} is already in this topic")
            post = TopicSource(
                topic_id=topic_id,
                obj_id=obj_id,
                author_id=self.associated_user_object.id,
                text=(body.text or "").strip() or None,
            )
            session.add(post)
            await session.commit()
            return self.success(data={"id": post.id})

    @auth_or_token
    async def delete(self, topic_id: int, obj_id: str):
        """
        ---
        summary: Remove a source posted to a topic
        description: Restricted to the user who posted it and the topic creator.
        tags:
          - topics
        """
        async with self.AsyncSession() as session:
            post = await session.scalar(
                TopicSource.select(session.user_or_token, mode="delete").where(
                    TopicSource.topic_id == topic_id, TopicSource.obj_id == obj_id
                )
            )
            if post is None:
                return self.error("Cannot remove this source", status=403)
            await session.delete(post)
            await session.commit()
            return self.success()


class TopicFeedHandler(BaseHandler):
    @auth_or_token
    async def get(self, *, query: TopicFeedQuery = None) -> TopicFeedResponse:
        """
        ---
        summary: Read a topic feed
        description: >
            What happened lately to the sources of a topic, or of every topic
            the requesting user is subscribed to: posts, human
            classifications, object tags, comments and spectra. Only the data
            the user can already access is listed. Pass the time of the oldest
            item received as `before` to get the ones preceding it.
        tags:
          - topics
        """
        query = self.parse_query(TopicFeedQuery)
        before = query.before
        if before is not None and before.tzinfo is not None:
            before = before.astimezone(UTC).replace(tzinfo=None)
        limit = query.limit

        async with self.AsyncSession() as session:
            user_or_token = session.user_or_token
            stmt = Topic.select(user_or_token)
            if query.topic_id is not None:
                stmt = stmt.where(Topic.id == query.topic_id)
            else:
                stmt = stmt.where(
                    Topic.id.in_(
                        sa.select(TopicSubscription.topic_id).where(
                            TopicSubscription.user_id == self.associated_user_object.id
                        )
                    )
                )
            topics = (await session.scalars(stmt)).all()
            if query.topic_id is not None and not topics:
                return self.error("Invalid topic ID")
            if not topics:
                return self.success(data={"items": [], "has_more": False})

            topic_ids = [t.id for t in topics]
            classifications = sorted({c for t in topics for c in t.classifications})
            tag_ids = sorted({i for t in topics for i in t.tag_ids})
            tags = await tag_options(session, tag_ids)

            members = [
                sa.select(TopicSource.obj_id).where(TopicSource.topic_id.in_(topic_ids))
            ]
            if classifications:
                members.append(
                    human_classifications(
                        user_or_token, [Classification.obj_id], classifications
                    )
                )
            if tag_ids:
                members.append(
                    ObjTag.select(user_or_token, columns=[ObjTag.obj_id]).where(
                        ObjTag.objtagoption_id.in_(tag_ids)
                    )
                )
            topic_objs = sa.union(*members) if len(members) > 1 else members[0]

            def newest(model, stmt):
                if before is not None:
                    stmt = stmt.where(model.created_at < before)
                return stmt.order_by(model.created_at.desc()).limit(limit + 1)

            async def fetch(model, stmt):
                return (await session.scalars(newest(model, stmt))).unique().all()

            items = []
            for post in await fetch(
                TopicSource,
                TopicSource.select(
                    user_or_token, options=[selectinload(TopicSource.author)]
                ).where(TopicSource.topic_id.in_(topic_ids)),
            ):
                items.append(
                    {
                        "type": "post",
                        "id": post.id,
                        "time": post.created_at,
                        "obj_id": post.obj_id,
                        "author": author_dict(post.author),
                        "text": post.text,
                        "topic_ids": [post.topic_id],
                    }
                )
            for classification in await fetch(
                Classification,
                Classification.select(
                    user_or_token, options=[selectinload(Classification.author)]
                ).where(*HUMAN_CLASSIFICATION, Classification.obj_id.in_(topic_objs)),
            ):
                items.append(
                    {
                        "type": "classification",
                        "id": classification.id,
                        "time": classification.created_at,
                        "obj_id": classification.obj_id,
                        "author": author_dict(classification.author),
                        "label": classification.classification,
                    }
                )
            if tag_ids:
                for tag in await fetch(
                    ObjTag,
                    ObjTag.select(
                        user_or_token, options=[selectinload(ObjTag.author)]
                    ).where(ObjTag.objtagoption_id.in_(tag_ids)),
                ):
                    items.append(
                        {
                            "type": "tag",
                            "id": tag.id,
                            "time": tag.created_at,
                            "obj_id": tag.obj_id,
                            "author": author_dict(tag.author),
                            "label": tags[tag.objtagoption_id].name,
                        }
                    )
            for comment in await fetch(
                Comment,
                Comment.select(
                    user_or_token, options=[selectinload(Comment.author)]
                ).where(
                    Comment.channel.is_(None),
                    Comment.bot.is_(False),
                    Comment.obj_id.in_(topic_objs),
                ),
            ):
                items.append(
                    {
                        "type": "comment",
                        "id": comment.id,
                        "time": comment.created_at,
                        "obj_id": comment.obj_id,
                        "author": author_dict(comment.author),
                        "text": comment.text,
                    }
                )
            for spectrum in await fetch(
                Spectrum,
                Spectrum.select(
                    user_or_token,
                    options=[
                        load_only(
                            Spectrum.id,
                            Spectrum.obj_id,
                            Spectrum.created_at,
                            Spectrum.owner_id,
                            Spectrum.instrument_id,
                        ),
                        selectinload(Spectrum.owner),
                        selectinload(Spectrum.instrument),
                    ],
                ).where(Spectrum.obj_id.in_(topic_objs)),
            ):
                items.append(
                    {
                        "type": "spectrum",
                        "id": spectrum.id,
                        "time": spectrum.created_at,
                        "obj_id": spectrum.obj_id,
                        "author": author_dict(spectrum.owner),
                        "label": spectrum.instrument.name,
                    }
                )

            items.sort(key=lambda item: item["time"], reverse=True)
            has_more = len(items) > limit
            items = items[:limit]

            obj_ids = {item["obj_id"] for item in items}
            membership = defaultdict(set)
            for topic_id, obj_id in await session.execute(
                sa.select(TopicSource.topic_id, TopicSource.obj_id).where(
                    TopicSource.topic_id.in_(topic_ids),
                    TopicSource.obj_id.in_(obj_ids),
                )
            ):
                membership[obj_id].add(topic_id)
            if classifications:
                for obj_id, name in await session.execute(
                    human_classifications(
                        user_or_token,
                        [Classification.obj_id, Classification.classification],
                        classifications,
                    ).where(Classification.obj_id.in_(obj_ids))
                ):
                    membership[obj_id].update(
                        t.id for t in topics if name in t.classifications
                    )
            if tag_ids:
                for obj_id, tag_id in await session.execute(
                    ObjTag.select(
                        user_or_token, columns=[ObjTag.obj_id, ObjTag.objtagoption_id]
                    ).where(
                        ObjTag.objtagoption_id.in_(tag_ids), ObjTag.obj_id.in_(obj_ids)
                    )
                ):
                    membership[obj_id].update(
                        t.id for t in topics if tag_id in t.tag_ids
                    )
            for item in items:
                item.setdefault("topic_ids", sorted(membership[item["obj_id"]]))

            return self.success(data={"items": items, "has_more": has_more})
