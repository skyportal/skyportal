import os
import io
import base64
from pathlib import Path
import tornado.web
from astropy.time import Time
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from PIL import Image
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from .thumbnail import create_thumbnail
from ...models import (
    DBSession, Photometry, Comment, Instrument, Source, Thumbnail
)


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

        # TODO should filters be a table/plaintext/limited set of strings?
        if 'time_format' not in data or 'time_scale' not in data:
            return self.error('Time scale (\'time_scale\') and time format '
                              '(\'time_format\') are required parameters.')
        if not isinstance(data['mag'], (list, tuple)):
            data['observed_at'] = [data['observed_at']]
            data['mag'] = [data['mag']]
            data['e_mag'] = [data['e_mag']]
            data['lim_mag'] = [data['lim_mag']]
            data['filter'] = [data['filter']]
        ids = []
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            raise Exception('Invalid instrument ID') # TODO: handle invalid instrument ID
        source = Source.get_if_owned_by(data['source_id'], self.current_user)
        if not source:
            raise Exception('Invalid source ID') # TODO: handle invalid source ID
        for i in range(len(data['mag'])):
            if not (data['time_scale'] == 'tcb' and data['time_format'] == 'iso'):
                t = Time(data['observed_at'][i],
                         format=data['time_format'],
                         scale=data['time_scale'])
                observed_at = t.tcb.iso
            else:
                observed_at = data['time'][i]
            p = Photometry(source=source,
                           observed_at=observed_at,
                           mag=data['mag'][i],
                           e_mag=data['e_mag'][i],
                           time_scale='tcb',
                           time_format='iso',
                           instrument=instrument,
                           lim_mag=data['lim_mag'][i],
                           filter=data['filter'][i])
            DBSession().add(p)
            DBSession().flush()
            ids.append(p.id)
        if 'thumbnails' in data:
            p = Photometry.query.get(ids[0])
            for thumb in data['thumbnails']:
                create_thumbnail(thumb['data'], thumb['ttype'], source.id, p)
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
            return self.error ('Invalid photometry ID')
        # Ensure user/token has access to parent source
        s = Source.get_if_owned_by(info['photometry'].source_id,
                                   self.current_user)

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
        s = Source.get_if_owned_by(Photometry.query.get(photometry_id).source_id,
                                   self.current_user)
        data = self.get_json()
        data['id'] = photometry_id

        schema = Photometry.__schema__()
        try:
            schema.load(data)
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
        s = Source.get_if_owned_by(Photometry.query.get(photometry_id).source_id,
                                   self.current_user)
        DBSession.query(Photometry).filter(Photometry.id == int(photometry_id)).delete()
        DBSession().commit()

        return self.success()
