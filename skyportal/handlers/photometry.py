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
from .base import BaseHandler
from .thumbnail import create_thumbnail
from ..models import DBSession, Photometry, Comment, Instrument, Source, Thumbnail


class PhotometryHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload photometry
        parameters:
          - in: path
            name: time_format
            schema:
              type: string
            description: Valid time formats are listed in `astropy.time.Time.FORMATS` (https://docs.astropy.org/en/stable/api/astropy.time.Time.html#astropy.time.Time.FORMATS)
          - in: path
            name: time_scale
            schema:
              type: string
            description: Valid time scales are listed in `astropy.time.Time.SCALES` (https://docs.astropy.org/en/stable/api/astropy.time.Time.html#astropy.time.Time.SCALES)
          - in: path
            name: source_id
            schema:
              type: string
          - in: path
            name: instrument_id
            schema:
              type: integer
          - in: path
            name: time
            schema:
              type: string
          - in: path
            name: mag
            schema:
              type: number
          - in: path
            name: e_mag
            schema:
              type: number
          - in: path
            name: filter
            schema:
              type: string
          - in: path
            name: lim_mag
            schema:
              type: number
          - in: path
            name: thumbnails
            schema:
              type: array
              items:
                type: object
                properties:
                  data:
                    type: string
                    format: byte
                    description: base64-encoded PNG image file contents. Image size must be between 100px and 500px on a side.
                  ttype:
                    type: string
                    description: Must be one of 'new', 'ref', 'sub', 'sdss', 'dr8', 'new_gz', 'ref_gz', 'sub_gz'
                required:
                  - data
                  - ttype
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
            data['time'] = [data['time']]
            data['mag'] = [data['mag']]
            data['e_mag'] = [data['e_mag']]
        ids = []
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            raise Exception('Invalid instrument ID') # TODO: handle invalid instrument ID
        source = Source.query.get(data['source_id'])
        if not source:
            raise Exception('Invalid source ID') # TODO: handle invalid source ID
        for i in range(len(data['mag'])):
            if not (data['time_scale'] == 'tcb' and data['time_format'] == 'iso'):
                t = Time(data['time'][i],
                         format=data['time_format'],
                         scale=data['time_scale'])
                time = t.tcb.iso
            else:
                time = data['time'][i]
            p = Photometry(source=source,
                           observed_at=time,
                           mag=data['mag'][i],
                           e_mag=data['e_mag'][i],
                           time_scale='tcb',
                           time_format='iso',
                           instrument=instrument,
                           lim_mag=data['lim_mag'],
                           filter=data['filter'])
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
        info = {}
        info['photometry'] = Photometry.query.get(photometry_id)

        if info['photometry'] is not None:
            return self.success(data=info)
        else:
            return self.error(f"Could not load photometry {photometry_id}",
                              data={"photometry_id": photometry_id})

    @permissions(['Manage sources'])
    def put(self, photometry_id):
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
        DBSession.query(Photometry).filter(Photometry.id == int(photometry_id)).delete()
        DBSession().commit()

        return self.success()
