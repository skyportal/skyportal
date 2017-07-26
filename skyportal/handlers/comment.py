from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Source, User, Comment
import tornado.web


class SourceCommentsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, source_id):
        comments_username = (Comment
                             .query
                             .filter(Source.id == source_id)
                             .all())

        return self.success(comments_username)


class CommentHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, comment_id):
        comment_id = int(comment_id)

        # TODO: Ensure that it's okay for anyone to read any comment
        comment = Comment.query.get(comment_id)
        return self.success(comment)

    @tornado.web.authenticated
    def post(self):
        data = self.get_json()

        c = Comment(user_id=self.current_user.username,
                    text=data['text'], source_id=data['source_id'])

        DBSession().add(c)
        DBSession().commit()

        return self.success({"id": s.id}, 'cesium/FETCH_COMMENTS')

    @tornado.web.authenticated
    def put(self, comment_id):
        data = self.get_json()

        # TODO: Check ownership
        c = Comment.query.get(comment_id)
        c.text = data['text']

        DBSession().commit()

        return self.success(action='cesium/FETCH_COMMENTS')

    @tornado.web.authenticated
    def delete(self, comment_id):
        # TODO: Check ownership
        c = Comment.query.get(source_id)
        DBSession().delete(c)
        DBSession().commit()

        return self.success(action='cesium/FETCH_COMMENTS')
