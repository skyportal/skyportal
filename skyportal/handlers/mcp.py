"""MCP (Model Context Protocol) endpoint at /mcp, protocol revision 2026-07-28.

Modern-only: no initialize handshake, no sessions, no SSE. Every POST is a
self-contained JSON-RPC request whose `_meta` carries the protocol version
and client capabilities, so requests can land on any app process. Tools are
async functions that may call the REST API (with the caller's own token, so
the usual permission checks apply) any number of times and return their own
content.
"""

import base64
import json
import statistics
from urllib.parse import urlencode, urlsplit

import jsonschema
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from baselayer.app.access import auth_or_token

from .. import __version__
from ..app_utils import get_app_base_url
from .base import BaseHandler

PROTOCOL_VERSION = "2026-07-28"
META = "io.modelcontextprotocol/"
SERVER_INFO = {"name": "SkyPortal", "version": __version__}
# The tool set only changes with a deploy
LIST_TTL_MS = 3_600_000

# JSON-RPC / MCP error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
HEADER_MISMATCH = -32020
UNSUPPORTED_PROTOCOL_VERSION = -32022

TOOLS = {}


def tool(name, description, properties, required=(), passthrough=None):
    """Register a tool. The wrapped `async fn(handler, args)` returns the tool's
    content: a JSON value (also sent as structuredContent) or a plain string.
    Raise ToolError, or let handler.api() raise APIError, to report a tool
    execution error. `passthrough` names the endpoint whose remaining
    parameters are accepted verbatim."""

    schema = {"type": "object", "properties": properties, "required": list(required)}
    if passthrough:
        schema["additionalProperties"] = True
        description += (
            f" Any other parameter accepted by {passthrough} may also be passed."
        )
    else:
        schema["additionalProperties"] = False
    jsonschema.Draft202012Validator.check_schema(schema)

    def register(fn):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "inputSchema": schema,
            "validator": jsonschema.Draft202012Validator(schema),
            "fn": fn,
        }
        return fn

    return register


def _prop(type_, description, **kwargs):
    return {"type": type_, "description": description, **kwargs}


def _scalar_or_list(type_, description, nullable=False):
    types = [type_, "null"] if nullable else [type_]
    return {
        "type": [*types, "array"],
        "items": {"type": types},
        "description": description,
    }


_GROUP_IDS = _prop(
    "array",
    "Group IDs to share with. Defaults to all of the token's groups.",
    items={"type": "integer"},
)


@tool(
    "get_sources",
    "Retrieve one source by ID, or search sources with filters. Results are "
    "paginated (numPerPage, pageNumber).",
    {
        "obj_id": _prop("string", "Source ID. If given, returns just that source."),
        "ra": _prop("number", "RA for cone search (decimal degrees)."),
        "dec": _prop("number", "Dec for cone search (decimal degrees)."),
        "radius": _prop("number", "Cone search radius (decimal degrees)."),
        "sourceID": _prop("string", "Portion of ID or TNS name to filter on."),
        "group_ids": _prop(
            "array", "Only sources saved to these groups.", items={"type": "integer"}
        ),
        "classifications": _prop(
            "array",
            'Classifications to filter on, e.g. ["Sitewide Taxonomy: Ia"].',
            items={"type": "string"},
        ),
        "hasSpectrum": _prop("boolean", "Only sources with at least one spectrum."),
        "savedAfter": _prop("string", "Only sources saved after this UTC datetime."),
        "savedBefore": _prop("string", "Only sources saved before this UTC datetime."),
        "minRedshift": _prop("number", "Minimum redshift."),
        "maxRedshift": _prop("number", "Maximum redshift."),
        "sortBy": _prop(
            "string",
            "Sort field: id, alias, origin, ra, dec, redshift, saved_at, gcn_status, favorites.",
        ),
        "sortOrder": _prop("string", "asc or desc.", enum=["asc", "desc"]),
        "numPerPage": _prop("integer", "Results per page (default 100, max 500)."),
        "pageNumber": _prop("integer", "Page number (default 1)."),
        "includePhotometry": _prop("boolean", "Include photometry in the response."),
        "includeSpectrumExists": _prop("boolean", "Flag whether spectra exist."),
        "includeThumbnails": _prop("boolean", "Include thumbnails."),
    },
    passthrough="GET /api/sources",
)
async def get_sources(handler, args):
    obj_id = args.pop("obj_id", None)
    path = f"/api/sources/{obj_id}" if obj_id else "/api/sources"
    return await handler.api("GET", path, query=args)


@tool(
    "post_source",
    "Create a source (or save an existing object to more groups).",
    {
        "id": _prop("string", "Source ID, e.g. ZTF21aaaaaaa."),
        "ra": _prop("number", "RA (decimal degrees)."),
        "dec": _prop("number", "Dec (decimal degrees)."),
        "redshift": _prop("number", "Redshift."),
        "redshift_error": _prop("number", "Redshift uncertainty."),
        "origin": _prop("string", "Origin of the source."),
        "alias": _prop("array", "Alternative names.", items={"type": "string"}),
        "group_ids": _GROUP_IDS,
    },
    required=("id", "ra", "dec"),
    passthrough="POST /api/sources",
)
async def post_source(handler, args):
    return await handler.api("POST", "/api/sources", body=args)


@tool(
    "get_photometry",
    "Retrieve all photometry of a source.",
    {
        "obj_id": _prop("string", "Source ID."),
        "format": _prop(
            "string",
            "Return magnitudes, fluxes, or both (default mag).",
            enum=["mag", "flux", "both"],
        ),
        "magsys": _prop("string", "Magnitude system for the output (default ab)."),
        "individualOrSeries": _prop(
            "string",
            "Individual points, photometric series, or both (default both).",
            enum=["individual", "series", "both"],
        ),
        "deduplicatePhotometry": _prop("boolean", "Deduplicate photometry."),
        "includeOwnerInfo": _prop("boolean", "Include who uploaded each point."),
    },
    required=("obj_id",),
    passthrough="GET /api/sources/{obj_id}/photometry",
)
async def get_photometry(handler, args):
    obj_id = args.pop("obj_id")
    return await handler.api("GET", f"/api/sources/{obj_id}/photometry", query=args)


@tool(
    "post_photometry",
    "Upload photometry. Pass scalars for one point, or equal-length lists for "
    "many. Give either mag/magerr (with limiting_mag for non-detections) or "
    "flux/fluxerr/zp.",
    {
        "obj_id": _scalar_or_list("string", "Source ID."),
        "instrument_id": _scalar_or_list("integer", "Instrument ID."),
        "mjd": _scalar_or_list("number", "MJD of the observation."),
        "filter": _scalar_or_list("string", "Bandpass, e.g. ztfg."),
        "magsys": _scalar_or_list("string", "Magnitude system, e.g. ab."),
        "mag": _scalar_or_list(
            "number", "Magnitude (null for non-detections).", nullable=True
        ),
        "magerr": _scalar_or_list("number", "Magnitude uncertainty.", nullable=True),
        "limiting_mag": _scalar_or_list("number", "Limiting magnitude."),
        "flux": _scalar_or_list(
            "number", "Flux (null for non-detections).", nullable=True
        ),
        "fluxerr": _scalar_or_list("number", "Flux uncertainty.", nullable=True),
        "zp": _scalar_or_list("number", "Zero point of the flux."),
        "ra": _scalar_or_list("number", "RA of the point (decimal degrees)."),
        "dec": _scalar_or_list("number", "Dec of the point (decimal degrees)."),
        "origin": _scalar_or_list("string", "Origin of the point."),
        "group_ids": _GROUP_IDS,
        "altdata": _prop("object", "Arbitrary extra metadata."),
    },
    required=("obj_id", "instrument_id", "mjd", "filter", "magsys"),
    passthrough="POST /api/photometry",
)
async def post_photometry(handler, args):
    return await handler.api("POST", "/api/photometry", body=args)


@tool(
    "get_spectra",
    "Retrieve all spectra of a source.",
    {
        "obj_id": _prop("string", "Source ID."),
        "normalization": _prop(
            "string", 'Normalization to apply, e.g. "median". Omit for raw fluxes.'
        ),
        "sortBy": _prop(
            "string",
            "Sort field (default observed_at).",
            enum=["observed_at", "created_at"],
        ),
        "sortOrder": _prop("string", "asc or desc.", enum=["asc", "desc"]),
    },
    required=("obj_id",),
    passthrough="GET /api/sources/{obj_id}/spectra",
)
async def get_spectra(handler, args):
    obj_id = args.pop("obj_id")
    return await handler.api("GET", f"/api/sources/{obj_id}/spectra", query=args)


@tool(
    "post_spectrum",
    "Upload a spectrum.",
    {
        "obj_id": _prop("string", "Source ID."),
        "instrument_id": _prop("integer", "Instrument ID."),
        "observed_at": _prop("string", "Observation time (ISO 8601 UTC)."),
        "wavelengths": _prop(
            "array", "Wavelengths (Angstroms).", items={"type": "number"}
        ),
        "fluxes": _prop("array", "Fluxes.", items={"type": "number"}),
        "errors": _prop("array", "Flux uncertainties.", items={"type": "number"}),
        "units": _prop("string", "Flux units, e.g. erg/s/cm/cm/AA."),
        "origin": _prop("string", "Origin of the spectrum."),
        "type": _prop("string", "Spectrum type, e.g. source, host, host_center."),
        "label": _prop("string", "Display label."),
        "group_ids": _GROUP_IDS,
        "altdata": _prop("object", "Arbitrary extra metadata."),
    },
    required=("obj_id", "instrument_id", "observed_at", "wavelengths", "fluxes"),
    passthrough="POST /api/spectrum",
)
async def post_spectrum(handler, args):
    return await handler.api("POST", "/api/spectrum", body=args)


def _analyze_band(points, baseline_threshold):
    """Light-curve metrics for one band from mag-format photometry points.

    Returns None with fewer than two detections.
    """
    detections = sorted(
        (p for p in points if p.get("mag") is not None), key=lambda p: p["mjd"]
    )
    limits = [
        p for p in points if p.get("mag") is None and p.get("limiting_mag") is not None
    ]
    if len(detections) < 2:
        return None
    mjds = [p["mjd"] for p in detections]
    mags = [p["mag"] for p in detections]
    peak = min(range(len(mags)), key=mags.__getitem__)
    rise_time = mjds[peak] - mjds[0]
    rise_mag = mags[0] - mags[peak]
    band = {
        "n_detections": len(detections),
        "n_upper_limits": len(limits),
        "first_detection": {"mjd": mjds[0], "mag": mags[0]},
        "last_detection": {"mjd": mjds[-1], "mag": mags[-1]},
        "peak": {
            "mjd": mjds[peak],
            "mag": mags[peak],
            "magerr": detections[peak].get("magerr"),
        },
        "rise_time_days": rise_time,
        "rise_mag": rise_mag,
        "rise_rate_mag_per_day": rise_mag / rise_time if rise_time > 0 else None,
    }
    if peak == len(mags) - 1:
        band.update(
            status="rising",
            fade_time_days=None,
            fade_mag=None,
            fade_rate_mag_per_day=None,
            duration_days=None,
        )
    else:
        # First post-peak point fainter than the peak by more than the threshold
        baseline = next(
            (
                i
                for i in range(peak + 1, len(mags))
                if mags[i] - mags[peak] > baseline_threshold
            ),
            None,
        )
        end = baseline if baseline is not None else len(mags) - 1
        fade_time = mjds[end] - mjds[peak]
        fade_mag = mags[end] - mags[peak]
        band.update(
            status="complete" if baseline is not None else "fading",
            fade_time_days=fade_time,
            fade_mag=fade_mag,
            fade_rate_mag_per_day=fade_mag / fade_time if fade_time > 0 else None,
            duration_days=rise_time + fade_time if baseline is not None else None,
        )
    pre_peak = mags[: peak + 1]
    band["pre_peak_brightening_events"] = sum(
        b - a < -0.1 for a, b in zip(pre_peak, pre_peak[1:], strict=False)
    )
    band["pre_peak_rms"] = statistics.pstdev(pre_peak) if len(pre_peak) > 1 else 0.0
    last_limit = max(
        (p for p in limits if p["mjd"] < mjds[0]), key=lambda p: p["mjd"], default=None
    )
    band["last_upper_limit_before_first_detection"] = (
        {
            "mjd": last_limit["mjd"],
            "limiting_mag": last_limit["limiting_mag"],
            "days_before_first_detection": mjds[0] - last_limit["mjd"],
        }
        if last_limit
        else None
    )
    return _rounded(band)


def _rounded(value, ndigits=4):
    if isinstance(value, float):
        return round(value, ndigits)
    if isinstance(value, dict):
        return {k: _rounded(v, ndigits) for k, v in value.items()}
    return value


def _band_summary(name, band):
    text = (
        f"{name}: {band['n_detections']} detections, peak {band['peak']['mag']:.2f} "
        f"mag at MJD {band['peak']['mjd']:.2f}, rose {band['rise_mag']:.2f} mag "
        f"in {band['rise_time_days']:.1f} d"
    )
    if band["fade_time_days"] is not None:
        text += f", faded {band['fade_mag']:.2f} mag in {band['fade_time_days']:.1f} d"
    return f"{text} ({band['status']})"


@tool(
    "analyze_light_curve",
    "Summarize how a source's light curve evolves, per band: first, last and "
    "peak detections, rise and fade times and rates, whether it is still "
    "rising, still fading, or complete (back to baseline), pre-peak "
    "variability, and the last upper limit before discovery.",
    {
        "obj_id": _prop("string", "Source ID."),
        "filters": _prop(
            "array",
            'Bands to analyze, e.g. ["ztfg", "ztfr"]. Defaults to every band with data.',
            items={"type": "string"},
        ),
        "baseline_threshold": _prop(
            "number",
            "Magnitudes fainter than peak at which the source counts as back at "
            "baseline (default 0.3).",
            minimum=0,
        ),
        "magsys": _prop("string", "Magnitude system (default ab)."),
    },
    required=("obj_id",),
)
async def analyze_light_curve(handler, args):
    obj_id = args["obj_id"]
    magsys = args.get("magsys", "ab")
    threshold = args.get("baseline_threshold", 0.3)
    photometry = await handler.api(
        "GET",
        f"/api/sources/{obj_id}/photometry",
        query={"format": "mag", "magsys": magsys},
    )
    by_filter = {}
    for p in photometry:
        by_filter.setdefault(p["filter"], []).append(p)
    bands, skipped = {}, []
    for name in args.get("filters") or sorted(by_filter):
        band = _analyze_band(by_filter.get(name, []), threshold)
        if band is None:
            skipped.append(name)
        else:
            bands[name] = band
    if not bands:
        raise ToolError(f"Fewer than two detections in any requested band for {obj_id}")
    return {
        "obj_id": obj_id,
        "magsys": magsys,
        "baseline_threshold": threshold,
        "summary": [_band_summary(name, band) for name, band in bands.items()],
        "bands": bands,
        "skipped_filters": skipped,
    }


@tool(
    "get_gcn_events",
    "List GCN events (gravitational-wave, GRB, neutrino and other multi-messenger "
    "triggers). Filter by date range, or by name with partialdateobs, which "
    "matches a dateobs prefix or any of the event's aliases.",
    {
        "partialdateobs": _prop(
            "string",
            "Match a dateobs prefix or an alias substring, e.g. 2026-06-04 or "
            "S190814bv.",
        ),
        "startDate": _prop("string", "Only events at or after this UTC time."),
        "endDate": _prop("string", "Only events at or before this UTC time."),
        "gcnTagKeep": _prop(
            "array", "Only events with these tags, e.g. GRB.", items={"type": "string"}
        ),
        "numPerPage": _prop("integer", "Events per page (default 10)."),
        "pageNumber": _prop("integer", "1-indexed page."),
    },
    passthrough="GET /api/gcn_event",
)
async def get_gcn_events(handler, args):
    return await handler.api("GET", "/api/gcn_event", query=args)


@tool(
    "get_gcn_event",
    "One GCN event in full: its aliases, tags, notices, localizations, and the "
    "GCN circulars associated with it. Use this to find what has been reported "
    "about an event.",
    {"dateobs": _prop("string", "The event's dateobs, e.g. 2026-06-04T20:20:37.")},
    required=("dateobs",),
)
async def get_gcn_event(handler, args):
    return await handler.api("GET", f"/api/gcn_event/{args['dateobs']}")


@tool(
    "get_gcn_event_extractions",
    "Structured data extracted from a GCN event's circulars by a pipeline "
    "(photometry, redshift, classification and the like). Unlike the circular "
    "text, these are machine-readable values. Filter by origin to select one "
    "producer, or by circularId for a single circular.",
    {
        "dateobs": _prop("string", "The event's dateobs."),
        "origin": _prop("string", "Only extractions from this producer, e.g. circex."),
        "circularId": _prop("integer", "Only extractions from this GCN circular."),
    },
    required=("dateobs",),
)
async def get_gcn_event_extractions(handler, args):
    dateobs = args.pop("dateobs")
    return await handler.api("GET", f"/api/gcn_event/{dateobs}/extractions", query=args)


@tool(
    "get_gcn_event_comments",
    "The discussion on a GCN event. Comments are how people talk about an event "
    "in SkyPortal.",
    {"dateobs": _prop("string", "The event's dateobs.")},
    required=("dateobs",),
)
async def get_gcn_event_comments(handler, args):
    return await handler.api("GET", f"/api/gcn_event/{args['dateobs']}/comments")


@tool(
    "post_gcn_event_comment",
    "Add a comment to a GCN event, to reply in the discussion on that event.",
    {
        "dateobs": _prop("string", "The event's dateobs."),
        "text": _prop("string", "The comment body."),
        "group_ids": _GROUP_IDS,
    },
    required=("dateobs", "text"),
)
async def post_gcn_event_comment(handler, args):
    dateobs = args.pop("dateobs")
    return await handler.api("POST", f"/api/gcn_event/{dateobs}/comments", body=args)


def _encode_query(query):
    """Encode tool arguments the way the REST handlers parse them."""
    out = {}
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, list | tuple):
            value = ",".join(str(v) for v in value)
        out[key] = value
    return urlencode(out)


def _decode_header_value(value):
    """Undo the transport's `=?base64?...?=` sentinel encoding, if used."""
    if value.startswith("=?base64?") and value.endswith("?="):
        try:
            return base64.b64decode(value[9:-2], validate=True).decode()
        except (ValueError, UnicodeDecodeError):
            raise RPCError(
                HEADER_MISMATCH, "Malformed Base64 header value", status=400
            ) from None
    return value


class ToolError(Exception):
    """A tool execution error, reported to the model as an isError result."""


class APIError(ToolError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class RPCError(Exception):
    def __init__(self, code, message, status=200, data=None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.data = data


class MCPHandler(BaseHandler):
    def prepare(self):
        # DNS-rebinding protection: only our own origin may call this endpoint
        origin = self.request.headers.get("Origin")
        if origin is not None and not self._origin_allowed(origin):
            self._respond(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": INVALID_REQUEST, "message": "Invalid Origin"},
                },
                status=403,
            )
            return None
        # MCP clients send "Bearer <token>"; auth_or_token expects "token <token>".
        auth = self.request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            self.request.headers["Authorization"] = "token " + auth[7:].strip()
        return super().prepare()

    def _origin_allowed(self, origin):
        allowed = {urlsplit(get_app_base_url()).netloc, self.request.host}
        return urlsplit(origin).netloc.lower() in {a.lower() for a in allowed}

    @auth_or_token
    async def post(self):
        request_id = None
        try:
            message = self._parse_message()
            if "id" not in message:
                # Notification: nothing to return
                self.set_status(202)
                return self.finish()
            request_id = message["id"]
            params = message.get("params") or {}
            if not isinstance(params, dict):
                raise RPCError(INVALID_PARAMS, "params must be an object", status=400)
            self._validate_request(message["method"], params)
            result = await self._dispatch(message["method"], params)
            result["resultType"] = "complete"
            result.setdefault("_meta", {})[f"{META}serverInfo"] = SERVER_INFO
            self._respond({"jsonrpc": "2.0", "id": request_id, "result": result})
        except RPCError as e:
            error = {"code": e.code, "message": str(e)}
            if e.data is not None:
                error["data"] = e.data
            self._respond(
                {"jsonrpc": "2.0", "id": request_id, "error": error}, status=e.status
            )

    def _respond(self, payload, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.finish(json.dumps(payload))

    def _parse_message(self):
        try:
            message = json.loads(self.request.body)
        except ValueError:
            raise RPCError(PARSE_ERROR, "Parse error", status=400) from None
        if (
            not isinstance(message, dict)
            or message.get("jsonrpc") != "2.0"
            or not isinstance(message.get("method"), str)
        ):
            raise RPCError(INVALID_REQUEST, "Invalid Request", status=400)
        if "id" in message and (
            isinstance(message["id"], bool) or not isinstance(message["id"], str | int)
        ):
            raise RPCError(
                INVALID_REQUEST, "Request id must be a string or integer", status=400
            )
        return message

    def _validate_request(self, method, params):
        """Enforce the transport's header/body mirroring and per-request _meta."""
        unsupported = RPCError(
            UNSUPPORTED_PROTOCOL_VERSION,
            f"Unsupported protocol version; this server speaks MCP {PROTOCOL_VERSION}",
            status=400,
            data={"supported": [PROTOCOL_VERSION]},
        )
        if method == "initialize":
            # Legacy handshake from a pre-2026-07-28 client
            unsupported.data["requested"] = params.get("protocolVersion")
            raise unsupported

        headers = self.request.headers

        def header(name):
            value = headers.get(name)
            if value is None:
                raise RPCError(
                    HEADER_MISMATCH, f"Missing required {name} header", status=400
                )
            return value

        def mismatch(name, header_value, body_value):
            raise RPCError(
                HEADER_MISMATCH,
                f"Header mismatch: {name} header value {header_value!r} does not "
                f"match body value {body_value!r}",
                status=400,
            )

        if header("Mcp-Method") != method:
            mismatch("Mcp-Method", headers["Mcp-Method"], method)
        header_version = header("MCP-Protocol-Version")
        if method == "tools/call":
            name = _decode_header_value(header("Mcp-Name"))
            if name != params.get("name"):
                mismatch("Mcp-Name", name, params.get("name"))

        meta = params.get("_meta")
        if not isinstance(meta, dict):
            raise RPCError(INVALID_PARAMS, "Missing required _meta", status=400)
        version = meta.get(f"{META}protocolVersion")
        if not isinstance(version, str):
            raise RPCError(
                INVALID_PARAMS,
                f"Missing required _meta field {META}protocolVersion",
                status=400,
            )
        if not isinstance(meta.get(f"{META}clientCapabilities"), dict):
            raise RPCError(
                INVALID_PARAMS,
                f"Missing required _meta field {META}clientCapabilities",
                status=400,
            )
        if header_version != version:
            mismatch("MCP-Protocol-Version", header_version, version)
        if version != PROTOCOL_VERSION:
            unsupported.data["requested"] = version
            raise unsupported

    async def _dispatch(self, method, params):
        if method == "server/discover":
            return {
                "supportedVersions": [PROTOCOL_VERSION],
                "capabilities": {"tools": {}},
                "instructions": (
                    "Read and write SkyPortal sources, photometry and spectra. "
                    "Tools run with the permissions of the API token you send."
                ),
                "ttlMs": LIST_TTL_MS,
                "cacheScope": "public",
            }
        if method == "tools/list":
            return {
                "tools": [
                    {k: t[k] for k in ("name", "description", "inputSchema")}
                    for t in TOOLS.values()
                ],
                "ttlMs": LIST_TTL_MS,
                "cacheScope": "public",
            }
        if method == "tools/call":
            return await self._call_tool(params)
        raise RPCError(METHOD_NOT_FOUND, f"Method not found: {method}", status=404)

    async def _call_tool(self, params):
        spec = TOOLS.get(params.get("name"))
        if spec is None:
            raise RPCError(INVALID_PARAMS, f"Unknown tool: {params.get('name')}")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise RPCError(INVALID_PARAMS, "Tool arguments must be an object")
        if "Authorization" not in self.request.headers:
            raise RPCError(
                INVALID_REQUEST,
                "Tools require an API token (Authorization: Bearer <token>).",
                status=401,
            )
        problems = [
            f"{'/'.join(str(p) for p in e.path) or 'arguments'}: {e.message}"
            for e in spec["validator"].iter_errors(arguments)
        ]
        if problems:
            return self._tool_result(
                "Invalid arguments: " + "; ".join(sorted(problems)), is_error=True
            )

        try:
            content = await spec["fn"](self, dict(arguments))
        except ToolError as e:
            return self._tool_result(f"Error: {e}", is_error=True)
        if isinstance(content, str):
            return self._tool_result(content)
        return {**self._tool_result(json.dumps(content)), "structuredContent": content}

    @staticmethod
    def _tool_result(text, is_error=False):
        return {"content": [{"type": "text", "text": text}], "isError": is_error}

    async def api(self, method, path, query=None, body=None):
        """Call the REST API through the local server with the caller's token.

        Returns the response's `data` on success; raises APIError otherwise.
        """
        url = f"http://localhost:{self.cfg['ports.app']}{path}"
        if query:
            url += "?" + _encode_query(query)
        request = HTTPRequest(
            url,
            method=method,
            headers={
                "Authorization": self.request.headers["Authorization"],
                "Content-Type": "application/json",
            },
            body=json.dumps(body) if body is not None else None,
            request_timeout=300,
        )
        response = await AsyncHTTPClient().fetch(request, raise_error=False)
        try:
            payload = json.loads(response.body or b"")
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        if response.code == 200 and payload.get("status") == "success":
            return payload.get("data")
        message = payload.get("message") or (
            response.body.decode(errors="replace")[:500] if response.body else None
        )
        raise APIError(response.code, message or f"HTTP {response.code}")
