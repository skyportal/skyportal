import base64
import hashlib
import io
import os
from pathlib import Path

import sqlalchemy as sa
from marshmallow.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func
from sqlalchemy.exc import StatementError

from baselayer.app.access import auth_or_token, permissions

from ...models import Obj, Thumbnail, User
from ..base import BaseHandler


async def post_thumbnail(data, user_id, session):
    """Post thumbnail to database (async).
    data: dict
        Thumbnail dictionary
    user_id : int
        SkyPortal ID of User posting the Thumbnail
    session: sqlalchemy.ext.asyncio.AsyncSession
        Async DB session for this transaction
    """

    user = await session.scalar(sa.select(User).where(User.id == user_id))

    obj = await session.scalar(Obj.select(user).where(Obj.id == data["obj_id"]))

    if obj is None:
        raise AttributeError(f"Invalid obj_id: {data['obj_id']}")

    basedir = Path(os.path.dirname(__file__)) / ".." / ".."
    obj_hash = hashlib.sha256(data["obj_id"].encode("utf-8")).hexdigest()

    # can someday make this a configurable parameter
    required_depth = 2
    subfolders = "/".join(obj_hash[i * 2 : (i + 1) * 2] for i in range(required_depth))

    if os.path.abspath(basedir).endswith("skyportal/skyportal"):
        basedir = basedir / ".."
    file_uri = os.path.abspath(
        basedir / f"static/thumbnails/{subfolders}/{data['obj_id']}_{data['ttype']}.png"
    )
    if not os.path.exists(os.path.dirname(file_uri)):
        Path(os.path.dirname(file_uri)).mkdir(parents=True)

    file_bytes = base64.b64decode(data["data"])
    try:
        im = Image.open(io.BytesIO(file_bytes))
    except UnidentifiedImageError as e:
        raise UnidentifiedImageError(f"Invalid file type: {e}")

    if im.format != "PNG":
        raise ValueError("Invalid thumbnail image type. Only PNG are supported.")
    if not all(16 <= x <= 500 for x in im.size):
        raise ValueError(
            "Invalid thumbnail size. Only thumbnails "
            "between (16, 16) and (500, 500) allowed."
        )
    try:
        t = Thumbnail(
            obj_id=data["obj_id"],
            type=data["ttype"],
            file_uri=file_uri,
            public_url=f"/static/thumbnails/{subfolders}/{data['obj_id']}_{data['ttype']}.png",
        )
        with open(file_uri, "wb") as f:
            f.write(file_bytes)

        session.add(t)
        await session.commit()

    except (LookupError, StatementError) as e:
        if "enum" in str(e):
            raise LookupError(f"Invalid ttype: {e}")
        raise StatementError(f"Error creating new thumbnail: {e}")

    return t.id


class ThumbnailHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self):
        """
        ---
        summary: Upload thumbnails
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
        if "obj_id" not in data:
            return self.error("Missing required parameter: obj_id")

        async with self.AsyncSession() as session:
            try:
                thumbnail_id = await post_thumbnail(
                    data, self.associated_user_object.id, session
                )
            except Exception as e:
                return self.error(f"Thumbnail failed to post: {str(e)}")
            return self.success(data={"id": thumbnail_id})

    @auth_or_token
    async def get(self, thumbnail_id: int):
        """
        ---
        summary: Get a thumbnail
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
        async with self.AsyncSession() as session:
            t = await session.scalar(
                Thumbnail.select(session.user_or_token).where(
                    Thumbnail.id == thumbnail_id
                )
            )
            if t is None:
                return self.error(f"Cannot find Thumbnail with ID: {thumbnail_id}")
            return self.success(data=t)

    @permissions(["Manage sources"])
    async def put(self, thumbnail_id: int):
        """
        ---
        summary: Update a thumbnail
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Thumbnail'
          400:
            content:
              application/json:
                schema: Error
        """
        async with self.AsyncSession() as session:
            t = await session.scalar(
                Thumbnail.select(session.user_or_token, mode="update").where(
                    Thumbnail.id == thumbnail_id
                )
            )
            if t is None:
                return self.error(f"Cannot find Thumbnail with ID: {thumbnail_id}")

            data = self.get_json()
            data["id"] = thumbnail_id

            schema = Thumbnail.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )

            for k in data:
                setattr(t, k, data[k])

            await session.commit()
            return self.success()

    @permissions(["Manage sources"])
    async def delete(self, thumbnail_id: int):
        """
        ---
        summary: Delete a thumbnail
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
        async with self.AsyncSession() as session:
            t = await session.scalar(
                Thumbnail.select(session.user_or_token, mode="delete").where(
                    Thumbnail.id == thumbnail_id
                )
            )
            if t is None:
                return self.error(f"Cannot find Thumbnail with ID: {thumbnail_id}")

            await session.delete(t)
            await session.commit()

            return self.success()


class ThumbnailPathHandler(BaseHandler):
    @permissions(["System admin"])
    async def get(self):
        """
        ---
        summary: Check thumbnail paths
        description: |
          Get information on thumbnails that are
          or are not in the correct folder/path.
        tags:
          - thumbnails
        parameters:
          - in: query
            name: types
            required: false
            default: ['new', 'ref', 'sub']
            schema:
              type: array
              items:
                type: string
            description: |
              types of thumbnails to check
              The default is ['new', 'ref', 'sub'] which
              are all the thumbnail types stored locally.
          - in: query
            name: requiredDepth
            required: false
            default: 2
            schema:
              type: integer
            description: |
              number of subdirectories that are desired for
              thumbnails. For example if requiredDepth is 2,
                then thumbnails will be stored in a folder like
                /skyportal/static/thumbnails/ab/cd/<source_name>_<type>.png
                where "ab" and "cd" are the first characters of the
                hash of the source name.
                If requiredDepth is 0, then thumbnails are expected
                to be all in one folder under /skyportal/static/thumbnails.
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
                            totalMatches:
                              type: integer
                            inCorrectFolder:
                              type: integer
                            inWrongFolder:
                              type: integer

        """
        types = self.get_query_argument("types", ["new", "ref", "sub"])
        required_depth = self.get_query_argument("requiredDepth", 2, type=int)
        if required_depth is None:
            return self.error("requiredDepth must be an integer")

        if required_depth < 0 or required_depth > 32:
            return self.error("requiredDepth must be between 0 and 32")

        good_like = f"%thumbnails{'/__' * required_depth}/%"
        bad_like = f"%thumbnails{'/__' * (required_depth + 1)}/%"

        async with self.AsyncSession() as session:
            (
                total_matches,
                good_matches,
                bad_matches,
            ) = await count_thumbnails_in_folders(session, types, good_like, bad_like)

        return self.success(
            data={
                "totalMatches": total_matches,
                "inCorrectFolder": good_matches,
                "inWrongFolder": bad_matches,
            }
        )

    @permissions(["System admin"])
    async def patch(self):
        """
        ---
        summary: Update thumbnail paths
        description: |
          Update the file path and file_uri of the database rows
          of thumbnails that are not in the correct folder/path.
        tags:
          - thumbnails
        parameters:
          - in: query
            name: types
            required: false
            default: ['new', 'ref', 'sub']
            schema:
              type: array
              items:
                type: string
            description: |
              types of thumbnails to check
              The default is ['new', 'ref', 'sub'] which
              are all the thumbnail types stored locally.
          - in: query
            name: requiredDepth
            required: false
            default: 2
            schema:
              type: integer
            description: |
              number of subdirectories that are desired for
              thumbnails. For example if requiredDepth is 2,
                then thumbnails will be stored in a folder like
                /skyportal/static/thumbnails/ab/cd/<source_name>_<type>.png
                where "ab" and "cd" are the first characters of the
                hash of the source name.
                If requiredDepth is 0, then thumbnails are expected
                to be all in one folder under /skyportal/static/thumbnails.
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of sources to check for updates. Defaults to 100. Max 500.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for iterating through all sources. Defaults to 1
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
                            totalMatches:
                              type: integer
                            inCorrectFolder:
                              type: integer
                            inWrongFolder:
                              type: integer

        """
        # need to import this here because alert.py might import this file
        from .alert import alert_available

        types = self.get_query_argument("types", ["new", "ref", "sub"])
        required_depth = self.get_query_argument("requiredDepth", 2, type=int)
        if required_depth is None:
            return self.error("requiredDepth must be an integer")

        if required_depth <= 0 or required_depth > 32:
            return self.error("requiredDepth must be at least 0 and no bigger than 31.")
        page_number = self.get_query_argument("pageNumber", 1, type=int)
        num_per_page = self.get_query_argument("numPerPage", 100, type=int)
        if page_number is None or num_per_page is None:
            return self.error(
                "Cannot parse inputs pageNumber or numPerPage as integers."
            )
        num_per_page = min(num_per_page, 1000)

        good_like = f"%thumbnails{'/__' * required_depth}/%"
        bad_like = f"%thumbnails{'/__' * (required_depth + 1)}/%"

        num_moved = 0
        async with self.AsyncSession() as session:
            stmt = sa.select(Thumbnail).where(Thumbnail.type.in_(types))
            stmt = stmt.where(
                sa.or_(
                    ~Thumbnail.file_uri.like(good_like),
                    Thumbnail.file_uri.like(bad_like),
                )
            )
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            result = await session.scalars(stmt)
            thumbnails = result.unique().all()
            for t in thumbnails:
                if t.file_uri is None:
                    continue

                if alert_available:
                    ok = await check_thumbnail_file(
                        t, self.associated_user_object.id, session
                    )
                    if not ok:
                        # the delete is committed in check_thumbnail_file
                        continue
                obj_hash = hashlib.sha256(t.obj_id.encode("utf-8")).hexdigest()
                subfolders = "/".join(
                    obj_hash[i * 2 : (i + 1) * 2] for i in range(required_depth)
                )
                path = (
                    "thumbnails".join(t.file_uri.split("thumbnails")[:-1])
                    + "thumbnails"
                )
                filename = os.path.basename(t.file_uri)
                new_file_uri = os.path.join(path, subfolders, filename)
                new_public_url = os.path.join(
                    "/static/thumbnails", subfolders, filename
                )
                old_file_uri = t.file_uri

                try:
                    os.makedirs(os.path.dirname(new_file_uri), exist_ok=True)
                    if os.path.isfile(old_file_uri):
                        os.rename(old_file_uri, new_file_uri)
                except Exception as e:
                    return self.error(
                        f"Could not move {old_file_uri} to {new_file_uri}: {e}"
                    )

                if not os.path.isfile(new_file_uri):
                    return self.error(f"File {new_file_uri} does not exist!")

                try:
                    t.file_uri = new_file_uri
                    t.public_url = new_public_url
                    session.add(t)
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    os.rename(new_file_uri, old_file_uri)
                    return self.error(f"Could not update database row: {e}")

                num_moved += 1

            (
                total_matches,
                good_matches,
                bad_matches,
            ) = await count_thumbnails_in_folders(session, types, good_like, bad_like)

        return self.success(
            data={
                "totalMatches": total_matches,
                "inCorrectFolder": good_matches,
                "inWrongFolder": bad_matches,
                "numMoved": num_moved,
            }
        )

    # TODO: add a POST that only checks each thumbnail
    # for missing or empty files, outside of the context
    # of moving them to the correct folder

    @permissions(["System admin"])
    async def delete(self):
        """
        ---
        summary: Delete empty thumbnail folders
        description: |
          Delete all empty subfolders under "thumbnails".
          These can be left over if moving thumbnails to a
          different folder structure.

        tags:
          - thumbnails
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        basepath = os.path.join(
            os.path.dirname(__file__), "../../../", "static", "thumbnails"
        )
        basepath = os.path.abspath(basepath)
        for root, dirs, _files in os.walk(basepath, topdown=False):
            for d in dirs:
                try:
                    os.removedirs(os.path.join(root, d))
                except OSError:
                    pass  # not empty, skipping

        return self.success()


async def count_thumbnails_in_folders(session, types, good_like, bad_like):
    """Async version: Count the number of thumbnails in the correct and incorrect folders."""
    stmt = sa.select(Thumbnail).where(Thumbnail.type.in_(types))
    total_matches = await session.scalar(
        sa.select(func.count()).select_from(stmt.subquery())
    )
    good_stmt = stmt.where(
        Thumbnail.file_uri.like(good_like), ~Thumbnail.file_uri.like(bad_like)
    )
    good_matches = await session.scalar(
        sa.select(func.count()).select_from(good_stmt.subquery())
    )
    bad_stmt = stmt.where(
        sa.or_(
            ~Thumbnail.file_uri.like(good_like),
            Thumbnail.file_uri.like(bad_like),
        )
    )
    bad_matches = await session.scalar(
        sa.select(func.count()).select_from(bad_stmt.subquery())
    )

    return total_matches, good_matches, bad_matches


async def check_thumbnail_file(thumbnail, user_id, session):
    """Async version: Check if a thumbnail file exists on disk and recreate via
    alerts if missing. Should NOT BE CALLED if alerts are not available.
    """
    # need to import this here because alert.py might import this file
    from .alert import alert_available, post_alert

    if not alert_available:
        raise RuntimeError("Cannot recreate thumbnails without alerts!")

    if (
        not os.path.isfile(thumbnail.file_uri)
        or os.stat(thumbnail.file_uri).st_size == 0
    ):
        try:
            os.remove(thumbnail.file_uri)
        except Exception:
            pass
        finally:
            await session.delete(thumbnail)
            await session.commit()

        # post_alert is overridden by Fritz; if it's been made async there, it
        # should be awaited; the base stub is a no-op.
        post_alert(
            object_id=thumbnail.obj_id,
            candid=None,
            group_ids="all",
            user_id=user_id,
            session=session,
            thumbnails_only=True,
        )

        return False

    return True
