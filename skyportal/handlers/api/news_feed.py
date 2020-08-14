from hashlib import md5
from sqlalchemy import desc
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Comment, User


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
            return (
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
                .limit(n_items)
                .all()
            )

        def fetch_newest_comments():
            owned_comments = (
                Comment.query.filter(
                    Comment.obj_id.in_(
                        DBSession()
                        .query(Source.obj_id)
                        .filter(
                            Source.group_id.in_(
                                [g.id for g in self.current_user.accessible_groups]
                            )
                        )
                    )
                )
                .order_by(desc(Comment.created_at or Comment.saved_at))
                .limit(n_items)
                .all()
            )

            for comment in owned_comments:
                author = User.query.filter(User.username == comment.author).first()
                if author:
                    comment.author_info = {
                        "username": author.username,
                        "first_name": author.first_name,
                        "last_name": author.last_name,
                        "gravatar_url": author.gravatar_url,
                    }
                else:
                    username = "unknown user"
                    digest = md5(username.lower().encode('utf-8')).hexdigest()
                    # return a 404 status code if not found on gravatar
                    gravatar_url = f'https://www.gravatar.com/avatar/{digest}?d=404'
                    comment.author_info = {
                        "username": username,
                        "first_name": None,
                        "last_name": None,
                        "gravatar_url": gravatar_url,
                    }

            return owned_comments

        sources = fetch_newest(Source)
        comments = fetch_newest_comments()
        news_feed_items = [
            {
                'type': 'source',
                'time': s.created_at,
                'message': f'New source created with ID: {s.obj_id}',
            }
            for s in sources
        ]
        news_feed_items.extend(
            [
                {
                    'type': 'comment',
                    'time': c.created_at,
                    'message': f'{c.text} ({c.obj_id})',
                    'author': c.author,
                    'author_info': c.author_info,
                }
                for c in comments
            ]
        )
        news_feed_items.sort(key=lambda x: x['time'], reverse=True)
        news_feed_items = news_feed_items[:n_items]

        return self.success(data=news_feed_items)
