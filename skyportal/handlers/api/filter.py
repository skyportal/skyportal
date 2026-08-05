from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token, permissions

from ...models import Filter
from ..base import BaseHandler


class FilterPostBody(BaseModel):
    """Request body for creating a filter."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Filter name.")
    stream_id: int = Field(description="ID of the Filter's Stream.")
    group_id: int = Field(description="ID of the Filter's Group.")
    broker_id: int | None = Field(
        default=None,
        description="ID of the Broker this Filter runs on, if any.",
    )
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary additional JSON data associated with the Filter.",
    )


class FilterPostResponse(BaseModel):
    """Data payload returned when creating a filter."""

    id: int = Field(description="New filter ID")


class FilterPatchBody(BaseModel):
    """Request body for updating a filter."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Filter name.")
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary additional JSON data associated with the Filter.",
    )
    group_id: int | None = Field(
        default=None,
        description="ID of the Filter's Group. Cannot be changed; accepted "
        "only if it matches the current value.",
    )
    stream_id: int | None = Field(
        default=None,
        description="ID of the Filter's Stream. Cannot be changed; accepted "
        "only if it matches the current value.",
    )


class FilterHandler(BaseHandler):
    @auth_or_token
    async def get(self, filter_id: int | None = None):
        """
        ---
        single:
          summary: Get a filter
          description: Retrieve a filter
          tags:
            - filters
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
          summary: Get all filters
          description: Retrieve all filters
          tags:
            - filters
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

        async with self.AsyncSession() as session:
            if filter_id is not None:
                f = await session.scalar(
                    Filter.select(
                        session.user_or_token, options=[joinedload(Filter.stream)]
                    ).where(Filter.id == filter_id)
                )
                if f is None:
                    return self.error(f"Cannot find a filter with ID: {filter_id}.")

                return self.success(data=f)

            list_result = await session.scalars(Filter.select(session.user_or_token))
            return self.success(data=list_result.all())

    @permissions(["Upload data"])
    async def post(self, *, body: FilterPostBody = None) -> FilterPostResponse:
        """
        ---
        summary: Create a new filter
        description: POST a new filter.
        tags:
          - filters
        """
        body = self.parse_body(FilterPostBody)
        async with self.AsyncSession() as session:
            fil = Filter(
                name=body.name,
                stream_id=body.stream_id,
                group_id=body.group_id,
                broker_id=body.broker_id,
                altdata=body.altdata,
            )
            session.add(fil)
            await session.commit()
            return self.success(data={"id": fil.id})

    @permissions(["Upload data"])
    async def patch(self, filter_id: int, *, body: FilterPatchBody = None):
        """
        ---
        summary: Update a filter
        description: Update filter name
        tags:
          - filters
        parameters:
          - in: path
            name: filter_id
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
        body = self.parse_body(FilterPatchBody)
        try:
            filter_id = int(filter_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid filter_id: {filter_id}")
        async with self.AsyncSession() as session:
            f = await session.scalar(
                Filter.select(session.user_or_token, mode="update").where(
                    Filter.id == filter_id
                )
            )
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")

            if (body.group_id is not None and body.group_id != f.group_id) or (
                body.stream_id is not None and body.stream_id != f.stream_id
            ):
                return self.error("Cannot update group_id or stream_id.")

            if body.name is not None:
                f.name = body.name
            if body.altdata is not None:
                f.altdata = body.altdata

            await session.commit()
            return self.success()

    @permissions(["Upload data"])
    async def delete(self, filter_id: int):
        """
        ---
        summary: Delete a filter
        description: Delete a filter
        tags:
          - filters
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
                schema: Success
        """

        try:
            filter_id = int(filter_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid filter_id: {filter_id}")
        async with self.AsyncSession() as session:
            f = await session.scalar(
                Filter.select(session.user_or_token, mode="delete").where(
                    Filter.id == filter_id
                )
            )
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")
            await session.delete(f)
            await session.commit()
            return self.success()
