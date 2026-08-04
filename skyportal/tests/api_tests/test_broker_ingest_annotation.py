import asyncio
import uuid

import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from skyportal.broker_apis._save import save_object_as_candidate
from skyportal.models import Annotation, DBSession, Instrument, Obj, User
from skyportal.tests.fixtures import InstrumentFactory


def test_broker_ingest_creates_filter_annotation(super_admin_user, public_filter):
    """A passing candidate must get the filter's auto-annotation (origin
    "{group}:{filter}"), scoped to the filter's group, on ingest."""
    # The ingest looks up the survey instrument by name; ensure a "ZTF" one exists.
    created_instrument = None
    if (
        DBSession().scalar(sa.select(Instrument).where(Instrument.name == "ZTF"))
        is None
    ):
        created_instrument = InstrumentFactory(name="ZTF")
        DBSession().commit()

    obj_id = f"ZTF{uuid.uuid4().hex[:10]}"
    annotation_data = {"mag_now": 18.53, "drb": 0.99}

    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            user = await session.get(User, super_admin_user.id)
            await save_object_as_candidate(
                {
                    "objectId": obj_id,
                    "candidate": {"ra": 10.0, "dec": 20.0, "drb": 0.99},
                },
                "ZTF",
                session,
                user,
                [public_filter.id],
                passing_alert_id=12345,
                annotations_by_filter_id={public_filter.id: annotation_data},
            )

    try:
        asyncio.run(_run())

        group = public_filter.group
        origin = f"{group.nickname or group.name}:{public_filter.name}"
        annotation = DBSession().scalar(
            sa.select(Annotation).where(
                Annotation.obj_id == obj_id, Annotation.origin == origin
            )
        )
        assert annotation is not None, "filter annotation was not created on ingest"
        assert annotation.data == annotation_data
        assert group.id in [g.id for g in annotation.groups]
    finally:
        # Cascade-delete the ingested obj (removes its candidate + annotation).
        DBSession().execute(sa.delete(Obj).where(Obj.id == obj_id))
        DBSession().commit()
        if created_instrument is not None:
            InstrumentFactory.teardown(created_instrument)
