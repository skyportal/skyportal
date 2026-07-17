import uuid
from types import SimpleNamespace
from urllib.parse import parse_qs

import pytest
import responses

from skyportal.broker_apis import GENERICBROKER, BrokerAPI
from skyportal.tests import api


def _broker_payload(**overrides):
    payload = {
        "name": str(uuid.uuid4()),
        "broker_classname": "GENERICBROKER",
        "altdata": {"base_url": "https://broker.test", "token": "secret"},
    }
    payload.update(overrides)
    return payload


def test_broker_crud(super_admin_token):
    payload = _broker_payload()
    status, data = api("POST", "brokers", data=payload, token=super_admin_token)
    assert status == 200
    broker_id = data["data"]["id"]

    # system admin sees decrypted altdata + capabilities
    status, data = api("GET", f"brokers/{broker_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["name"] == payload["name"]
    assert data["data"]["broker_classname"] == "GENERICBROKER"
    assert data["data"]["altdata"]["base_url"] == "https://broker.test"
    assert data["data"]["capabilities"]["query_alerts"] is True
    assert data["data"]["capabilities"]["cone_search"] is False

    # update
    status, data = api(
        "PATCH", f"brokers/{broker_id}", data={"active": False}, token=super_admin_token
    )
    assert status == 200
    status, data = api("GET", f"brokers/{broker_id}", token=super_admin_token)
    assert data["data"]["active"] is False

    # delete
    status, data = api("DELETE", f"brokers/{broker_id}", token=super_admin_token)
    assert status == 200
    status, data = api("GET", f"brokers/{broker_id}", token=super_admin_token)
    assert status == 400


def test_broker_invalid_classname(super_admin_token):
    payload = _broker_payload(broker_classname="NOTAREALBROKER")
    status, data = api("POST", "brokers", data=payload, token=super_admin_token)
    assert status == 400


def test_broker_invalid_config(super_admin_token):
    # GENERICBROKER.validate_config requires base_url
    payload = _broker_payload(altdata={})
    status, data = api("POST", "brokers", data=payload, token=super_admin_token)
    assert status == 400


def test_broker_requires_admin_and_redacts_altdata(super_admin_token, view_only_token):
    # non-admin cannot create
    status, data = api("POST", "brokers", data=_broker_payload(), token=view_only_token)
    assert status != 200

    status, data = api(
        "POST", "brokers", data=_broker_payload(), token=super_admin_token
    )
    assert status == 200
    broker_id = data["data"]["id"]

    # non-admin can read the broker, but altdata is redacted
    status, data = api("GET", f"brokers/{broker_id}", token=view_only_token)
    assert status == 200
    assert "altdata" not in data["data"]
    assert data["data"]["capabilities"]["query_alerts"] is True


def test_broker_apis_discovery(view_only_token):
    status, data = api("GET", "internal/broker_apis", token=view_only_token)
    assert status == 200
    assert "GENERICBROKER" in data["data"]
    caps = data["data"]["GENERICBROKER"]["methodsImplemented"]
    assert caps["query_alerts"] is True
    assert caps["get_alert"] is True
    assert caps["cone_search"] is False
    assert data["data"]["GENERICBROKER"]["formSchemaConfig"]["required"] == ["base_url"]


def test_broker_alerts_inactive(super_admin_token):
    payload = _broker_payload(active=False)
    status, data = api("POST", "brokers", data=payload, token=super_admin_token)
    assert status == 200
    broker_id = data["data"]["id"]
    status, data = api("GET", f"brokers/{broker_id}/alerts", token=super_admin_token)
    assert status == 400


# --- provider-level unit tests (no running server needed) ---


def test_brokerapi_base_implements_nothing():
    caps = BrokerAPI.implements()
    assert all(v is False for v in caps.values())
    with pytest.raises(NotImplementedError):
        BrokerAPI.query_alerts(None, None)


def test_genericbroker_capabilities():
    caps = GENERICBROKER.implements()
    assert caps["query_alerts"] is True
    assert caps["get_alert"] is True
    assert caps["validate_config"] is True
    # save_as_source is provided by the base for any provider that can fetch an
    # object, so it's gated on get_alert (which GENERICBROKER implements).
    assert caps["save_as_source"] is True


@responses.activate
def test_genericbroker_query_alerts_unit():
    responses.add(
        responses.GET,
        "https://broker.test/alerts",
        json={"data": [{"objectId": "ZTF1"}]},
        status=200,
    )
    broker = SimpleNamespace(altdata={"base_url": "https://broker.test", "token": "t"})
    result = GENERICBROKER.query_alerts(broker, None, objectId="ZTF1")
    assert result == [{"objectId": "ZTF1"}]


@responses.activate
def test_genericbroker_get_alert_unit():
    responses.add(
        responses.GET,
        "https://broker.test/alerts/ZTF1",
        json={"objectId": "ZTF1", "candid": 123},
        status=200,
    )
    broker = SimpleNamespace(altdata={"base_url": "https://broker.test"})
    result = GENERICBROKER.get_alert(broker, "ZTF1", None)
    assert result["candid"] == 123


def test_genericbroker_validate_config():
    GENERICBROKER.validate_config({"base_url": "https://broker.test"})
    with pytest.raises(ValueError):
        GENERICBROKER.validate_config({})


# --- LASAIRBROKER (mock the lasair client so no lib/network is needed) ---


def _add_lasair_responses():
    """Mock the Lasair REST methods the provider POSTs to (it calls the API
    directly rather than via the `lasair` client)."""
    responses.add(
        responses.POST,
        "https://x/api/object/",
        json={"objectId": "L9", "diaSourcesList": []},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://x/api/cone/",
        json={"count": 1, "objects": [{"objectId": "L1"}]},
        status=200,
    )


def test_lasairbroker_capabilities():
    from skyportal.broker_apis import LASAIRBROKER

    caps = LASAIRBROKER.implements()
    assert caps["query_alerts"] is True
    assert caps["get_alert"] is True
    assert caps["cone_search"] is True
    assert caps["validate_config"] is True
    with pytest.raises(ValueError):
        LASAIRBROKER.validate_config({})


@responses.activate
def test_lasairbroker_query_routing():
    from skyportal.broker_apis import LASAIRBROKER

    _add_lasair_responses()
    broker = SimpleNamespace(altdata={"token": "t", "endpoint": "https://x/api"})

    # objectId -> object()
    assert LASAIRBROKER.query_alerts(broker, None, objectId="L9")["objectId"] == "L9"
    assert responses.calls[0].request.url == "https://x/api/object/"
    assert parse_qs(responses.calls[0].request.body)["objectId"] == ["L9"]

    # ra/dec -> cone()
    res = LASAIRBROKER.query_alerts(broker, None, ra=194.0, dec=-3.0, radius=60)
    assert res["count"] == 1
    assert responses.calls[1].request.url == "https://x/api/cone/"
    cone = parse_qs(responses.calls[1].request.body)
    assert (cone["ra"], cone["dec"], cone["radius"], cone["requestType"]) == (
        ["194.0"],
        ["-3.0"],
        ["60.0"],
        ["all"],
    )

    # direct cone_search()
    LASAIRBROKER.cone_search(broker, 10.0, 20.0, 30.0, None)
    assert responses.calls[2].request.url == "https://x/api/cone/"
    cone = parse_qs(responses.calls[2].request.body)
    assert (cone["ra"], cone["dec"], cone["radius"], cone["requestType"]) == (
        ["10.0"],
        ["20.0"],
        ["30.0"],
        ["all"],
    )
