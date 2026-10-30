"""Backfilling a filter from a broker's own store, and replaying its stream."""

import asyncio
import re
import types

import pytest

from skyportal.app_server import skyportal_handlers
from skyportal.broker_apis import lasair
from skyportal.broker_apis._kafka import replay_group_id
from skyportal.handlers.api import (
    BrokerCredentialHandler,
    BrokerFilterBackfillHandler,
)


def route_for(path):
    for pattern, handler, *_ in skyportal_handlers:
        match = re.fullmatch(pattern, path)
        if match:
            return handler, match.groups()
    return None, None


def test_backfill_and_replay_routes():
    assert route_for("/api/brokers/1/filters/2/backfill") == (
        BrokerFilterBackfillHandler,
        ("1", "2"),
    )
    assert route_for("/api/brokers/1/credentials/replay") == (
        BrokerCredentialHandler,
        ("1", "replay"),
    )
    # The existing credential routes still resolve to the same handler.
    assert route_for("/api/brokers/1/credentials/topics") == (
        BrokerCredentialHandler,
        ("1", "topics"),
    )


def test_replay_group_id_only_suffixes_once_bumped():
    assert replay_group_id("skyportal-broker-3-user7", 0) == "skyportal-broker-3-user7"
    assert replay_group_id("skyportal-broker-3-user7", None) == (
        "skyportal-broker-3-user7"
    )
    # A distinct group is the whole mechanism: the upstream holds no offset for
    # it, so the consumer falls back to reading from the earliest message.
    assert replay_group_id("g", 1) == "g-r1"
    assert replay_group_id("g", 2) == "g-r2"


def test_credential_sets_carry_the_epoch():
    broker = types.SimpleNamespace(
        id=3, altdata={"kafka": {"topics": ["t"], "stream_epoch": 4}}
    )
    shared = lasair._credential_sets(broker)[0]
    assert shared["stream_epoch"] == 4

    broker = types.SimpleNamespace(id=3, altdata={})
    sets = lasair._credential_sets(
        broker, [{"label": "user7", "topics": ["t"], "stream_epoch": 2}]
    )
    assert sets[0]["stream_epoch"] == 2


def test_credential_set_without_an_epoch_reads_as_zero():
    broker = types.SimpleNamespace(id=3, altdata={})
    sets = lasair._credential_sets(broker, [{"label": "user7", "topics": ["t"]}])
    assert sets[0]["stream_epoch"] == 0


def test_filter_query_needs_tables():
    assert lasair.filter_query(types.SimpleNamespace(altdata=None)) is None
    assert lasair.filter_query(types.SimpleNamespace(altdata={})) is None
    assert lasair.filter_query(types.SimpleNamespace(altdata={"lasair": {}})) is None
    assert (
        lasair.filter_query(
            types.SimpleNamespace(altdata={"lasair": {"conditions": "x > 1"}})
        )
        is None
    )


def test_filter_query_falls_back_to_default_fields():
    query = lasair.filter_query(
        types.SimpleNamespace(altdata={"lasair": {"tables": "objects"}})
    )
    assert query == {
        "fields": lasair.DEFAULT_QUERY_FIELDS,
        "tables": "objects",
        "conditions": "",
    }


def test_filter_query_prefers_selected_over_fields():
    query = lasair.filter_query(
        types.SimpleNamespace(
            altdata={
                "lasair": {
                    "tables": "objects",
                    "selected": "a, b",
                    "fields": "c",
                    "conditions": "a > 1",
                }
            }
        )
    )
    assert query == {"fields": "a, b", "tables": "objects", "conditions": "a > 1"}


def test_backfill_ingests_each_object_once(monkeypatch):
    rows = [
        {"objectId": "ZTF1"},
        {"objectId": "ZTF2"},
        {"objectId": "ZTF1"},  # a repeat in the result set costs no second call
        {"ramean": 1.0},  # no object id at all
    ]
    monkeypatch.setattr(lasair, "_query", lambda *a, **k: rows)
    ingested = []

    async def fake_ingest(broker, oid, survey, filter_ids, token=None, payload=None):
        ingested.append((oid, filter_ids, token))

    monkeypatch.setattr(lasair, "_ingest_object", fake_ingest)

    done, failed, found = asyncio.run(
        lasair._run_backfill(
            types.SimpleNamespace(id=3),
            "ZTF",
            types.SimpleNamespace(id=9, altdata={"lasair": {"tables": "objects"}}),
            token="tok",
            interval=0,
        )
    )
    assert (done, failed, found) == (2, 0, 2)
    assert ingested == [("ZTF1", [9], "tok"), ("ZTF2", [9], "tok")]


def test_backfill_counts_a_failure_and_keeps_going(monkeypatch):
    monkeypatch.setattr(
        lasair, "_query", lambda *a, **k: [{"objectId": "A"}, {"objectId": "B"}]
    )

    async def fake_ingest(broker, oid, survey, filter_ids, token=None, payload=None):
        if oid == "A":
            raise ValueError("upstream said no")

    monkeypatch.setattr(lasair, "_ingest_object", fake_ingest)
    assert asyncio.run(
        lasair._run_backfill(
            types.SimpleNamespace(id=3),
            "ZTF",
            types.SimpleNamespace(id=9, altdata={"lasair": {"tables": "objects"}}),
            interval=0,
        )
    ) == (1, 1, 2)


def test_backfill_refuses_a_filter_with_no_saved_query():
    with pytest.raises(ValueError, match="no saved Lasair query"):
        asyncio.run(
            lasair._run_backfill(
                types.SimpleNamespace(id=3),
                "ZTF",
                types.SimpleNamespace(id=9, altdata={}),
            )
        )
