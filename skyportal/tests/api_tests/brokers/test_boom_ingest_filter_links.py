import asyncio
import uuid
from datetime import timedelta
from types import SimpleNamespace

import confluent_kafka
import pytest
import sqlalchemy as sa

from skyportal.broker_apis import _kafka, boom
from skyportal.broker_apis.boom import BOOMBROKER
from skyportal.models import Candidate, DBSession, Instrument, Obj
from skyportal.tests.fixtures import InstrumentFactory


@pytest.fixture()
def ztf_instrument():
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
def obj_ids():
    obj_ids = [f"ZTF{uuid.uuid4().hex[:10]}" for _ in range(2)]
    yield obj_ids
    DBSession().execute(sa.delete(Obj).where(Obj.id.in_(obj_ids)))
    DBSession().commit()


def test_filter_linked_while_ingesting_gets_its_alerts(
    public_filter, ztf_instrument, obj_ids, monkeypatch
):
    """A Filter linked to a BOOM filter once the ingestion is running gets that
    BOOM filter's alerts without a restart."""
    boom_filter_id = str(uuid.uuid4())
    messages = [
        SimpleNamespace(
            error=lambda: None,
            value=lambda obj_id=obj_id: {
                "objectId": obj_id,
                "survey": "ZTF",
                "ra": 10.0,
                "dec": 20.0,
                "filters": [{"filter_id": boom_filter_id}],
            },
        )
        for obj_id in obj_ids
    ]

    class FakeConsumer:
        def __init__(self, config):
            pass

        def subscribe(self, topics):
            pass

        def poll(self, timeout):
            return messages.pop(0) if messages else None

        def close(self):
            pass

    def read_avro(record):
        if record["objectId"] == obj_ids[1]:
            public_filter.altdata = {"boom": {"filter_id": boom_filter_id}}
            DBSession().add(public_filter)
            DBSession().commit()
        return record

    monkeypatch.setattr(confluent_kafka, "Consumer", FakeConsumer)
    monkeypatch.setattr(_kafka, "read_avro", read_avro)
    monkeypatch.setattr(boom, "FILTER_LINKS_TTL", timedelta(0))

    broker = SimpleNamespace(id=0, altdata={"kafka": {}})
    assert asyncio.run(BOOMBROKER.run_ingestion(broker, max_messages=2)) == 2

    DBSession().expire_all()
    ingested = DBSession().scalars(
        sa.select(Candidate.obj_id).where(Candidate.filter_id == public_filter.id)
    )
    assert ingested.all() == [obj_ids[1]]
