import json
import uuid
from types import SimpleNamespace
from urllib.parse import parse_qs

import pytest
import responses

from skyportal.broker_apis import GENERICBROKER, BrokerAPI
from skyportal.tests import api


def _force_active(broker_id):
    """Activate a credential-gated broker without the live connection check the
    API runs (no broker to reach from the tests)."""
    import sqlalchemy as sa

    from skyportal.models import Broker, DBSession

    DBSession().execute(
        sa.update(Broker).where(Broker.id == broker_id).values(active=True)
    )
    DBSession().commit()


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


def test_activation_checks_credentials(super_admin_token):
    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(
            broker_classname="BOOMBROKER",
            altdata={"host": "boom.test"},
            active=True,
        ),
        token=super_admin_token,
    )
    assert status == 200, data
    boom_id = data["data"]["id"]

    status, data = api(
        "POST", "brokers", data=_broker_payload(active=False), token=super_admin_token
    )
    assert status == 200, data
    generic_id = data["data"]["id"]

    try:
        status, data = api("GET", f"brokers/{boom_id}", token=super_admin_token)
        assert data["data"]["active"] is False

        status, data = api(
            "PATCH",
            f"brokers/{boom_id}",
            data={"active": True},
            token=super_admin_token,
        )
        assert status == 400, data
        # the handler names the refused action and the underlying reason
        assert "cannot be activated" in data["message"]
        assert "username" in data["message"] and "password" in data["message"]

        status, data = api("GET", f"brokers/{boom_id}", token=super_admin_token)
        assert data["data"]["active"] is False

        status, data = api(
            "PATCH",
            f"brokers/{generic_id}",
            data={"active": True},
            token=super_admin_token,
        )
        assert status == 200, data
        status, data = api("GET", f"brokers/{generic_id}", token=super_admin_token)
        assert data["data"]["active"] is True
    finally:
        api("DELETE", f"brokers/{boom_id}", token=super_admin_token)
        api("DELETE", f"brokers/{generic_id}", token=super_admin_token)


def test_default_requires_the_capability(super_admin_token):
    status, data = api(
        "POST", "brokers", data=_broker_payload(), token=super_admin_token
    )
    assert status == 200, data
    generic_id = data["data"]["id"]

    try:
        status, data = api(
            "PATCH",
            f"brokers/{generic_id}",
            data={"default_crossmatch": True},
            token=super_admin_token,
        )
        assert status == 400, data
        assert "cross_match_catalogs" in data["message"]

        status, data = api("GET", f"brokers/{generic_id}", token=super_admin_token)
        assert data["data"]["default_crossmatch"] is False

        status, data = api(
            "PATCH",
            f"brokers/{generic_id}",
            data={"default_alert_search": True, "default_photometry": True},
            token=super_admin_token,
        )
        assert status == 200, data
    finally:
        api("DELETE", f"brokers/{generic_id}", token=super_admin_token)


def test_broker_defaults_are_exclusive(super_admin_token):
    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(
            broker_classname="BOOMBROKER",
            altdata={"host": "boom.test"},
            default_alert_search=True,
            default_crossmatch=True,
            default_photometry=True,
        ),
        token=super_admin_token,
    )
    assert status == 200, data
    first_id = data["data"]["id"]

    status, data = api(
        "POST", "brokers", data=_broker_payload(), token=super_admin_token
    )
    assert status == 200, data
    second_id = data["data"]["id"]

    try:
        status, data = api("GET", f"brokers/{first_id}", token=super_admin_token)
        assert data["data"]["default_alert_search"] is True
        assert data["data"]["default_crossmatch"] is True
        assert data["data"]["default_photometry"] is True

        status, data = api(
            "PATCH",
            f"brokers/{second_id}",
            data={"default_alert_search": True, "default_photometry": True},
            token=super_admin_token,
        )
        assert status == 200, data

        status, data = api("GET", f"brokers/{second_id}", token=super_admin_token)
        assert data["data"]["default_alert_search"] is True
        assert data["data"]["default_crossmatch"] is False
        assert data["data"]["default_photometry"] is True

        status, data = api("GET", f"brokers/{first_id}", token=super_admin_token)
        assert data["data"]["default_alert_search"] is False
        assert data["data"]["default_crossmatch"] is True
        assert data["data"]["default_photometry"] is False
    finally:
        api("DELETE", f"brokers/{first_id}", token=super_admin_token)
        api("DELETE", f"brokers/{second_id}", token=super_admin_token)


def _post_photometry(token, obj_id, instrument_id, group_ids, mjd):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(obj_id),
            "mjd": mjd,
            "instrument_id": instrument_id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": group_ids,
        },
        token=token,
    )
    assert status == 200, data


def test_default_photometry_broker_serves_object_photometry(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    """The broker-address-free passthrough the source page calls serves the
    object's DB photometry when no broker is the photometry default, and still
    serves it when the default one cannot be reached."""
    _post_photometry(
        upload_data_token, public_source.id, ztf_camera.id, [public_group.id], 58000.0
    )

    status, data = api(
        "GET", f"brokers/photometry/{public_source.id}", token=upload_data_token
    )
    assert status == 200, data
    assert any(point["mjd"] == 58000.0 for point in data["data"])

    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(default_photometry=True),
        token=super_admin_token,
    )
    assert status == 200, data
    broker_id = data["data"]["id"]

    try:
        status, data = api(
            "GET", f"brokers/photometry/{public_source.id}", token=upload_data_token
        )
        assert status == 200, data
        assert any(point["mjd"] == 58000.0 for point in data["data"])
    finally:
        api("DELETE", f"brokers/{broker_id}", token=super_admin_token)


def test_default_photometry_broker_serves_super_obj_photometry(
    super_admin_token,
    upload_data_token,
    public_source,
    public_source_group2,
    public_group,
    public_group2,
    ztf_camera,
):
    """With includeSuperObjsPhotometry the passthrough serves every obj of the
    SuperObj, matching GET /sources/{id}/photometry."""
    _post_photometry(
        upload_data_token, public_source.id, ztf_camera.id, [public_group.id], 58000.0
    )
    _post_photometry(
        super_admin_token,
        public_source_group2.id,
        ztf_camera.id,
        [public_group2.id],
        58001.0,
    )

    status, data = api(
        "POST",
        "super_objs",
        data={"obj_ids": [str(public_source.id), str(public_source_group2.id)]},
        token=super_admin_token,
    )
    assert status == 200, data
    super_obj_id = data["data"]["id"]

    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(default_photometry=True),
        token=super_admin_token,
    )
    assert status == 200, data
    broker_id = data["data"]["id"]

    try:
        status, data = api(
            "GET", f"brokers/photometry/{public_source.id}", token=super_admin_token
        )
        assert status == 200, data
        assert {point["obj_id"] for point in data["data"]} == {str(public_source.id)}

        status, data = api(
            "GET",
            f"brokers/photometry/{public_source.id}?includeSuperObjsPhotometry=true",
            token=super_admin_token,
        )
        assert status == 200, data
        assert {point["obj_id"] for point in data["data"]} == {
            str(public_source.id),
            str(public_source_group2.id),
        }

        status, data = api(
            "GET",
            f"brokers/photometry/{public_source.id}?includeSuperObjsPhotometry=true",
            token=upload_data_token,
        )
        assert status == 200, data
        assert {point["obj_id"] for point in data["data"]} == {str(public_source.id)}
    finally:
        api("DELETE", f"brokers/{broker_id}", token=super_admin_token)
        api("DELETE", f"super_objs/{super_obj_id}", token=super_admin_token)


def test_photometry_passthrough_refuses_an_unknown_obj(view_only_token):
    """``Obj.read`` is public, so the guard is an existence check: the passthrough
    refuses an id with no obj exactly like GET /sources/{id}/photometry does. The
    access control that matters is on the points themselves, and is covered by
    test_default_photometry_broker_serves_super_obj_photometry."""
    status, data = api("GET", "brokers/photometry/NOSUCHOBJ", token=view_only_token)
    assert status == 403, data


def test_photometry_passthrough_keeps_the_source_page_contract(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    """The passthrough serves the same fields as GET /sources/{id}/photometry, so
    routing the source page through it does not silently drop owner, groups,
    created_at or the extinction-corrected values."""
    _post_photometry(
        upload_data_token, public_source.id, ztf_camera.id, [public_group.id], 58002.0
    )

    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(default_photometry=True),
        token=super_admin_token,
    )
    assert status == 200, data
    broker_id = data["data"]["id"]

    try:
        params = (
            "includeOwnerInfo=true&includeStreamInfo=true&"
            "includeValidationInfo=true&includeExtinction=true"
        )
        status, data = api(
            "GET",
            f"brokers/photometry/{public_source.id}?{params}",
            token=upload_data_token,
        )
        assert status == 200, data
        point = next(p for p in data["data"] if p["mjd"] == 58002.0)
        assert point["owner"]["id"] is not None
        assert public_group.id in [group["id"] for group in point["groups"]]
        assert point["created_at"] is not None
        assert point["streams"] == []
        assert point["extinction"] is not None
        assert point["mag_corr"] is not None
    finally:
        api("DELETE", f"brokers/{broker_id}", token=super_admin_token)


def test_photometry_passthrough_serves_photometric_series(
    super_admin_token, public_source, public_photometric_series
):
    """The source page reads its lightcurve from the passthrough for every
    deployment, so it must serve the photometric series and the mjd order
    GET /sources/{id}/photometry does."""
    status, data = api(
        "GET", f"brokers/photometry/{public_source.id}", token=super_admin_token
    )
    assert status == 200, data
    assert [
        point
        for point in data["data"]
        if point["origin"] == public_photometric_series.origin
    ]
    assert data["data"] == sorted(data["data"], key=lambda point: point["mjd"])


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

    # admins get the config, minus the credentials (GENERICBROKER renders
    # `token` as a password field)
    status, data = api("GET", f"brokers/{broker_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["altdata"]["base_url"] == "https://broker.test"
    assert "token" not in data["data"]["altdata"]

    # so editing another field must not wipe the stored credential
    status, _ = api(
        "PATCH",
        f"brokers/{broker_id}",
        data={"altdata": {"base_url": "https://broker2.test"}},
        token=super_admin_token,
    )
    assert status == 200
    status, data = api("GET", f"brokers/{broker_id}", token=super_admin_token)
    assert data["data"]["altdata"]["base_url"] == "https://broker2.test"


def test_altdata_merge_and_redaction():
    from skyportal.handlers.api.broker import merge_altdata, strip_secrets

    stored = {
        "base_url": "https://a",
        "token": "secret",
        "scimma": {"password": "p", "user": "u"},
    }

    assert strip_secrets(stored, ["token", "scimma.password"]) == {
        "base_url": "https://a",
        "scimma": {"user": "u"},
    }
    assert stored["token"] == "secret"

    # blank means "keep what is stored", at any depth
    merged = merge_altdata(
        stored, {"base_url": "https://b", "token": "", "scimma": {"password": "  "}}
    )
    assert merged["base_url"] == "https://b"
    assert merged["token"] == "secret"
    assert merged["scimma"]["password"] == "p"

    assert merge_altdata(stored, {"token": "new"})["token"] == "new"


def test_secret_config_fields_cover_every_provider():
    from skyportal import broker_apis

    expected = {
        "ALERCEBROKER": [],
        "AMPELBROKER": ["scimma.password"],
        "ANTARESBROKER": [],
        "BABAMULBROKER": ["token"],
        "BOOMBROKER": ["password"],
        "FINKBROKER": ["fink.password"],
        "GENERICBROKER": ["token"],
        "LASAIRBROKER": ["token", "kafka.password"],
        "PITTGOOGLEBROKER": ["service_account_key"],
    }
    for name, paths in expected.items():
        provider = getattr(broker_apis, name)
        assert sorted(provider.secret_config_fields()) == sorted(paths), name


def test_lasair_credential_sets():
    """One consumer per Lasair account: shared config, separate identity."""
    from types import SimpleNamespace

    from skyportal.broker_apis.lasair import _credential_sets

    broker = SimpleNamespace(
        id=7,
        altdata={
            "token": "shared-token",
            "filter_ids": [1],
            "kafka": {
                "host": "lasair-lsst-kafka_pub.lsst.ac.uk",
                "port": 9092,
                "username": "shared",
                "password": "shared-pw",
                "topics": ["lasair_2SNe"],
            },
        },
    )

    only_shared = _credential_sets(broker)
    assert [c["label"] for c in only_shared] == ["shared"]
    assert only_shared[0]["token"] == "shared-token"

    sets = _credential_sets(
        broker,
        [
            {
                "label": "camille",
                "token": "her-token",
                "topics": ["lasair_9private"],
                "filter_ids": [2],
                "kafka": {"username": "camille", "password": "her-pw"},
            }
        ],
    )
    assert [c["label"] for c in sets] == ["shared", "camille"]
    personal = sets[1]
    assert personal["kafka"]["host"] == "lasair-lsst-kafka_pub.lsst.ac.uk"
    assert personal["kafka"]["username"] == "camille"
    assert personal["kafka"]["password"] == "her-pw"
    assert personal["token"] == "her-token"
    assert personal["topics"] == ["lasair_9private"]
    assert personal["filter_ids"] == [2]
    assert sets[0]["topics"] == ["lasair_2SNe"]
    assert sets[0]["token"] == "shared-token"


def test_lasair_credential_sets_without_topics():
    """No topics anywhere means nothing to consume, not a consumer on nothing."""
    from types import SimpleNamespace

    from skyportal.broker_apis.lasair import _credential_sets

    broker = SimpleNamespace(id=7, altdata={"token": "t", "kafka": {"host": "h"}})
    assert _credential_sets(broker) == []


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
    # falsy rather than False: the semantics flags are not all booleans
    # (filter_pipeline names a dialect, and the base speaks none).
    assert all(not v for v in caps.values())
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
    LASAIRBROKER.validate_config({"endpoint": "https://lasair.test/api"})


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
    with pytest.raises(ValueError):
        BOOMBROKER.validate_config({})
    BOOMBROKER.validate_config({"host": "boom.test"})


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


# --- custom filter modules (the altdata-backed default store, via Lasair) ---


@pytest.fixture
def lasair_broker_id(super_admin_token):
    status, data = api(
        "POST",
        "brokers",
        data=_broker_payload(
            broker_classname="LASAIRBROKER",
            altdata={"token": "t", "endpoint": "https://x/api"},
        ),
        token=super_admin_token,
    )
    assert status == 200, data
    broker_id = data["data"]["id"]
    _force_active(broker_id)
    yield broker_id
    api("DELETE", f"brokers/{broker_id}", token=super_admin_token)


def test_filter_module_round_trip_normalizes_streams(
    lasair_broker_id, super_admin_token
):
    """A module saved with a full stream name is stored under the bare survey
    token -- the builder filters saved modules on the token, so anything else is
    invisible in the builder that wrote it."""
    status, data = api(
        "POST",
        f"brokers/{lasair_broker_id}/filter_modules/myvar",
        data={"elements": "variables", "data": {"streams": ["ZTF (1, 2)"], "x": 1}},
        token=super_admin_token,
    )
    assert status == 200, data

    status, data = api(
        "GET",
        f"brokers/{lasair_broker_id}/filter_modules",
        params={"elements": "variables"},
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["variables"] == [
        {"name": "myvar", "streams": ["ZTF"], "x": 1},
    ]


def test_filter_module_lookup_by_name(lasair_broker_id, super_admin_token):
    """The by-name read backs the builder's name-availability check: a real doc
    for a hit, null for a miss (never an empty list, which reads as a hit)."""
    status, _ = api(
        "POST",
        f"brokers/{lasair_broker_id}/filter_modules/known",
        data={"elements": "blocks", "data": {"streams": ["ZTF Alerts"]}},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"brokers/{lasair_broker_id}/filter_modules/known",
        params={"elements": "blocks"},
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["blocks"]["name"] == "known"
    assert data["data"]["blocks"]["streams"] == ["ZTF"]

    status, data = api(
        "GET",
        f"brokers/{lasair_broker_id}/filter_modules/nope",
        params={"elements": "blocks"},
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["blocks"] is None


def test_filter_module_update(lasair_broker_id, super_admin_token):
    status, _ = api(
        "POST",
        f"brokers/{lasair_broker_id}/filter_modules/v",
        data={"elements": "variables", "data": {"streams": ["ZTF"], "x": 1}},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "PUT",
        f"brokers/{lasair_broker_id}/filter_modules/v",
        data={"elements": "variables", "data": {"x": 2}},
        token=super_admin_token,
    )
    assert status == 200, data

    status, data = api(
        "GET",
        f"brokers/{lasair_broker_id}/filter_modules/v",
        params={"elements": "variables"},
        token=super_admin_token,
    )
    assert data["data"]["variables"]["x"] == 2

    # updating a module that does not exist is an error, not an insert
    status, data = api(
        "PUT",
        f"brokers/{lasair_broker_id}/filter_modules/ghost",
        data={"elements": "variables", "data": {"x": 1}},
        token=super_admin_token,
    )
    assert status == 400
    assert "No variables named 'ghost'" in data["message"]


def test_filter_module_invalid_elements(lasair_broker_id, super_admin_token):
    """'elements' is validated on read too -- it used to reach the store as an
    arbitrary collection name."""
    status, data = api(
        "GET",
        f"brokers/{lasair_broker_id}/filter_modules",
        params={"elements": "; drop"},
        token=super_admin_token,
    )
    assert status == 400
    assert "elements: Input should be 'schema'" in data["message"]

    status, data = api(
        "POST",
        f"brokers/{lasair_broker_id}/filter_modules/x",
        data={"elements": "bogus", "data": {}},
        token=super_admin_token,
    )
    assert status == 400


def test_normalize_module_streams():
    """Full stream names collapse to the survey token, deduped; payloads without
    a streams list pass through untouched."""
    from skyportal.broker_apis.interface import normalize_module_streams

    assert normalize_module_streams({"streams": ["ZTF (1, 2)", "ZTF Alerts"]}) == {
        "streams": ["ZTF"]
    }
    assert normalize_module_streams({"x": 1}) == {"x": 1}


def test_boom_ingestion_survey_is_uppercased():
    """BOOM emits title-case survey names ("Ztf"), but instruments, zeropoints and
    streams are all keyed on the uppercase form, so a verbatim name drops every
    alert (`Instrument 'Ztf' not found`)."""
    from skyportal.broker_apis.boom import _record_survey

    assert _record_survey({"survey": "Ztf"}) == "ZTF"
    assert _record_survey({"survey": "Lsst"}) == "LSST"
    assert _record_survey({"survey": "ZTF"}) == "ZTF"
    # BOOM leaving the field unset (or null) is why this went unnoticed for so
    # long: DEFAULT_SURVEY is already correctly cased.
    assert _record_survey({"survey": None}) == "ZTF"
    assert _record_survey({}) == "ZTF"


# --- BOOM's own module store (Mongo), against a recording fake ---


class _FakeCollection:
    """Just enough of a pymongo collection to record how the provider calls it."""

    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.updates = []

    def find_one(self, query, projection=None):
        self.last_projection = projection
        return next((d for d in self.docs if d["name"] == query["name"]), None)

    def find(self, query, projection=None):
        self.last_projection = projection
        return iter(self.docs)

    def update_one(self, query, update, upsert=False):
        self.updates.append((query, update, upsert))


class _FakeDB(dict):
    def __missing__(self, key):
        self[key] = _FakeCollection()
        return self[key]


def _boom_with_store(monkeypatch, docs=None):
    from skyportal.broker_apis import boom

    db = _FakeDB()
    db["blocks"] = _FakeCollection(docs)
    monkeypatch.setattr(boom, "_modules_db", lambda broker: db)
    return db


def test_boom_filter_modules_read(monkeypatch):
    from skyportal.broker_apis import BOOMBROKER

    db = _boom_with_store(monkeypatch, [{"name": "b1", "streams": ["ZTF"]}])

    assert BOOMBROKER.filter_modules(None, None, elements="blocks") == {
        "blocks": [{"name": "b1", "streams": ["ZTF"]}]
    }
    # raw ObjectIds are not JSON-serializable, so they must be projected away
    assert db["blocks"].last_projection == {"_id": 0}

    # by name: the doc on a hit, None on a miss (an empty list would read as a hit)
    assert (
        BOOMBROKER.filter_modules(None, None, elements="blocks", name="b1")["blocks"][
            "name"
        ]
        == "b1"
    )
    assert BOOMBROKER.filter_modules(None, None, elements="blocks", name="x") == {
        "blocks": None
    }


def test_boom_filter_modules_unconfigured_store(monkeypatch):
    """With no store configured, reads degrade to empty rather than raising."""
    from skyportal.broker_apis import BOOMBROKER, boom

    monkeypatch.setattr(boom, "_modules_db", lambda broker: None)
    assert BOOMBROKER.filter_modules(None, None, elements="blocks") == {"blocks": []}
    assert BOOMBROKER.filter_modules(None, None, elements="blocks", name="b") == {
        "blocks": None
    }


def test_boom_write_filter_module(monkeypatch):
    from skyportal.broker_apis import BOOMBROKER

    db = _boom_with_store(monkeypatch, [{"name": "b1", "streams": ["ZTF"]}])

    BOOMBROKER.write_filter_module(
        None, None, "b2", "blocks", {"streams": ["ZTF Alerts"]}, insert=True
    )
    query, update, upsert = db["blocks"].updates[-1]
    assert (query, upsert) == ({"name": "b2"}, True)
    assert update["$set"]["streams"] == ["ZTF"]  # normalized to the survey token
    assert "created_at" in update["$setOnInsert"]
    assert "updated_at" in update["$set"]

    # update of an existing module touches updated_at only
    BOOMBROKER.write_filter_module(None, None, "b1", "blocks", {"x": 1}, insert=False)
    query, update, upsert = db["blocks"].updates[-1]
    assert (query, upsert) == ({"name": "b1"}, False)
    assert update["$set"]["x"] == 1
    assert "$setOnInsert" not in update

    with pytest.raises(ValueError, match="No blocks named 'ghost'"):
        BOOMBROKER.write_filter_module(None, None, "ghost", "blocks", {}, insert=False)


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
    assert "Invalid/missing parameters: ra: Field required" in data["message"]


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
    _force_active(broker_id)
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


def test_broker_credentials_crud(
    super_admin_token,
    view_only_token,
    view_only_token_group2,
    public_filter,
    public_filter2,
):
    payload = _broker_payload()
    status, data = api("POST", "brokers", data=payload, token=super_admin_token)
    assert status == 200
    broker_id = data["data"]["id"]
    try:
        status, data = api(
            "GET", f"brokers/{broker_id}/credentials", token=view_only_token
        )
        assert status == 200
        assert data["data"] is None

        status, data = api(
            "PUT",
            f"brokers/{broker_id}/credentials",
            data={"credentials": {"token": "mine"}, "topics": ["lasair_1x"]},
            token=view_only_token,
        )
        assert status == 200, data

        status, data = api(
            "GET", f"brokers/{broker_id}/credentials", token=view_only_token
        )
        assert status == 200
        assert data["data"]["topics"] == ["lasair_1x"]

        status, data = api(
            "PUT",
            f"brokers/{broker_id}/credentials",
            data={"topic_filter_ids": {"lasair_1x": [public_filter2.id]}},
            token=view_only_token,
        )
        assert status == 400
        assert "not accessible" in data["message"]

        status, data = api(
            "PUT",
            f"brokers/{broker_id}/credentials",
            data={"topic_filter_ids": {"lasair_1x": [public_filter.id]}},
            token=view_only_token,
        )
        assert status == 200, data

        status, data = api(
            "GET", f"brokers/{broker_id}/credentials", token=view_only_token_group2
        )
        assert status == 200
        assert data["data"] is None

        status, data = api(
            "DELETE", f"brokers/{broker_id}/credentials", token=view_only_token
        )
        assert status == 200
        status, data = api(
            "GET", f"brokers/{broker_id}/credentials", token=view_only_token
        )
        assert data["data"] is None
    finally:
        api("DELETE", f"brokers/{broker_id}", token=super_admin_token)
