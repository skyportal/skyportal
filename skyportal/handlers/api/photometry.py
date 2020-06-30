import uuid
import numpy as np
import arrow
from astropy.time import Time
import pandas as pd
from marshmallow.exceptions import ValidationError
import sncosmo
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession, Group, Photometry, Instrument, Source, Obj,
    PHOT_ZP, PHOT_SYS, Thumbnail
)

from ...schema import (PhotometryMag, PhotometryFlux)
from ...phot_enum import ALLOWED_MAGSYSTEMS


def nan_to_none(value):
    """Coerce a value to None if it is nan, else return value."""
    try:
        return None if np.isnan(value) else value
    except TypeError:
        return value


def allscalar(d):
    return all(np.isscalar(v) or v is None for v in d.values())


def serialize(phot, outsys, format):

    retval = {
        'obj_id': phot.obj_id,
        'ra': phot.ra,
        'dec': phot.dec,
        'filter': phot.filter,
        'mjd': phot.mjd,
        'instrument_id': phot.instrument_id,
        'ra_unc': phot.ra_unc,
        'dec_unc': phot.dec_unc,
        'alert_id': phot.alert_id
    }

    filter = phot.filter

    magsys_db = sncosmo.get_magsystem('ab')
    outsys = sncosmo.get_magsystem(outsys)

    relzp_out = 2.5 * np.log10(outsys.zpbandflux(filter))

    # note: these are not the actual zeropoints for magnitudes in the db or
    # packet, just ones that can be used to derive corrections when
    # compared to relzp_out

    relzp_db = 2.5 * np.log10(magsys_db.zpbandflux(filter))
    db_correction = relzp_out - relzp_db

    # this is the zeropoint for fluxes in the database that is tied
    # to the new magnitude system
    corrected_db_zp = PHOT_ZP + db_correction

    if format == 'mag':
        if phot.original_user_data is not None and 'limiting_mag' in phot.original_user_data:
            magsys_packet = sncosmo.get_magsystem(phot.original_user_data['magsys'])
            relzp_packet = 2.5 * np.log10(magsys_packet.zpbandflux(filter))
            packet_correction = relzp_out - relzp_packet
            maglimit = phot.original_user_data['limiting_mag']
            maglimit_out = maglimit + packet_correction
        else:
            # calculate the limiting mag
            fluxerr = phot.fluxerr
            fivesigma = 5 * fluxerr
            maglimit_out = -2.5 * np.log10(fivesigma) + corrected_db_zp

        retval.update({
            'mag': phot.mag + db_correction if phot.mag is not None else None,
            'magerr': phot.e_mag if phot.e_mag is not None else None,
            'magsys': outsys.name,
            'limiting_mag': maglimit_out
        })
    elif format == 'flux':
        retval.update({
            'flux': phot.flux,
            'magsys': outsys.name,
            'zp': corrected_db_zp,
            'fluxerr': phot.fluxerr
        })
    else:
        raise ValueError('Invalid output format specified. Must be one of '
                         f"['flux', 'mag'], got '{format}'.")
    return retval


class PhotometryHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload photometry
        requestBody:
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: "#/components/schemas/PhotMagFlexible"
                  - $ref: "#/components/schemas/PhotFluxFlexible"
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
                            ids:
                              type: array
                              items:
                                type: integer
                              description: List of new photometry IDs
                            upload_id:
                              type: string
                              description: |
                                Upload ID associated with all photometry points
                                added in request. Can be used to later delete all
                                points in a single request.
        """

        data = self.get_json()

        if not isinstance(data, dict):
            return self.error('Top level JSON must be an instance of `dict`, got '
                              f'{type(data)}.')

        if "altdata" in data and not data["altdata"]:
            del data["altdata"]
        try:
            group_ids = data.pop("group_ids")
        except KeyError:
            return self.error("Missing required field: group_ids")
        groups = Group.query.filter(Group.id.in_(group_ids)).all()
        if not groups:
            return self.error("Invalid group_ids field. "
                              "Specify at least one valid group ID.")
        if "Super admin" not in [r.id for r in self.associated_user_object.roles]:
            if not all([group in self.current_user.groups for group in groups]):
                return self.error("Cannot upload photometry to groups that you "
                                  "are not a member of.")
        if "alert_id" in data:
            phot = Photometry.query.filter(
                Photometry.alert_id == data["alert_id"]
            ).filter(Photometry.alert_id.isnot(None)).first()
            if phot is not None:
                phot.groups = groups
                DBSession().commit()
                return self.success(data={"ids": [phot.id],
                                          "upload_id": phot.upload_id})

        if allscalar(data):
            data = [data]

        upload_id = str(uuid.uuid4())

        try:
            df = pd.DataFrame(data)
        except ValueError as e:
            if "altdata" in data and "Mixing dicts with non-Series" in str(e):
                try:
                    data["altdata"] = [
                        {key: value[i] for key, value in data["altdata"].items()}
                        for i in range(len(data["altdata"][list(data["altdata"].keys())[-1]]))
                    ]
                    df = pd.DataFrame(data)
                except ValueError:
                    return self.error('Unable to coerce passed JSON to a series of packets. '
                                      f'Error was: "{e}"')
            else:
                return self.error('Unable to coerce passed JSON to a series of packets. '
                                  f'Error was: "{e}"')

        # pop out thumbnails and process what's left using schemas

        ids = []
        for i, row in df.iterrows():
            packet = row.to_dict()

            # coerce nans to nones
            for key in packet:
                packet[key] = nan_to_none(packet[key])

            try:
                phot = PhotometryFlux.load(packet)
            except ValidationError as e1:
                try:
                    phot = PhotometryMag.load(packet)
                except ValidationError as e2:
                    return self.error('Invalid input format: Tried to parse packet '
                                      f'{i} as PhotometryFlux, got: '
                                      f'"{e1.normalized_messages()}." Tried '
                                      f'to parse packet {i} as PhotometryMag, got:'
                                      f' "{e2.normalized_messages()}."')

            phot.original_user_data = packet
            phot.upload_id = upload_id
            phot.groups = groups
            DBSession().add(phot)

            # to set up obj link
            DBSession().flush()

            time = arrow.get(Time(phot.mjd, format='mjd').iso)
            phot.obj.last_detected = max(
                time,
                phot.obj.last_detected
                if phot.obj.last_detected is not None
                else arrow.get("1000-01-01")
            )
            ids.append(phot.id)

        DBSession().commit()
        return self.success(data={"ids": ids, "upload_id": upload_id})

    @auth_or_token
    def get(self, photometry_id):
        # The full docstring/API spec is below as an f-string

        phot = Photometry.get_if_owned_by(photometry_id, self.current_user)
        if phot is None:
            return self.error('Invalid photometry ID')

        # get the desired output format
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')
        output = serialize(phot, outsys, format)
        return self.success(data=output)

    @permissions(['Manage sources'])
    def put(self, photometry_id):
        """
        ---
        description: Update photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: "#/components/schemas/PhotometryMag"
                  - $ref: "#/components/schemas/PhotometryFlux"
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
        _ = Photometry.get_if_owned_by(photometry_id, self.current_user)
        data = self.get_json()
        group_ids = data.pop("group_ids", None)

        try:
            phot = PhotometryFlux.load(data)
        except ValidationError as e1:
            try:
                phot = PhotometryMag.load(data)
            except ValidationError as e2:
                return self.error('Invalid input format: Tried to parse '
                                  f'{data} as PhotometryFlux, got: '
                                  f'"{e1.normalized_messages()}." Tried '
                                  f'to parse {data} as PhotometryMag, got:'
                                  f' "{e2.normalized_messages()}."')

        phot.original_user_data = data
        phot.id = photometry_id
        DBSession().merge(phot)
        DBSession.flush()
        # Update groups, if relevant
        if group_ids is not None:
            photometry = Photometry.query.get(photometry_id)
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error("Invalid group_ids field. "
                                  "Specify at least one valid group ID.")
            if "Super admin" not in [r.id for r in self.associated_user_object.roles]:
                if not all([group in self.current_user.groups for group in groups]):
                    return self.error("Cannot upload photometry to groups you "
                                      "are not a member of.")
            photometry.groups = groups
        DBSession().commit()
        return self.success()

    @permissions(['Manage sources'])
    def delete(self, photometry_id):
        """
        ---
        description: Delete photometry
        parameters:
          - in: path
            name: photometry_id
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
        _ = Photometry.get_if_owned_by(photometry_id, self.current_user)
        DBSession.query(Photometry).filter(Photometry.id == int(photometry_id)).delete()
        DBSession().commit()

        return self.success()


class ObjPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        obj = Obj.query.get(obj_id)
        if obj is None:
            return self.error('Invalid object id.')
        photometry = Obj.get_photometry_owned_by_user(obj_id, self.current_user)
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')
        return self.success(
            data=[serialize(phot, outsys, format) for phot in photometry]
        )


class BulkDeletePhotometryHandler(BaseHandler):
    @auth_or_token
    def delete(self, upload_id):
        """
        ---
        description: Delete bulk-uploaded photometry set
        parameters:
          - in: path
            name: upload_id
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
        # Permissions check:
        phot_id = Photometry.query.filter(
            Photometry.upload_id == upload_id).first().id
        _ = Photometry.get_if_owned_by(phot_id, self.current_user)

        n_deleted = DBSession.query(Photometry).filter(
            Photometry.upload_id == upload_id).delete()
        DBSession().commit()

        return self.success(f"Deleted {n_deleted} photometry points.")


PhotometryHandler.get.__doc__ = f"""
        ---
        description: Retrieve photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
          - in: query
            name: format
            required: false
            description: >-
              Return the photometry in flux or magnitude space?
              If a value for this query parameter is not provided, the
              result will be returned in magnitude space.
            schema:
              type: string
              enum:
                - mag
                - flux
          - in: query
            name: magsys
            required: false
            description: >-
              The magnitude or zeropoint system of the output. (Default AB)
            schema:
              type: string
              enum: {list(ALLOWED_MAGSYSTEMS)}

        responses:
          200:
            content:
              application/json:
                schema:
                  oneOf:
                    - $ref: "#/components/schemas/SinglePhotometryFlux"
                    - $ref: "#/components/schemas/SinglePhotometryMag"
          400:
            content:
              application/json:
                schema: Error
        """

ObjPhotometryHandler.get.__doc__ = f"""
        ---
        description: Retrieve all photometry associated with an Object
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: ID of the object to retrieve photometry for
          - in: query
            name: format
            required: false
            description: >-
              Return the photometry in flux or magnitude space?
              If a value for this query parameter is not provided, the
              result will be returned in magnitude space.
            schema:
              type: string
              enum:
                - mag
                - flux
          - in: query
            name: magsys
            required: false
            description: >-
              The magnitude or zeropoint system of the output. (Default AB)
            schema:
              type: string
              enum: {list(ALLOWED_MAGSYSTEMS)}

        responses:
          200:
            content:
              application/json:
                schema:
                  oneOf:
                    - $ref: "#/components/schemas/ArrayOfPhotometryFluxs"
                    - $ref: "#/components/schemas/ArrayOfPhotometryMags"
          400:
            content:
              application/json:
                schema: Error
        """
