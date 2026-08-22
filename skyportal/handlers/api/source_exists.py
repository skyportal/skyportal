import conesearch_alchemy as ca
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token

from ...models import (
    Obj,
    Source,
)
from ..base import BaseHandler


class SourceExistsGetQuery(BaseModel):
    """Query parameters for checking whether a source already exists."""

    model_config = ConfigDict(extra="forbid")

    ra: float | None = Field(
        default=None,
        description="RA for spatial filtering (in decimal degrees)",
    )
    dec: float | None = Field(
        default=None,
        description="Declination for spatial filtering (in decimal degrees)",
    )
    radius: float | None = Field(
        default=None,
        description="Radius for spatial filtering if ra & dec are provided (in decimal degrees)",
    )


class SourceExistsHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str = None, *, query: SourceExistsGetQuery = None):
        """
        ---
        single:
          summary: Check if a source exists
          description: Check if a source exists by ID
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
                              source_exists:
                                type: boolean
                              message:
                                type: string
        multiple:
          summary: Check if a source exists by position
          description: Check if a source exists by RA, Dec, and radius
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
                              source_exists:
                                type: boolean
                              message:
                                type: string
        """
        query = self.parse_query(SourceExistsGetQuery)
        ra, dec, radius = query.ra, query.dec, query.radius
        has_position = ra is not None and dec is not None and radius is not None

        if not has_position and not obj_id:
            return self.error(
                "Provide an obj_id, or either ra, dec, and radius for spatial filtering."
            )

        async with self.AsyncSession() as session:
            if obj_id:
                obj_result = await session.scalars(
                    Obj.select(session.user_or_token).where(Obj.id == obj_id)
                )
                s = obj_result.first()
                if s is not None:
                    return self.success(
                        {
                            "source_exists": True,
                            "message": f"A source with the name {obj_id} already exists.",
                        }
                    )
                if not has_position:
                    return self.success(
                        {
                            "source_exists": False,
                            "message": f"No sources exist with the name {obj_id}.",
                        }
                    )

            source_query = Source.select(session.user_or_token)
            other = ca.Point(ra=ra, dec=dec)
            obj_query = Obj.select(session.user_or_token).where(
                Obj.within(other, radius)
            )
            obj_subquery = obj_query.subquery()
            sources_result = await session.scalars(
                source_query.join(
                    obj_subquery, Source.obj_id == obj_subquery.c.id
                ).distinct()
            )
            sources = sources_result.unique().all()
            source_names = list({source.obj_id for source in sources})
            if len(source_names) == 1:
                return self.success(
                    {
                        "source_exists": True,
                        "message": f"A source at that location already exists: {source_names[0]}.",
                    }
                )
            elif len(source_names) > 1:
                return self.success(
                    {
                        "source_exists": True,
                        "message": f"Sources at that location already exist: {','.join(source_names)}.",
                    }
                )
            return self.success(
                {
                    "source_exists": False,
                    "message": f"No sources exist at this location{f' or with the name {obj_id}' if obj_id else ''}.",
                }
            )
