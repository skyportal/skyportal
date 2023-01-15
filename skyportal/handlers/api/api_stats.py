import sqlalchemy as sa

from baselayer.app.access import permissions

from ..base import BaseHandler
from ...models import (
    APICall,
)


class APIStatsHandler(BaseHandler):
    @permissions(["System admin"])
    def get(self):
        """
        ---
        description: Retrieve basic API statistics
        tags:
          - system_info
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

        data = {}

        with self.Session() as session:
            # Get unique API uris
            uris = session.scalars(sa.select(APICall.uri).distinct()).unique().all()
            for uri in uris:
                stmt = sa.select(APICall).where(APICall.uri == uri)
                data[uri] = session.scalar(sa.select(sa.func.count()).select_from(stmt))
            return self.success(data=data)
