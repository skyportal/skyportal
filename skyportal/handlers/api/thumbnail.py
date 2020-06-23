import os
import io
import base64
from pathlib import Path
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import StatementError
from PIL import Image
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Photometry, Obj, Source, Thumbnail


class ThumbnailHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload thumbnails
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  obj_id:
                    type: string
                    description: ID of object associated with thumbnails. If specified, without `photometry_id`, the first photometry point associated with specified object will be associated with thumbnail(s).
                  photometry_id:
                    type: integer
                    description: ID of photometry to be associated with thumbnails. If omitted, `obj_id` must be specified, in which case the first photometry entry associated with object will be used.
                  data:
                    type: string
                    format: byte
                    description: base64-encoded PNG image file contents. Image size must be between 16px and 500px on a side.
                  ttype:
                    type: string
                    description: Thumbnail type. Must be one of 'new', 'ref', 'sub', 'sdss', 'dr8', 'new_gz', 'ref_gz', 'sub_gz'
                required:
                  - data
                  - ttype
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
                            id:
                              type: integer
                              description: New thumbnail ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        if 'photometry_id' in data:
            phot = Photometry.query.get(int(data['photometry_id']))
            obj_id = phot.obj.id
            obj = Obj.get_if_owned_by(obj_id, self.current_user)
        elif 'obj_id' in data:
            obj_id = data['obj_id']
            obj = Obj.get_if_owned_by(obj_id, self.current_user)
            if obj is None:
                return self.error(f"Invalid obj_id: {obj_id}")
            try:
                phot = obj.photometry[0]
            except IndexError:
                return self.error('Specified source does not yet have any photometry data.')
        else:
            return self.error('One of either obj_id or photometry_id are required.')
        try:
            t = create_thumbnail(data['data'], data['ttype'], obj_id, phot)
        except ValueError as e:
            return self.error(f"Error in creating new thumbnail: invalid value(s): {e}")
        except (LookupError, StatementError) as e:
            return self.error(f"Invalid ttype: {e}")
        DBSession().commit()

        return self.success(data={"id": t.id})

    @auth_or_token
    def get(self, thumbnail_id):
        """
        ---
        description: Retrieve a thumbnail
        parameters:
          - in: path
            name: thumbnail_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: SingleThumbnail
          400:
            content:
              application/json:
                schema: Error
        """
        t = Thumbnail.query.get(thumbnail_id)
        if t is None:
            return self.error(f"Could not load thumbnail with ID {thumbnail_id}")
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(t.obj.id, self.current_user)

        return self.success(data=t)

    @permissions(['Manage sources'])
    def put(self, thumbnail_id):
        """
        ---
        description: Update thumbnail
        parameters:
          - in: path
            name: thumbnail_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: ThumbnailNoID
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
        t = Thumbnail.query.get(thumbnail_id)
        if t is None:
            return self.error('Invalid thumbnail ID.')
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(t.obj.id, self.current_user)

        data = self.get_json()
        data['id'] = thumbnail_id

        schema = Thumbnail.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, thumbnail_id):
        """
        ---
        description: Delete a thumbnail
        parameters:
          - in: path
            name: thumbnail_id
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
        t = Thumbnail.query.get(thumbnail_id)
        if t is None:
            return self.error('Invalid thumbnail ID.')
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(t.obj.id, self.current_user)

        DBSession.query(Thumbnail).filter(Thumbnail.id == int(thumbnail_id)).delete()
        DBSession().commit()

        return self.success()


def create_thumbnail(thumbnail_data, thumbnail_type, obj_id, photometry_obj):
    basedir = Path(os.path.dirname(__file__)) / '..' / '..'
    if os.path.abspath(basedir).endswith('skyportal/skyportal'):
        basedir = basedir / '..'
    file_uri = os.path.abspath(
        basedir / f'static/thumbnails/{obj_id}_{thumbnail_type}.png')
    if not os.path.exists(os.path.dirname(file_uri)):
        (basedir / 'static/thumbnails').mkdir(parents=True)
    file_bytes = base64.b64decode(thumbnail_data)
    im = Image.open(io.BytesIO(file_bytes))
    if im.format != 'PNG':
        raise ValueError('Invalid thumbnail image type. Only PNG are supported.')
    if not all(16 <= x <= 500 for x in im.size):
        raise ValueError('Invalid thumbnail size. Only thumbnails '
                         'between (16, 16) and (500, 500) allowed.')
    t = Thumbnail(type=thumbnail_type,
                  photometry=photometry_obj,
                  file_uri=file_uri,
                  public_url=f'/static/thumbnails/{obj_id}_{thumbnail_type}.png')
    DBSession.add(t)
    DBSession.flush()

    with open(file_uri, 'wb') as f:
        f.write(file_bytes)
    return t
