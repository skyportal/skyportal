import sqlalchemy as sa
from sqlalchemy import desc, or_
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    Source,
    Comment,
    Classification,
    Spectrum,
    Photometry,
    basic_user_display_info,
)

MAX_NEWSFEED_ITEMS = 1000
DEFAULT_NEWSFEED_ITEMS = 50


class NewsFeedHandler(BaseHandler):
    @auth_or_token
    def get(self):
        f"""
        ---
        description: Retrieve summary of recent activity
        tags:
          - news_feed
        parameters:
          - in: query
            name: numItems
            nullable: true
            schema:
              type: integer
            description: Number of newsfeed items to return.
            Defaults to {DEFAULT_NEWSFEED_ITEMS}. Max is {MAX_NEWSFEED_ITEMS}.
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                  - $ref: '#/components/schemas/Success'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          type: object
                          properties:
                            type:
                              type: string
                            time:
                              type: string
                            message:
                              type: string
          400:
            content:
              application/json:
                schema: Error
        """

        preferences = getattr(self.current_user, 'preferences', None) or {}
        n_items_query = self.get_query_argument("numItems", None)
        if n_items_query is not None:
            n_items_query = int(n_items_query)
        n_items_feed = preferences.get('newsFeed', {}).get('numItems', None)
        if n_items_feed is not None:
            n_items_feed = int(n_items_feed)

        n_items_list = [n_items_query, n_items_feed]
        if all(v is None for v in n_items_list):
            n_items = DEFAULT_NEWSFEED_ITEMS
        else:
            n_items = max(x for x in n_items_list if x is not None)
        if n_items > MAX_NEWSFEED_ITEMS:
            return self.error(
                f'numItems should be no larger than {MAX_NEWSFEED_ITEMS}.'
            )

        with self.Session() as session:
            user_accessible_group_ids = [
                g.id for g in self.associated_user_object.accessible_groups
            ]

            def fetch_newest(
                model, include_bot_comments=False, include_ml_classifications=False
            ):
                query = model.select(self.associated_user_object)
                if model == Photometry:
                    query = query.where(
                        or_(
                            Photometry.followup_request_id.isnot(None),
                            Photometry.assignment_id.isnot(None),
                        )
                    )
                elif model == Comment:
                    if not include_bot_comments:
                        query = query.where(Comment.bot.is_(False))
                    if not self.associated_user_object.is_admin:
                        query = query.where(
                            Comment.obj_id.in_(
                                sa.select(Source.obj_id).where(
                                    Source.group_id.in_(user_accessible_group_ids),
                                    Source.active.is_(True),
                                )
                            )
                        )
                elif model == Classification:
                    if not include_ml_classifications:
                        query = query.where(Classification.ml.is_(False))
                    if not self.associated_user_object.is_admin:
                        query = query.where(
                            Classification.obj_id.in_(
                                sa.select(Source.obj_id).where(
                                    Source.group_id.in_(user_accessible_group_ids),
                                    Source.active.is_(True),
                                )
                            )
                        )
                query = (
                    query.order_by(desc(model.created_at or model.saved_at))
                    .distinct(model.obj_id, model.created_at)
                    .limit(n_items)
                )
                newest = session.scalars(query).unique().all()

                if model == Comment:
                    for comment in newest:
                        comment.author_info = comment.construct_author_info_dict()

                return newest

            def latest_classification(obj):
                classification = None
                try:
                    if len(obj.classifications) > 0:
                        # Display the most recent non-zero probability class,
                        # and that isn't a ml classifier
                        sortedClasses = sorted(
                            (
                                c
                                for c in obj.classifications
                                if c.probability > 0 and c.ml is False
                            ),
                            key=lambda x: x.modified,
                        )
                        if len(sortedClasses) > 0:
                            classification = sortedClasses[0].classification
                except Exception:
                    pass
                return classification

            news_feed_items = []
            if (
                preferences.get("newsFeed", {})
                .get("categories", {})
                .get("sources", True)
            ):
                sources = fetch_newest(Source)
                source_seen = set()
                # Iterate in reverse so that we arrive at re-saved sources second
                for s in reversed(sources):
                    if s.obj_id in source_seen:
                        message = 'Source saved to new group'
                    else:
                        message = 'New source saved'
                        source_seen.add(s.obj_id)

                    # Prepend since we are iterating in reverse
                    news_feed_items.insert(
                        0,
                        {
                            'type': 'source',
                            'time': s.created_at,
                            'message': message,
                            'source_id': s.obj_id,
                            'classification': latest_classification(s.obj),
                        },
                    )
            if (
                preferences.get("newsFeed", {})
                .get("categories", {})
                .get("comments", True)
            ):
                include_bot_comments = (
                    preferences.get("newsFeed", {})
                    .get("categories", {})
                    .get("includeCommentsFromBots", False)
                )
                comments = fetch_newest(Comment, include_bot_comments)
                # Add latest comments
                news_feed_items.extend(
                    [
                        {
                            'type': 'comment',
                            'time': c.created_at,
                            'message': c.text,
                            'source_id': c.obj_id,
                            'author': c.author.username,
                            'author_info': c.author_info,
                            'classification': latest_classification(c.obj),
                        }
                        for c in comments
                    ]
                )
            if (
                preferences.get("newsFeed", {})
                .get("categories", {})
                .get("classifications", True)
            ):
                classifications = fetch_newest(Classification)
                # Add latest classifications
                news_feed_items.extend(
                    [
                        {
                            "type": "classification",
                            "time": c.created_at,
                            "message": f"New classification for {c.obj_id} added by {c.author.username}: {c.classification}",
                            "source_id": c.obj_id,
                            "author_info": basic_user_display_info(c.author),
                            "classification": latest_classification(c.obj),
                        }
                        for c in classifications
                    ]
                )
            if (
                preferences.get("newsFeed", {})
                .get("categories", {})
                .get("spectra", True)
            ):
                spectra = fetch_newest(Spectrum)
                # Add latest spectra
                news_feed_items.extend(
                    [
                        {
                            "type": "spectrum",
                            "time": s.created_at,
                            "message": f"{s.owner.first_name} {s.owner.last_name} uploaded a new spectrum taken with {s.instrument.name} for {s.obj_id}",
                            "source_id": s.obj_id,
                            "author_info": basic_user_display_info(s.owner),
                            "classification": latest_classification(s.obj),
                        }
                        for s in spectra
                    ]
                )
            if (
                preferences.get("newsFeed", {})
                .get("categories", {})
                .get("photometry", True)
            ):
                photometry = fetch_newest(Photometry)
                # Add latest follow-up photometry
                news_feed_items.extend(
                    [
                        {
                            "type": "photometry",
                            "time": p.created_at,
                            "message": f"{p.owner.first_name} {p.owner.last_name} uploaded new follow-up photometry taken with {p.instrument.name} for {p.obj_id}",
                            "source_id": p.obj_id,
                            "author_info": basic_user_display_info(p.owner),
                            "classification": latest_classification(p.obj),
                        }
                        for p in photometry
                    ]
                )

            news_feed_items.sort(key=lambda x: x['time'], reverse=True)
            news_feed_items = news_feed_items[:n_items]
            return self.success(data=news_feed_items)
