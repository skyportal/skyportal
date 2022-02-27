from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
import sqlalchemy as sa

from ..base import BaseHandler
from ...models import DBSession, Telescope


class TelescopeHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Create telescopes
        tags:
          - telescopes
        requestBody:
          content:
            application/json:
              schema: TelescopeNoID
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: integer
                              description: New telescope ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        schema = Telescope.__schema__()

        try:
            telescope = schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        DBSession().add(telescope)
        self.verify_and_commit()

        self.push_all(action="skyportal/REFRESH_TELESCOPES")
        return self.success(data={"id": telescope.id})

    @auth_or_token
    def get(self, telescope_id=None):
        """
        ---
        single:
          description: Retrieve a telescope
          tags:
            - telescopes
          parameters:
            - in: path
              name: telescope_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleTelescope
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all telescopes
          tags:
            - telescopes
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name (exact match)
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfTelescopes
            400:
              content:
                application/json:
                  schema: Error
        """
        if telescope_id is not None:
            t = DBSession().execute(sa.select(Telescope).get(int(telescope_id)))
            if t is None:
                return self.error(f"Could not load telescope with ID {telescope_id}")
            self.verify_and_commit()
            return self.success(data=t)
        tel_name = self.get_query_argument("name", None)
        query = sa.select(Telescope)
        if tel_name is not None:
            query = query.where(Telescope.name == tel_name)
        data = [t for t, in DBSession().execute(query).all()]
        self.verify_and_commit()
        return self.success(data=data)

    @permissions(['Manage sources'])
    def put(self, telescope_id):
        """
        ---
        description: Update telescope
        tags:
          - telescopes
        parameters:
          - in: path
            name: telescope_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: TelescopeNoID
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
        t = Telescope.query.get(int(telescope_id))
        if t is None:
            return self.error('Invalid telescope ID.')
        data = self.get_json()
        data['id'] = int(telescope_id)

        schema = Telescope.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        self.verify_and_commit()

        self.push_all(action="skyportal/REFRESH_TELESCOPES")
        return self.success()

    @permissions(['Manage sources'])
    def delete(self, telescope_id):
        """
        ---
        description: Delete a telescope
        tags:
          - telescopes
        parameters:
          - in: path
            name: telescope_id
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
        t = Telescope.query.get(int(telescope_id))
        if t is None:
            return self.error('Invalid telescope ID.')

        DBSession().query(Telescope).filter(Telescope.id == int(telescope_id)).delete()
        self.verify_and_commit()

        self.push_all(action="skyportal/REFRESH_TELESCOPES")
        return self.success()
