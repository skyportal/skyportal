from sqlalchemy import desc
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Photometry, Comment, GroupSource


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
                        comments:
                          type: arrayOfComments
                          description: Newest comments
                        sources:
                          type: arrayOfSources
                          description: Newest updated sources
                        photometry:
                          type: arrayOfPhotometry
                          description: Newest photometry entries
          400:
            content:
              application/json:
                schema: Error
        """
        if ('newsFeed' in self.current_user.preferences and
            'numItemsPerCategory' in self.current_user.preferences['newsFeed']):
            n_items = int(self.current_user.preferences['newsFeed']['numItemsPerCategory'])
        else:
            n_items = 5
        sources = Source.query.filter(Source.id.in_(DBSession.query(
            GroupSource.source_id).filter(GroupSource.group_id.in_(
                [g.id for g in self.current_user.groups])
            ))).order_by(desc(Source.modified)).limit(n_items).all()
        photometry = Photometry.query.filter(Photometry.source_id.in_(DBSession.query(
            GroupSource.source_id).filter(GroupSource.group_id.in_(
                [g.id for g in self.current_user.groups])
            ))).order_by(desc(Photometry.created_at)).limit(n_items).all()
        comments = Comment.query.filter(Comment.source_id.in_(DBSession.query(
            GroupSource.source_id).filter(GroupSource.group_id.in_(
                [g.id for g in self.current_user.groups])
            ))).order_by(desc(Comment.created_at)).limit(n_items).all()

        return self.success(
            data={
                'comments': comments,
                'sources': sources,
                'photometry': photometry,
            })
