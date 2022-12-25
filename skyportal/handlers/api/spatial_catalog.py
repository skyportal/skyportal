from tornado.ioloop import IOLoop
from sqlalchemy.orm import sessionmaker, scoped_session
import operator  # noqa: F401

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ..base import BaseHandler
from ...models import (
    DBSession,
    SpatialCatalog,
    SpatialCatalogEntry,
    SpatialCatalogEntryTile,
)
from ...utils.gcn import (
    from_ellipse,
)

log = make_log('api/spatial_catalog')

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))

MAX_SPATIAL_CATALOG_ENTRIES = 1000


def add_catalog(catalog_id, catalog_data):

    log(f"Generating catalog with ID {catalog_id}")

    session = Session()
    try:
        entries = []
        for ra, dec, name, amaj, amin, phi in zip(
            catalog_data['ra'],
            catalog_data['dec'],
            catalog_data['name'],
            catalog_data['amaj'],
            catalog_data['amin'],
            catalog_data['phi'],
        ):

            name = name.strip().replace(" ", "-")
            skymap = from_ellipse(name, ra, dec, amaj, amin, phi)
            skymap['entry_name'] = skymap['localization_name']
            del skymap['localization_name']

            entry = SpatialCatalogEntry(**{**skymap, 'catalog_id': catalog_id})
            entries.append(entry)

        session.add_all(entries)
        session.commit()

        for entry in entries:
            tiles = [
                SpatialCatalogEntryTile(
                    entry_name=entry.entry_name, healpix=uniq, probdensity=probdensity
                )
                for uniq, probdensity in zip(entry.uniq, entry.probdensity)
            ]

            session.add_all(tiles)
        session.commit()

        log(f"Generated catalog with ID {catalog_id}")
    except Exception as e:
        log(f"Unable to generate catalog: {e}")
    finally:
        Session.remove()


class SpatialCatalogHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Ingest a Spatial Catalog
        tags:
          - galaxies
        requestBody:
          content:
            application/json:
              schema: SpatialCatalogHandlerPost
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

        if catalog_name is None:
            return self.error("catalog_name is a required parameter.")
        if catalog_data is None:
            return self.error("catalog_data is a required parameter.")

        # check RA bounds
        if any([(x < 0) or (x >= 360) for x in catalog_data['ra']]):
            return self.error("ra should span 0=<ra<360.")

        # check Declination bounds
        if any([(x > 90) or (x < -90) for x in catalog_data['dec']]):
            return self.error("declination should span -90<dec<90.")

        with self.Session() as session:
            catalog = SpatialCatalog(catalog_name=catalog_name)
            session.add(catalog)
            session.commit()

            IOLoop.current().run_in_executor(
                None, lambda: add_catalog(catalog.id, catalog_data)
            )

            return self.success(data={"id": catalog.id})

    @auth_or_token
    async def get(self, catalog_id=None):
        """
        ---
        single:
          description: Retrieve a SpatialCatalog
          tags:
            - spatial_catalogs
          parameters:
            - in: path
              name: catalog_id
              required: true
              schema:
                type: integer
        multiple:
          description: Retrieve all SpatialCatalogs
          tags:
            - spatial_catalogs
        """

        catalog_name = self.get_query_argument("catalog_name", None)

        with self.Session() as session:

            if catalog_id is not None:

                stmt = SpatialCatalog.select(self.current_user).where(
                    SpatialCatalog.id == int(catalog_id)
                )
                catalog = session.scalars(stmt).first()
                if catalog is None:
                    return self.error(f'No catalog with name: {catalog_name}')

                data = catalog.to_dict()
                data['entries'] = [entry.to_dict() for entry in catalog.entries]
                return self.success(data=data)

            stmt = SpatialCatalog.select(self.current_user)
            catalogs = session.scalars(stmt).all()
            data = [catalog.to_dict() for catalog in catalogs]
            return self.success(data=data)

    @auth_or_token
    def delete(self, catalog_id):
        """
        ---
        description: Delete a spatial catalog
        tags:
          - instruments
        parameters:
          - in: path
            name: catalog_id
            required: true
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
        with self.Session() as session:
            stmt = SpatialCatalog.select(session.user_or_token, mode="delete").where(
                SpatialCatalog.id == int(catalog_id)
            )
            catalog = session.scalars(stmt).first()
            if catalog is None:
                return self.error(f'Missing catalog with ID {catalog_id}')

            session.delete(catalog)
            session.commit()

        self.push_all(action="skyportal/REFRESH_SPATIAL_CATALOGS")
        return self.success()
