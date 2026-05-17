from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import Group
from ..base import BaseHandler

env, cfg = load_env()


class PublicGroupHandler(BaseHandler):
    @auth_or_token
    async def get(self, group_id=None):
        """
        ---
        single:
          summary: Get the public group
          description: Retrieve the public group
          tags:
            - groups
          responses:
            200:
              content:
                application/json:
                  schema: SingleGroup
        """
        async with self.AsyncSession() as session:
            pg = await session.scalar(
                Group.select(session.user_or_token).where(
                    Group.name == cfg["misc.public_group_name"]
                )
            )
            if pg is None:
                return self.error("Public group does not exist")
            return self.success(data=pg)
