import datetime
import os
import time
from io import StringIO

import astropy.units as u
import arrow
import healpix_alchemy as ha
import healpy as hp
import numpy as np
import pandas as pd
import sqlalchemy as sa
from astropy.io import ascii
from geojson import Feature, Point
from scipy.stats import norm
from scipy.integrate import quad
from sqlalchemy import func
from sqlalchemy.orm import scoped_session, sessionmaker
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ...models import DBSession, Galaxy, Localization, LocalizationTile, Obj
from ..base import BaseHandler

log = make_log('api/galaxy')
env, cfg = load_env()

Session = scoped_session(sessionmaker())

MAX_GALAXIES = 10000


def get_galaxies(
    session,
    catalog_name=None,
    min_redshift=None,
    max_redshift=None,
    min_distance=None,
    max_distance=None,
    localization_dateobs=None,
    localization_name=None,
    localization_cumprob=None,
    includeGeoJSON=False,
    catalog_names_only=False,
    page_number=1,
    num_per_page=MAX_GALAXIES,
    return_probability=False,
):
    if catalog_names_only:
        stmt = Galaxy.select(
            session.user_or_token, columns=[Galaxy.catalog_name]
        ).distinct(Galaxy.catalog_name)
        catalogs = session.scalars(stmt).all()
        query_result = []
        for catalog_name in catalogs:
            stmt = Galaxy.select(session.user_or_token).where(
                Galaxy.catalog_name == catalog_name
            )
            count_stmt = sa.select(func.count()).select_from(stmt)
            total_matches = session.execute(count_stmt).scalar()
            query_result.append(
                {
                    'catalog_name': catalog_name,
                    'catalog_count': int(total_matches),
                }
            )

        return query_result

    if min_redshift is not None:
        try:
            min_redshift = float(min_redshift)
        except ValueError:
            raise ValueError(
                "Invalid values for min_redshift - could not convert to float"
            )

    if max_redshift is not None:
        try:
            max_redshift = float(max_redshift)
        except ValueError:
            raise ValueError(
                "Invalid values for max_redshift - could not convert to float"
            )

    if min_distance is not None:
        try:
            min_distance = float(min_distance)
        except ValueError:
            raise ValueError(
                "Invalid values for min_distance - could not convert to float"
            )

    if max_distance is not None:
        try:
            max_distance = float(max_distance)
        except ValueError:
            raise ValueError(
                "Invalid values for max_distance - could not convert to float"
            )

    if localization_dateobs is not None:

        if localization_name is not None:
            localization = session.scalars(
                Localization.select(session.user_or_token).where(
                    Localization.dateobs == localization_dateobs,
                    Localization.localization_name == localization_name,
                )
            ).first()
        else:
            localization = session.scalars(
                Localization.select(session.user_or_token).where(
                    Localization.dateobs == localization_dateobs,
                )
            ).first()
        if localization is None:
            if localization_name is not None:
                raise ValueError(
                    f"Localization {localization_dateobs} with name {localization_name} not found",
                )
            else:
                raise ValueError(f"Localization {localization_dateobs} not found")

        distmean, distsigma = localization.marginal_moments
        if (distmean is not None) and (distsigma is not None):
            if min_distance is None:
                min_distance = np.max([distmean - 3 * distsigma, 0])
            if max_distance is not None:
                max_distance = np.min([distmean + 3 * distsigma, 10000])

        # now get the dateobs in the format YYYY_MM
        partition_key = arrow.get(localization.dateobs).datetime
        localizationtile_partition_name = (
            f'{partition_key.year}_{partition_key.month:02d}'
        )
        localizationtilescls = LocalizationTile.partitions.get(
            localizationtile_partition_name, None
        )
        if localizationtilescls is None:
            localizationtilescls = LocalizationTile.partitions.get(
                'def', LocalizationTile
            )
        else:
            # check that there is actually a localizationTile with the given localization_id in the partition
            # if not, use the default partition
            if not (
                session.scalars(
                    localizationtilescls.select(session.user_or_token).where(
                        localizationtilescls.localization_id == localization.id
                    )
                ).first()
            ):
                localizationtilescls = localizationtilescls.partitions.get(
                    'def', localizationtilescls
                )

        cum_prob = (
            sa.func.sum(
                localizationtilescls.probdensity * localizationtilescls.healpix.area
            )
            .over(order_by=localizationtilescls.probdensity.desc())
            .label('cum_prob')
        )
        localizationtile_subquery = (
            sa.select(localizationtilescls.probdensity, cum_prob).filter(
                localizationtilescls.localization_id == localization.id
            )
        ).subquery()

        min_probdensity = (
            sa.select(sa.func.min(localizationtile_subquery.columns.probdensity)).where(
                localizationtile_subquery.columns.cum_prob <= localization_cumprob
            )
        ).scalar_subquery()

        tile_ids = session.scalars(
            sa.select(localizationtilescls.id).where(
                localizationtilescls.localization_id == localization.id,
                localizationtilescls.probdensity >= min_probdensity,
            )
        ).all()

        tiles_subquery = (
            sa.select(Galaxy.id)
            .where(
                localizationtilescls.id.in_(tile_ids),
                localizationtilescls.healpix.contains(Galaxy.healpix),
            )
            .subquery()
        )

    query = Galaxy.select(session.user_or_token)
    if localization_dateobs is not None:
        query = query.join(
            tiles_subquery,
            Galaxy.id == tiles_subquery.c.id,
        )

    if catalog_name is not None:
        query = query.where(Galaxy.catalog_name == catalog_name)

    if min_redshift is not None:
        query = query.where(Galaxy.redshift >= min_redshift)

    if max_redshift is not None:
        query = query.where(Galaxy.redshift <= max_redshift)

    if min_distance is not None:
        query = query.where(Galaxy.distmpc >= min_distance)

    if max_distance is not None:
        query = query.where(Galaxy.distmpc <= max_distance)

    count_stmt = sa.select(func.count()).select_from(query)
    total_matches = session.execute(count_stmt).scalar()
    if num_per_page is not None:
        query = query.limit(num_per_page).offset((page_number - 1) * num_per_page)

    galaxies = session.scalars(query).all()
    if return_probability:

        PROB, DISTMU, DISTSIGMA, DISTNORM = localization.flat
        ras = np.array([galaxy.ra for galaxy in galaxies])
        decs = np.array([galaxy.dec for galaxy in galaxies])
        ipix = hp.ang2pix(localization.nside, ras, decs, lonlat=True)

        if localization.is_3d:
            dists = np.array([galaxy.distmpc for galaxy in galaxies])

            probability = (
                PROB[ipix]
                * (DISTNORM[ipix] * norm(DISTMU[ipix], DISTSIGMA[ipix]).pdf(dists))
                / hp.nside2pixarea(localization.nside)
            )
        else:
            probability = PROB[ipix]

        galaxies = [
            {**galaxy.to_dict(), 'probability': prob}
            for galaxy, prob in zip(galaxies, probability)
        ]
    else:
        galaxies = [galaxy.to_dict() for galaxy in galaxies]

    query_results = {"galaxies": galaxies, "totalMatches": int(total_matches)}

    if includeGeoJSON:
        # features are JSON representations that the d3 stuff understands.
        # We use these to render the contours of the sky localization and
        # locations of the transients.

        features = []
        for source in query_results["galaxies"]:
            point = Point((source["ra"], source["dec"]))
            if source["name"] is not None:
                source_name = source["name"]
            else:
                source_name = f'{source["ra"]},{source["dec"]}'

            features.append(Feature(geometry=point, properties={"name": source_name}))

        query_results["geojson"] = {
            'type': 'FeatureCollection',
            'features': features,
        }
    return query_results


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
            'sfr_w4',
            'mstar',
            'magk',
            'magb',
            'mag_fuv',
            'mag_nuv',
            'mag_w1',
            'mag_w2',
            'mag_w3',
            'mag_w4',
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
    async def get(self, catalog_name=None):
        """
        ---
          description: Retrieve all galaxies
          tags:
            - galaxies
          parameters:
            - in: query
              name: catalog_name
              schema:
                type: string
              description: Filter by catalog name (exact match)
            - in: query
              name: minDistance
              nullable: true
              schema:
                type: number
              description: |
                If provided, return only galaxies with a distance of at least this value
            - in: query
              name: maxDistance
              nullable: true
              schema:
                type: number
              description: |
                If provided, return only galaxies with a distance of at most this value
            - in: query
              name: minRedshift
              nullable: true
              schema:
                type: number
              description: |
                If provided, return only galaxies with a redshift of at least this value
            - in: query
              name: maxRedshift
              nullable: true
              schema:
                type: number
              description: |
                If provided, return only galaxies with a redshift of at most this value
            - in: query
              name: localizationDateobs
              schema:
                type: string
              description: |
                Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
            - in: query
              name: localizationName
              schema:
                type: string
              description: |
                Name of localization / skymap to use. Can be found in Localization.localization_name queried from /api/localization endopoint or skymap name in GcnEvent page table.
            - in: query
              name: localizationCumprob
              schema:
                type: number
              description: |
                Cumulative probability up to which to include galaxies
            - in: query
              name: includeGeoJSON
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated GeoJSON. Defaults to
                false.
            - in: query
              name: numPerPage
              nullable: true
              schema:
                type: integer
              description: |
                Number of galaxies to return per paginated request.
                Defaults to 100. Can be no larger than {MAX_OBSERVATIONS}.
            - in: query
              name: pageNumber
              nullable: true
              schema:
                type: integer
              description: Page number for paginated query results. Defaults to 1
            - in: query
              name: catalogNamesOnly
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to just return catalog names. Defaults to
                false.
            - in: query
              name: returnProbability
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return probability density.
                Defaults to false.
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
        includeGeoJSON = self.get_query_argument("includeGeoJSON", False)
        catalog_names_only = self.get_query_argument("catalogNamesOnly", False)
        min_redshift = self.get_query_argument("minRedshift", None)
        max_redshift = self.get_query_argument("maxRedshift", None)
        min_distance = self.get_query_argument("minDistance", None)
        max_distance = self.get_query_argument("maxDistance", None)
        return_probability = self.get_query_argument("returnProbability", False)

        page_number = self.get_query_argument("pageNumber", 1)
        try:
            page_number = int(page_number)
        except ValueError as e:
            return self.error(f'pageNumber fails: {e}')

        num_per_page = self.get_query_argument("numPerPage", 1000)
        try:
            num_per_page = int(num_per_page)
        except ValueError as e:
            return self.error(f'numPerPage fails: {e}')
        with self.Session() as session:
            try:
                data = get_galaxies(
                    session,
                    catalog_name=catalog_name,
                    min_redshift=min_redshift,
                    max_redshift=max_redshift,
                    min_distance=min_distance,
                    max_distance=max_distance,
                    localization_dateobs=localization_dateobs,
                    localization_name=localization_name,
                    localization_cumprob=localization_cumprob,
                    includeGeoJSON=includeGeoJSON,
                    catalog_names_only=catalog_names_only,
                    return_probability=return_probability,
                    page_number=page_number,
                    num_per_page=num_per_page,
                )
                return self.success(data)
            except Exception as e:
                return self.error(f'get_galaxies fails: {e}')

    @permissions(['System admin'])
    def delete(self, catalog_name):
        """
        ---
        description: Delete a galaxy catalog
        tags:
          - instruments
        parameters:
          - in: path
            name: catalog_name
            required: true
            schema:
              type: str
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

        with self.Session():

            IOLoop.current().run_in_executor(
                None, lambda: delete_galaxies(catalog_name)
            )

            return self.success()


def delete_galaxies(catalog_name):

    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        session.execute(sa.delete(Galaxy).where(Galaxy.catalog_name == catalog_name))
        session.commit()
        return log(f"Deleted galaxy table: {catalog_name}")
    except Exception as e:
        return log(f"Unable to generate galaxy table: {e}")
    finally:
        session.close()
        Session.remove()


def add_galaxies(catalog_name, catalog_data):

    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

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
                sfr_w4=sfr_w4,
                mstar=mstar,
                magk=magk,
                magb=magb,
                mag_nuv=mag_nuv,
                mag_fuv=mag_fuv,
                mag_w1=mag_w1,
                mag_w2=mag_w2,
                mag_w3=mag_w3,
                mag_w4=mag_w4,
                a=a,
                b2a=b2a,
                pa=pa,
                btc=btc,
                healpix=ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg),
            )
            for ra, dec, name, alt_name, distmpc, distmpc_unc, redshift, redshift_error, sfr_fuv, sfr_w4, mstar, magb, magk, mag_fuv, mag_nuv, mag_w1, mag_w2, mag_w3, mag_w4, a, b2a, pa, btc in zip(
                catalog_data['ra'],
                catalog_data['dec'],
                catalog_data['name'],
                catalog_data['alt_name'],
                catalog_data['distmpc'],
                catalog_data['distmpc_unc'],
                catalog_data['redshift'],
                catalog_data['redshift_error'],
                catalog_data['sfr_fuv'],
                catalog_data['sfr_w4'],
                catalog_data['mstar'],
                catalog_data['magb'],
                catalog_data['magk'],
                catalog_data['mag_fuv'],
                catalog_data['mag_nuv'],
                catalog_data['mag_w1'],
                catalog_data['mag_w2'],
                catalog_data['mag_w3'],
                catalog_data['mag_w4'],
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
        session.close()
        Session.remove()


class GalaxyASCIIFileHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload galaxies from ASCII file
        tags:
          - galaxys
        requestBody:
          content:
            application/json:
              schema: GalaxyASCIIFileHandlerPost
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

        json = self.get_json()
        catalog_data = json.pop('catalogData', None)
        catalog_name = json.pop('catalogName', None)

        if catalog_data is None:
            return self.error(message="Missing catalog_data")

        try:
            catalog_data = pd.read_table(StringIO(catalog_data), sep=",").to_dict(
                orient='list'
            )
        except Exception as e:
            return self.error(f"Unable to read in galaxy file: {e}")

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
            'sf4_w4',
            'mstar',
            'magk',
            'magb',
            'mag_fuv',
            'mag_nuv',
            'mag_w1',
            'mag_w2',
            'mag_w3',
            'mag_w4',
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


def add_glade(file_path=None, file_url=None):

    column_names = [
        'GLADE_no',
        'PGC_no',
        'GWGC_name',
        'HyperLEDA_name',
        '2MASS_name',
        'WISExSCOS_name',
        'SDSS-DR16Q_name',
        'Object_type',
        'RA',
        'Dec',
        'B',
        'B_err',
        'B_flag',
        'B_Abs',
        'J',
        'J_err',
        'H',
        'H_err',
        'K',
        'K_err',
        'W1',
        'W1_err',
        'W2',
        'W2_err',
        'W1_flag',
        'B_J',
        'B_J_err',
        'z_helio',
        'z_cmb',
        'z_flag',
        'v_err',
        'z_err',
        'd_L',
        'd_L_err',
        'dist',
        'Mstar',
        'Mstar_err',
        'Mstar_flag',
        'Merger_rate',
        'Merger_rate_error',
    ]

    if file_path is not None:
        datafile = file_path
    elif file_url is not None:
        datafile = file_url
    else:
        datafile = "http://elysium.elte.hu/~dalyag/GLADE+.txt"

    if datafile.startswith("http"):
        log(f"add_glade - Downloading {datafile}")
    else:
        log(f"add_glade - Reading {datafile}")

    start_dl_timer = time.perf_counter()
    tbls = ascii.read(
        datafile,
        names=column_names,
        guess=False,
        delimiter=' ',
        format='no_header',
        fast_reader={'chunk_size': int(10 * 1e7), 'chunk_generator': True},  # 100 MB
    )
    if datafile.startswith('http'):
        end_dl_timer = time.perf_counter()
        print(
            f"add_glade - Downloaded {datafile} in {end_dl_timer - start_dl_timer:0.4f} seconds"
        )
    full_length = 0
    full_blueshift_length = 0
    start_loop_timer = time.perf_counter()
    for ii, df in enumerate(tbls):

        try:
            start_timer = time.perf_counter()
            df = df.to_pandas()
            df = df.replace({'null': np.nan})
            # df['GLADE_name'] = ['GLADE-' + str(n) for n in df['GLADE_no']]
            # create a GLADE_name column, where names are: GLADE-<GLADE_no> with GLADE_no as a string using pandas
            df['GLADE_name'] = 'GLADE-' + df['GLADE_no'].astype(str)
            df.rename(
                columns={
                    'RA': 'ra',
                    'Dec': 'dec',
                    'GLADE_name': 'name',
                    'Mstar': 'mstar',
                    'K': 'magk',
                    'B': 'magb',
                    'W1': 'mag_w1',
                    'W2': 'mag_w2',
                    'z_helio': 'redshift',
                    'z_err': 'redshift_error',
                    'd_L': 'distmpc',
                    'd_L_err': 'distmpc_unc',
                },
                inplace=True,
            )

            float_columns = [
                'ra',
                'dec',
                'mstar',
                'magk',
                'magb',
                'mag_w1',
                'mag_w2',
                'mag_w3',
                'mag_w4',
                'redshift',
                'redshift_error',
                'distmpc',
                'distmpc_unc',
            ]
            for col in float_columns:
                df[col] = df[col].astype(float)

            drop_columns = list(
                set(df.columns.values)
                - {
                    'ra',
                    'dec',
                    'name',
                    'mstar',
                    'magk',
                    'magb',
                    'redshift',
                    'redshift_error',
                    'distmpc',
                    'distmpc_unc',
                }
            )

            df.drop(
                columns=drop_columns,
                inplace=True,
            )
            df = df.replace({np.nan: None})
            positive_definite_parameters = [
                'distmpc',
                'distmpc_unc',
                'redshift_error',
            ]
            # remove rows where any of the positive definite parameters are negative using pandas
            for key in positive_definite_parameters:
                df = df.drop(df.index[df[key] < 0])
            # if ra, dec or name are missing, remove the row
            required_columns = ['ra', 'dec', 'name']
            df = df[df[required_columns].notnull().all(axis=1)]

            # fill in any missing optional parameters
            optional_parameters = [
                'alt_name',
                'distmpc',
                'distmpc_unc',
                'redshift',
                'redshift_error',
                'sfr_fuv',
                'mstar',
                'magk',
                'magb',
                'mag_fuv',
                'mag_nuv',
                'mag_w1',
                'mag_w2',
                'mag_w3',
                'mag_w4',
                'a',
                'b2a',
                'pa',
                'btc',
            ]

            # for the optional parameters, if a row is missing a value, fill it in with None
            for key in optional_parameters:
                if key not in df.columns.values:
                    df[key] = None
            # remove rows with incorrect ra or dec
            df = df[(df['ra'] >= 0) & (df['ra'] < 360)]
            df = df[(df['dec'] >= -90) & (df['dec'] <= 90)]

            # add a healpix column where healpix = ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)
            df['healpix'] = [
                ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)
                for ra, dec in zip(df['ra'], df['dec'])
            ]
            # add a catalog_name column where catalog_name = 'GLADE'
            df['catalog_name'] = 'GLADE'
            utcnow = datetime.datetime.utcnow().isoformat()
            df['created_at'] = utcnow
            df['modified_at'] = utcnow
            blueshift_length = len(df[(df['redshift'] < 0)])
            length = len(df)
            full_length += length
            full_blueshift_length += blueshift_length
            columns = (
                "ra",
                "dec",
                "magb",
                "magk",
                "redshift",
                "redshift_error",
                "distmpc",
                "distmpc_unc",
                "mstar",
                "name",
                "alt_name",
                "sfr_fuv",
                'mag_fuv',
                'mag_nuv',
                'mag_w1',
                'mag_w2',
                'mag_w3',
                'mag_w4',
                "a",
                "b2a",
                "pa",
                "btc",
                "healpix",
                "catalog_name",
                'created_at',
                'modified',
            )
            output = StringIO()
            df.replace("NaN", "null", inplace=True)
            df.replace(np.nan, "NaN", inplace=True)
            df.to_csv(
                output,
                index=False,
                sep='\t',
                header=False,
                encoding='utf8',
                quotechar="'",
            )
            output.seek(0)
            connection = DBSession().connection().connection
            cursor = connection.cursor()
            cursor.copy_from(
                output,
                "galaxys",
                sep='\t',
                null='',
                columns=columns,
            )
            cursor.close()
            output.close()
            DBSession().commit()
            end_timer = time.perf_counter()
            log(
                f"add_glade - File part {ii}: Added {length} galaxies (including {blueshift_length} with a negative redshift) in {end_timer - start_timer:0.4f} seconds"
            )
        except Exception as e:
            log(f"add_glade - File part {ii}: Error: {e}")
            continue
    log(
        f"add_glade - Added a total of {full_length} galaxies (including {full_blueshift_length} with a negative redshift) to the database in {time.perf_counter() - start_loop_timer:0.4f} seconds"
    )
    return full_length, full_blueshift_length


def get_galaxies_completeness(
    galaxies,
    dist_min=0,
    dist_max=10000,
    M_min=8,
    M_max=12,
    M_x12=10.676,
):

    # standard constants
    h = 0.7
    phiStar_M1 = 10 ** (-3.31) * h**3
    phiStar_M2 = 10 ** (-2.01) * h**3
    alpha_M1 = -1.61
    alpha_M2 = -0.79
    logMStar = 10.79

    schechter_M_log_2 = (
        lambda x: np.log(10)
        * np.exp(-(10 ** (x - logMStar)))
        * (
            phiStar_M1 * (10 ** (x - logMStar)) ** (alpha_M1 + 1)
            + phiStar_M2 * (10 ** (x - logMStar)) ** (alpha_M2 + 1)
        )
    )

    logM = np.linspace(M_min, M_max, num=50)
    M_ave = (10 ** logM[:-1] + 10 ** logM[1:]) / 2

    N = [quad(schechter_M_log_2, logM[i], logM[i + 1])[0] for i in range(len(logM) - 1)]
    V = ((4 / 3) * np.pi * dist_max**3) - ((4 / 3) * np.pi * dist_min**3)
    hist_schechter = np.array(N) * V

    mstar = [galaxy['mstar'] for galaxy in galaxies if galaxy['mstar'] is not None]
    mstar = np.log10(mstar)
    hist_galaxies, _ = np.histogram(mstar, bins=logM)

    mass_schechter = np.sum(M_ave * hist_schechter)
    mass_galaxies = np.sum(M_ave * hist_galaxies)

    completeness = np.min([1, mass_galaxies / mass_schechter])

    return completeness


class GalaxyGladeHandler(BaseHandler):
    @permissions(['System Admin'])
    async def post(self):
        """
        ---
        description: Upload galaxies from GLADE+ catalog. If no file_name or file_url is provided, will look for the GLADE+ catalog in the data directory. If it can't be found, it will download it.
        tags:
          - galaxys
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                    file_name:
                        type: string
                        description: Name of the file containing the galaxies (in the data directory)
                    file_url:
                        type: string
                        description: URL of the file containing the galaxies
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

        def add_glade_and_notify(file_path=None, file_url=None):
            full_length, full_blueshift_length = add_glade(file_path, file_url)
            self.push(
                f'Added {full_length} galaxies (including {full_blueshift_length} with a negative redshift) to the database'
            )

        try:
            file_name = None
            file_url = None
            data = self.get_json()
            if 'file_name' in data:
                file_name = data['file_name']
                if not file_name.endswith('.txt'):
                    return self.error("Catalog's file type is incorrect. Must be .txt.")
                file_path = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    '../../../data',
                    file_name,
                )
                if not os.path.isfile(file_path):
                    return self.error("File does not exist.")
                file_url = file_path
            elif 'file_url' in data:
                file_url = data['file_url']
                if not file_url.endswith('.txt'):
                    return self.error(
                        "Catalog's url points to an incorrect file type. Must be .txt."
                    )
                if not file_url.startswith('http'):
                    return self.error("Catalog's file URL is incorrect.")
            else:
                file_path = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    '../../../data',
                    'GLADE+.txt',
                )
                if not os.path.isfile(file_path):
                    file_path = None

            IOLoop.current().run_in_executor(
                None,
                lambda: add_glade_and_notify(file_path=file_path, file_url=file_url),
            )

            return self.success()
        except Exception as e:
            return self.error(str(e))


class ObjHostHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, obj_id):
        """
        ---
        description: Set an object's host galaxy
        tags:
          - objs
          - galaxys
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  galaxyName:
                    type: string
                    description: |
                      Name of the galaxy to associate with the object
                required:
                  - galaxyName
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

        name = data.get("galaxyName")
        if name is None:
            return self.error("galaxyName required to set object host")

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token, mode='update').where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            galaxy = session.scalars(
                Galaxy.select(session.user_or_token).where(Galaxy.name == name)
            ).first()
            if galaxy is None:
                return self.error(f"Cannot find Galaxy with name {name}")

            obj.host_id = galaxy.id
            session.commit()

            self.push_all(
                "skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )

            return self.success()

    @permissions(["Upload data"])
    def delete(self, obj_id):
        """
        ---
        description: Delete an object's host galaxy
        tags:
          - objs
          - galaxys
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
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
            obj = session.scalars(
                Obj.select(session.user_or_token, mode='update').where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            obj.host_id = None
            session.commit()

            self.push_all(
                "skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )

            return self.success()
