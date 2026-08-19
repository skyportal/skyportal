"""A broker cutout thumbnail records the survey it came from (e.g. ZTF, LSST) so
the source page can label per-survey tiles — obj.origin is too noisy to rely on."""

import asyncio
import base64
import io

import sqlalchemy as sa
from PIL import Image

from baselayer.app import models as baselayer_models
from skyportal.handlers.api.thumbnail import post_thumbnail
from skyportal.models import DBSession, Thumbnail


def _png_b64():
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (10, 20, 30)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def test_post_thumbnail_persists_survey(super_admin_user, public_source):
    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            return await post_thumbnail(
                {
                    "obj_id": public_source.id,
                    "data": _png_b64(),
                    "ttype": "new",
                    "survey": "LSST",
                },
                super_admin_user.id,
                session,
            )

    thumbnail_id = asyncio.run(_run())
    try:
        DBSession().expire_all()
        thumbnail = DBSession().scalar(
            sa.select(Thumbnail).where(Thumbnail.id == thumbnail_id)
        )
        assert thumbnail is not None
        assert thumbnail.survey == "LSST", "thumbnail did not persist its survey"
    finally:
        DBSession().execute(sa.delete(Thumbnail).where(Thumbnail.id == thumbnail_id))
        DBSession().commit()
