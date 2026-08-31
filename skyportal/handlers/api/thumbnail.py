import base64
import hashlib
import io
import os
import re
from pathlib import Path

import sqlalchemy as sa
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import StatementError

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.models import utcnow
from baselayer.log import make_log

from ...models import Broker, Obj, Thumbnail, User
from ...utils.thumbnail import image_is_grayscale
from ..base import BaseHandler

log = make_log("api/thumbnail")

SURVEY_RE = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,31}")


class ThumbnailPostBody(BaseModel):
    """Request body for uploading a thumbnail."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str = Field(description="ID of object associated with thumbnails.")
    data: str = Field(
        description="base64-encoded PNG image file contents. Image size must "
        "be between 16px and 500px on a side."
    )
    ttype: str = Field(
        description="Thumbnail type. Must be one of 'new', 'ref', 'sub', "
        "'sdss', 'dr8', 'new_gz', 'ref_gz', 'sub_gz'"
    )
    survey: str | None = Field(
        default=None,
        description="Survey the cutout came from (e.g. ZTF, LSST). NULL for "
        "all-sky archival thumbnails.",
    )


class ThumbnailPostResponse(BaseModel):
    """Data payload returned when uploading a thumbnail."""

    id: int = Field(description="New thumbnail ID")


class ThumbnailPutBody(BaseModel):
    """Request body for updating a thumbnail."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(default=None, description="ID of the thumbnail's obj.")
    type: str | None = Field(
        default=None, description="Thumbnail type (e.g., ref, new, sub, ls, ps1, ...)"
    )
    file_uri: str | None = Field(
        default=None,
        description="Path of the Thumbnail on the machine running SkyPortal.",
    )
    public_url: str | None = Field(
        default=None, description="Publically accessible URL of the thumbnail."
    )
    origin: str | None = Field(default=None, description="Origin of the Thumbnail.")
    is_grayscale: bool | None = Field(
        default=None, description="Whether the thumbnail is (mostly) grayscale."
    )


async def post_thumbnail(data, user_id, session):
    """Post thumbnail to database (async).
    data: dict
        Thumbnail dictionary
    user_id : int
        SkyPortal ID of User posting the Thumbnail
    session: sqlalchemy.ext.asyncio.AsyncSession
        Async DB session for this transaction
    """

    obj_id, ttype = data["obj_id"], data["ttype"]
    user = await session.get(User, user_id)

    if await session.scalar(Obj.select(user).where(Obj.id == obj_id)) is None:
        raise AttributeError(f"Invalid obj_id: {obj_id}")

    basedir = Path(os.path.dirname(__file__)) / ".." / ".."
    obj_hash = hashlib.sha256(obj_id.encode("utf-8")).hexdigest()

    required_depth = 2
    subfolders = "/".join(obj_hash[i * 2 : (i + 1) * 2] for i in range(required_depth))

    if os.path.abspath(basedir).endswith("skyportal/skyportal"):
        basedir = basedir / ".."

    # BOOM emits title-case names ("Ztf"), which the constraint reads as not "ZTF".
    survey = (data.get("survey") or "").strip().upper() or None
    # survey lands in the file path below, so it must not contain separators.
    if survey is not None and not SURVEY_RE.fullmatch(survey):
        raise ValueError(f"Invalid survey: {data['survey']}")
    filename = f"{obj_id}_{ttype}{f'_{survey}' if survey else ''}.png"
    file_uri = os.path.abspath(basedir / f"static/thumbnails/{subfolders}/{filename}")
    public_url = f"/static/thumbnails/{subfolders}/{filename}"
    os.makedirs(os.path.dirname(file_uri), exist_ok=True)

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
        with open(file_uri, "wb") as f:
            f.write(file_bytes)

        # before_insert-only event listener doesn't fire on the upsert path below.
        is_grayscale = image_is_grayscale(file_uri)

        if survey is not None:
            # Relabel one pre-survey row so it stops rendering as a second tile;
            # one only, and never onto an existing survey, or the update collides.
            legacy, sibling = sa.orm.aliased(Thumbnail), sa.orm.aliased(Thumbnail)
            await session.execute(
                sa.update(Thumbnail)
                .where(
                    Thumbnail.id
                    == sa.select(legacy.id)
                    .where(
                        legacy.obj_id == obj_id,
                        legacy.type == ttype,
                        legacy.survey.is_(None),
                    )
                    .order_by(legacy.id)
                    .limit(1)
                    .scalar_subquery(),
                    ~sa.select(sibling.id)
                    .where(
                        sibling.obj_id == obj_id,
                        sibling.type == ttype,
                        sibling.survey == survey,
                    )
                    .exists(),
                )
                .values(survey=survey)
            )
            # A SELECT-then-write loses to a concurrent ingest, and the resulting
            # IntegrityError kills the whole ingest, not just this thumbnail.
            thumbnail_id = await session.scalar(
                pg_insert(Thumbnail)
                .values(
                    obj_id=obj_id,
                    type=ttype,
                    survey=survey,
                    file_uri=file_uri,
                    public_url=public_url,
                    is_grayscale=is_grayscale,
                )
                .on_conflict_do_update(
                    index_elements=["obj_id", "type", "survey"],
                    # ON CONFLICT ignores the column's onupdate, hence modified here.
                    set_={
                        "file_uri": file_uri,
                        "public_url": public_url,
                        "is_grayscale": is_grayscale,
                        "modified": utcnow,
                    },
                )
                .returning(Thumbnail.id)
            )
        else:
            # Each NULL is distinct to the index, so ON CONFLICT never fires here.
            t = await session.scalar(
                sa.select(Thumbnail).where(
                    Thumbnail.obj_id == obj_id,
                    Thumbnail.type == ttype,
                    Thumbnail.survey.is_(None),
                )
            )
            if t is None:
                t = Thumbnail(obj_id=obj_id, type=ttype)
                session.add(t)
            t.file_uri = file_uri
            t.public_url = public_url
            t.is_grayscale = is_grayscale
            await session.flush()
            thumbnail_id = t.id

        await session.commit()

    except StatementError as e:
        if "enum" in str(e):
            raise LookupError(f"Invalid ttype: {e}") from e
        raise

    return thumbnail_id


class ThumbnailHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self, *, body: ThumbnailPostBody = None) -> ThumbnailPostResponse:
        """
        ---
        summary: Upload thumbnails
        description: Upload thumbnails
        tags:
          - thumbnails
        """
        body = self.parse_body(ThumbnailPostBody)

        async with self.AsyncSession() as session:
            try:
                thumbnail_id = await post_thumbnail(
                    body.model_dump(), self.associated_user_object.id, session
                )
            except Exception as e:
                return self.error(f"Thumbnail failed to post: {e}")
            return self.success(data={"id": thumbnail_id})

    @auth_or_token
    async def get(self, thumbnail_id: int):
        """
        ---
        summary: Get a thumbnail
        description: Retrieve a thumbnail
        tags:
          - thumbnails
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
    async def put(self, thumbnail_id: int, *, body: ThumbnailPutBody = None):
        """
        ---
        summary: Update a thumbnail
        description: Update thumbnail
        tags:
          - thumbnails
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
        body = self.parse_body(ThumbnailPutBody)
        async with self.AsyncSession() as session:
            t = await session.scalar(
                Thumbnail.select(session.user_or_token, mode="update").where(
                    Thumbnail.id == thumbnail_id
                )
            )
            if t is None:
                return self.error(f"Cannot find Thumbnail with ID: {thumbnail_id}")

            for field in body.model_fields_set:
                setattr(t, field, getattr(body, field))

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


class ThumbnailPathGetQuery(BaseModel):
    """Query parameters for checking thumbnail paths."""

    model_config = ConfigDict(extra="forbid")

    types: list[str] = Field(
        default=["new", "ref", "sub"],
        description=(
            "types of thumbnails to check. The default is ['new', 'ref', 'sub'] "
            "which are all the thumbnail types stored locally."
        ),
    )
    requiredDepth: int = Field(
        default=2,
        description=(
            "number of subdirectories that are desired for thumbnails. For example "
            "if requiredDepth is 2, then thumbnails will be stored in a folder like "
            "/skyportal/static/thumbnails/ab/cd/<source_name>_<type>.png where 'ab' "
            "and 'cd' are the first characters of the hash of the source name. "
            "If requiredDepth is 0, then thumbnails are expected to be all in one "
            "folder under /skyportal/static/thumbnails."
        ),
    )


class ThumbnailPathPatchQuery(ThumbnailPathGetQuery):
    """Query parameters for updating thumbnail paths (same filters as the
    check, plus pagination over the rows to move)."""

    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=100,
        description=(
            "Number of thumbnails to update per paginated request. Defaults to "
            "100. Capped at 1000."
        ),
    )


class ThumbnailPathHandler(BaseHandler):
    @permissions(["System admin"])
    async def get(self, *, query: ThumbnailPathGetQuery = None):
        """
        ---
        summary: Check thumbnail paths
        description: |
          Get information on thumbnails that are
          or are not in the correct folder/path.
        tags:
          - thumbnails
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
        query = self.parse_query(ThumbnailPathGetQuery)
        types = query.types
        required_depth = query.requiredDepth

        if required_depth < 0 or required_depth > 32:
            return self.error("requiredDepth must be between 0 and 32")

        good_like = f"%thumbnails{'/__' * required_depth}/%"
        bad_like = f"%thumbnails{'/__' * (required_depth + 1)}/%"

        async with self.AsyncSession() as session:
            total, good, bad = await count_thumbnails_in_folders(
                session, types, good_like, bad_like
            )

        return self.success(
            data={
                "totalMatches": total,
                "inCorrectFolder": good,
                "inWrongFolder": bad,
            }
        )

    @permissions(["System admin"])
    async def patch(self, *, query: ThumbnailPathPatchQuery = None):
        """
        ---
        summary: Update thumbnail paths
        description: |
          Update the file path and file_uri of the database rows
          of thumbnails that are not in the correct folder/path.
        tags:
          - thumbnails
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

        query = self.parse_query(ThumbnailPathPatchQuery)

        types = query.types
        required_depth = query.requiredDepth
        if required_depth < 0 or required_depth > 32:
            return self.error("requiredDepth must be between 0 and 32")
        page_number = query.pageNumber
        num_per_page = min(query.numPerPage, 1000)

        good_like = f"%thumbnails{'/__' * required_depth}/%"
        bad_like = f"%thumbnails{'/__' * (required_depth + 1)}/%"

        num_moved = 0
        async with self.AsyncSession() as session:
            stmt = (
                sa.select(Thumbnail)
                .where(
                    Thumbnail.type.in_(types),
                    sa.or_(
                        ~Thumbnail.file_uri.like(good_like),
                        Thumbnail.file_uri.like(bad_like),
                    ),
                )
                .offset((page_number - 1) * num_per_page)
                .limit(num_per_page)
            )
            for t in (await session.scalars(stmt)).unique().all():
                if t.file_uri is None:
                    continue

                # the delete is committed in check_thumbnail_file
                if alert_available and not await check_thumbnail_file(
                    t, self.associated_user_object.id, session
                ):
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

            total, good, bad = await count_thumbnails_in_folders(
                session, types, good_like, bad_like
            )

        return self.success(
            data={
                "totalMatches": total,
                "inCorrectFolder": good,
                "inWrongFolder": bad,
                "numMoved": num_moved,
            }
        )

    # TODO: add a POST that only checks for missing or empty files

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
    """Count the thumbnails in the correct and incorrect folders."""
    in_good_folder = sa.and_(
        Thumbnail.file_uri.like(good_like), ~Thumbnail.file_uri.like(bad_like)
    )
    in_bad_folder = sa.or_(
        ~Thumbnail.file_uri.like(good_like), Thumbnail.file_uri.like(bad_like)
    )
    counts = await session.execute(
        sa.select(
            func.count(),
            func.count().filter(in_good_folder),
            func.count().filter(in_bad_folder),
        ).where(Thumbnail.type.in_(types))
    )
    return counts.one()


async def recreate_thumbnails_from_broker(obj_id, user_id, session):
    """Rebuild an object's thumbnails from a broker's cutouts.

    Uses the broker flagged for alert search, else any active broker that can
    serve both an alert and its cutouts. Returns whether anything was posted.
    """
    from ...broker_apis._thumbnails import add_thumbnails
    from .broker import alert_permissions_async

    user = await session.get(User, user_id)
    if user is None:
        return False
    # Providers fail closed on the stream scope: no permissions means no alert
    # matches, and the rebuild silently does nothing instead of raising.
    permissions = await alert_permissions_async(user, session)

    brokers = await session.scalars(
        sa.select(Broker)
        .where(Broker.active.is_(True))
        .order_by(Broker.default_alert_search.desc(), Broker.id)
    )

    for broker in brokers:
        capabilities = broker.broker_class.implements()
        if not capabilities.get("get_alert") or not capabilities.get("get_cutouts"):
            continue
        try:
            data = (
                broker.broker_class.get_alert(
                    broker, obj_id, session, permissions=permissions
                )
                or {}
            )
            candid = data.get("candid") or (data.get("candidate") or {}).get("candid")
            if candid is None:
                continue
            survey = data.get("survey") or (broker.altdata or {}).get("survey")
            cutouts = broker.broker_class.get_cutouts(
                broker, candid, session, survey=survey, permissions=permissions
            )
            if not cutouts:
                continue
            await add_thumbnails(obj_id, cutouts, survey, session, user_id=user_id)
            return True
        except Exception as e:
            log(f"Could not rebuild thumbnails for {obj_id} from {broker.name}: {e}")

    return False


async def check_thumbnail_file(thumbnail, user_id, session):
    """Check whether a thumbnail's file is present, and rebuild it if not.

    Returns True when the file is usable; when it is missing the row is dropped
    and the cutouts are re-fetched, so the caller should skip this thumbnail.
    """
    # need to import this here because alert.py might import this file
    from .alert import alert_available, post_alert

    if os.path.isfile(thumbnail.file_uri) and os.stat(thumbnail.file_uri).st_size != 0:
        return True

    obj_id = thumbnail.obj_id
    try:
        os.remove(thumbnail.file_uri)
    except OSError:
        pass
    await session.delete(thumbnail)
    await session.commit()

    if alert_available:
        # Fritz overrides this stub; await it there if it was made async.
        post_alert(
            object_id=obj_id,
            candid=None,
            group_ids="all",
            user_id=user_id,
            session=session,
            thumbnails_only=True,
        )
    else:
        await recreate_thumbnails_from_broker(obj_id, user_id, session)

    return False
