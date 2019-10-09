from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from .base import BaseHandler
from ..models import DBSession, Telescope


class TelescopeHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Create telescopes
        parameters:
          - in: path
            name: telescope
            schema: Telescope
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        id:
                          type: integer
                          description: New telescope ID
        """
        data = self.get_json()
        schema = Telescope.__schema__()

        try:
            telescope = schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession.add(telescope)
        DBSession().commit()

        return self.success(data={"id": telescope.id})

    @auth_or_token
    def get(self, telescope_id):
        info = {}
        info['telescope'] = Telescope.query.get(int(telescope_id))

        if info['telescope'] is not None:
            return self.success(data=info)
        else:
            return self.error(f"Could not load telescope {telescope_id}",
                              data={"telescope_id": telescope_id})

    @permissions(['Manage sources'])
    def put(self, telescope_id):
        data = self.get_json()
        data['id'] = int(telescope_id)

        schema = Telescope.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, telescope_id):
        DBSession.query(Telescope).filter(Telescope.id == int(telescope_id)).delete()
        DBSession().commit()

        return self.success()
