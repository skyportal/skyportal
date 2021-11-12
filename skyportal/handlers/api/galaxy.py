from baselayer.app.access import permissions, auth_or_token

from ..base import BaseHandler
from ...models import DBSession, Galaxy


class GalaxyCatalogHandler(BaseHandler):
    @permissions(['System admin'])
    async def post(self):
        """
        ---
        description: Ingest a Galaxy catalog
        tags:
          - galaxies
        requestBody:
          content:
            application/json:
              schema: GalaxyHandlerPost
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

        data = self.get_json()
        catalog_name = data.get('catalog_name')
        catalog_data = data.get('catalog_data')

        galaxies = [
            Galaxy(
                catalog_name=catalog_name,
                ra=ra,
                dec=dec,
                name=name,
                distmpc=distmpc,
                sfr_fuv=sfr_fuv,
                mstar=mstar,
                magb=magb,
                a=a,
                b2a=b2a,
                pa=pa,
                btc=btc,
            )
            for ra, dec, name, distmpc, sfr_fuv, mstar, magb, a, b2a, pa, btc in zip(
                catalog_data['ra'],
                catalog_data['dec'],
                catalog_data['name'],
                catalog_data['distmpc'],
                catalog_data['sfr_fuv'],
                catalog_data['mstar'],
                catalog_data['magb'],
                catalog_data['a'],
                catalog_data['b2a'],
                catalog_data['pa'],
                catalog_data['btc'],
            )
        ]

        for galaxy in galaxies:
            DBSession().add(galaxy)
        self.verify_and_commit()

        return self.success()

    @auth_or_token
    def get(self, catalog_name=None):
        """
        ---
          description: Retrieve all galaxies
          tags:
            - galaxies
          parameters:
            - in: catalog_query
              name: name
              schema:
                type: string
              description: Filter by catalog name (exact match)
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfGalaxys
            400:
              content:
                application/json:
                  schema: Error
        """

        catalog_name = self.get_query_argument("catalog_name", None)
        query = Galaxy.query_records_accessible_by(self.current_user, mode="read")
        if catalog_name is not None:
            query = query.filter(Galaxy.catalog_name == catalog_name)
        galaxies = query.all()
        self.verify_and_commit()
        return self.success(data=galaxies)
