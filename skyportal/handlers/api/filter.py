from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token, permissions

from ...models import Filter
from ..base import BaseHandler


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
    async def post(self):
        """
        ---
        summary: Create a new filter
        description: POST a new filter.
        tags:
          - filters
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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
                              description: New filter ID
        """
        data = self.get_json()
        async with self.AsyncSession() as session:
            schema = Filter.__schema__()
            try:
                fil = schema.load(data)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )
            session.add(fil)
            await session.commit()
            return self.success(data={"id": fil.id})

    @permissions(["Upload data"])
    async def patch(self, filter_id: int):
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
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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

            data = self.get_json()
            data["id"] = filter_id

            schema = Filter.__schema__()
            try:
                fil = schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )

            if fil.group_id != f.group_id or fil.stream_id != f.stream_id:
                return self.error("Cannot update group_id or stream_id.")

            for k in data:
                setattr(f, k, data[k])

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
