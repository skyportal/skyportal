import json
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


def test_broker_capabilities_expose_cross_match_catalogs(super_admin_token):
    """GET /brokers surfaces cross_match_catalogs in capabilities -- the flag the
    source-page centroid overlay reads to pick a reference-catalog broker (so it
    only cone_searches BOOM, never alert-only brokers)."""
    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(
            broker_classname="BOOMBROKER",
            altdata={"host": "boom.test", "username": "x", "password": "y"},
        ),
        token=super_admin_token,
    )
    assert status == 200, data
    boom_id = data["data"]["id"]

    status, data = api(
        "POST", "brokers", data=_broker_payload(), token=super_admin_token
    )
    assert status == 200, data
    generic_id = data["data"]["id"]

    try:
        status, data = api("GET", f"brokers/{boom_id}", token=super_admin_token)
        assert status == 200, data
        assert data["data"]["capabilities"]["cross_match_catalogs"] is True

        status, data = api("GET", f"brokers/{generic_id}", token=super_admin_token)
        assert status == 200, data
        assert data["data"]["capabilities"]["cross_match_catalogs"] is False
    finally:
        api("DELETE", f"brokers/{boom_id}", token=super_admin_token)
        api("DELETE", f"brokers/{generic_id}", token=super_admin_token)


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


def test_cross_match_catalogs_capability():
    """Only BOOM's cone_search returns reference catalogs, so only it advertises
    cross_match_catalogs. The source-page centroid overlay gates on this flag so
    it never cone_searches alert-only brokers (Lasair/Fink), which rate-limit."""
    from skyportal.broker_apis import BOOMBROKER, LASAIRBROKER

    assert BOOMBROKER.implements()["cross_match_catalogs"] is True
    assert LASAIRBROKER.implements()["cross_match_catalogs"] is False
    assert BrokerAPI.implements()["cross_match_catalogs"] is False


def test_configured_surveys_per_record():
    """A record's surveys reflect the deployment for one-survey-per-instance
    providers (Lasair), but stay the full list for multi-survey ones (BOOM)."""
    from skyportal.broker_apis import BOOMBROKER, LASAIRBROKER

    # BOOM serves both surveys from one connection (survey is a per-query kwarg)
    assert set(BOOMBROKER.configured_surveys({"survey": "ZTF"})) == {"ZTF", "LSST"}

    # Lasair's ZTF/LSST are separate deployments (distinct endpoint + token)
    assert LASAIRBROKER.configured_surveys(
        {"endpoint": "https://lasair-ztf.lsst.ac.uk/api"}
    ) == ["ZTF"]
    assert LASAIRBROKER.configured_surveys({"survey": "LSST"}) == ["LSST"]
    assert LASAIRBROKER.configured_surveys({}) == ["LSST"]  # default endpoint


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


# --- BOOMBROKER cone_search (reference-catalog cross-match) ---


def _boom_broker():
    return SimpleNamespace(
        altdata={
            "protocol": "https",
            "host": "boom.test",
            "username": "u",
            "password": "p",
        }
    )


def test_boombroker_capabilities():
    from skyportal.broker_apis import BOOMBROKER

    caps = BOOMBROKER.implements()
    assert caps["cone_search"] is True
    assert caps["get_photometry"] is True


@responses.activate
def test_boombroker_cone_search():
    from skyportal.broker_apis import BOOMBROKER
    from skyportal.broker_apis.boom import _CATALOGS_CACHE, _TOKENS

    # module-scope caches persist across tests; reset so this run is deterministic
    _CATALOGS_CACHE.clear()
    _TOKENS.clear()

    responses.add(
        responses.POST,
        "https://boom.test/auth",
        json={"access_token": "tok", "expires_in": 3600},
        status=200,
    )
    # a reference catalog plus a survey/alert catalog that must be filtered out
    responses.add(
        responses.GET,
        "https://boom.test/catalogs",
        json={"data": [{"name": "Gaia_DR3"}, {"name": "ZTF_alerts"}]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://boom.test/queries/cone_search",
        json={
            "data": {
                "query": [
                    {
                        "_id": 42,
                        "coordinates": {
                            "radec_geojson": {"coordinates": [-100.0, 20.0]}
                        },
                    }
                ]
            }
        },
        status=200,
    )

    result = BOOMBROKER.cone_search(
        _boom_broker(), 80.0, 20.0, 5.0, None, radius_units="arcsec"
    )

    # ZTF_alerts (survey) is excluded; only the reference catalog is searched
    assert set(result.keys()) == {"Gaia_DR3"}
    source = result["Gaia_DR3"][0]
    assert source["_id"] == "42"  # coerced to str
    assert source["ra"] == 80.0  # GeoJSON longitude (-100) shifted +180
    assert source["dec"] == 20.0
    # BOOM's cone_search was sent the mapped unit label
    cone_call = next(
        c for c in responses.calls if c.request.url.endswith("cone_search")
    )
    assert json.loads(cone_call.request.body)["unit"] == "Arcseconds"


def test_broker_cone_search_unsupported(super_admin_token):
    """A broker whose provider does not implement cone_search is rejected."""
    status, data = api(
        "POST", "brokers", data=_broker_payload(), token=super_admin_token
    )
    assert status == 200
    broker_id = data["data"]["id"]

    status, data = api(
        "GET",
        f"brokers/{broker_id}/cone_search",
        params={"ra": 10.0, "dec": 20.0, "radius": 5.0},
        token=super_admin_token,
    )
    assert status == 400
    assert "does not support cone_search" in data["message"]


def test_broker_cone_search_missing_params(super_admin_token):
    status, data = api(
        "POST", "brokers", data=_broker_payload(), token=super_admin_token
    )
    assert status == 200
    broker_id = data["data"]["id"]

    status, data = api(
        "GET", f"brokers/{broker_id}/cone_search", token=super_admin_token
    )
    assert status == 400
    assert "Missing required parameters" in data["message"]


def test_boom_filter_activation_requires_validation(
    super_admin_token, upload_data_token, public_filter
):
    """A BOOM-managed filter cannot be activated by a non-admin until a passing
    validation is recorded (the slow check is now an explicit, separate step)."""
    import sqlalchemy as sa
    from sqlalchemy.orm.attributes import flag_modified

    from skyportal.models import DBSession, Filter

    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(
            broker_classname="BOOMBROKER",
            altdata={"host": "boom.test", "username": "x", "password": "y"},
        ),
        token=super_admin_token,
    )
    assert status == 200
    broker_id = data["data"]["id"]
    try:
        # Mark the filter broker-managed with no validation on record.
        f = (
            DBSession()
            .scalars(sa.select(Filter).where(Filter.id == public_filter.id))
            .first()
        )
        f.altdata = {"boom": {"filter_id": "boom-test-id"}}
        flag_modified(f, "altdata")
        DBSession().commit()

        status, data = api(
            "PATCH",
            f"brokers/{broker_id}/filters/{public_filter.id}",
            data={"active": True, "active_fid": "v1"},
            token=upload_data_token,
        )
        assert status == 400
        assert "validat" in data["message"].lower()

        # An admin bypasses the gate: it gets past validation and only then fails
        # at the unreachable test BOOM, so the error is not the validation one.
        status, data = api(
            "PATCH",
            f"brokers/{broker_id}/filters/{public_filter.id}",
            data={"active": True, "active_fid": "v1"},
            token=super_admin_token,
        )
        assert "validat" not in (data.get("message") or "").lower()
    finally:
        api("DELETE", f"brokers/{broker_id}", token=super_admin_token)
