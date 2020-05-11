import arrow
from astropy.time import Time
import pandas as pd
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from .thumbnail import create_thumbnail
from ...models import (
    DBSession, Photometry, Instrument, Source, Obj
)


PHOTOMETRY_COLUMNS = ['mjd', 'flux', 'fluxerr', 'zpsys', 'zp', 'filter']

class PhotometryHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload photometry
        requestBody:
          content:
            application/json:
              schema: PhotometryNoID
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        ids:
                          type: array
                          description: List of new photometry IDs
        """

        data = self.get_json()

        if 'mjd' not in data:
            return self.error('mjd is a required parameter.')
        if not isinstance(data['flux'], (list, tuple)):
            for colname in PHOTOMETRY_COLUMNS:
                data[colname] = [data[colname]]

        try:
            lc = pd.DataFrame(data)[PHOTOMETRY_COLUMNS]
        except ValueError:
            return self.error('Improperly formatted input data')

        ids = []
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            return self.error('Invalid instrument ID')
        obj = Obj.query.get(data['obj_id'])  # TODO : implement permissions checking
        if not obj:
            return self.error('Invalid object ID')
        converted_times = []

        for i, row in lc.iterrows():
            p = Photometry(obj=obj,
                           mjd=row['mjd'],
                           flux=row['flux'],
                           fluxerr=row['fluxerr'],
                           instrument=instrument,
                           filter=row['filter'],
                           zpsys=row['zpsys'],
                           zp=row['zp'])

            t = Time(row['mjd'], format='mjd')
            converted_times.append(t.iso)

            DBSession().add(p)
            DBSession().flush()
            ids.append(p.id)
        if 'thumbnails' in data:
            p = Photometry.query.get(ids[0])
            for thumb in data['thumbnails']:
                create_thumbnail(thumb['data'], thumb['ttype'], obj.id, p)
        obj.last_detected = max(
            converted_times
            + [
                obj.last_detected
                if obj.last_detected is not None
                else arrow.get("1000-01-01")
            ]
        )
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
        responses:
          200:
            content:
              application/json:
                schema: SinglePhotometry
          400:
            content:
              application/json:
                schema: Error
        """
        info = {}
        info['photometry'] = Photometry.query.get(photometry_id)
        if info['photometry'] is None:
            return self.error('Invalid photometry ID')
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(info['photometry'].obj_id, self.current_user)

        return self.success(data=info)

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
              schema: PhotometryNoID
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
        data = self.get_json()
        data['id'] = photometry_id

        schema = Photometry.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
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
