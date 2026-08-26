import base64
import json
import uuid

from skyportal.handlers.mcp import TOOLS
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


def test_mcp_legacy_initialize_rejected(view_only_token):
    status, data = mcp(
        "initialize",
        {"protocolVersion": "2025-06-18", "capabilities": {}},
        token=view_only_token,
        headers={"Mcp-Method": None, "MCP-Protocol-Version": None},
        meta=False,
    )
    assert status == 400
    assert data["error"]["code"] == -32022
    assert data["error"]["data"] == {"supported": [VERSION], "requested": "2025-06-18"}
    assert VERSION in data["error"]["message"]


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


def test_mcp_tool_request_mapping():
    fn = TOOLS["get_sources"]["fn"]
    assert fn({"obj_id": "X", "includePhotometry": True}) == (
        "GET",
        "/api/sources/X",
        {"includePhotometry": True},
        None,
    )
    assert fn({"ra": 1, "dec": 2, "radius": 0.1})[1] == "/api/sources"

    assert TOOLS["get_photometry"]["fn"]({"obj_id": "X", "format": "flux"}) == (
        "GET",
        "/api/sources/X/photometry",
        {"format": "flux"},
        None,
    )
    assert TOOLS["get_spectra"]["fn"]({"obj_id": "X"})[1] == "/api/sources/X/spectra"

    body = {"id": "X", "ra": 1, "dec": 2}
    assert TOOLS["post_source"]["fn"](dict(body)) == (
        "POST",
        "/api/sources",
        None,
        body,
    )
    assert TOOLS["post_photometry"]["fn"]({})[1] == "/api/photometry"
    assert TOOLS["post_spectrum"]["fn"]({})[1] == "/api/spectrum"


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
