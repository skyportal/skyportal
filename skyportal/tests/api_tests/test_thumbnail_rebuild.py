"""Rebuilding missing thumbnails from a broker's cutouts.

Fritz overlays `handlers/api/alert.py` to back-populate thumbnails from
Kowalski; a plain SkyPortal has no such hook, so the broker framework is what
has to supply the cutouts.
"""

import asyncio
import uuid

import pytest
import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from skyportal.broker_apis import _thumbnails, generic
from skyportal.handlers.api.thumbnail import recreate_thumbnails_from_broker
from skyportal.models import Broker, DBSession

OBJ_ID = "ZTFthumbprobe"
USER_ID = 1


@pytest.fixture()
def cutout_broker():
    broker = Broker(
        name=f"stub_{uuid.uuid4().hex[:8]}",
        broker_classname="GENERICBROKER",
        altdata={"base_url": "https://broker.test", "token": "secret"},
        active=True,
    )
    DBSession().add(broker)
    DBSession().commit()
    broker_id = broker.id
    yield broker
    DBSession().execute(sa.delete(Broker).where(Broker.id == broker_id))
    DBSession().commit()


def stub_provider(monkeypatch, cutouts, capabilities=None):
    """Point GENERICBROKER at canned responses instead of the network."""
    monkeypatch.setattr(
        generic.GENERICBROKER,
        "implements",
        classmethod(
            lambda cls: capabilities or {"get_alert": True, "get_cutouts": True}
        ),
    )
    monkeypatch.setattr(
        generic.GENERICBROKER,
        "get_alert",
        staticmethod(
            lambda broker, alert_id, session, **kw: {
                "candid": 1234567890,
                "survey": "ZTF",
            }
        ),
    )
    monkeypatch.setattr(
        generic.GENERICBROKER,
        "get_cutouts",
        staticmethod(lambda broker, alert_id, session, **kw: cutouts),
    )


def rebuild(obj_id, user_id):
    result = {}

    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            result["rebuilt"] = await recreate_thumbnails_from_broker(
                obj_id, user_id, session
            )

    asyncio.run(_run())
    return result["rebuilt"]


def test_rebuild_posts_thumbnails_from_broker_cutouts(monkeypatch, cutout_broker):
    posted = []

    async def fake_add_thumbnails(obj_id, cutouts, survey, session, user_id=1):
        posted.append((obj_id, sorted(cutouts), survey, user_id))

    stub_provider(monkeypatch, {"cutoutScience": b"fits", "cutoutTemplate": b"fits"})
    monkeypatch.setattr(_thumbnails, "add_thumbnails", fake_add_thumbnails)

    assert rebuild(OBJ_ID, USER_ID) is True
    assert posted == [
        (
            OBJ_ID,
            ["cutoutScience", "cutoutTemplate"],
            "ZTF",
            USER_ID,
        )
    ]


def test_rebuild_skips_brokers_that_cannot_serve_cutouts(monkeypatch, cutout_broker):
    called = []

    async def fake_add_thumbnails(*args, **kwargs):
        called.append(args)

    stub_provider(
        monkeypatch,
        {"cutoutScience": b"fits"},
        capabilities={"get_alert": True, "get_cutouts": False},
    )
    monkeypatch.setattr(_thumbnails, "add_thumbnails", fake_add_thumbnails)

    assert rebuild(OBJ_ID, USER_ID) is False
    assert called == []


def test_rebuild_reports_failure_when_the_broker_has_no_cutouts(
    monkeypatch, cutout_broker
):
    """An alert with no cutout payload is not an error, but nothing is posted."""
    called = []

    async def fake_add_thumbnails(*args, **kwargs):
        called.append(args)

    stub_provider(monkeypatch, {})
    monkeypatch.setattr(_thumbnails, "add_thumbnails", fake_add_thumbnails)

    assert rebuild(OBJ_ID, USER_ID) is False
    assert called == []
