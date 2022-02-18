import sqlalchemy as sa
from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import Group, DBSession


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
        pg = (
            DBSession.execute(
                sa.select(Group).filter(Group.name == cfg['misc.public_group_name'])
            )
            .scalars()
            .first()
        )
        if pg is None:
            return self.error('Public group does not exist')
        self.verify_and_commit()
        return self.success(data=pg)
