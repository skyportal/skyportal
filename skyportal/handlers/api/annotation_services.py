from astropy.coordinates import SkyCoord
import astropy.units as u
from dl import queryClient as qc
import pandas as pd
from io import StringIO
from sqlalchemy.exc import IntegrityError
from astroquery.irsa import Irsa
import numpy as np
from astroquery.vizier import Vizier

from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import auth_or_token

from ..base import BaseHandler
from ...models import (
    DBSession,
    Annotation,
    Group,
    Obj,
)


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

        group_ids = data.pop('group_ids', None)
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'At least some of the groups are not accessible.', status=403
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

        DBSession().add_all(annotations)
        try:
            self.verify_and_commit()
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

        group_ids = data.pop('group_ids', None)
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'At least some of the groups are not accessible.', status=403
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

        DBSession().add_all(annotations)
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

        group_ids = data.pop('group_ids', None)
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible groups.', status=403)

        author = self.associated_user_object

        catalog = data.pop('catalog', "ls_dr8")
        radius_arcsec = data.pop('crossmatchRadius', 2.0)
        radius_deg = radius_arcsec / 3600.0

        sql_query = f"""SELECT {catalog}.photo_z.ls_id, z_phot_median, z_phot_std, ra, dec, type, z_phot_l95, flux_z from {catalog}.photo_z
                      INNER JOIN {catalog}.tractor
                      ON {catalog}.tractor.ls_id = {catalog}.photo_z.ls_id
                      where 't' = Q3C_RADIAL_QUERY(ra, dec, {obj.ra}, {obj.dec}, {radius_deg})"""
        query = qc.query(sql=sql_query)
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

        DBSession().add_all(annotations)
        try:
            self.verify_and_commit()
        except IntegrityError:
            return self.error("Annotation already posted.")

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj.internal_key},
        )
        return self.success()
