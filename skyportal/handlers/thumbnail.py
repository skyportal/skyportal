import os
import io
import base64
from pathlib import Path
from marshmallow.exceptions import ValidationError
from PIL import Image
from baselayer.app.access import permissions, auth_or_token
from .base import BaseHandler
from ..models import DBSession, Photometry, Comment, Instrument, Source, Thumbnail


class ThumbnailHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload thumbnails
        parameters:
          - in: path
            name: source_id
            schema:
              type: string
            description: ID of source associated with thumbnails. If specified, without `photometry_id`, the first photometry point associated with specified source will be associated with thumbnail(s).
          - in: path
            name: photometry_id
            schema:
              type: integer
            description: ID of photometry to be associated with thumbnails. If omitted, `source_id` must be specified, in which case the first photometry entry associated with source will be used.
          - in: path
            name: data
            schema:
              type: string
              format: byte
            description: base64-encoded PNG image file contents. Image size must be between 100px and 500px on a side.
          - in: path
            name: ttype
            schema:
              type: string
            description: Thumbnail type. Must be one of 'new', 'ref', 'sub', 'sdss', 'dr8', 'new_gz', 'ref_gz', 'sub_gz'
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        id:
                          type: int
                          description: New thumbnail ID
        """
        data = self.get_json()
        if 'photometry_id' in data:
            phot = Photometry.query.get(int(data['photometry_id']))
            source = phot.source
        elif 'source_id' in data:
            source = Source.query.get(data['source_id'])
            try:
                phot = source.photometry[0]
            except IndexError:
                return self.error('Specified source does not yet have any photometry data.')
        else:
            return self.error('One of either source_id or photometry_id are required.')
        t = create_thumbnail(data['data'], data['ttype'], source.id, phot)
        DBSession().commit()

        return self.success(data={"id": t.id})

    @auth_or_token
    def get(self, thumbnail_id):
        info = {}
        info['thumbnail'] = Thumbnail.query.get(thumbnail_id)

        if info['thumbnail'] is not None:
            return self.success(data=info)
        else:
            return self.error(f"Could not load thumbnail {thumbnail_id}",
                              data={"thumbnail_id": thumbnail_id})

    @permissions(['Manage sources'])
    def put(self, thumbnail_id):
        data = self.get_json()
        data['id'] = thumbnail_id

        schema = Thumbnail.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, thumbnail_id):
        DBSession.query(Thumbnail).filter(Thumbnail.id == int(thumbnail_id)).delete()
        DBSession().commit()

        return self.success()


def create_thumbnail(thumbnail_data, thumbnail_type, source_id, photometry_obj):
    basedir = Path(os.path.dirname(__file__))/'..'/'..'
    if os.path.abspath(basedir).endswith('skyportal/skyportal'):
        basedir = basedir/'..'
    file_uri = os.path.abspath(
        basedir/f'static/thumbnails/{source_id}_{thumbnail_type}.png')
    if not os.path.exists(os.path.dirname(file_uri)):
        (basedir/'static/thumbnails').mkdir(parents=True)
    file_bytes = base64.b64decode(thumbnail_data)
    im = Image.open(io.BytesIO(file_bytes))
    if im.format != 'PNG':
        raise ValueError('Invalid thumbnail image type. Only PNG are supported.')
    if not (100, 100) <= im.size <= (500, 500):
        raise ValueError('Invalid thumbnail size. Only thumbnails '
                        'between (100, 100) and (500, 500) allowed.')
    t = Thumbnail(type=thumbnail_type,
                  photometry=photometry_obj,
                  file_uri=file_uri,
                  public_url=f'/static/thumbnails/{source_id}_{thumbnail_type}.png')
    DBSession.add(t)
    DBSession.flush()

    with open(file_uri, 'wb') as f:
        f.write(file_bytes)
    return t
