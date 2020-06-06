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
        'dec_unc': phot.dec_unc
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
                            bulk_upload_id:
                              type: string
                              description: |
                                If multiple data points are posted, a bulk upload ID is
                                provided so that they may all be deleted in one request.
                                Otherwise null.
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

        if allscalar(data):
            data = [data]

        bulk_upload_id = str(uuid.uuid4())

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
            phot.bulk_upload_id = bulk_upload_id
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
        return self.success(data={"ids": ids, "bulk_upload_id": bulk_upload_id})

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
        packet = self.get_json()
        group_ids = packet.pop("group_ids", None)

        try:
            phot = PhotometryFlux.load(packet)
        except ValidationError as e1:
            try:
                phot = PhotometryMag.load(packet)
            except ValidationError as e2:
                return self.error('Invalid input format: Tried to parse '
                                  f'{packet} as PhotometryFlux, got: '
                                  f'"{e1.normalized_messages()}." Tried '
                                  f'to parse {packet} as PhotometryMag, got:'
                                  f' "{e2.normalized_messages()}."')

        phot.original_user_data = packet
        phot.id = photometry_id
        if group_ids is not None:
            phot.groups = Group.query.filter(Group.id.in_(group_ids)).all()
        DBSession().merge(phot)
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


class SourcePhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        obj = Obj.query.get(obj_id)
        if obj is None:
            return self.error('Invalid source id.')
        photometry = Obj.get_photometry_owned_by_user(obj_id, self.current_user)
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')
        return self.success(
            data=[serialize(phot, outsys, format) for phot in photometry]
        )


class BulkDeletePhotometryHandler(BaseHandler):
    @auth_or_token
    def delete(self, bulk_upload_id):
        """
        ---
        description: Delete bulk-uploaded photometry set
        parameters:
          - in: path
            name: bulk_upload_id
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
            Photometry.bulk_upload_id == bulk_upload_id).first().id
        _ = Photometry.get_if_owned_by(phot_id, self.current_user)

        n_deleted = DBSession.query(Photometry).filter(
            Photometry.bulk_upload_id == bulk_upload_id).delete()
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

SourcePhotometryHandler.get.__doc__ = f"""
        ---
        description: Retrieve photometry
        parameters:
          - in: path
            name: source_id
            required: true
            schema:
              type: integer
            description: ID of the source to retrieve photometry for
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
