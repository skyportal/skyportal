"""Requests the ATCA API sends to the rapid response service, and how it reads the replies."""

import asyncio
import base64
import json
import types
from datetime import datetime

import pytest
from aiohttp import web

from skyportal.facility_apis import atca
from skyportal.facility_apis.atca import (
    ATCAAPI,
    build_form_data,
    build_request_dict,
    scheduled_id,
    submission_status,
    validate_request,
)

ALTDATA = {"auth_token": "jwt", "email": "pi@example.org", "project": "C3456"}


def _payload(**overrides):
    payload = {
        "bands": ["4cm", "15mm"],
        "exposure_time": 30,
        "maximum_duration": 12,
        "minimum_duration": 3,
    }
    payload.update(overrides)
    return payload


def _request(payload, obj_id="ZTF24abcdefg", ra=15.17958, dec=-72.19272):
    obj = types.SimpleNamespace(id=obj_id, ra=ra, dec=dec)
    allocation = types.SimpleNamespace(altdata=ALTDATA)
    return types.SimpleNamespace(id=1, obj=obj, allocation=allocation, payload=payload)


def _transaction(content, created_at):
    return types.SimpleNamespace(
        response={
            "content": json.dumps(content) if isinstance(content, dict) else content
        },
        created_at=created_at,
    )


def test_request_dict_matches_the_service_format():
    request_dict = build_request_dict(_request(_payload()))
    assert request_dict == {
        "source": "F24abcdefg",
        "rightAscension": "01:00:43.10",
        "declination": "-72:11:33.8",
        "project": "C3456",
        "maxExposureLength": "12:00:00",
        "minExposureLength": "03:00:00",
        "4cm": {
            "use": True,
            "exposureLength": "00:30:00",
            "freq1": 5500,
            "freq2": 9000,
        },
        "15mm": {
            "use": True,
            "exposureLength": "00:30:00",
            "freq1": 17000,
            "freq2": 19000,
        },
    }


def test_chosen_frequencies_and_source_name_override_the_defaults():
    request_dict = build_request_dict(
        _request(
            _payload(
                bands=["7mm"],
                freq1_7mm=43000,
                freq2_7mm=45000,
                source_name="GRB241119",
                maximum_duration=1.5,
            )
        )
    )
    assert request_dict["source"] == "GRB241119"
    assert request_dict["maxExposureLength"] == "01:30:00"
    assert request_dict["7mm"]["freq1"] == 43000
    assert request_dict["7mm"]["freq2"] == 45000
    assert "4cm" not in request_dict


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"bands": ["3mm"]}, "Band 3mm unknown"),
        ({"bands": []}, "At least one band"),
        ({"bands": ["4cm"], "freq1_4cm": 2100}, "freq1 for 4cm"),
        ({"minimum_duration": 13}, "cannot exceed"),
        ({"exposure_time": 0}, "exposure_time must be positive"),
        ({"source_name": "ZTF24abcdefg"}, "at most 10"),
    ],
)
def test_invalid_requests_are_refused(overrides, message):
    request = _request(_payload(**overrides))
    with pytest.raises(ValueError, match=message):
        validate_request(request)
        build_request_dict(request)


def test_live_requests_carry_no_test_fields():
    data = build_form_data(ALTDATA, {"source": "x"}, maximum_lag=24)
    assert data == {
        "authToken": "jwt",
        "email": "pi@example.org",
        "request": '{"source": "x"}',
        "maximumLag": "24",
    }


def test_test_mode_fields_are_spelled_as_python_booleans():
    altdata = {
        **ALTDATA,
        "test": True,
        "no_score_limit": True,
        "email_only": "me@example.org",
    }
    data = build_form_data(altdata, {})
    assert data["test"] == "True"
    assert data["noScoreLimit"] == "True"
    assert data["noTimeLimit"] == "False"
    assert data["emailOnly"] == "me@example.org"
    assert "noEmail" not in data


@pytest.mark.parametrize(
    "response, status",
    [
        (
            {
                "authenticationToken": {"received": True, "verified": True},
                "success": True,
                "testMode": False,
                "observations": {
                    "startDate": "2026-11-19 04:56:50",
                    "endDate": "2026-11-19 16:56:50",
                },
            },
            "submitted: scheduled 2026-11-19 04:56:50 to 2026-11-19 16:56:50 UT",
        ),
        (
            {
                "authenticationToken": {"verified": True},
                "success": True,
                "testMode": True,
            },
            "submitted (test mode)",
        ),
        (
            {"error": "Source is never above the horizon."},
            "rejected: Source is never above the horizon.",
        ),
        (
            {
                "authenticationToken": {"received": True, "verified": False},
                "success": False,
            },
            "rejected: ATCA did not verify the authentication token",
        ),
        (
            {"authenticationToken": {"verified": True}, "success": False},
            "rejected: ATCA could not schedule the request",
        ),
        (
            None,
            "rejected: no JSON reply from ATCA (HTTP 401), check the HTTP credentials",
        ),
    ],
)
def test_replies_map_to_request_status(response, status):
    assert submission_status(response, 401) == status


def test_cancellation_targets_the_latest_accepted_request():
    transactions = [
        _transaction({"success": True, "id": "older"}, datetime(2026, 11, 1)),
        _transaction({"success": True, "id": "newer"}, datetime(2026, 11, 2)),
        _transaction({"success": False, "error": "no slot"}, datetime(2026, 11, 3)),
        _transaction("<html>401</html>", datetime(2026, 11, 4)),
    ]
    assert scheduled_id(transactions) == "newer"
    assert scheduled_id(transactions[2:]) is None


def test_altdata_requires_the_token_email_and_project():
    with pytest.raises(ValueError, match="project is required"):
        ATCAAPI.validate_altdata({"auth_token": "jwt", "email": "pi@example.org"})
    with pytest.raises(ValueError, match="together"):
        ATCAAPI.validate_altdata({**ALTDATA, "http_username": "user"})
    assert ATCAAPI.validate_altdata(ALTDATA) == ALTDATA


def test_post_sends_basic_auth_and_never_records_the_token(monkeypatch):
    received = {}

    async def handler(request):
        received["form"] = dict(await request.post())
        received["authorization"] = request.headers.get("Authorization")
        return web.json_response({"success": True, "id": "abc"})

    async def run():
        app = web.Application()
        app.router.add_post("/rapid", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        monkeypatch.setattr(
            atca, "cfg", {"app.atca_endpoint": f"http://127.0.0.1:{port}/rapid"}
        )
        try:
            altdata = {**ALTDATA, "http_username": "user", "http_password": "secret"}
            return await atca.post_to_atca(
                altdata, build_form_data(altdata, {"cancel": "abc"})
            )
        finally:
            await runner.cleanup()

    response, status, transaction = asyncio.run(run())

    assert status == 200
    assert response == {"success": True, "id": "abc"}
    assert received["form"]["authToken"] == "jwt"
    assert (
        received["authorization"]
        == "Basic " + base64.b64encode(b"user:secret").decode()
    )
    assert "jwt" not in transaction["request"]["body"]
    assert json.loads(transaction["request"]["body"])["authToken"] == "REDACTED"
