import tornado.web
from baselayer.app.access import permissions
from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Source, User, Comment, Role


class CommentHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, comment_id):
        # TODO: Ensure that it's okay for anyone to read any comment
        comment = Comment.query.get(comment_id)
        return self.success(data=comment)

    @permissions(['Comment'])
    def post(self):
        data = self.get_json()
        source_id = data['source_id'];

        comment = Comment(user=self.current_user,
                          text=data['text'], source_id=source_id)

        DBSession().add(comment)
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'source_id': comment.source_id})
        return self.success()

    @permissions(['Comment'])
    def put(self, comment_id):
        data = self.get_json()

        # TODO: Check ownership
        comment = Comment.query.get(comment_id)
        comment.text = data['text']

        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'source_id': comment.source_id})
        return self.success()

    @permissions(['Comment'])
    def delete(self, comment_id):
        # TODO: Check ownership
        comment = Comment.query.get(comment_id)
        DBSession().delete(c)
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'source_id': comment.source_id})
        return self.success()
