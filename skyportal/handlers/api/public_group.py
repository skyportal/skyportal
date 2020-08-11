import tornado.web
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import DBSession, Group, GroupUser, User, Token


env, cfg = load_env()


class PublicGroupHandler(BaseHandler):
    @auth_or_token
    def get(self, group_id=None):
        """
        ---
        single:
          description: Retrieve the ID of the public group
          responses:
            200:
              content:
                application/json:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: object
                        properties:
                          id:
                            type: integer
                            description: ID of the public group
        """
        pg = Group.query.filter(Group.name == cfg['misc.public_group_name']).first()
        if pg is None:
            return self.error('Public group does not exist')
        return self.success(data=pg)

