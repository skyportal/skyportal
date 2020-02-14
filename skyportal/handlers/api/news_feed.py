from sqlalchemy import desc
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Comment, GroupSource


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
                    - Success
                    - type: object
                      properties:
                        newsFeedItems:
                          type: arrayOfNewsFeedItems
                          description: List of recent activity
          400:
            content:
              application/json:
                schema: Error
        """
        preferences = self.current_user.preferences if self.current_user.preferences else {}
        if 'newsFeed' in preferences and 'numItems' in preferences['newsFeed']:
            n_items = min(int(preferences['newsFeed']['numItems']), 20)
        else:
            n_items = 5

        def fetch_newest(model):
            if model == Source:
                source_id_attr = 'id'
            else:
                source_id_attr = 'source_id'
            return model.query.filter(getattr(model, source_id_attr).in_(
                DBSession.query(GroupSource.source_id).filter(
                    GroupSource.group_id.in_([g.id for g in self.current_user.groups])
                ))).order_by(desc(model.created_at)).limit(n_items).all()

        sources = fetch_newest(Source)
        comments = fetch_newest(Comment)
        news_feed_items = [{'type': 'source', 'time': s.created_at,
                            'message': f'New source {s.id}'} for s in sources]
        news_feed_items.extend([{'type': 'comment', 'time': c.created_at,
                                 'message': f'{c.author}: {c.text} ({c.source_id})'}
                                for c in comments])
        news_feed_items.sort(key=lambda x: x['time'], reverse=True)
        news_feed_items = news_feed_items[:n_items]

        return self.success(data={'newsFeedItems': news_feed_items})
