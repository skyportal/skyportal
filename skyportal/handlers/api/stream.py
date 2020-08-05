from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Stream,
)


class StreamHandler(BaseHandler):
    @auth_or_token
    def get(self, stream_id=None):
        """
        ---
        single:
          description: Retrieve a stream
          parameters:
            - in: path
              name: filter_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleFilter
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all streams
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfFilters
            400:
              content:
                application/json:
                  schema: Error
        """
        if stream_id is not None:
            # fixme: add ACLs! Users should be created with specific Stream access permissions
            # s = Stream.get_if_owned_by(stream_id, self.current_user)
            s = DBSession().query(Stream).filter(Stream.id == stream_id).first()
            if s is None:
                return self.error("Invalid stream ID.")
            return self.success(data=s)
        streams = (
            DBSession().query(Stream)
            # fixme: results in error "'Token' object has no attribute 'streams'"
            # .filter(Stream.id.in_([s.id for s in self.current_user.streams]))
            .all()
        )
        return self.success(data=streams)

    @permissions(["System admin"])
    def post(self):
        """
        ---
        description: POST a new stream.
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  altdata:
                    type: object
                required:
                  - name
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
                              description: New stream ID
        """
        data = self.get_json()
        schema = Stream.__schema__()
        try:
            stream = schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        DBSession().add(stream)
        DBSession().commit()

        return self.success(data={"id": stream.id})

    @permissions(["System admin"])
    def patch(self, stream_id):
        """
        ---
        description: Update a stream
        parameters:
          - in: path
            name: stream_id
            required: True
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  altdata:
                    type: object
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
        data = self.get_json()
        data["id"] = stream_id
        schema = Stream.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()
        return self.success()

    @permissions(["System admin"])
    def delete(self, stream_id):
        """
        ---
        description: Delete a stream
        parameters:
          - in: path
            name: stream_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        DBSession().delete(Stream.query.get(stream_id))
        DBSession().commit()

        return self.success()
