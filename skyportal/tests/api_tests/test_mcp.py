import asyncio
import base64
import json
import uuid

from skyportal.handlers.mcp import TOOLS, _analyze_band, _versions
from skyportal.tests import cfg, session

VERSION = "2026-07-28"
META = "io.modelcontextprotocol/"
URL = f"http://localhost:{cfg['ports.app']}/mcp"


def mcp(
    method,
    params=None,
    token=None,
    id=1,
    scheme="Bearer",
    headers=None,
    body=None,
    meta=True,
    version=VERSION,
):
    """Post one 2026-07-28 JSON-RPC message to /mcp; returns (status, body or None).

    `headers` overrides the standard transport headers (None removes one).
    """
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if body is None:
        params = dict(params or {})
        if meta:
            params["_meta"] = {
                f"{META}protocolVersion": version,
                f"{META}clientCapabilities": {},
                f"{META}clientInfo": {"name": "pytest", "version": "0"},
            }
        body = {"jsonrpc": "2.0", "method": method, "params": params}
        if id is not None:
            body["id"] = id
        h["Mcp-Method"] = method
        h["MCP-Protocol-Version"] = version
        if method == "tools/call" and "name" in params:
            h["Mcp-Name"] = params["name"]
    if token:
        h["Authorization"] = f"{scheme} {token}"
    for name, value in (headers or {}).items():
        if value is None:
            h.pop(name, None)
        else:
            h[name] = value
    response = session.post(URL, json=body, headers=h)
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, None


def call_tool(name, arguments, token, **kwargs):
    status, data = mcp(
        "tools/call", {"name": name, "arguments": arguments}, token, **kwargs
    )
    assert status == 200, data
    assert "error" not in data, data
    result = data["result"]
    assert result["resultType"] == "complete"
    return result["isError"], result["content"][0]["text"], result


# ─── Auth ───────────────────────────────────────────────────────────────────


def test_mcp_requires_auth():
    status, _ = mcp("server/discover")
    assert status == 401


def test_mcp_rejects_bad_token():
    status, _ = mcp("server/discover", token="not-a-token")
    assert status == 401


# ─── Discovery and listing ──────────────────────────────────────────────────


def test_mcp_discover(view_only_token):
    for scheme in ("Bearer", "token"):
        status, data = mcp("server/discover", token=view_only_token, scheme=scheme)
        assert status == 200
        assert data["id"] == 1
        result = data["result"]
        assert result["resultType"] == "complete"
        assert result["supportedVersions"] == [VERSION]
        assert "tools" in result["capabilities"]
        assert result["_meta"][f"{META}serverInfo"]["name"] == "SkyPortal"
        assert result["ttlMs"] >= 0
        assert result["cacheScope"] in ("public", "private")


def test_mcp_tools_list(view_only_token):
    status, data = mcp("tools/list", token=view_only_token)
    assert status == 200
    result = data["result"]
    assert result["resultType"] == "complete"
    assert result["ttlMs"] >= 0
    assert result["cacheScope"] == "public"
    names = [t["name"] for t in result["tools"]]
    assert set(names) == {
        "get_sources",
        "post_source",
        "get_photometry",
        "post_photometry",
        "get_spectra",
        "post_spectrum",
        "analyze_light_curve",
        "get_gcn_events",
        "get_gcn_event",
        "get_gcn_event_extractions",
        "get_gcn_event_comments",
        "post_gcn_event_comment",
        "get_broker_filter",
        "diff_broker_filter_versions",
        "run_broker_filter",
        "post_broker_filter_version",
        "activate_broker_filter_version",
        "post_filter",
    }
    tools = {t["name"]: t for t in result["tools"]}
    for t in tools.values():
        assert t["inputSchema"]["type"] == "object"
        assert t["description"]
    assert tools["post_photometry"]["inputSchema"]["required"] == [
        "obj_id",
        "instrument_id",
        "mjd",
        "filter",
        "magsys",
    ]
    # Deterministic ordering
    _, again = mcp("tools/list", token=view_only_token)
    assert [t["name"] for t in again["result"]["tools"]] == names


# ─── Transport rules ────────────────────────────────────────────────────────


def test_mcp_notification_is_accepted(view_only_token):
    status, data = mcp("notifications/cancelled", token=view_only_token, id=None)
    assert status == 202
    assert data is None


def test_mcp_get_and_delete_not_allowed(view_only_token):
    headers = {"Authorization": f"Bearer {view_only_token}"}
    assert session.get(URL, headers=headers).status_code == 405
    assert session.delete(URL, headers=headers).status_code == 405


def test_mcp_unknown_method(view_only_token):
    status, data = mcp("ping", token=view_only_token)
    assert status == 404
    assert data["error"]["code"] == -32601
    assert data["id"] == 1


LEGACY_VERSION = "2025-06-18"
# The deprecated profile: no Mcp-* headers, no per-request _meta.
LEGACY = {"Mcp-Method": None, "MCP-Protocol-Version": None, "Mcp-Name": None}


def legacy(method, params=None, token=None):
    return mcp(method, params, token=token, headers=LEGACY, meta=False)


def test_mcp_legacy_handshake_is_answered_without_a_session(view_only_token):
    """A pre-2026 client hands over its version and gets one back, and no
    session id, so its later requests stay independent of this process."""
    status, data = legacy(
        "initialize",
        {"protocolVersion": LEGACY_VERSION, "capabilities": {}},
        token=view_only_token,
    )
    assert status == 200, data
    result = data["result"]
    assert result["protocolVersion"] == LEGACY_VERSION
    assert "tools" in result["capabilities"]
    assert result["serverInfo"]["name"] == "SkyPortal"
    assert result["instructions"]
    # resultType is a 2026-07-28 addition and has no place in this response.
    assert "resultType" not in result


def test_mcp_legacy_unknown_version_negotiates_down(view_only_token):
    status, data = legacy(
        "initialize",
        {"protocolVersion": "2025-03-26", "capabilities": {}},
        token=view_only_token,
    )
    assert status == 200, data
    assert data["result"]["protocolVersion"] == LEGACY_VERSION


def test_mcp_legacy_tools_list_and_call(view_only_token, public_source):
    """The whole point: the same tools, reachable without the 2026 envelope."""
    status, data = legacy("tools/list", token=view_only_token)
    assert status == 200, data
    assert len(data["result"]["tools"]) == len(TOOLS)

    status, data = legacy(
        "tools/call",
        {"name": "get_sources", "arguments": {"sourceID": public_source.id}},
        token=view_only_token,
    )
    assert status == 200, data
    assert data["result"]["isError"] is False


def test_mcp_legacy_initialized_notification_accepted(view_only_token):
    status, data = mcp(
        "notifications/initialized",
        token=view_only_token,
        headers=LEGACY,
        meta=False,
        id=None,
    )
    assert status == 202
    assert data is None


def test_mcp_initialize_at_our_own_version_is_method_not_found(view_only_token):
    """A client that knows this revision but still handshakes needs to hear that
    the handshake is missing, not that its version is unsupported."""
    status, data = mcp(
        "initialize",
        {"protocolVersion": VERSION, "capabilities": {}},
        token=view_only_token,
        headers={"Mcp-Method": None, "MCP-Protocol-Version": None},
        meta=False,
    )
    assert status == 404
    assert data["error"]["code"] == -32601
    assert "initialize handshake" in data["error"]["message"]
    assert "_meta" in data["error"]["message"]


def test_mcp_unsupported_version(view_only_token):
    status, data = mcp("server/discover", token=view_only_token, version="2025-06-18")
    assert status == 400
    assert data["error"]["code"] == -32022
    assert data["error"]["data"] == {"supported": [VERSION], "requested": "2025-06-18"}


def test_mcp_header_validation(view_only_token):
    def expect_mismatch(**kwargs):
        status, data = mcp("server/discover", token=view_only_token, **kwargs)
        assert status == 400, data
        assert data["error"]["code"] == -32020, data
        assert data["id"] == 1

    expect_mismatch(headers={"Mcp-Method": None})
    expect_mismatch(headers={"Mcp-Method": "tools/list"})
    expect_mismatch(headers={"MCP-Protocol-Version": None})
    expect_mismatch(headers={"MCP-Protocol-Version": "2025-06-18"})

    call = {"name": "get_sources", "arguments": {"obj_id": "x"}}
    status, data = mcp(
        "tools/call", call, token=view_only_token, headers={"Mcp-Name": None}
    )
    assert status == 400 and data["error"]["code"] == -32020
    status, data = mcp(
        "tools/call", call, token=view_only_token, headers={"Mcp-Name": "other"}
    )
    assert status == 400 and data["error"]["code"] == -32020

    # Base64 sentinel encoding of Mcp-Name is decoded before comparison
    encoded = "=?base64?" + base64.b64encode(b"get_sources").decode() + "?="
    status, data = mcp(
        "tools/call", call, token=view_only_token, headers={"Mcp-Name": encoded}
    )
    assert status == 200 and "result" in data
    status, data = mcp(
        "tools/call", call, token=view_only_token, headers={"Mcp-Name": "=?base64?!?="}
    )
    assert status == 400 and data["error"]["code"] == -32020


def test_mcp_meta_required(view_only_token):
    status, data = mcp("server/discover", token=view_only_token, meta=False)
    assert status == 400
    assert data["error"]["code"] == -32602

    params = {"_meta": {f"{META}protocolVersion": VERSION}}
    status, data = mcp("server/discover", params, token=view_only_token, meta=False)
    assert status == 400
    assert data["error"]["code"] == -32602
    assert "clientCapabilities" in data["error"]["message"]


def test_mcp_origin_validation(view_only_token):
    status, data = mcp(
        "server/discover",
        token=view_only_token,
        headers={"Origin": f"http://localhost:{cfg['ports.app']}"},
    )
    assert status == 200 and "result" in data

    status, data = mcp(
        "server/discover",
        token=view_only_token,
        headers={"Origin": "http://evil.example.com"},
    )
    assert status == 403
    assert "error" in data and "id" not in data


def test_mcp_malformed_requests(view_only_token):
    status, data = mcp(None, token=view_only_token, body=[1, 2])
    assert status == 400 and data["error"]["code"] == -32600

    status, data = mcp(
        None,
        token=view_only_token,
        body={"jsonrpc": "2.0", "id": None, "method": "server/discover"},
    )
    assert status == 400 and data["error"]["code"] == -32600

    response = session.post(
        URL,
        data="{not json",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {view_only_token}",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32700


# ─── Tools ──────────────────────────────────────────────────────────────────


def test_mcp_unknown_tool_and_invalid_arguments(view_only_token):
    status, data = mcp(
        "tools/call", {"name": "nope", "arguments": {}}, token=view_only_token
    )
    assert status == 200 and data["error"]["code"] == -32602

    is_error, text, _ = call_tool("get_photometry", {}, view_only_token)
    assert is_error and "obj_id" in text

    is_error, text, _ = call_tool("get_sources", {"numPerPage": "ten"}, view_only_token)
    assert is_error and "numPerPage" in text


class FakeHandler:
    """Records REST calls made by a tool and returns canned data."""

    def __init__(self, data=None):
        self.data = data
        self.calls = []

    async def api(self, method, path, query=None, body=None):
        self.calls.append((method, path, query, body))
        return self.data


def run_tool(name, args, data=None):
    handler = FakeHandler(data)
    content = asyncio.run(TOOLS[name]["fn"](handler, dict(args)))
    return handler.calls, content


def test_mcp_tool_request_mapping():
    calls, content = run_tool(
        "get_sources", {"obj_id": "X", "includePhotometry": True}, data={"id": "X"}
    )
    assert calls == [("GET", "/api/sources/X", {"includePhotometry": True}, None)]
    assert content == {"id": "X"}
    calls, _ = run_tool("get_sources", {"ra": 1, "dec": 2, "radius": 0.1})
    assert calls[0][1] == "/api/sources"

    calls, _ = run_tool("get_photometry", {"obj_id": "X", "format": "flux"})
    assert calls == [("GET", "/api/sources/X/photometry", {"format": "flux"}, None)]
    calls, _ = run_tool("get_spectra", {"obj_id": "X"})
    assert calls[0][1] == "/api/sources/X/spectra"

    body = {"id": "X", "ra": 1, "dec": 2}
    calls, _ = run_tool("post_source", body)
    assert calls == [("POST", "/api/sources", None, body)]
    assert run_tool("post_photometry", {})[0][0][1] == "/api/photometry"
    assert run_tool("post_spectrum", {})[0][0][1] == "/api/spectrum"


def test_mcp_analyze_band():
    def pt(mjd, mag=None, limit=None):
        return {
            "mjd": mjd,
            "mag": mag,
            "magerr": 0.05 if mag else None,
            "limiting_mag": limit,
        }

    assert _analyze_band([pt(1, 19.0)], 0.3) is None
    assert _analyze_band([pt(1, limit=20.5), pt(2, limit=20.6)], 0.3) is None

    rising = _analyze_band([pt(10, 20.0), pt(12, 19.5), pt(14, 19.0)], 0.3)
    assert rising["status"] == "rising"
    assert rising["peak"] == {"mjd": 14, "mag": 19.0, "magerr": 0.05}
    assert rising["rise_time_days"] == 4 and rising["rise_mag"] == 1.0
    assert rising["rise_rate_mag_per_day"] == 0.25
    assert rising["fade_time_days"] is None and rising["duration_days"] is None

    # Non-detection two days before discovery, peak, then a fade below baseline
    complete = _analyze_band(
        [
            pt(8, limit=20.5),
            pt(10, 20.0),
            pt(12, 19.0),
            pt(13, 19.1),
            pt(16, 19.5),
        ],
        0.3,
    )
    assert complete["status"] == "complete"
    assert complete["n_detections"] == 4 and complete["n_upper_limits"] == 1
    assert complete["fade_time_days"] == 4 and complete["fade_mag"] == 0.5
    assert complete["duration_days"] == 6
    assert complete["last_upper_limit_before_first_detection"] == {
        "mjd": 8,
        "limiting_mag": 20.5,
        "days_before_first_detection": 2,
    }

    fading = _analyze_band([pt(10, 20.0), pt(12, 19.0), pt(13, 19.1)], 0.3)
    assert fading["status"] == "fading"
    assert fading["fade_time_days"] == 1 and fading["duration_days"] is None

    # A pre-peak dip and re-brightening counts as a brightening event
    flare = _analyze_band([pt(1, 20.0), pt(2, 19.5), pt(3, 19.8), pt(4, 19.0)], 0.3)
    assert flare["pre_peak_brightening_events"] == 2
    assert flare["pre_peak_rms"] > 0


def test_mcp_analyze_light_curve(upload_data_token, public_group, ztf_camera):
    obj_id = str(uuid.uuid4())
    is_error, text, _ = call_tool(
        "post_source",
        {"id": obj_id, "ra": 10.0, "dec": 10.0, "group_ids": [public_group.id]},
        upload_data_token,
    )
    assert not is_error, text

    is_error, text, _ = call_tool(
        "analyze_light_curve", {"obj_id": obj_id}, upload_data_token
    )
    assert is_error and "Fewer than two detections" in text

    is_error, text, _ = call_tool(
        "post_photometry",
        {
            "obj_id": obj_id,
            "instrument_id": ztf_camera.id,
            "mjd": [58000.0, 58002.0, 58004.0, 58005.0, 58008.0, 58003.0],
            "filter": ["ztfg"] * 5 + ["ztfr"],
            "magsys": "ab",
            "mag": [None, 20.0, 19.0, 19.1, 19.5, 19.3],
            "magerr": [None, 0.1, 0.1, 0.1, 0.1, 0.1],
            "limiting_mag": [20.5, 21.0, 21.0, 21.0, 21.0, 21.0],
            "group_ids": [public_group.id],
        },
        upload_data_token,
    )
    assert not is_error, text

    is_error, text, result = call_tool(
        "analyze_light_curve", {"obj_id": obj_id}, upload_data_token
    )
    assert not is_error, text
    analysis = result["structuredContent"]
    assert analysis["skipped_filters"] == ["ztfr"]
    band = analysis["bands"]["ztfg"]
    assert band["status"] == "complete"
    assert band["peak"]["mjd"] == 58004.0
    assert band["rise_time_days"] == 2 and band["fade_time_days"] == 4
    assert band["last_upper_limit_before_first_detection"]["mjd"] == 58000.0
    assert analysis["summary"][0].startswith("ztfg: 4 detections")

    is_error, text, result = call_tool(
        "analyze_light_curve",
        {"obj_id": obj_id, "filters": ["ztfg"], "baseline_threshold": 1.0},
        upload_data_token,
    )
    assert not is_error, text
    assert result["structuredContent"]["bands"]["ztfg"]["status"] == "fading"


def test_mcp_source_photometry_spectrum_round_trip(
    upload_data_token, public_group, ztf_camera, lris
):
    obj_id = str(uuid.uuid4())

    is_error, text, result = call_tool(
        "post_source",
        {"id": obj_id, "ra": 234.22, "dec": -22.33, "group_ids": [public_group.id]},
        upload_data_token,
    )
    assert not is_error, text
    assert json.loads(text)["id"] == obj_id
    assert result["structuredContent"]["id"] == obj_id

    is_error, text, result = call_tool(
        "get_sources", {"obj_id": obj_id}, upload_data_token
    )
    assert not is_error, text
    source = json.loads(text)
    assert source["id"] == obj_id
    assert source["ra"] == 234.22
    assert result["structuredContent"] == source

    is_error, text, _ = call_tool(
        "get_sources",
        {"sourceID": obj_id, "group_ids": [public_group.id], "numPerPage": 5},
        upload_data_token,
    )
    assert not is_error, text
    assert [s["id"] for s in json.loads(text)["sources"]] == [obj_id]

    is_error, text, _ = call_tool(
        "post_photometry",
        {
            "obj_id": obj_id,
            "instrument_id": ztf_camera.id,
            "mjd": [58000.0, 58001.0],
            "filter": "ztfg",
            "magsys": "ab",
            "mag": [19.5, 19.7],
            "magerr": [0.1, 0.1],
            "limiting_mag": 20.5,
            "group_ids": [public_group.id],
        },
        upload_data_token,
    )
    assert not is_error, text
    assert len(json.loads(text)["ids"]) == 2

    is_error, text, _ = call_tool(
        "get_photometry", {"obj_id": obj_id, "format": "mag"}, upload_data_token
    )
    assert not is_error, text
    phot = json.loads(text)
    assert sorted(p["mjd"] for p in phot) == [58000.0, 58001.0]
    assert all(p["filter"] == "ztfg" for p in phot)

    is_error, text, _ = call_tool(
        "post_spectrum",
        {
            "obj_id": obj_id,
            "instrument_id": lris.id,
            "observed_at": "2020-01-10T00:00:00",
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        upload_data_token,
    )
    assert not is_error, text
    spectrum_id = json.loads(text)["id"]

    is_error, text, _ = call_tool("get_spectra", {"obj_id": obj_id}, upload_data_token)
    assert not is_error, text
    spectra = json.loads(text)["spectra"]
    assert [s["id"] for s in spectra] == [spectrum_id]
    assert spectra[0]["wavelengths"] == [664, 665, 666]


def test_mcp_api_errors_become_tool_errors(view_only_token, upload_data_token):
    is_error, text, result = call_tool(
        "get_sources", {"obj_id": "does-not-exist"}, upload_data_token
    )
    assert is_error
    assert text.startswith("Error:")
    assert "structuredContent" not in result

    # Permission checks of the underlying API apply to the token used
    is_error, text, _ = call_tool(
        "post_source",
        {"id": str(uuid.uuid4()), "ra": 1.0, "dec": 1.0},
        view_only_token,
    )
    assert is_error, text


# ─── GCN event tools ────────────────────────────────────────────────────────


def _call(name, args, token):
    return mcp("tools/call", {"name": name, "arguments": args}, token=token)


def test_mcp_get_gcn_event(gcn_GW190814, view_only_token):
    status, data = _call(
        "get_gcn_event", {"dateobs": gcn_GW190814.dateobs.isoformat()}, view_only_token
    )
    assert status == 200, data
    event = data["result"]["structuredContent"]
    assert event["dateobs"].startswith("2019-08-14")
    assert "LVC#S190814bv" in event["aliases"]


def test_mcp_get_gcn_events_by_alias(gcn_GW190814, view_only_token):
    """The name a circular uses resolves the event, via the alias substring."""
    status, data = _call(
        "get_gcn_events", {"partialdateobs": "S190814bv"}, view_only_token
    )
    assert status == 200, data
    events = data["result"]["structuredContent"]["events"]
    assert any(e["dateobs"].startswith("2019-08-14") for e in events)


def test_mcp_gcn_extractions_are_empty_before_any_are_written(
    gcn_GW190814, view_only_token
):
    status, data = _call(
        "get_gcn_event_extractions",
        {"dateobs": gcn_GW190814.dateobs.isoformat()},
        view_only_token,
    )
    assert status == 200, data
    assert data["result"]["structuredContent"] == []


def test_mcp_gcn_comment_round_trip(gcn_GW190814, super_admin_token):
    """Comments are the discussion on an event, so an assistant can reply there."""
    dateobs = gcn_GW190814.dateobs.isoformat()
    status, data = _call(
        "post_gcn_event_comment",
        {"dateobs": dateobs, "text": "Follow-up requested."},
        super_admin_token,
    )
    assert status == 200, data

    status, data = _call(
        "get_gcn_event_comments", {"dateobs": dateobs}, super_admin_token
    )
    assert status == 200, data
    texts = [c["text"] for c in data["result"]["structuredContent"]]
    assert "Follow-up requested." in texts


# ─── Broker filter tools ────────────────────────────────────────────────────


def test_versions_reads_oldest_first():
    record = {
        "fv": [
            {"fid": "a", "pipeline": [{"$match": {}}]},
            {"fid": "b", "pipeline": [{"$project": {}}]},
        ]
    }
    assert [fid for fid, _ in _versions(record)] == ["a", "b"]


def test_versions_skips_entries_without_an_fid():
    # A version with no fid cannot be activated or diffed, so it is not one.
    record = {"fv": [{"pipeline": []}, {"fid": "b", "pipeline": []}]}
    assert [fid for fid, _ in _versions(record)] == ["b"]


def test_versions_of_a_filter_with_no_history():
    assert _versions({}) == []
    assert _versions({"fv": None}) == []


def test_broker_filter_tools_require_their_identifiers():
    for name in (
        "get_broker_filter",
        "diff_broker_filter_versions",
        "run_broker_filter",
        "post_broker_filter_version",
        "activate_broker_filter_version",
    ):
        assert "broker_id" in TOOLS[name]["schema"]["required"], name


def test_run_broker_filter_takes_a_pipeline_as_stages():
    # The pipeline is a list of stages; passing a mapping is the mistake that
    # made a broker filter reject every alert.
    schema = TOOLS["run_broker_filter"]["schema"]
    assert schema["properties"]["pipeline"]["type"] == "array"
    assert "pipeline" in schema["required"]


def test_posting_a_version_does_not_activate_it():
    # Activation is a separate step, so a bad version cannot go live by being
    # uploaded.
    assert (
        "active_fid" not in TOOLS["post_broker_filter_version"]["schema"]["properties"]
    )
    assert "active_fid" in TOOLS["activate_broker_filter_version"]["schema"]["required"]
