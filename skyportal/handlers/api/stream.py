from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Stream,
    StreamUser,
)


class StreamHandler(BaseHandler):
    @auth_or_token
    def get(self, stream_id=None):
        """
        ---
        single:
          description: Retrieve a stream
          tags:
            - streams
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
                  schema: SingleStream
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all streams
          tags:
            - streams
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfStreams
            400:
              content:
                application/json:
                  schema: Error
        """
        if stream_id is not None:
            s = DBSession().query(Stream).filter(Stream.id == stream_id).first()
            if s is None:
                return self.error("Invalid stream ID.")
            return self.success(data=s)
        streams = DBSession().query(Stream).all()
        self.verify_permissions()
        return self.success(data=streams)

    @permissions(["System admin"])
    def post(self):
        """
        ---
        description: POST a new stream.
        tags:
          - streams
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
        self.finalize_transaction()

        return self.success(data={"id": stream.id})

    @permissions(["System admin"])
    def patch(self, stream_id):
        """
        ---
        description: Update a stream
        tags:
          - streams
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
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        self.finalize_transaction()
        return self.success()

    @permissions(["System admin"])
    def delete(self, stream_id):
        """
        ---
        description: Delete a stream
        tags:
          - streams
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
        self.finalize_transaction()

        return self.success()


class StreamUserHandler(BaseHandler):
    @permissions(["Manage users"])
    def post(self, stream_id, *ignored_args):
        """
        ---
        description: Grant stream access to a user
        tags:
          - streams
          - users
        parameters:
          - in: path
            name: stream_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: integer
                required:
                  - user_id
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
                            stream_id:
                              type: integer
                              description: Stream ID
                            user_id:
                              type: integer
                              description: User ID
        """
        data = self.get_json()

        user_id = data.pop("user_id", None)
        if user_id is None:
            return self.error("User ID must be specified")

        stream_id = int(stream_id)
        su = (
            StreamUser.query.filter(StreamUser.stream_id == stream_id)
            .filter(StreamUser.user_id == user_id)
            .first()
        )
        if su is None:
            DBSession.add(StreamUser(stream_id=stream_id, user_id=user_id))
        else:
            return self.error("Specified user already has access to this stream.")
        self.finalize_transaction()

        return self.success(data={'stream_id': stream_id, 'user_id': user_id})

    @permissions(["Manage users"])
    def delete(self, stream_id, user_id):
        """
        ---
        description: Delete a stream user (revoke stream access for user)
        tags:
          - streams
          - users
        parameters:
          - in: path
            name: stream_id
            required: true
            schema:
              type: integer
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
        """
        su = (
            StreamUser.query.filter(StreamUser.stream_id == stream_id)
            .filter(StreamUser.user_id == user_id)
            .first()
        )
        if su is None:
            return self.error("Stream user does not exist.")
        DBSession().delete(su)
        self.finalize_transaction()
        return self.success()
