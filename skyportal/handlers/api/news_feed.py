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


class NewsFeedHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve summary of recent activity
        tags:
          - news_feed
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
        preferences = (
            self.current_user.preferences if self.current_user.preferences else {}
        )
        if 'newsFeed' in preferences and 'numItems' in preferences['newsFeed']:
            n_items = min(int(preferences['newsFeed']['numItems']), 50)
        else:
            n_items = 10

        def fetch_newest(model):
            query = model.query_records_accessible_by(self.current_user)
            if model == Photometry:
                query = query.filter(
                    or_(
                        Photometry.followup_request_id.isnot(None),
                        Photometry.assignment_id.isnot(None),
                    )
                )
            query = (
                query.order_by(desc(model.created_at or model.saved_at))
                .distinct(model.obj_id, model.created_at)
                .limit(n_items)
            )
            newest = query.all()

            if model == Comment:
                for comment in newest:
                    comment.author_info = comment.construct_author_info_dict()

            return newest

        news_feed_items = []
        if preferences.get("newsFeed", {}).get("categories", {}).get("sources", True):
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
                    },
                )
        if preferences.get("newsFeed", {}).get("categories", {}).get("comments", True):
            comments = fetch_newest(Comment)
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
                    }
                    for c in classifications
                ]
            )
        if preferences.get("newsFeed", {}).get("categories", {}).get("spectra", True):
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
                    }
                    for p in photometry
                ]
            )

        news_feed_items.sort(key=lambda x: x['time'], reverse=True)
        news_feed_items = news_feed_items[:n_items]
        self.verify_and_commit()
        return self.success(data=news_feed_items)
