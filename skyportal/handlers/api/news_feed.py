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
                          description: Newest comments (up to 5)
                        sources:
                          type: arrayOfSources
                          description: Newest updated sources (up to 5)
                        photometry:
                          type: arrayOfPhotometry
                          description: Newest photometry entries (up to 5)
          400:
            content:
              application/json:
                schema: Error
        """
        sources = Source.query.filter(Source.id.in_(DBSession.query(
            GroupSource.source_id).filter(GroupSource.group_id.in_(
                [g.id for g in self.current_user.groups])
            ))).order_by(desc(Source.modified)).limit(5).all()
        photometry = Photometry.query.filter(Photometry.source_id.in_(DBSession.query(
            GroupSource.source_id).filter(GroupSource.group_id.in_(
                [g.id for g in self.current_user.groups])
            ))).order_by(desc(Photometry.created_at)).limit(5).all()
        comments = Comment.query.filter(Comment.source_id.in_(DBSession.query(
            GroupSource.source_id).filter(GroupSource.group_id.in_(
                [g.id for g in self.current_user.groups])
            ))).order_by(desc(Comment.created_at)).limit(5).all()

        return self.success(
            data={
                'comments': comments,
                'sources': sources,
                'photometry': photometry,
            })
