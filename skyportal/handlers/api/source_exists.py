import conesearch_alchemy as ca

from baselayer.app.access import auth_or_token

from ..base import BaseHandler
from ...models import (
    Obj,
)


class SourceExistsHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        single:
          description: Retrieve a source
          tags:
            - sources
          parameters:
            - in: path
              name: obj_id
              required: false
              schema:
                type: string
        multiple:
          description: Retrieve all sources
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

        ra = self.get_query_argument('ra', None)
        dec = self.get_query_argument('dec', None)
        radius = self.get_query_argument('radius', None)

        if obj_id is not None:
            s = Obj.get_if_accessible_by(obj_id, self.current_user)
            print(obj_id)
            if s is not None:
                return self.success("A source of that name already exists.")
        obj_query = Obj.query_records_accessible_by(self.current_user)
        if any([ra, dec, radius]):
            if not all([ra, dec, radius]):
                return self.error(
                    "If any of 'ra', 'dec' or 'radius' are "
                    "provided, all three are required."
                )
            try:
                ra = float(ra)
                dec = float(dec)
                radius = float(radius)
            except ValueError:
                return self.error(
                    "Invalid values for ra, dec or radius - could not convert to float"
                )
            other = ca.Point(ra=ra, dec=dec)
            obj_query = obj_query.filter(Obj.within(other, radius))
            objs = obj_query.all()
            if len(objs) == 1:
                return self.success(
                    f"A source at that location already exists: {objs[0].id}."
                )
            elif len(objs) > 1:
                return self.success(
                    f"Sources at that location already exist: {','.join([obj.id for obj in objs])}."
                )

        return self.success(False)
