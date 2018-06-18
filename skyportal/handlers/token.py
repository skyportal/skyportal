from baselayer.app.handlers.base import BaseHandler
from ..models import User
from ..model_util import create_token

import tornado.web


class TokenHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        data = self.get_json()

        user = (User.query.filter(User.username == self.current_user.username)
                    .first())
        user_acls = [acl.id for acl in user.acls]
        requested_acls = [k.replace('acls_', '') for k, v in data.items() if
                          k.startswith('acls_') and v == True]
        token_acls = [acl for acl in requested_acls if acl in user_acls]
        token_id = create_token(group_id=data['group_id'],
                                permissions=token_acls,
                                created_by_id=user.id,
                                description=data['description'])
        return self.success(token_id, 'skyportal/FETCH_USER_PROFILE')
