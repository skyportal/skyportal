from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import Group


env, cfg = load_env()


class PublicGroupHandler(BaseHandler):
    @auth_or_token
    def get(self, group_id=None):
        """
        ---
        single:
          description: Retrieve the public group
          tags:
            - groups
          responses:
            200:
              content:
                application/json:
                  schema: SingleGroup
        """
        pg = Group.query.filter(Group.name == cfg['misc.public_group_name']).first()
        if pg is None:
            return self.error('Public group does not exist')
        self.verify_permissions()
        return self.success(data=pg)
