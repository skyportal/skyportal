from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import joinedload, load_only

from baselayer.app.access import auth_or_token, permissions

from ...models import Broker, Filter, set_autosave
from ..base import BaseHandler
from .group import has_admin_access_for_group


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
    broker_id: int | None = Field(
        default=None,
        description="ID of the Broker this Filter runs on. Can only be set "
        "while the filter has none: moving a filter between brokers would "
        "orphan whatever the first one holds for it.",
    )
    autosave: bool | None = Field(
        default=None,
        description="Whether objects passing this filter during broker ingestion "
        "are auto-saved as Sources to the Filter's Group.",
    )


class FilterGetQuery(BaseModel):
    """Query parameters for listing filters."""

    model_config = ConfigDict(extra="forbid")

    group_id: int | None = Field(
        default=None,
        description="Only return filters belonging to this Group.",
    )
    stream_id: int | None = Field(
        default=None,
        description="Only return filters reading from this Stream.",
    )


# A filter's altdata holds its whole broker definition, which runs to tens of
# kilobytes apiece and is only of use one filter at a time. The list leaves it
# out; GET on a single filter still returns it.
LIST_FIELDS = (
    "id",
    "name",
    "group_id",
    "stream_id",
    "broker_id",
    "autosave",
    "created_at",
    "modified",
)


class FilterHandler(BaseHandler):
    @auth_or_token
    async def get(self, filter_id: int | None = None, *, query: FilterGetQuery = None):
        """
        ---
        single:
          summary: Get a filter
          description: Retrieve a filter
          tags:
            - filters
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
          description: |
            Retrieve all filters, optionally restricted to one group or stream.
            Each filter is returned without its altdata, which holds the whole
            broker definition; GET on a single filter returns that.
          tags:
            - filters
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfFilterListItems
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

            query = self.parse_query(FilterGetQuery)
            stmt = Filter.select(
                session.user_or_token,
                options=[load_only(*(getattr(Filter, f) for f in LIST_FIELDS))],
            )
            if query.group_id is not None:
                stmt = stmt.where(Filter.group_id == query.group_id)
            if query.stream_id is not None:
                stmt = stmt.where(Filter.stream_id == query.stream_id)

            # The access-control join returns a row per group membership, so the
            # same filter comes back once per member without unique().
            filters = (await session.scalars(stmt)).unique().all()
            return self.success(
                data=[{f: getattr(fil, f) for f in LIST_FIELDS} for fil in filters]
            )

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
                Filter.select(
                    session.user_or_token,
                    mode="update",
                    options=[joinedload(Filter.broker)],
                ).where(Filter.id == filter_id)
            )
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")

            if not await has_admin_access_for_group(
                self.associated_user_object, f.group_id, session
            ):
                return self.error(
                    "Insufficient permissions: must be a group admin or system "
                    "admin to modify a filter.",
                    status=403,
                )

            if (body.group_id is not None and body.group_id != f.group_id) or (
                body.stream_id is not None and body.stream_id != f.stream_id
            ):
                return self.error("Cannot update group_id or stream_id.")

            # A filter created without one cannot otherwise be attached to a
            # broker at all, and without a broker it is never ingested.
            if body.broker_id is not None and body.broker_id != f.broker_id:
                if f.broker_id is not None:
                    return self.error(
                        "Cannot move a filter to a different broker; create a "
                        "new filter instead."
                    )
                broker = await session.scalar(
                    Broker.select(session.user_or_token).where(
                        Broker.id == body.broker_id
                    )
                )
                if broker is None:
                    return self.error(f"No accessible broker {body.broker_id}.")
                f.broker_id = body.broker_id

            # A renamed filter must be renamed on the broker too, or the two
            # names drift and the broker-side filter becomes unidentifiable.
            # Unlike delete, this is not best-effort: fail rather than drift.
            if body.name is not None and body.name != f.name:
                broker = f.broker
                broker_filter_id = ((f.altdata or {}).get("boom") or {}).get(
                    "filter_id"
                )
                if (
                    broker is not None
                    and broker_filter_id is not None
                    and broker.broker_class.implements().get("update_filter")
                ):
                    try:
                        broker.broker_class.update_filter(
                            broker,
                            session,
                            boom_filter_id=broker_filter_id,
                            name=body.name,
                        )
                    except Exception as e:
                        return self.error(
                            f"Failed to rename filter on {broker.name}: {e}"
                        )

            if body.name is not None:
                f.name = body.name
            if body.altdata is not None:
                f.altdata = body.altdata
            if body.autosave is not None:
                set_autosave(f, body.autosave)

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
