from baselayer.app.handlers.base import BaseHandler
from baselayer.app.access import auth_or_token
from ..models import User

import tornado.web


class ProfileHandler(BaseHandler):
    @auth_or_token
    def get(self):
        user = (User.query.filter(User.username == self.current_user.username)
                    .first())
        user_roles = [role.id for role in user.roles]
        user_acls = [acl.id for acl in user.acls]
        user_tokens = [{'id': token.id,
                        'description': token.description,
                        'acls': [acl.id for acl in token.acls],
                        'created_at': token.created_at}
                       for token in user.tokens]
        return self.success({'username': self.current_user.username,
                             'roles': user_roles,
                             'acls': user_acls,
                             'tokens': user_tokens})
