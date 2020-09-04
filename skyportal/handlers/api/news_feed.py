from sqlalchemy import desc
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Comment


class NewsFeedHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve summary of recent activity
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
            n_items = min(int(preferences['newsFeed']['numItems']), 20)
        else:
            n_items = 5

        def fetch_newest(model):
            newest = (
                model.query.filter(
                    model.obj_id.in_(
                        DBSession()
                        .query(Source.obj_id)
                        .filter(
                            Source.group_id.in_(
                                [g.id for g in self.current_user.accessible_groups]
                            )
                        )
                    )
                )
                .order_by(desc(model.created_at or model.saved_at))
                .distinct(model.obj_id, model.created_at)
                .limit(n_items)
                .all()
            )

            if model == Comment:
                for comment in newest:
                    comment.author_info = comment.construct_author_info_dict()

            return newest

        sources = fetch_newest(Source)
        comments = fetch_newest(Comment)
        news_feed_items = [
            {
                'type': 'source',
                'time': s.created_at,
                'message': 'New source added',
                'source_id': s.obj_id,
            }
            for s in sources
        ]
        news_feed_items.extend(
            [
                {
                    'type': 'comment',
                    'time': c.created_at,
                    'message': c.text,
                    'source_id': c.obj_id,
                    'author': c.author,
                    'author_info': c.author_info,
                }
                for c in comments
            ]
        )
        news_feed_items.sort(key=lambda x: x['time'], reverse=True)
        news_feed_items = news_feed_items[:n_items]

        return self.success(data=news_feed_items)
