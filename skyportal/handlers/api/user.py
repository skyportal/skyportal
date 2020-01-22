from ..base import BaseHandler
from baselayer.app.access import permissions
from ...models import DBSession, User

from sqlalchemy.orm import joinedload


class UserHandler(BaseHandler):
    @permissions(['Manage users'])
    def get(self, user_id=None):
        """
        ---
        description: Retrieve a user
        parameters:
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: SingleUser
          400:
            content:
              application/json:
                schema: Error
        """
        user = User.query.options(joinedload(User.acls)).get(int(user_id))
        if user is None:
            return self.error('Invalid user ID.', data={'id': user_id})
        else:
            return self.success(data={'user': user})

    @permissions(['Manage users'])
    def delete(self, user_id=None):
        """
        ---
        description: Delete a user
        parameters:
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        user_id = int(user_id)
        DBSession.query(User).filter(User.id == user_id).delete()
        DBSession.commit()
        return self.success(data={'user_id': user_id})
