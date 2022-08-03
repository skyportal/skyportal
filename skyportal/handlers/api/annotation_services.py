from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.time import Time

try:
    from dl import queryClient as qc
except Exception:

    class qc:
        def query(*args, **kwargs):
            return ""


import pandas as pd
from io import StringIO
from sqlalchemy.exc import IntegrityError
from astroquery.gaia import GaiaClass
from astroquery.irsa import Irsa
import numpy as np
from astroquery.vizier import Vizier

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ..base import BaseHandler
from ...models import (
    Annotation,
    Group,
    Obj,
)

_, cfg = load_env()


class GaiaQueryHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_id):
        """
        ---
        description: |
            get Gaia parallax and magnitudes and post them as an annotation,
            based on cross-match to the Gaia DR3.
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: ID of the object to retrieve Gaia colors for
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  catalog:
                    required: false
                    type: string
                    description: |
                      The name of the catalog key, associated with a
                      catalog cross match,
                      from which the data should be retrieved.
                      Default is "gaiadr3.gaia_source".
                  crossmatchRadius:
                    required: false
                    type: number
                    description: |
                      Crossmatch radius (in arcseconds) to retrieve Gaia sources
                      If not specified (or None) will use the default from
                      the config file, or 2 arcsec if not specified in the config.
                  crossmatchLimmag:
                    required: false
                    type: number
                    description: |
                      Crossmatch limiting magnitude (for Gaia G mag).
                      Will ignore sources fainter than this magnitude.
                      If not specified, will use the default value in
                      the config file, or None if not specified in the config.
                      If value is cast to False (0, False or None),
                      will take sources of any magnitude.
                  group_ids:
                    required: false
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups
                      should be able to view annotation.
                      Defaults to all of requesting user's groups.
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
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error('Invalid object id.')

        data = self.get_json()

        author = self.associated_user_object

        catalog = data.pop('catalog', "gaiadr3.gaia_source")
        radius_arcsec = data.pop('crossmatchRadius', cfg['cross_match.gaia.radius'])
        limmag = data.pop('crossmatchLimmag', cfg['cross_match.gaia.limmag'])
        num_matches = data.pop('crossmatchNumber', cfg['cross_match.gaia.number'])
        candidate_coord = SkyCoord(ra=obj.ra * u.deg, dec=obj.dec * u.deg)

        df = (
            GaiaClass()
            .cone_search(
                candidate_coord,
                radius_arcsec * u.arcsec,
                table_name=catalog,
            )
            .get_data()
            .to_pandas()
        )

        # first remove rows that have faint magnitudes
        if limmag:  # do not remove if limmag is None or zero
            df = df[df['phot_g_mean_mag'] < limmag]

        # propagate the stars using Gaia proper motion
        # then choose the closest match
        if len(df) > 1:
            df['adjusted_dist'] = np.nan  # new column
            for index, row in df.iterrows():
                c = SkyCoord(
                    ra=row['ra'] * u.deg,
                    dec=row['dec'] * u.deg,
                    pm_ra_cosdec=row['pmra'] * u.mas / u.yr,
                    pm_dec=row['pmdec'] * u.mas / u.yr,
                    frame='icrs',
                    distance=min(abs(1 / row['parallax']), 10) * u.kpc,
                    obstime=Time(row['ref_epoch'], format='jyear'),
                )
                new_dist = c.separation(candidate_coord).deg
                df.at[index, 'adjusted_dist'] = new_dist

            df.sort_values(by=['adjusted_dist'], inplace=True)
            df = df.head(num_matches)

        columns = {
            'ra': 'ra',
            'dec': 'dec',
            'pm_ra': 'pmra',
            'pm_dec': 'pmdec',
            'Mag_G': 'phot_g_mean_mag',
            'Mag_BP': 'phot_bp_mean_mag',
            'Mag_RP': 'phot_rp_mean_mag',
            'Plx': 'parallax',
            'Plx_err': 'parallax_error',
            'A_G': 'a_g_val',
            'RUWE': 'ruwe',
        }

        # TODO: convert the above code to the new SQLA 2.0 methods
        with self.Session() as session:
            group_ids = data.pop('group_ids', None)

            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]
            groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            ).all()

            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            annotations = []
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                annotation_data = {}
                for local_key, gaia_key in columns.items():
                    value = row_dict.get(gaia_key, np.nan)
                    if not np.isnan(value):
                        annotation_data[local_key] = value
                if annotation_data:
                    if len(df) > 1:
                        origin = f"{catalog}-{row['ra']}-{row['dec']}"
                    else:
                        origin = catalog
                    annotation = Annotation(
                        data=annotation_data,
                        obj_id=obj_id,
                        origin=origin,
                        author=author,
                        groups=groups,
                    )
                    annotations.append(annotation)

            if len(annotations) == 0:
                return self.error("No Gaia Photometry available.")

            session.add_all(annotations)
            try:
                session.commit()
            except IntegrityError:
                return self.error("Annotation already posted.")

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj.internal_key},
        )
        return self.success()


class IRSAQueryWISEHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_id):
        """
        ---
        description: |
            get WISE colors and post them as an annotation
            based on cross-matches to some catalog (default is allwise_p3as_psd).
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: ID of the object to retrieve WISE colors for
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  catalog:
                    required: false
                    type: string
                    description: |
                      The name of the catalog key, associated with a
                      catalog cross match,
                      from which the data should be retrieved.
                      Default is allwise_p3as_psd.
                  crossmatchRadius:
                    required: false
                    type: number
                    description: |
                      Crossmatch radius (in arcseconds) to retrieve photoz's
                      Default is 2.
                  group_ids:
                    required: false
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups
                      should be able to view annotation.
                      Defaults to all of requesting user's groups.
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
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error('Invalid object id.')

        data = self.get_json()
        with self.Session() as session:
            group_ids = data.pop('group_ids', None)

            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]
            groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            ).all()

            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            author = self.associated_user_object

            catalog = data.pop('catalog', "allwise_p3as_psd")
            radius_arcsec = data.pop('crossmatchRadius', 2.0)
            candidate_coord = SkyCoord(ra=obj.ra * u.deg, dec=obj.dec * u.deg)

            df = Irsa.query_region(
                coordinates=candidate_coord,
                catalog=catalog,
                spatial="Cone",
                radius=radius_arcsec * u.arcsec,
            ).to_pandas()

            keys = [
                'ra',
                'dec',
                'w1mpro',
                'w1sigmpro',
                'w2mpro',
                'w2sigmpro',
                'w3mpro',
                'w3sigmpro',
                'w4mpro',
                'w4sigmpro',
            ]
            annotations = []
            for index, row in df.iterrows():
                annotation_data = {
                    k: row.to_dict().get(k, None)
                    for k in keys
                    if not np.isnan(row.to_dict().get(k, None))
                }

                origin = f"{catalog}-{row['ra']}-{row['dec']}"
                annotation = Annotation(
                    data=annotation_data,
                    obj_id=obj_id,
                    origin=origin,
                    author=author,
                    groups=groups,
                )
                annotations.append(annotation)

            if len(annotations) == 0:
                return self.error("No WISE Photometry available.")

            session.add_all(annotations)
            try:
                session.commit()
            except IntegrityError:
                return self.error("Annotation already posted.")

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj.internal_key},
        )
        return self.success()


class VizierQueryHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_id):
        """
        ---
        description: |
            get cross-match with Vizier and post them as an annotation
            based on cross-matches to some catalog
            (default is VII/290, i.e. the million quasar catalog).
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: ID of the object to retrieve the Vizier crossmatch for
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  catalog:
                    required: false
                    type: string
                    description: |
                      The name of the catalog key, associated with a
                      catalog cross match,
                      from which the data should be retrieved.
                      Default is VII/290.
                  crossmatchRadius:
                    required: false
                    type: number
                    description: |
                      Crossmatch radius (in arcseconds) to retrieve photoz's
                      Default is 2.
                  group_ids:
                    required: false
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups
                      should be able to view annotation.
                      Defaults to all of requesting user's groups.
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
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error('Invalid object id.')

        data = self.get_json()

        with self.Session() as session:
            group_ids = data.pop('group_ids', None)

            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]
            groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            ).all()

            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            author = self.associated_user_object

            catalog = data.pop('catalog', "VII/290")
            radius_arcsec = data.pop('crossmatchRadius', 2.0)
            candidate_coord = SkyCoord(ra=obj.ra * u.deg, dec=obj.dec * u.deg)

            tl = Vizier.query_region(
                coordinates=candidate_coord,
                catalog=catalog,
                radius=radius_arcsec * u.arcsec,
            )

            if len(tl) == 0:
                return self.error("No successful cross-match available.")

            if len(tl) > 1:
                return self.error("Should only have one table from that query.")
            df = tl[0].filled(fill_value=-99).to_pandas()
            keys = [
                'Qpct',
                'z',
            ]
            annotations = []
            for index, row in df.iterrows():
                annotation_data = {
                    k: row.to_dict().get(k, None)
                    for k in keys
                    if not row.to_dict().get(k, None) == -99
                }
                origin = f"{catalog}-{row['Name']}"
                annotation = Annotation(
                    data=annotation_data,
                    obj_id=obj_id,
                    origin=origin,
                    author=author,
                    groups=groups,
                )
                annotations.append(annotation)

            if len(annotations) == 0:
                return self.error("No crossmatch annotation available.")

            session.add_all(annotations)
            try:
                self.verify_and_commit()
            except IntegrityError:
                return self.error("Annotation already posted.")

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj.internal_key},
        )
        return self.success()


class DatalabQueryHandler(BaseHandler):
    """
    ---
    description: |
        get photo(z) of nearby sources and post them as an annotation
        based on cross-matches to some catalog (default is LegacySurvey DR8).
    parameters:
    - in: path
        name: obj_id
        required: true
        schema:
          type: string
        description: ID of the object to retrieve photoz's for
      - in: query
        name: catalog
        required: false
        schema:
          type: string
        description: |
          The name of the catalog key, associated with a catalog cross match,
          from which the photoz data should be retrieved.
          Default is ls_dr8.
      - in: query
        name: crossmatchRadius
        required: false
        schema:
          type: number
        description: |
          Crossmatch radius (in arcseconds) to retrieve photoz's
          Default is 2.
      - in: query
        name: group_ids
        required: false
        schema:
          type: array
          items:
            type: integer
        description: |
          List of group IDs corresponding to which groups should be
          able to view annotation. Defaults to all of requesting user's groups.
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

    @auth_or_token
    def post(self, obj_id):
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error('Invalid object id.')

        data = self.get_json()

        with self.Session() as session:
            group_ids = data.pop('group_ids', None)

            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]
            groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            ).all()

            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            author = self.associated_user_object

            catalog = data.pop('catalog', "ls_dr8")
            radius_arcsec = data.pop('crossmatchRadius', 2.0)
            radius_deg = radius_arcsec / 3600.0

            sql_query = f"""SELECT {catalog}.photo_z.ls_id, z_phot_median, z_phot_std, ra, dec, type, z_phot_l95, flux_z from {catalog}.photo_z
                          INNER JOIN {catalog}.tractor
                          ON {catalog}.tractor.ls_id = {catalog}.photo_z.ls_id
                          where 't' = Q3C_RADIAL_QUERY(ra, dec, {obj.ra}, {obj.dec}, {radius_deg})"""
            try:
                query = qc.query(sql=sql_query)
            except qc.queryClientError as e:
                return self.error(f'Error initializing query: {str(e)}')

            df = pd.read_table(StringIO(query), sep=",")
            annotations = []
            for index, row in df.iterrows():
                ls_id = row['ls_id']
                origin = f"{catalog}-{ls_id}"
                row.drop(index=['ls_id'], inplace=True)
                annotation_data = row.to_dict()
                annotation = Annotation(
                    data=annotation_data,
                    obj_id=obj_id,
                    origin=origin,
                    author=author,
                    groups=groups,
                )
                annotations.append(annotation)

            if len(annotations) == 0:
                return self.error("No photo z's available.")

            session.add_all(annotations)
            try:
                session.commit()
            except IntegrityError:
                return self.error("Annotation already posted.")

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj.internal_key},
        )
        return self.success()
