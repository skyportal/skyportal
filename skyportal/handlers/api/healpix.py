import sqlalchemy as sa
from sqlalchemy import func
import healpix_alchemy as ha
import astropy.units as u

from ..base import BaseHandler
from ...models import (
    Obj,
)
from baselayer.app.access import permissions

DEFAULT_SOURCES_PER_PAGE = 100
MAX_SOURCES_PER_PAGE = 500


class HealpixUpdateHandler(BaseHandler):
    @permissions(['System admin'])
    def get(self):
        """
        ---
        summary: Get a count of sources w/ and w/o Healpix values
        description: find the number of sources with and without a Healpix value
        tags:
          - sources
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
                              totalWithoutHealpix:
                                type: integer
                              totalWithHealpix:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:
            stmt = sa.select(Obj).where(Obj.healpix.is_(None))
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_missing = session.execute(count_stmt).scalar()

            # get the number of Objs with Healpix
            stmt = sa.select(Obj).where(Obj.healpix.isnot(None))
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_healpix = session.execute(count_stmt).scalar()

        results = {
            'totalWithoutHealpix': total_missing,
            'totalWithHealpix': total_healpix,
        }
        return self.success(data=results)

    @permissions(['System admin'])
    def post(self):
        """
        ---
        summary: Calculate Healpix values for sources w/o them
        description: calculate healpix values for a batch of sources without a Healpix value
        tags:
          - sources
        parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of sources to check for updates. Defaults to 100. Max 500.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for iterating through all sources. Defaults to 1
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
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              numPerPage:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        try:
            page_number = int(self.get_query_argument('pageNumber', 1))
            num_per_page = min(
                int(self.get_query_argument("numPerPage", DEFAULT_SOURCES_PER_PAGE)),
                MAX_SOURCES_PER_PAGE,
            )
        except ValueError:
            return self.error(
                f'Cannot parse inputs pageNumber ({page_number}) '
                f'or numPerPage ({num_per_page}) as an integers.'
            )

        with self.Session() as session:
            stmt = sa.select(Obj).where(Obj.healpix.is_(None))
            # select only objects that don't have a Healpix value
            count_stmt = sa.select(func.count()).select_from(stmt)
            total_matches = session.execute(count_stmt).scalar()
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            objects = session.execute(stmt).scalars().unique().all()

            for i, obj in enumerate(objects):
                obj.healpix = ha.constants.HPX.lonlat_to_healpix(
                    obj.ra * u.deg, obj.dec * u.deg
                )
            session.commit()

        results = {
            'totalMatches': total_matches,
            'numPerPage': num_per_page,
            'pageNumber': page_number,
        }
        return self.success(data=results)
