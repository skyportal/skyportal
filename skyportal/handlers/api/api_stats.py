import arrow
import sqlalchemy as sa

from baselayer.app.access import permissions

from ..base import BaseHandler
from ...models import (
    APICall,
    User,
)


class APIStatsHandler(BaseHandler):
    @permissions(["System admin"])
    def get(self):
        """
        ---
        description: Retrieve basic API statistics
        tags:
          - system_info
        parameters:
          - in: query
            name: startDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              created_at >= startDate
          - in: query
            name: endDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              created_at <= endDate
          - in: query
            name: username
            nullable: true
            schema:
              type: string
            description: |
              Username of the user performing the API call.
          - in: query
            name: size
            nullable: true
            schema:
              type: string
            description: |
              Minimum payload size for the API call.
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
                            uri:
                              type: integer
                              description: Number of calls for that uri
        """

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        username = self.get_query_argument('username', None)
        size = self.get_query_argument('size', None)

        data = {}

        with self.Session() as session:
            # Get unique API uris
            uris = sorted(
                session.scalars(sa.select(APICall.uri).distinct()).unique().all()
            )
            for uri in uris:
                stmt = sa.select(APICall).where(APICall.uri == uri)
                if start_date:
                    start_date = str(arrow.get(start_date.strip()).datetime)
                    stmt = stmt.where(APICall.created_at >= start_date)
                if end_date:
                    end_date = str(arrow.get(end_date.strip()).datetime)
                    stmt = stmt.where(APICall.created_at <= end_date)
                if size:
                    stmt = stmt.where(APICall.size >= size)
                if username:
                    user_query = sa.select(User).where(User.username == username)
                    user_subquery = user_query.subquery()
                    stmt = stmt.join(
                        user_subquery, APICall.user_id == user_subquery.c.id
                    )

                data[uri] = session.scalar(sa.select(sa.func.count()).select_from(stmt))
            return self.success(data=data)
