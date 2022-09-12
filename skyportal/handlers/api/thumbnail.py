import os
import io
import base64
from pathlib import Path
from marshmallow.exceptions import ValidationError
import sqlalchemy as sa
from sqlalchemy.exc import StatementError
from PIL import Image, UnidentifiedImageError

from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import Obj, Thumbnail, User


def post_thumbnail(data, user_id, session):
    """Post thumbnail to database.
    data: dict
        Thumbnail dictionary
    user_id : int
        SkyPortal ID of User posting the Thumbnail
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.scalar(sa.select(User).where(User.id == user_id))

    obj = session.scalars(Obj.select(user).where(Obj.id == data["obj_id"])).first()

    if obj is None:
        raise AttributeError(f"Invalid obj_id: {data['obj_id']}")

    basedir = Path(os.path.dirname(__file__)) / '..' / '..'
    if os.path.abspath(basedir).endswith('skyportal/skyportal'):
        basedir = basedir / '..'
    file_uri = os.path.abspath(
        basedir / f'static/thumbnails/{data["obj_id"]}_{data["ttype"]}.png'
    )
    if not os.path.exists(os.path.dirname(file_uri)):
        (basedir / 'static/thumbnails').mkdir(parents=True)

    file_bytes = base64.b64decode(data['data'])
    try:
        im = Image.open(io.BytesIO(file_bytes))
    except UnidentifiedImageError as e:
        raise UnidentifiedImageError(f"Invalid file type: {e}")

    if im.format != 'PNG':
        raise ValueError('Invalid thumbnail image type. Only PNG are supported.')
    if not all(16 <= x <= 500 for x in im.size):
        raise ValueError(
            'Invalid thumbnail size. Only thumbnails '
            'between (16, 16) and (500, 500) allowed.'
        )
    try:
        t = Thumbnail(
            obj_id=data["obj_id"],
            type=data["ttype"],
            file_uri=file_uri,
            public_url=f'/static/thumbnails/{data["obj_id"]}_{data["ttype"]}.png',
        )
        with open(file_uri, 'wb') as f:
            f.write(file_bytes)

        session.add(t)
        session.flush()
        session.commit()

    except (LookupError, StatementError) as e:
        if "enum" in str(e):
            raise LookupError(f"Invalid ttype: {e}")
        raise StatementError(f"Error creating new thumbnail: {e}")

    return t.id


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

        with self.Session() as session:
            try:
                obj_id = post_thumbnail(data, self.associated_user_object.id, session)
            except Exception as e:
                return self.error(f'Thumbnail failed to post: {str(e)}')
            return self.success(data={"id": obj_id})

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
