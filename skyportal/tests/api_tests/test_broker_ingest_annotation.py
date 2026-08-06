import asyncio
import uuid

import pytest
import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from skyportal.broker_apis._save import save_object_as_candidate
from skyportal.models import (
    Annotation,
    Candidate,
    DBSession,
    Instrument,
    Obj,
    Source,
    User,
)
from skyportal.tests.fixtures import InstrumentFactory


@pytest.fixture()
def ztf_instrument():
    """The ingest looks up the survey instrument by name; ensure a "ZTF" one exists."""
    created = None
    if (
        DBSession().scalar(sa.select(Instrument).where(Instrument.name == "ZTF"))
        is None
    ):
        created = InstrumentFactory(name="ZTF")
        DBSession().commit()
    yield
    if created is not None:
        InstrumentFactory.teardown(created)


@pytest.fixture()
def obj_id():
    obj_id = f"ZTF{uuid.uuid4().hex[:10]}"
    yield obj_id
    DBSession().execute(sa.delete(Obj).where(Obj.id == obj_id))
    DBSession().commit()


def ingest(obj_id, user_id, filter_id, annotations, alert_id=12345):
    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            user = await session.get(User, user_id)
            await save_object_as_candidate(
                {
                    "objectId": obj_id,
                    "candidate": {"ra": 10.0, "dec": 20.0, "drb": 0.99},
                },
                "ZTF",
                session,
                user,
                [filter_id],
                passing_alert_id=alert_id,
                annotations_by_filter_id={filter_id: annotations},
            )

    asyncio.run(_run())


def fetch_annotation(obj_id, filter_):
    group = filter_.group
    origin = f"{group.nickname or group.name}:{filter_.name}"
    DBSession().expire_all()
    return DBSession().scalar(
        sa.select(Annotation).where(
            Annotation.obj_id == obj_id, Annotation.origin == origin
        )
    )


def test_broker_ingest_creates_filter_annotation(
    super_admin_user, public_filter, ztf_instrument, obj_id
):
    """A passing candidate must get the filter's auto-annotation (origin
    "{group}:{filter}"), scoped to the filter's group, on ingest."""
    annotation_data = {"mag_now": 18.53, "drb": 0.99}
    ingest(obj_id, super_admin_user.id, public_filter.id, annotation_data)

    annotation = fetch_annotation(obj_id, public_filter)
    assert annotation is not None, "filter annotation was not created on ingest"
    assert annotation.data == annotation_data
    assert public_filter.group.id in [g.id for g in annotation.groups]


def test_broker_ingest_refreshes_its_own_annotation(
    super_admin_user, public_filter, ztf_instrument, obj_id
):
    """Re-ingesting the same obj+filter upserts on (obj_id, origin) instead of
    raising an IntegrityError that would roll back the whole alert."""
    ingest(obj_id, super_admin_user.id, public_filter.id, {"mag_now": 18.53})
    ingest(
        obj_id, super_admin_user.id, public_filter.id, {"mag_now": 17.1}, alert_id=67890
    )

    annotation = fetch_annotation(obj_id, public_filter)
    assert annotation.data == {"mag_now": 17.1}
    assert public_filter.group.id in [g.id for g in annotation.groups]


def fetch_source(obj_id, filter_):
    DBSession().expire_all()
    return DBSession().scalar(
        sa.select(Source).where(
            Source.obj_id == obj_id, Source.group_id == filter_.group_id
        )
    )


def test_broker_ingest_autosave_saves_source(
    super_admin_user, public_filter, ztf_instrument, obj_id
):
    """With the filter's `autosave` flag set, a passing object is saved as a
    Source in the filter's group, not only registered as a Candidate."""
    public_filter.autosave = True
    DBSession().add(public_filter)
    DBSession().commit()

    ingest(obj_id, super_admin_user.id, public_filter.id, {})

    source = fetch_source(obj_id, public_filter)
    assert source is not None, "autosave did not save the object as a Source"
    assert source.saved_by_id == super_admin_user.id


def test_broker_ingest_without_autosave_registers_candidate_only(
    super_admin_user, public_filter, ztf_instrument, obj_id
):
    """With `autosave` off (the default), a passing object is registered as a
    Candidate but not saved as a Source."""
    ingest(obj_id, super_admin_user.id, public_filter.id, {})

    assert fetch_source(obj_id, public_filter) is None, (
        "object should not be saved as a Source when autosave is off"
    )
    candidate = DBSession().scalar(
        sa.select(Candidate).where(
            Candidate.obj_id == obj_id, Candidate.filter_id == public_filter.id
        )
    )
    assert candidate is not None, "candidate was not registered on ingest"


def test_broker_ingest_leaves_another_authors_annotation_alone(
    super_admin_user, user, public_filter, ztf_instrument, obj_id
):
    """origin is user-writable through the annotation API, so an annotation another
    user already owns on that origin must not be overwritten by the ingest."""
    ingest(obj_id, user.id, public_filter.id, {"posted_by": "user"})

    ingest(
        obj_id,
        super_admin_user.id,
        public_filter.id,
        {"posted_by": "broker"},
        alert_id=67890,
    )

    annotation = fetch_annotation(obj_id, public_filter)
    assert annotation.data == {"posted_by": "user"}
    assert annotation.author_id == user.id
