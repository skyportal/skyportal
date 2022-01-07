from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log
from tornado.ioloop import IOLoop
from geojson import Point, Feature

from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy as sa

import astropy.units as u
import healpix_alchemy as ha

from ..base import BaseHandler
from ...models import DBSession, Galaxy, Localization, LocalizationTile


log = make_log('api/galaxy')

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


class GalaxyCatalogHandler(BaseHandler):
    @permissions(['System admin'])
    def post(self):
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

        if catalog_name is None:
            return self.error("catalog_name is a required parameter.")
        if catalog_data is None:
            return self.error("catalog_data is a required parameter.")

        if not all(k in catalog_data for k in ['ra', 'dec', 'name']):
            return self.error("ra, dec, and name required in catalog_data.")

        # fill in any missing optional parameters
        optional_parameters = [
            'alt_name',
            'distmpc',
            'distmpc_unc',
            'redshift',
            'redshift_error',
            'sfr_fuv',
            'mstar',
            'magb',
            'a',
            'b2a',
            'pa',
            'btc',
        ]
        for key in optional_parameters:
            if key not in catalog_data:
                catalog_data[key] = [None] * len(catalog_data['ra'])

        # check for positive definite parameters
        positive_definite_parameters = [
            'distmpc',
            'distmpc_unc',
            'redshift',
            'redshift_error',
        ]
        for key in positive_definite_parameters:
            if any([(x is not None) and (x < 0) for x in catalog_data[key]]):
                return self.error(f"{key} should be positive definite.")

        # check RA bounds
        if any([(x < 0) or (x >= 360) for x in catalog_data['ra']]):
            return self.error("ra should span 0=<ra<360.")

        # check Declination bounds
        if any([(x > 90) or (x < -90) for x in catalog_data['dec']]):
            return self.error("declination should span -90<dec<90.")

        IOLoop.current().run_in_executor(
            None, lambda: add_galaxies(catalog_name, catalog_data)
        )

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
        localization_dateobs = self.get_query_argument("localizationDateobs", None)
        localization_name = self.get_query_argument("localizationName", None)
        localization_cumprob = self.get_query_argument("localizationCumprob", 0.95)
        includeGeojson = self.get_query_argument("includeGeojson", False)

        query = Galaxy.query_records_accessible_by(self.current_user, mode="read")
        if catalog_name is not None:
            query = query.filter(Galaxy.catalog_name == catalog_name)

        if localization_dateobs is not None:
            if localization_name is not None:
                localization = (
                    Localization.query_records_accessible_by(self.current_user)
                    .filter(Localization.dateobs == localization_dateobs)
                    .filter(Localization.localization_name == localization_name)
                    .first()
                )
            else:
                localization = (
                    Localization.query_records_accessible_by(self.current_user)
                    .filter(Localization.dateobs == localization_dateobs)
                    .first()
                )
            if localization is None:
                if localization_name is not None:
                    return self.error(
                        f"Localization {localization_dateobs} with name {localization_name} not found",
                        status=404,
                    )
                else:
                    return self.error(
                        f"Localization {localization_dateobs} not found", status=404
                    )

            cum_prob = (
                sa.func.sum(
                    LocalizationTile.probdensity * LocalizationTile.healpix.area
                )
                .over(order_by=LocalizationTile.probdensity.desc())
                .label('cum_prob')
            )
            subquery1 = (
                sa.select(LocalizationTile.probdensity, cum_prob).filter(
                    LocalizationTile.localization_id == localization.id
                )
            ).subquery()

            min_probdensity = (
                sa.select(sa.func.min(subquery1.columns.probdensity)).filter(
                    subquery1.columns.cum_prob <= localization_cumprob
                )
            ).scalar_subquery()

            tiles_subquery = (
                sa.select(Galaxy.id)
                .filter(
                    LocalizationTile.localization_id == localization.id,
                    LocalizationTile.healpix.contains(Galaxy.healpix),
                    LocalizationTile.probdensity >= min_probdensity,
                )
                .subquery()
            )

            query = query.join(
                tiles_subquery,
                Galaxy.id == tiles_subquery.c.id,
            )
            print(query)

        galaxies = query.all()
        query_results = {'sources': galaxies}

        if includeGeojson:
            # features are JSON representations that the d3 stuff understands.
            # We use these to render the contours of the sky localization and
            # locations of the transients.

            features = []
            for source in query_results["sources"]:
                print(source)
                point = Point((source.ra, source.dec))
                if source.name is not None:
                    source_name = source.name
                else:
                    source_name = f'{source.ra},{source.dec}'

                features.append(
                    Feature(geometry=point, properties={"name": source_name})
                )

            query_results["geojson"] = features

        self.verify_and_commit()
        return self.success(data=query_results)


def add_galaxies(catalog_name, catalog_data):

    session = Session()
    try:
        galaxies = [
            Galaxy(
                catalog_name=catalog_name,
                ra=ra,
                dec=dec,
                name=name,
                alt_name=alt_name,
                distmpc=distmpc,
                distmpc_unc=distmpc_unc,
                redshift=redshift,
                redshift_error=redshift_error,
                sfr_fuv=sfr_fuv,
                mstar=mstar,
                magb=magb,
                a=a,
                b2a=b2a,
                pa=pa,
                btc=btc,
                healpix=ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg),
            )
            for ra, dec, name, alt_name, distmpc, distmpc_unc, redshift, redshift_error, sfr_fuv, mstar, magb, a, b2a, pa, btc in zip(
                catalog_data['ra'],
                catalog_data['dec'],
                catalog_data['name'],
                catalog_data['alt_name'],
                catalog_data['distmpc'],
                catalog_data['distmpc_unc'],
                catalog_data['redshift'],
                catalog_data['redshift_error'],
                catalog_data['sfr_fuv'],
                catalog_data['mstar'],
                catalog_data['magb'],
                catalog_data['a'],
                catalog_data['b2a'],
                catalog_data['pa'],
                catalog_data['btc'],
            )
        ]

        session.add_all(galaxies)
        session.commit()
        return log("Generated galaxy table")
    except Exception as e:
        return log(f"Unable to generate galaxy table: {e}")
    finally:
        Session.remove()
