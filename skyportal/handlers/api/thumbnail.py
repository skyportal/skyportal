import os
import io
import base64
from pathlib import Path
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import StatementError
from PIL import Image, UnidentifiedImageError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import Obj, Thumbnail


class ThumbnailHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload thumbnails
        tags:
          - thumbnails
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  obj_id:
                    type: string
                    description: ID of object associated with thumbnails.
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
        if 'obj_id' not in data:
            return self.error("Missing required parameter: obj_id")
        obj_id = data['obj_id']

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Invalid obj_id: {obj_id}")
            try:
                t = create_thumbnail(data['data'], data['ttype'], obj_id, session)
            except ValueError as e:
                return self.error(
                    f"Error in creating new thumbnail: invalid value(s): {e}"
                )
            except (LookupError, StatementError) as e:
                if "enum" in str(e):
                    return self.error(f"Invalid ttype: {e}")
                return self.error(f"Error creating new thumbnail: {e}")
            except UnidentifiedImageError as e:
                return self.error(f"Invalid file type: {e}")
            session.commit()

            return self.success(data={"id": t.id})

    @auth_or_token
    def get(self, thumbnail_id):
        """
        ---
        description: Retrieve a thumbnail
        tags:
          - thumbnails
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
        with self.Session() as session:
            t = session.scalars(
                Thumbnail.select(session.user_or_token).where(
                    Thumbnail.id == thumbnail_id
                )
            ).first()
            if t is None:
                return self.error(f'Cannot find Thumbnail with ID: {thumbnail_id}')
            return self.success(data=t)

    @permissions(['Manage sources'])
    def put(self, thumbnail_id):
        """
        ---
        description: Update thumbnail
        tags:
          - thumbnails
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
        with self.Session() as session:
            t = session.scalars(
                Thumbnail.select(session.user_or_token, mode="update").where(
                    Thumbnail.id == thumbnail_id
                )
            ).first()
            if t is None:
                return self.error(f'Cannot find Thumbnail with ID: {thumbnail_id}')

            data = self.get_json()
            data['id'] = thumbnail_id

            schema = Thumbnail.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            for k in data:
                setattr(t, k, data[k])

            session.commit()
            return self.success()

    @permissions(['Manage sources'])
    def delete(self, thumbnail_id):
        """
        ---
        description: Delete a thumbnail
        tags:
          - thumbnails
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

        with self.Session() as session:
            t = session.scalars(
                Thumbnail.select(session.user_or_token, mode="delete").where(
                    Thumbnail.id == thumbnail_id
                )
            ).first()
            if t is None:
                return self.error(f'Cannot find Thumbnail with ID: {thumbnail_id}')

            session.delete(t)
            session.commit()

            return self.success()


def create_thumbnail(thumbnail_data, thumbnail_type, obj_id, session):
    basedir = Path(os.path.dirname(__file__)) / '..' / '..'
    if os.path.abspath(basedir).endswith('skyportal/skyportal'):
        basedir = basedir / '..'
    file_uri = os.path.abspath(
        basedir / f'static/thumbnails/{obj_id}_{thumbnail_type}.png'
    )
    if not os.path.exists(os.path.dirname(file_uri)):
        (basedir / 'static/thumbnails').mkdir(parents=True)
    file_bytes = base64.b64decode(thumbnail_data)
    im = Image.open(io.BytesIO(file_bytes))
    if im.format != 'PNG':
        raise ValueError('Invalid thumbnail image type. Only PNG are supported.')
    if not all(16 <= x <= 500 for x in im.size):
        raise ValueError(
            'Invalid thumbnail size. Only thumbnails '
            'between (16, 16) and (500, 500) allowed.'
        )
    t = Thumbnail(
        obj_id=obj_id,
        type=thumbnail_type,
        file_uri=file_uri,
        public_url=f'/static/thumbnails/{obj_id}_{thumbnail_type}.png',
    )
    with open(file_uri, 'wb') as f:
        f.write(file_bytes)

    session.add(t)
    session.flush()

    return t
