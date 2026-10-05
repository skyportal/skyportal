import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

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


def ingest(obj_id, user_id, filter_id, annotations, alert_id=12345, **data):
    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            user = await session.get(User, user_id)
            await save_object_as_candidate(
                {
                    "objectId": obj_id,
                    "candidate": {"ra": 10.0, "dec": 20.0, "drb": 0.99},
                    **data,
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


def _save_to_group(obj_id, group, user):
    """Pre-create the object and an active Source in `group` (e.g. a junk group)."""
    DBSession().add(Obj(id=obj_id, ra=10.0, dec=20.0))
    DBSession().flush()
    DBSession().add(
        Source(obj_id=obj_id, group_id=group.id, saved_by_id=user.id, active=True)
    )
    DBSession().commit()


def test_broker_ingest_autosave_skips_ignored_group(
    super_admin_user, public_filter, public_group2, ztf_instrument, obj_id
):
    """autosave skips an object already actively saved to one of the filter's
    `autoSaveIgnoreGroupIds` (e.g. a junk group)."""
    _save_to_group(obj_id, public_group2, super_admin_user)
    public_filter.autosave = True
    public_filter.altdata = {"autoSaveIgnoreGroupIds": [public_group2.id]}
    DBSession().add(public_filter)
    DBSession().commit()

    ingest(obj_id, super_admin_user.id, public_filter.id, {})

    assert fetch_source(obj_id, public_filter) is None, (
        "object in an ignored group should not be auto-saved to the filter group"
    )


def test_broker_ingest_autosave_ignore_is_group_specific(
    super_admin_user, public_filter, public_group2, ztf_instrument, obj_id
):
    """An object saved to a group that is NOT in `autoSaveIgnoreGroupIds` is
    still auto-saved."""
    _save_to_group(obj_id, public_group2, super_admin_user)
    public_filter.autosave = True
    public_filter.altdata = {"autoSaveIgnoreGroupIds": []}  # junk group not ignored
    DBSession().add(public_filter)
    DBSession().commit()

    ingest(obj_id, super_admin_user.id, public_filter.id, {})

    assert fetch_source(obj_id, public_filter) is not None, (
        "object should be auto-saved when not in an ignored group"
    )


def test_broker_ingest_dates_thumbnails_with_boom_alert_epoch(
    super_admin_user, public_filter, ztf_instrument, obj_id, monkeypatch
):
    """The cutouts of a BOOM alert are dated with the alert's own epoch."""
    from skyportal.broker_apis import _thumbnails
    from skyportal.broker_apis.boom import _normalize_boom_alert

    dates = []

    async def fake_add_thumbnails(obj_id, cutouts, survey, session, user_id=1, jd=None):
        dates.append(jd)

    monkeypatch.setattr(_thumbnails, "add_thumbnails", fake_add_thumbnails)
    data = _normalize_boom_alert(
        {
            "objectId": obj_id,
            "candid": 12345,
            "jd": 2461317.5,
            "ra": 10.0,
            "dec": 20.0,
            "drb": 0.99,
            "photometry": [],
        }
    )

    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            user = await session.get(User, super_admin_user.id)
            await save_object_as_candidate(
                data,
                "ZTF",
                session,
                user,
                [public_filter.id],
                passing_alert_id=12345,
                cutouts={"cutoutScience": b"fits"},
            )

    asyncio.run(_run())

    assert dates == [2461317.5]


def test_broker_ingest_survives_a_concurrent_obj_insert(
    super_admin_user, public_filter, ztf_instrument, obj_id
):
    with baselayer_models.new_session() as other, ThreadPoolExecutor(1) as pool:
        other.add(Obj(id=obj_id, ra=10.0, dec=20.0))
        other.flush()
        ingesting = pool.submit(
            ingest, obj_id, super_admin_user.id, public_filter.id, {}
        )
        time.sleep(1)
        other.commit()
        ingesting.result()

    candidate = DBSession().scalar(
        sa.select(Candidate).where(
            Candidate.obj_id == obj_id, Candidate.filter_id == public_filter.id
        )
    )
    assert candidate is not None


def test_broker_ingest_autosave_survives_a_concurrent_save(
    super_admin_user, public_filter, ztf_instrument, obj_id
):
    public_filter.autosave = True
    DBSession().add(public_filter)
    DBSession().add(Obj(id=obj_id, ra=10.0, dec=20.0))
    DBSession().commit()

    with baselayer_models.new_session() as other, ThreadPoolExecutor(1) as pool:
        other.add(
            Source(
                obj_id=obj_id,
                group_id=public_filter.group_id,
                saved_by_id=super_admin_user.id,
            )
        )
        other.flush()
        ingesting = pool.submit(
            ingest, obj_id, super_admin_user.id, public_filter.id, {}
        )
        time.sleep(1)
        other.commit()
        ingesting.result()

    candidate = DBSession().scalar(
        sa.select(Candidate).where(
            Candidate.obj_id == obj_id, Candidate.filter_id == public_filter.id
        )
    )
    assert candidate is not None
    assert fetch_source(obj_id, public_filter) is not None


def test_broker_ingest_keeps_the_candidate_when_photometry_fails(
    super_admin_user, public_filter, ztf_instrument, obj_id
):
    public_filter.stream.altdata = {"collection": "ZTF_alerts", "selector": [1]}
    DBSession().add(public_filter.stream)
    DBSession().commit()

    ingest(
        obj_id,
        super_admin_user.id,
        public_filter.id,
        {},
        prv_candidates=[
            {"jd": 2461317.5, "band": "r", "psfFlux": None, "psfFluxErr": float("inf")}
        ],
    )

    candidate = DBSession().scalar(
        sa.select(Candidate).where(
            Candidate.obj_id == obj_id, Candidate.filter_id == public_filter.id
        )
    )
    assert candidate is not None


def test_broker_ingest_keeps_the_candidate_when_the_photometry_insert_fails(
    super_admin_user, public_filter, ztf_instrument, obj_id, monkeypatch
):
    from skyportal.handlers.api import photometry

    async def failing_insert(
        df, instrument_cache, group_ids, stream_ids, user, session, **kwargs
    ):
        await session.execute(
            sa.update(Obj).where(Obj.id == obj_id).values(score=0.0),
            execution_options={"synchronize_session": False},
        )
        raise ValueError("photometry insert failed")

    monkeypatch.setattr(photometry, "insert_new_photometry_data", failing_insert)
    public_filter.stream.altdata = {"collection": "ZTF_alerts", "selector": [1]}
    DBSession().add(public_filter.stream)
    DBSession().commit()

    ingest(
        obj_id,
        super_admin_user.id,
        public_filter.id,
        {},
        prv_candidates=[
            {"jd": 2461317.5, "band": "r", "psfFlux": 1000.0, "psfFluxErr": 10.0}
        ],
    )

    candidate = DBSession().scalar(
        sa.select(Candidate).where(
            Candidate.obj_id == obj_id, Candidate.filter_id == public_filter.id
        )
    )
    assert candidate is not None
    score = DBSession().scalar(sa.select(Obj.score).where(Obj.id == obj_id))
    assert score == pytest.approx(0.99)


def test_broker_ingest_registers_a_concurrently_reconsumed_alert_once(
    super_admin_user, public_filter, ztf_instrument, obj_id, monkeypatch
):
    from skyportal.broker_apis import _save

    def slow_photometry_groups(*args):
        time.sleep(2)
        return {}

    monkeypatch.setattr(_save, "build_photometry_groups", slow_photometry_groups)
    DBSession().add(Obj(id=obj_id, ra=10.0, dec=20.0))
    DBSession().commit()

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(ingest, obj_id, super_admin_user.id, public_filter.id, {})
        time.sleep(1)
        second = pool.submit(ingest, obj_id, super_admin_user.id, public_filter.id, {})
        first.result()
        second.result()

    candidates = DBSession().scalars(
        sa.select(Candidate).where(
            Candidate.obj_id == obj_id, Candidate.filter_id == public_filter.id
        )
    )
    assert len(candidates.all()) == 1
