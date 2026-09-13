"""The request body a broker filter version is posted with.

A compiled native filter is a mongo aggregation pipeline -- a list of stages --
and is forwarded verbatim as ``pipeline=``. The body has to accept it as one.
"""

import pytest
from pydantic import ValidationError

from skyportal.handlers.api.broker import BrokerFiltersPostBody

PIPELINE = [
    {"$match": {"candidate.drb": {"$gt": 0.5}}},
    {"$project": {"objectId": 1, "candid": 1, "candidate": 1}},
]


def test_altdata_accepts_a_pipeline():
    body = BrokerFiltersPostBody(altdata=PIPELINE, filters="v1")
    assert body.altdata == PIPELINE


def test_altdata_rejects_a_mapping():
    # A mapping reaches the broker as a pipeline it cannot run, so it is refused
    # at the boundary rather than failing further in.
    with pytest.raises(ValidationError):
        BrokerFiltersPostBody(altdata={"$match": {"candidate.drb": {"$gt": 0.5}}})


def test_altdata_is_optional_for_query_brokers():
    # A query-kind broker (Lasair) carries `query` and no pipeline.
    body = BrokerFiltersPostBody(
        query={"selected": "objectId", "tables": "objects", "conditions": ""}
    )
    assert body.altdata is None
