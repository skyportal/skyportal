"""Wendelstein requests: 3KK and SEDM-FTW on the 2m, and the 43cm imager.

The telescope is operated by hand rather than from a queue, so a 3KK request
produces a script the observer runs at the telescope. ``submit`` validates and
records the request; the script itself is rendered on demand from the payload
by ``generate_script``, so editing a request changes its script. With a Redmine
API key on the allocation, each request also opens an issue in the
observatory's Redmine, the queue its observers pick targets from, and
withdrawing the request closes it.
"""

import json
import re

import aiohttp
import sqlalchemy as sa
from astropy.coordinates import SkyCoord
from astropy.time import Time, TimeDelta
from sqlalchemy.orm import selectinload

from baselayer.app.env import load_env

from ..utils import http
from ..utils.app import get_app_base_url
from . import FollowUpAPI
from .interface import push_followup_refresh

env, cfg = load_env()

REDMINE_URL = "https://luna.mpe.mpg.de/redmine"
REDMINE_TRACKER_ID = 4
REDMINE_WITHDRAWN_STATUS_ID = 6
REDMINE_OBSERVED_STATUS = "Observed"
REDMINE_FIELDS = {
    "instrument": 7,
    "object_name": 14,
    "ra": 3,
    "dec": 4,
    "maximum_airmass": 6,
    "lunar_phase": 2,
    "minimum_sky": 9,
    "maximum_seeing": 5,
    "transparency": 15,
}
REDMINE_INSTRUMENTS = {
    "Wendelstein 3KK": "3kk",
    "SEDM-FTW": "SEDM-FTW",
    "Wendelstein QHY600": "PIma",
}
LUNAR_PHASES = ["any", "dark", "gray", "bright"]
TRANSPARENCIES = ["any", "thin cirrus", "clear", "photometric"]
CONSTRAINT_DEFAULTS = {
    "maximum_airmass": 2.0,
    "maximum_seeing": 3.0,
    "minimum_sky": 16.0,
    "lunar_phase": "any",
    "transparency": "any",
}

# The arm each 3KK filter sits in, and the token the control language uses for
# it. 3KK splits one pointing across three arms that expose at the same time,
# so a sequence names one filter from each.
THREEKK_FILTERS = {
    "sdssu": ("blue", "bu"),
    "sdssg": ("blue", "bg"),
    "sdssr": ("blue", "br"),
    "sdssi": ("red", "ri"),
    "sdssz": ("red", "rz"),
    "2massj": ("nir", "nJ"),
    "2massh": ("nir", "nH"),
    "2massks": ("nir", "nK"),
}

# 2mf names its filters blue to NIR; 2mt gives its times in the opposite order.
ARMS = ("blue", "red", "nir")
EXPOSURE_ARMS = ("nir", "red", "blue")
ARM_EXPOSURE_TOKENS = {"nir": "n", "red": "r", "blue": "b"}
DEFAULT_ARM_EXPOSURES = {
    "blue": ("sdssg", 150.0),
    "red": ("sdssi", 150.0),
    "nir": ("2massks", 60.0),
}

SCRIPT_TOKEN = r"[A-Za-z0-9_.:+-]*"
OBJECT_NAME = r"[A-Za-z0-9_+-]+"
CONTROL_CHARACTERS = r"[\x00-\x1f\x7f]"

SCRIPT_INSTRUMENTS = {"Wendelstein 3KK"}
IMAGING_INSTRUMENTS = {"Wendelstein QHY600"}
SUPPORTED_INSTRUMENTS = set(REDMINE_INSTRUMENTS)


def filters_for_arm(instrument, arm):
    """The instrument's filters that sit in one 3KK arm."""
    return [
        f
        for f in (instrument.to_dict().get("filters") or [])
        if THREEKK_FILTERS.get(f, (None, None))[0] == arm
    ]


def validate_request(request, instrument):
    """Check a payload before it reaches the observer."""
    instrument_name = getattr(instrument, "name", None)
    if instrument_name not in SUPPORTED_INSTRUMENTS:
        raise ValueError(
            f"Wendelstein requests are implemented for "
            f"{', '.join(sorted(SUPPORTED_INSTRUMENTS))}, not {instrument_name}."
        )

    payload = request.payload or {}
    scripted = instrument_name in SCRIPT_INSTRUMENTS
    imaged = instrument_name in IMAGING_INSTRUMENTS
    dated = ["start_date", "end_date", "priority"]
    listed = ["sequences", "dither_size"] if scripted else []
    if imaged:
        listed = ["exposures"]
    for param in listed + dated:
        if param not in payload:
            raise ValueError(f"Parameter {param} required.")

    object_name = str(payload.get("object_name") or request.obj_id)
    if not re.fullmatch(OBJECT_NAME, object_name):
        raise ValueError(
            f"The object name {object_name!r} may only contain letters, digits and _+-"
        )
    tokens = {}
    if scripted:
        sequences = payload["sequences"]
        if not isinstance(sequences, list) or not sequences:
            raise ValueError("At least one sequence is required.")
        tokens["program id"] = payload.get("program_id")
        for index, sequence in enumerate(sequences, start=1):
            tokens[f"sequence {index} readout mode"] = sequence.get("readout_mode")
    for name, value in tokens.items():
        if value is not None and not re.fullmatch(SCRIPT_TOKEN, str(value)):
            raise ValueError(
                f"The {name} {value!r} may only contain letters, digits and _.:+-"
            )
    for param in dated:
        if re.search(CONTROL_CHARACTERS, str(payload[param])):
            raise ValueError(f"Parameter {param} cannot contain control characters.")
    if imaged:
        _validate_exposures(payload["exposures"], instrument)
    if not scripted:
        return

    known = instrument.to_dict().get("filters") or []
    for index, sequence in enumerate(sequences, start=1):
        for arm in ARMS:
            filt = sequence.get(f"{arm}_filter")
            if filt in (None, ""):
                continue
            if filt not in known:
                raise ValueError(
                    f"Sequence {index}: filter {filt} is not on {instrument_name}."
                )
            if THREEKK_FILTERS.get(filt, (None, None))[0] != arm:
                raise ValueError(
                    f"Sequence {index}: filter {filt} is not in the {arm} arm."
                )
        if not any(sequence.get(f"{arm}_filter") for arm in ARMS):
            raise ValueError(f"Sequence {index}: at least one filter is required.")
        for arm in ARMS:
            if not sequence.get(f"{arm}_filter"):
                continue
            exposure_time = sequence.get(f"{arm}_exposure_time")
            if not exposure_time:
                raise ValueError(
                    f"Sequence {index}: {arm} filter set without an exposure time."
                )
            if not isinstance(exposure_time, (int, float)) or round(exposure_time) < 1:
                raise ValueError(
                    f"Sequence {index}: {arm} exposure time must round to at least 1 s."
                )


def _validate_exposures(exposures, instrument):
    if not isinstance(exposures, list) or not exposures:
        raise ValueError("At least one exposure is required.")
    known = instrument.to_dict().get("filters") or []
    for index, exposure in enumerate(exposures, start=1):
        if exposure.get("filter") not in known:
            raise ValueError(
                f"Exposure {index}: filter {exposure.get('filter')}"
                f" is not on {instrument.name}."
            )
        for key in ["exposure_time", "exposure_count"]:
            value = exposure.get(key)
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"Exposure {index}: {key} must be positive.")


def _sexagesimal(obj):
    """The object's position in the sexagesimal form 2mradec takes."""
    coord = SkyCoord(ra=obj.ra, dec=obj.dec, unit="deg")
    return coord.to_string("hmsdms", sep=":", precision=2).split(" ")


def _exposure_line(sequence):
    """The 2mt line for one sequence.

    One time for every arm collapses to the bare form the control language
    accepts; otherwise each arm carries its own token.
    """
    times = {
        arm: round(sequence.get(f"{arm}_exposure_time"))
        for arm in ARMS
        if sequence.get(f"{arm}_filter")
    }
    distinct = set(times.values())
    if len(distinct) == 1:
        return f"2mt {distinct.pop()}"
    parts = [
        f"{ARM_EXPOSURE_TOKENS[arm]}{times[arm]}"
        for arm in EXPOSURE_ARMS
        if arm in times
    ]
    return "2mt " + " ".join(parts)


def _filter_line(sequence):
    """The 2mf line naming one filter per arm."""
    parts = []
    for arm in ARMS:
        filt = sequence.get(f"{arm}_filter")
        if filt:
            parts.append(THREEKK_FILTERS[filt][1])
    return "2mf " + " ".join(parts)


def generate_script(request, instrument):
    """The observer's script for one request.

    Built from the payload rather than stored, so a request edited after
    submission yields the corrected script.
    """
    validate_request(request, instrument)
    if instrument.name not in SCRIPT_INSTRUMENTS:
        raise ValueError(f"No observing script is built for {instrument.name}.")
    payload = request.payload
    obj = request.obj
    ra, dec = _sexagesimal(obj)

    comment = str(payload.get("comment") or "").strip()
    lines = [
        f"# {request.obj_id}, requested through SkyPortal",
        f"# window {payload['start_date']} to {payload['end_date']} UT,"
        f" priority {payload['priority']}",
    ]
    if comment:
        lines += [f"# {line}" for line in comment.splitlines()]
    lines += [
        "",
        f"2mdithersize {int(payload['dither_size'])}",
        "",
        _filter_line(payload["sequences"][0]),
        f"2mradec {ra} {dec}",
        "2mh calcz",
    ]
    if payload.get("autofocus", True):
        lines.append("2mautofocus")

    obj_line = f"2mobj {payload.get('object_name') or request.obj_id}"
    if payload.get("program_id") not in (None, ""):
        obj_line += f" {payload['program_id']}"
    lines.append(obj_line)

    for index, sequence in enumerate(payload["sequences"]):
        # The first sequence's filters are already set above, beside the slew.
        if index:
            lines += ["", _filter_line(sequence)]
        lines.append(_exposure_line(sequence))
        lines.append("2mh best")
        lines.append(
            f"2mo {sequence.get('readout_mode') or 'r4'}"
            f" {int(sequence.get('exposure_count') or 1)}"
        )

    return "\n".join(lines) + "\n"


async def _reload(request, session):
    from ..models import Allocation, FollowupRequest

    return await session.scalar(
        sa.select(FollowupRequest)
        .where(FollowupRequest.id == request.id)
        .options(
            selectinload(FollowupRequest.allocation).selectinload(
                Allocation.instrument
            ),
            selectinload(FollowupRequest.obj),
            selectinload(FollowupRequest.transactions),
        )
    )


def _redmine(request):
    """The Redmine base URL and auth headers, or None without an API key."""
    altdata = request.allocation.altdata or {}
    if not altdata.get("api_key"):
        return None
    url = (altdata.get("redmine_url") or REDMINE_URL).rstrip("/")
    return url, {"X-Redmine-API-Key": altdata["api_key"]}


def _issue_id(request):
    """The id of the issue opened for a request, read from its creation."""
    for transaction in request.transactions:
        content = (transaction.response or {}).get("content")
        try:
            return json.loads(content)["issue"]["id"]
        except (TypeError, ValueError, KeyError):
            continue
    return None


async def _issue_state(http_session, url, headers, issue_id):
    """The issue's status name and whether it is closed, or None once deleted."""
    async with http_session.get(f"{url}/issues/{issue_id}.json", headers=headers) as r:
        content = await r.text()
        if r.status == 404:
            return None
        if r.status != 200:
            raise ValueError(f"Redmine returned status {r.status}: {content}")
    status = json.loads(content)["issue"]["status"]
    # Issues carry no is_closed on this Redmine version, only the status list does.
    async with http_session.get(f"{url}/issue_statuses.json", headers=headers) as r:
        statuses = (await r.json())["issue_statuses"]
    closed = {s["id"] for s in statuses if s.get("is_closed")}
    return status["name"], status["id"] in closed


def _number(value):
    return f"{float(value):g}"


def _filter_label(filt):
    return filt.removeprefix("sdss")


def _issue_fields(request, script):
    """The issue as the observers write theirs, script included for 3KK."""
    payload = request.payload
    obj = request.obj
    name = payload.get("object_name") or request.obj_id
    comment = str(payload.get("comment") or "").strip()
    exposures = payload.get("exposures") or []
    lines = []
    if exposures:
        labels = {_filter_label(e["filter"]) for e in exposures}
        lines += [f"Filters: {''.join(sorted(labels, key='ugriz'.find))}", ""]
    lines += [
        "Notes:",
        f"* Requested through SkyPortal for {payload['start_date']} to"
        f" {payload['end_date']} UT, priority {payload['priority']}",
        *[f"* {line}" for line in comment.splitlines() if line.strip()],
    ]
    if exposures:
        lines += ["", "Exposures:"] + [
            f"* {_filter_label(e['filter'])}: {int(e['exposure_count'])}"
            f" x {_number(e['exposure_time'])} s"
            for e in exposures
        ]
    lines += [
        "",
        "Links:",
        f"{get_app_base_url()}/source/{request.obj_id}",
        "",
        "Visibility:",
        f"https://airmass.org/chart/obsid:wendelstein/object:{name}"
        f"/ra:{obj.ra:.6f}/dec:{obj.dec:.6f}",
    ]
    if script:
        lines += ["", "Observation Script:", "<pre>", script.rstrip("\n"), "</pre>"]

    values = {
        "instrument": [REDMINE_INSTRUMENTS[request.allocation.instrument.name]],
        "object_name": name,
        "ra": f"{obj.ra / 15:.2f}",
        "dec": f"{obj.dec:.2f}",
    }
    for key, default in CONSTRAINT_DEFAULTS.items():
        value = default if payload.get(key) is None else payload[key]
        values[key] = _number(value) if isinstance(default, float) else value
    custom_fields = [
        {"id": REDMINE_FIELDS[key], "value": value} for key, value in values.items()
    ]

    return {
        "subject": f"{name} (SkyPortal request {request.id})",
        "description": "\n".join(lines),
        "start_date": Time(payload["start_date"]).datetime.date().isoformat(),
        "due_date": Time(payload["end_date"]).datetime.date().isoformat(),
        "custom_fields": custom_fields,
    }


async def _sync_issue(request, session, script):
    """Open the request's Redmine issue, or bring an existing one up to date."""
    from ..models import FacilityTransaction

    url, headers = _redmine(request)
    altdata = request.allocation.altdata
    issue_id = _issue_id(request)
    issue = _issue_fields(request, script)
    if issue_id is None:
        method, issue_url = "POST", f"{url}/issues.json"
        issue.update(
            project_id=altdata.get("project_id"),
            tracker_id=altdata.get("tracker_id") or REDMINE_TRACKER_ID,
        )
    else:
        method, issue_url = "PUT", f"{url}/issues/{issue_id}.json"
        issue["notes"] = "Updated in SkyPortal."
    body = {"issue": issue}

    async with aiohttp.ClientSession() as http_session:
        async with http_session.request(
            method, issue_url, json=body, headers=headers
        ) as r:
            content = await r.text()

    request.status = "submitted" if r.status < 300 else f"rejected: {content}"
    session.add(
        FacilityTransaction(
            request=http.serialize_aiohttp_request(method, issue_url, body=body),
            response=await http.serialize_aiohttp_response(r, content),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )
    )


def _validated_script(request):
    instrument = request.allocation.instrument
    validate_request(request, instrument)
    if instrument.name in SCRIPT_INSTRUMENTS:
        return generate_script(request, instrument)
    return None


class WENDELSTEINAPI(FollowUpAPI):
    """SkyPortal interface to the Wendelstein Observatory telescopes."""

    generate_script = staticmethod(generate_script)

    @staticmethod
    async def submit(request, session, **kwargs):
        """Record a request, opening its Redmine issue when the allocation has a key.

        A 3KK script is fetched from ``/api/followup_request/{id}/script`` and
        written into the issue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        from ..models import FacilityTransaction

        request = await _reload(request, session)
        script = _validated_script(request)

        if _redmine(request):
            await _sync_issue(request, session, script)
        else:
            request.status = "submitted"
            session.add(
                FacilityTransaction(
                    request=None,
                    response=None,
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )
            )

        push_followup_refresh(
            request.obj.internal_key, request.last_modified_by_id, **kwargs
        )

    @staticmethod
    async def get(request, session, **kwargs):
        """Mark a request completed once its Redmine issue is set to Observed.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to check.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        request = await _reload(request, session)
        redmine = _redmine(request)
        issue_id = _issue_id(request)
        if redmine is None or issue_id is None:
            raise ValueError("This request has no Redmine issue.")
        url, headers = redmine

        async with aiohttp.ClientSession() as http_session:
            state = await _issue_state(http_session, url, headers, issue_id)
        if state is None:
            raise ValueError(f"Redmine issue {issue_id} no longer exists.")

        name, closed = state
        if name == REDMINE_OBSERVED_STATUS:
            request.status = "completed"
        elif closed:
            request.status = name.lower()

    @staticmethod
    async def delete(request, session, **kwargs):
        """Delete a request, closing its Redmine issue first.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        from ..models import FollowupRequest

        request = await _reload(request, session)
        obj_internal_key = request.obj.internal_key
        last_modified_by_id = request.last_modified_by_id

        redmine = _redmine(request)
        issue_id = _issue_id(request)
        if redmine is not None and issue_id is not None:
            url, headers = redmine
            altdata = request.allocation.altdata
            body = {
                "issue": {
                    "status_id": altdata.get("withdrawn_status_id")
                    or REDMINE_WITHDRAWN_STATUS_ID,
                    "notes": "Withdrawn in SkyPortal.",
                }
            }
            async with aiohttp.ClientSession() as http_session:
                state = await _issue_state(http_session, url, headers, issue_id)
                if state is not None and not state[1]:
                    async with http_session.put(
                        f"{url}/issues/{issue_id}.json", json=body, headers=headers
                    ) as r:
                        content = await r.text()
                        if r.status >= 300:
                            raise ValueError(
                                f"Could not close Redmine issue {issue_id}:"
                                f" status {r.status}: {content}"
                            )

        await session.execute(
            FollowupRequest.__table__.delete().where(
                FollowupRequest.id == request.id,
            )
        )

        push_followup_refresh(obj_internal_key, last_modified_by_id, **kwargs)

    @staticmethod
    async def update(request, session, **kwargs):
        """Re-validate an edited request and refresh its Redmine issue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        request = await _reload(request, session)
        script = _validated_script(request)
        if _redmine(request):
            await _sync_issue(request, session, script)
        else:
            request.status = "submitted"

        push_followup_refresh(
            request.obj.internal_key, request.last_modified_by_id, **kwargs
        )

    @staticmethod
    def custom_json_schema(instrument, user, **kwargs):
        """The request form, with 3KK sequences or 43cm exposures."""
        properties = {
            "object_name": {
                "title": "Object name",
                "type": "string",
                "description": "Defaults to the SkyPortal object id.",
                "pattern": f"^{OBJECT_NAME}$",
            },
            "priority": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.0,
                "maximum": 5.0,
                "title": "Priority",
            },
            "start_date": {
                "type": "string",
                "default": Time.now().isot,
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": (Time.now() + TimeDelta(7, format="jd")).isot,
            },
            "maximum_airmass": {
                "title": "Maximum airmass",
                "type": "number",
                "minimum": 1.0,
            },
            "maximum_seeing": {
                "title": "Maximum seeing [arcsec]",
                "type": "number",
                "exclusiveMinimum": 0,
            },
            "minimum_sky": {
                "title": "Minimum sky brightness [mag/arcsec^2]",
                "type": "number",
            },
            "lunar_phase": {
                "title": "Lunar phase",
                "type": "string",
                "enum": LUNAR_PHASES,
            },
            "transparency": {
                "title": "Transparency",
                "type": "string",
                "enum": TRANSPARENCIES,
            },
            "comment": {
                "type": "string",
                "title": "Note to the observer",
            },
        }
        for key, default in CONSTRAINT_DEFAULTS.items():
            properties[key]["default"] = default
        required = ["priority", "start_date", "end_date", *CONSTRAINT_DEFAULTS]
        name = getattr(instrument, "name", None)
        if name in IMAGING_INSTRUMENTS:
            filters = instrument.to_dict().get("filters") or []
            exposure = {
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "title": "Filter", "enum": filters},
                    "exposure_time": {
                        "type": "number",
                        "title": "Exposure time [s]",
                        "default": 300,
                        "exclusiveMinimum": 0,
                    },
                    "exposure_count": {
                        "type": "integer",
                        "title": "Exposures",
                        "default": 10,
                        "minimum": 1,
                    },
                },
                "required": ["filter", "exposure_time", "exposure_count"],
            }
            default_filter = (
                "sdssr" if "sdssr" in filters else next(iter(filters), None)
            )
            return {
                "type": "object",
                "properties": {
                    "exposures": {
                        "type": "array",
                        "title": "Exposures",
                        "minItems": 1,
                        "items": exposure,
                        "default": [
                            {
                                "filter": default_filter,
                                "exposure_time": 300,
                                "exposure_count": 10,
                            }
                        ],
                    },
                    **properties,
                },
                "required": ["exposures", *required],
            }
        if name not in SCRIPT_INSTRUMENTS:
            return {"type": "object", "properties": properties, "required": required}

        sequence = {
            "type": "object",
            "properties": {},
        }
        default_sequence = {}
        for arm in ARMS:
            options = filters_for_arm(instrument, arm)
            if not options:
                continue
            sequence["properties"][f"{arm}_filter"] = {
                "type": ["string", "null"],
                "title": f"{arm.capitalize()} filter",
                "enum": [None, *options],
            }
            sequence["properties"][f"{arm}_exposure_time"] = {
                "type": ["number", "null"],
                "title": f"{arm.capitalize()} exposure time [s]",
                "exclusiveMinimum": 0,
            }
            default_filter, default_exposure_time = DEFAULT_ARM_EXPOSURES[arm]
            default_sequence[f"{arm}_filter"] = (
                default_filter if default_filter in options else options[0]
            )
            default_sequence[f"{arm}_exposure_time"] = default_exposure_time
        sequence["properties"]["exposure_count"] = {
            "type": "number",
            "title": "Exposures",
            "default": 5,
            "minimum": 1,
        }
        sequence["properties"]["readout_mode"] = {
            "type": "string",
            "title": "Readout mode",
            "default": "r4",
            "pattern": f"^{SCRIPT_TOKEN}$",
        }
        default_sequence.update(exposure_count=5, readout_mode="r4")

        return {
            "type": "object",
            "properties": {
                "sequences": {
                    "type": "array",
                    "title": "Sequences",
                    "minItems": 1,
                    "items": sequence,
                    "default": [default_sequence],
                },
                "dither_size": {
                    "title": "Dither size",
                    "type": "number",
                    "default": 275,
                },
                "autofocus": {
                    "title": "Autofocus after the slew",
                    "type": "boolean",
                    "default": True,
                },
                "program_id": {
                    "title": "Program id",
                    "type": ["string", "null"],
                    "pattern": f"^{SCRIPT_TOKEN}$",
                },
                **properties,
            },
            "required": ["sequences", "dither_size", *required],
        }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "redmine_url": {
                "type": "string",
                "title": "Redmine URL",
                "default": REDMINE_URL,
            },
            "api_key": {
                "type": "string",
                "title": "Redmine API key",
            },
            "project_id": {
                "type": "string",
                "title": "Redmine project identifier",
            },
            "tracker_id": {
                "type": "integer",
                "title": "Redmine tracker id",
                "default": REDMINE_TRACKER_ID,
            },
            "withdrawn_status_id": {
                "type": "integer",
                "title": "Redmine status id of withdrawn requests",
                "default": REDMINE_WITHDRAWN_STATUS_ID,
            },
        },
    }

    ui_json_schema = {"comment": {"ui:widget": "textarea"}}

    alias_lookup = {
        "dither_size": "Dither size",
        "readout_mode": "Readout mode",
        "exposure_count": "Exposures",
        "exposure_time": "Exposure time",
        "program_id": "Program id",
        "maximum_airmass": "Max airmass",
        "maximum_seeing": "Max seeing",
        "minimum_sky": "Min sky",
        "lunar_phase": "Lunar phase",
    }
