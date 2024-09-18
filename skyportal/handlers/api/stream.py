from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    Stream,
    StreamUser,
)


class StreamHandler(BaseHandler):
    @auth_or_token
    def get(self, stream_id=None):
        """
        ---
        single:
          summary: Get a stream
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
          summary: Get all streams
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
        with self.Session() as session:
            if stream_id is not None:
                s = session.scalars(
                    Stream.select(session.user_or_token).where(Stream.id == stream_id)
                ).first()
                if s is None:
                    return self.error(f"Could not retrieve stream with ID {stream_id}.")
                return self.success(data=s)
            streams = session.scalars(Stream.select(session.user_or_token)).all()
            return self.success(data=streams)

    @permissions(["System admin"])
    def post(self):
        """
        ---
        summary: Create a new stream
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
        with self.Session() as session:
            schema = Stream.__schema__()
            try:
                stream = schema.load(data)
            except ValidationError as e:
                return self.error(
                    "Invalid/missing parameters: " f"{e.normalized_messages()}"
                )
            session.add(stream)
            session.commit()

            return self.success(data={"id": stream.id})

    @permissions(["System admin"])
    def patch(self, stream_id):
        """
        ---
        summary: Update a stream
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
        with self.Session() as session:
            s = session.scalars(
                Stream.select(session.user_or_token, mode="update").where(
                    Stream.id == stream_id
                )
            ).first()
            if s is None:
                return self.error(f"Could not retrieve stream with ID {stream_id}.")

            schema = Stream.__schema__()
            try:
                schema.load(data)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )
            for k in data:
                setattr(s, k, data[k])

            session.commit()
            return self.success()

    @permissions(["System admin"])
    def delete(self, stream_id):
        """
        ---
        summary: Delete a stream
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
        with self.Session() as session:
            stream = session.scalars(
                Stream.select(session.user_or_token, mode="delete").where(
                    Stream.id == stream_id
                )
            ).first()
            if stream is None:
                return self.error(f"Could not retrieve stream with ID {stream_id}.")
            session.delete(stream)
            session.commit()

            return self.success()


class StreamUserHandler(BaseHandler):
    @permissions(["System admin"])
    def post(self, stream_id, *ignored_args):
        """
        ---
        summary: Grant stream access to a user
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
        with self.Session() as session:
            su = session.scalars(
                StreamUser.select(session.user_or_token)
                .where(StreamUser.stream_id == stream_id)
                .where(StreamUser.user_id == user_id)
            ).first()
            if su is None:
                session.add(StreamUser(stream_id=stream_id, user_id=user_id))
            else:
                return self.error("Specified user already has access to this stream.")
            session.commit()

            return self.success(data={'stream_id': stream_id, 'user_id': user_id})

    @permissions(["System admin"])
    def delete(self, stream_id, user_id):
        """
        ---
        summary: Revoke stream access from a user
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
        with self.Session() as session:
            su = session.scalars(
                StreamUser.select(session.user_or_token, mode="delete")
                .where(StreamUser.stream_id == stream_id)
                .where(StreamUser.user_id == user_id)
            ).first()
            if su is None:
                return self.error("Stream user does not exist.")
            session.delete(su)
            session.commit()
            return self.success()
