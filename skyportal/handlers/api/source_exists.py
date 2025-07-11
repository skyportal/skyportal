import conesearch_alchemy as ca

from baselayer.app.access import auth_or_token

from ...models import (
    Obj,
    Source,
)
from ..base import BaseHandler


class SourceExistsHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        single:
          summary: Check if a source exists
          description: Check if a source exists by ID
          tags:
            - sources
          parameters:
            - in: path
              name: obj_id
              required: false
              schema:
                type: string
        multiple:
          summary: Check if a source exists by position
          description: Check if a source exists by RA, Dec, and radius
          tags:
            - sources
          parameters:
          - in: query
            name: ra
            nullable: true
            schema:
              type: number
            description: RA for spatial filtering (in decimal degrees)
          - in: query
            name: dec
            nullable: true
            schema:
              type: number
            description: Declination for spatial filtering (in decimal degrees)
          - in: query
            name: radius
            nullable: true
            schema:
              type: number
            description: Radius for spatial filtering if ra & dec are provided (in decimal degrees)
        """

        ra = self.get_query_argument("ra", None)
        dec = self.get_query_argument("dec", None)
        radius = self.get_query_argument("radius", None)

        if not (all([ra, dec, radius]) or obj_id):
            return self.error(
                "Provide an obj_id, or either ra, dec, and radius for spatial filtering."
            )

        with self.Session() as session:
            if obj_id:
                s = session.scalars(
                    Obj.select(session.user_or_token).where(Obj.id == obj_id)
                ).first()
                if s is not None:
                    return self.success(
                        {
                            "source_exists": True,
                            "message": f"A source with the name {obj_id} already exists.",
                        }
                    )
                if not all([ra, dec, radius]):
                    return self.success(
                        {
                            "source_exists": False,
                            "message": f"No sources exist with the name {obj_id}.",
                        }
                    )

            source_query = Source.select(session.user_or_token)
            try:
                ra = float(ra)
                dec = float(dec)
                radius = float(radius)
            except ValueError:
                return self.error(
                    "Invalid values for ra, dec or radius - could not convert to float"
                )
            other = ca.Point(ra=ra, dec=dec)
            obj_query = Obj.select(session.user_or_token).where(
                Obj.within(other, radius)
            )
            obj_subquery = obj_query.subquery()
            sources = (
                session.scalars(
                    source_query.join(
                        obj_subquery, Source.obj_id == obj_subquery.c.id
                    ).distinct()
                )
                .unique()
                .all()
            )
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
