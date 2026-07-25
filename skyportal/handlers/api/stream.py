from typing import Any

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app import models as baselayer_models
from baselayer.app.access import auth_or_token, permissions

from ...models import (
    Stream,
    StreamUser,
)
from ..base import BaseHandler


class StreamPostBody(BaseModel):
    """Request body for creating a stream."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Stream name.")
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Misc. metadata stored in JSON format, e.g. "
        "`{'collection': 'ZTF_alerts', selector: [1, 2]}`",
    )
    auto_join: bool = Field(
        default=False,
        description="Boolean indicating whether any user may add themselves "
        "to this stream. Auto-join streams are visible to all users.",
    )


class StreamPostResponse(BaseModel):
    """Data payload returned when creating a stream."""

    id: int = Field(description="New stream ID")


class StreamPatchBody(BaseModel):
    """Request body for updating a stream."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Stream name.")
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Misc. metadata stored in JSON format, e.g. "
        "`{'collection': 'ZTF_alerts', selector: [1, 2]}`",
    )
    auto_join: bool | None = Field(
        default=None,
        description="Boolean indicating whether any user may add themselves "
        "to this stream. Auto-join streams are visible to all users.",
    )


class StreamUserPostBody(BaseModel):
    """Request body for granting stream access to a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(description="ID of the user to be granted stream access")


class StreamUserPostResponse(BaseModel):
    """Data payload returned when granting stream access to a user."""

    stream_id: int = Field(description="Stream ID")
    user_id: int = Field(description="User ID")


class StreamHandler(BaseHandler):
    @auth_or_token
    async def get(self, stream_id: int | None = None):
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
        if stream_id is not None:
            try:
                stream_id = int(stream_id)
            except (TypeError, ValueError):
                return self.error(f"Invalid stream_id: {stream_id}")
        async with self.AsyncSession() as session:
            if stream_id is not None:
                s = await session.scalar(
                    Stream.select(session.user_or_token).where(Stream.id == stream_id)
                )
                if s is None:
                    return self.error(f"Could not retrieve stream with ID {stream_id}.")
                return self.success(data=s)
            result = await session.scalars(Stream.select(session.user_or_token))
            return self.success(data=result.all())

    @permissions(["System admin"])
    async def post(self, *, body: StreamPostBody = None) -> StreamPostResponse:
        """
        ---
        summary: Create a new stream
        description: POST a new stream.
        tags:
          - streams
        """
        body = self.parse_body(StreamPostBody)
        async with self.AsyncSession() as session:
            stream = Stream(
                name=body.name, altdata=body.altdata, auto_join=body.auto_join
            )
            session.add(stream)
            await session.commit()

            return self.success(data={"id": stream.id})

    @permissions(["System admin"])
    async def patch(self, stream_id: int, *, body: StreamPatchBody = None):
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
        body = self.parse_body(StreamPatchBody)
        try:
            stream_id = int(stream_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid stream_id: {stream_id}")
        async with self.AsyncSession() as session:
            s = await session.scalar(
                Stream.select(session.user_or_token, mode="update").where(
                    Stream.id == stream_id
                )
            )
            if s is None:
                return self.error(f"Could not retrieve stream with ID {stream_id}.")

            s.name = body.name
            if "altdata" in body.model_fields_set:
                s.altdata = body.altdata
            if body.auto_join is not None:
                s.auto_join = body.auto_join

            await session.commit()
            return self.success()

    @permissions(["System admin"])
    async def delete(self, stream_id: int):
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
        try:
            stream_id = int(stream_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid stream_id: {stream_id}")
        async with self.AsyncSession() as session:
            stream = await session.scalar(
                Stream.select(session.user_or_token, mode="delete").where(
                    Stream.id == stream_id
                )
            )
            if stream is None:
                return self.error(f"Could not retrieve stream with ID {stream_id}.")
            await session.delete(stream)
            await session.commit()

            return self.success()


class StreamUserHandler(BaseHandler):
    @auth_or_token
    async def post(
        self, stream_id: int, *ignored_args, body: StreamUserPostBody = None
    ) -> StreamUserPostResponse:
        """
        ---
        summary: Grant stream access to a user
        description: |
          Grant stream access to a user. System admins may add any user; a
          non-admin user may add only themselves, and only to an auto-join
          stream.
        tags:
          - streams
          - users
        parameters:
          - in: path
            name: stream_id
            required: true
            schema:
              type: integer
        """
        body = self.parse_body(StreamUserPostBody)
        user_id = body.user_id

        try:
            stream_id = int(stream_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid stream_id/user_id: {stream_id}/{user_id}")

        async with self.AsyncSession() as session:
            # Plain select (not RLS-gated) so we can make an explicit
            # authorization decision below rather than leaking it as "not found".
            stream = await session.scalar(
                sa.select(Stream).where(Stream.id == stream_id)
            )
            if stream is None:
                return self.error(f"Could not retrieve stream with ID {stream_id}.")

            # A non-admin may add only themselves, and only to an auto-join stream.
            self_join = user_id == self.associated_user_object.id and stream.auto_join
            if not self.current_user.is_system_admin and not self_join:
                return self.error(
                    "Insufficient permissions: only system admins can grant stream "
                    "access to other users or to non-auto-join streams."
                )

            # Plain select (not RLS-gated) so an already-present membership is
            # detected even for a self-joining non-admin.
            su = await session.scalar(
                sa.select(StreamUser)
                .where(StreamUser.stream_id == stream_id)
                .where(StreamUser.user_id == user_id)
            )
            if su is not None:
                return self.error("Specified user already has access to this stream.")

        # StreamUser.create is restricted; add via an unverified session so a
        # self-joining non-admin can be granted access.
        async with baselayer_models.async_plain_session_factory() as plain_session:
            plain_session.add(StreamUser(stream_id=stream_id, user_id=user_id))
            await plain_session.commit()

        self.push(action="skyportal/FETCH_USER_PROFILE")
        return self.success(data={"stream_id": stream_id, "user_id": user_id})

    @permissions(["System admin"])
    async def delete(self, stream_id: int, user_id: int):
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
        try:
            stream_id = int(stream_id)
            user_id = int(user_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid stream_id/user_id: {stream_id}/{user_id}")
        async with self.AsyncSession() as session:
            su = await session.scalar(
                StreamUser.select(session.user_or_token, mode="delete")
                .where(StreamUser.stream_id == stream_id)
                .where(StreamUser.user_id == user_id)
            )
            if su is None:
                return self.error("Stream user does not exist.")
            await session.delete(su)
            await session.commit()
            return self.success()
