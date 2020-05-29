import numpy as np
import arrow
from astropy.time import Time
from astropy.table import Table
import pandas as pd
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession, Photometry, Instrument, Source, Obj,
    PHOT_ZP, PHOT_SYS, Thumbnail
)

from ...schema import (PhotometryMag, PhotometryFlux, PhotometryThumbnailURL,
                       PhotometryThumbnailData)
import sncosmo
import operator

def nan_to_none(value):
    """Coerce a value to None if it is nan, else return value."""
    try:
        return None if np.isnan(value) else value
    except TypeError:
        return value

def allscalar(d):
    return all(np.isscalar(v) or v is None for v in d.values())


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
        """

        data = self.get_json()

        if not isinstance(data, dict):
            return self.error('Top level JSON must be an instance of `dict`, got '
                              f'{type(data)}.')

        if allscalar(data):
            data = [data]

        try:
            df = pd.DataFrame(data)
        except ValueError as e:
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
                    return self.error('Invalid input format: Tried to parse '
                                      f'{packet} as PhotometryFlux, got: '
                                      f'"{e1.normalized_messages()}." Tried '
                                      f'to parse {packet} as PhotometryMag, got:'
                                      f' "{e2.normalized_messages()}."')

            phot.packet = packet
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
        return self.success(data={"ids": ids})

    @auth_or_token
    def get(self, photometry_id):
        """
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
        phot = Photometry.query.get(photometry_id)
        if phot is None:
            return self.error('Invalid photometry ID')
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(phot.obj_id, self.current_user)

        retval = {
            'obj_id': phot.obj_id,
            'ra': phot.ra,
            'dec': phot.dec,
            'filter': phot.filter,
            'mjd': phot.mjd,
            'instrument_id': phot.instrument_id
        }

        if format == 'mag':
            if 'limiting_mag' in phot.packet:
                maglimit = phot.packet['limiting_mag']
                magsys = sncosmo.get_magsystem(phot.packet['magsys'])
                filter = phot.packet['filter']
                ab = sncosmo.get_magsystem('ab')
                zp_magsys = 2.5 * np.log10(magsys.zpbandflux(filter))
                zp_ab = 2.5 * np.log10(ab.zpbandflux(filter))
                maglimit_ab = maglimit - zp_magsys + zp_ab
            else:
                # calculate the limiting mag
                fluxerr = phot.fluxerr
                fivesigma = 5 * fluxerr
                maglimit_ab = -2.5 * np.log10(fivesigma) + PHOT_ZP

            retval.update({
                'mag': phot.mag,
                'magerr': phot.e_mag,
                'magsys': 'ab',
                'limiting_mag': maglimit_ab
            })
        else:
            retval.update({
                'flux': phot.flux,
                'magsys': 'ab',
                'zp': PHOT_ZP,
                'fluxerr': phot.fluxerr
            })

        return self.success(data=retval)

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
        # Ensure user/token has access to parent source
        s = Source.get_if_owned_by(Photometry.query.get(photometry_id).obj_id,
                                   self.current_user)
        packet = self.get_json()

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

        phot.id = photometry_id
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
        # Ensure user/token has access to parent source
        s = Source.get_if_owned_by(Photometry.query.get(photometry_id).obj_id,
                                   self.current_user)
        DBSession.query(Photometry).filter(Photometry.id == int(photometry_id)).delete()
        DBSession().commit()

        return self.success()
