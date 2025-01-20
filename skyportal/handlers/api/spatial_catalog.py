import time
from io import StringIO

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import scoped_session, sessionmaker
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...models import (
    DBSession,
    SpatialCatalog,
    SpatialCatalogEntry,
    SpatialCatalogEntryTile,
)
from ...utils.gcn import (
    from_cone,
    from_ellipse,
)
from ..base import BaseHandler

log = make_log("api/spatial_catalog")

Session = scoped_session(sessionmaker())

MAX_SPATIAL_CATALOG_ENTRIES = 1000


def add_catalog(catalog_id, catalog_data):
    log(f"Generating catalog with ID {catalog_id}")
    start = time.time()

    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        entries = []
        # check for cone key
        if {"radius"}.issubset(set(catalog_data.keys())):
            for ra, dec, name, radius in zip(
                catalog_data["ra"],
                catalog_data["dec"],
                catalog_data["name"],
                catalog_data["radius"],
            ):
                name = name.strip().replace(" ", "-")
                skymap = from_cone(ra, dec, radius, n_sigma=2)
                del skymap["localization_name"]
                skymap["entry_name"] = name

                data = {"ra": ra, "dec": dec, "radius": radius}

                entry = SpatialCatalogEntry(
                    **{**skymap, "catalog_id": catalog_id, "data": data}
                )
                entries.append(entry)
        elif {"amaj", "amin", "phi"}.issubset(set(catalog_data.keys())):
            for ra, dec, name, amaj, amin, phi in zip(
                catalog_data["ra"],
                catalog_data["dec"],
                catalog_data["name"],
                catalog_data["amaj"],
                catalog_data["amin"],
                catalog_data["phi"],
            ):
                name = name.strip().replace(" ", "-")
                if np.isclose(amaj, amin):
                    skymap = from_cone(ra, dec, amaj, n_sigma=1)
                else:
                    skymap = from_ellipse(name, ra, dec, amaj, amin, phi)
                skymap["entry_name"] = skymap["localization_name"]
                del skymap["localization_name"]

                data = {"ra": ra, "dec": dec, "amaj": amaj, "amin": amin, "phi": phi}

                entry = SpatialCatalogEntry(
                    **{**skymap, "catalog_id": catalog_id, "data": data}
                )
                entries.append(entry)

        else:
            return ValueError("Could not disambiguate keys")

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

        flow = Flow()
        flow.push(
            "*",
            "skyportal/REFRESH_SPATIAL_CATALOGS",
        )

        end = time.time()
        duration = end - start

        log(f"Generated catalog with ID {catalog_id} in {duration} seconds")
    except Exception as e:
        log(f"Unable to generate catalog: {e}")
    finally:
        session.close()
        Session.remove()


def delete_catalog(catalog_id):
    log(f"Deleting catalog with ID {catalog_id}")

    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        catalog = session.scalar(
            sa.select(SpatialCatalog).where(SpatialCatalog.id == int(catalog_id))
        )
        session.delete(catalog)
        session.commit()

        flow = Flow()
        flow.push(
            "*",
            "skyportal/REFRESH_SPATIAL_CATALOGS",
        )

        log(f"Deleted catalog with ID {catalog_id}")
    except Exception as e:
        log(f"Unable to delete catalog: {e}")
    finally:
        session.close()
        Session.remove()


class SpatialCatalogHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        summary: Ingest a Spatial Catalog
        description: Ingest a Spatial Catalog
        tags:
          - spatial catalogs
        requestBody:
          content:
            application/json:
              schema: SpatialCatalogHandlerPost
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
                              description: New spatial catalog ID
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        catalog_name = data.get("catalog_name")
        catalog_data = data.get("catalog_data")

        if catalog_name is None:
            return self.error("catalog_name is a required parameter.")
        if catalog_data is None:
            return self.error("catalog_data is a required parameter.")

        if type(catalog_name) is not str:
            return self.error("catalog_name must be a string")

        if type(catalog_data) is not dict:
            return self.error("catalog_data must be a dictionary")

        # check for required parameters
        if not {"name", "ra", "dec"}.issubset(set(catalog_data.keys())):
            return self.error("name, ra, and dec required in field_data.")

        # check RA bounds
        if any((x < 0) or (x >= 360) for x in catalog_data["ra"]):
            return self.error("ra should span 0=<ra<360.")

        # check Declination bounds
        if any((x > 90) or (x < -90) for x in catalog_data["dec"]):
            return self.error("declination should span -90<dec<90.")

        # check for cone or ellipse keys
        if (not {"radius"}.issubset(set(catalog_data.keys()))) and (
            not {"amaj", "amin", "phi"}.issubset(set(catalog_data.keys()))
        ):
            return self.error("error or amaj, amin, and phi required in field_data.")

        with self.Session() as session:
            stmt = SpatialCatalog.select(self.current_user).where(
                SpatialCatalog.catalog_name == catalog_name
            )
            catalog = session.scalars(stmt).first()
            if catalog is None:
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
          summary: Get a Spatial Catalog
          description: Retrieve a SpatialCatalog
          tags:
            - spatial catalogs
          parameters:
            - in: path
              name: catalog_id
              required: true
              schema:
                type: integer
        multiple:
          summary: Get all Spatial Catalogs
          description: Retrieve all SpatialCatalogs
          tags:
            - spatial catalogs
        """

        catalog_name = self.get_query_argument("catalog_name", None)

        with self.Session() as session:
            if catalog_id is not None:
                try:
                    catalog_id = int(catalog_id)
                except ValueError:
                    return self.error("catalog_id must be an integer")

                stmt = SpatialCatalog.select(self.current_user).where(
                    SpatialCatalog.id == catalog_id
                )
                catalog = session.scalars(stmt).first()
                if catalog is None:
                    return self.error(f"No catalog with name: {catalog_name}")

                data = catalog.to_dict()
                data["entries"] = [entry.to_dict() for entry in catalog.entries]
                return self.success(data=data)

            stmt = SpatialCatalog.select(self.current_user)
            catalogs = session.scalars(stmt).all()
            data = []
            for catalog in catalogs:
                count_stmt = SpatialCatalogEntry.select(self.current_user).where(
                    SpatialCatalogEntry.catalog_id == catalog.id
                )

                entries_count = session.execute(
                    sa.select(func.count()).select_from(count_stmt)
                ).scalar()
                data.append({**catalog.to_dict(), "entries_count": entries_count})
            return self.success(data=data)

    @auth_or_token
    def delete(self, catalog_id):
        """
        ---
        summary: Delete a Spatial Catalog
        description: Delete a spatial catalog
        tags:
          - spatial catalogs
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
                return self.error(f"Missing catalog with ID {catalog_id}")

            IOLoop.current().run_in_executor(None, lambda: delete_catalog(catalog.id))

            self.push_all(action="skyportal/REFRESH_SPATIAL_CATALOGS")
            return self.success()


class SpatialCatalogASCIIFileHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self):
        """
        ---
        summary: Upload a Spatial Catalog from ASCII file
        description: Upload spatial catalog from ASCII file
        tags:
          - spatial catalogs
        requestBody:
          content:
            application/json:
              schema: SpatialCatalogASCIIFileHandlerPost
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
                              description: New spatial catalog ID
          400:
            content:
              application/json:
                schema: Error
        """

        json = self.get_json()
        catalog_data = json.pop("catalogData", None)
        catalog_name = json.pop("catalogName", None)

        if catalog_data is None:
            return self.error(message="Missing catalog_data")

        try:
            catalog_data = pd.read_table(StringIO(catalog_data), sep=",").to_dict(
                orient="list"
            )
        except Exception as e:
            return self.error(f"Unable to read in galaxy file: {e}")

        if catalog_name is None:
            return self.error("catalog_name is a required parameter.")
        if catalog_data is None:
            return self.error("catalog_data is a required parameter.")

        # check for required parameters
        if not {"name", "ra", "dec"}.issubset(set(catalog_data.keys())):
            return self.error("name, ra, and dec required in field_data.")

        # check RA bounds
        if any((x < 0) or (x >= 360) for x in catalog_data["ra"]):
            return self.error("ra should span 0=<ra<360.")

        # check Declination bounds
        if any((x > 90) or (x < -90) for x in catalog_data["dec"]):
            return self.error("declination should span -90<dec<90.")

        # check for cone or ellipse keys
        if (not {"radius"}.issubset(set(catalog_data.keys()))) and (
            not {"amaj", "amin", "phi"}.issubset(set(catalog_data.keys()))
        ):
            return self.error("error or amaj, amin, and phi required in field_data.")

        with self.Session() as session:
            stmt = SpatialCatalog.select(self.current_user).where(
                SpatialCatalog.catalog_name == catalog_name
            )
            catalog = session.scalars(stmt).first()
            if catalog is None:
                catalog = SpatialCatalog(catalog_name=catalog_name)
                session.add(catalog)
                session.commit()

            IOLoop.current().run_in_executor(
                None, lambda: add_catalog(catalog.id, catalog_data)
            )

            return self.success(data={"id": catalog.id})
