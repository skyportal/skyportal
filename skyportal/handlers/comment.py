import tornado.web
import base64
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Source, User, Comment, Role


class CommentHandler(BaseHandler):
    @auth_or_token
    def get(self, comment_id, action=None):
        comment = Comment.query.get(comment_id)
        if action == 'download_attachment':
            self.set_header(
                "Content-Disposition", "attachment; "
                f"filename={comment.attachment_name}")
            self.write(base64.b64decode(comment.attachment_bytes))
        else:
            # TODO: Ensure that it's okay for anyone to read any comment
            return self.success(data=comment)

    @permissions(['Comment'])
    def post(self):
        data = self.get_json()
        source_id = data['source_id']
        if 'attachment' in data and 'body' in data['attachment']:
            attachment_bytes = str.encode(data['attachment']['body']
                                          .split('base64,')[-1])
            attachment_name = data['attachment']['name']
        else:
            attachment_bytes, attachment_name = None, None

        comment = Comment(user=self.current_user, text=data['text'],
                          source_id=source_id, attachment_bytes=attachment_bytes,
                          attachment_name=attachment_name)

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
