"""Wendelstein 2m (Fraunhofer) observing scripts.

The telescope is operated by hand rather than from a queue, so a request here
produces a script the observer runs at the telescope. ``submit`` validates and
records the request; the script itself is rendered on demand from the payload
by ``generate_script``, so editing a request changes its script.
"""

import re

import sqlalchemy as sa
from astropy.coordinates import SkyCoord
from astropy.time import Time, TimeDelta
from sqlalchemy.orm import selectinload

from baselayer.app.env import load_env

from . import FollowUpAPI
from .interface import push_followup_refresh

env, cfg = load_env()

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

SCRIPT_TOKEN = r"[^\s\x00-\x1f\x7f]*"
SCRIPT_TOKEN_PARAMS = [
    "object_name",
    "program_id",
    "start_date",
    "end_date",
    "priority",
]

SUPPORTED_INSTRUMENTS = {"Wendelstein 3KK"}


def filters_for_arm(instrument, arm):
    """The instrument's filters that sit in one 3KK arm."""
    return [
        f
        for f in (instrument.to_dict().get("filters") or [])
        if THREEKK_FILTERS.get(f, (None, None))[0] == arm
    ]


def validate_request(request, instrument):
    """Check a payload before a script is built from it."""
    instrument_name = getattr(instrument, "name", None)
    if instrument_name not in SUPPORTED_INSTRUMENTS:
        raise ValueError(
            f"Wendelstein scripts are implemented for "
            f"{', '.join(sorted(SUPPORTED_INSTRUMENTS))}, not {instrument_name}."
        )

    payload = request.payload or {}
    for param in ["sequences", "dither_size", "start_date", "end_date", "priority"]:
        if param not in payload:
            raise ValueError(f"Parameter {param} required.")

    for param in SCRIPT_TOKEN_PARAMS:
        value = payload.get(param)
        if value is not None and not re.fullmatch(SCRIPT_TOKEN, str(value)):
            raise ValueError(
                f"Parameter {param} cannot contain spaces or control characters."
            )

    sequences = payload["sequences"]
    if not isinstance(sequences, list) or not sequences:
        raise ValueError("At least one sequence is required.")

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
        readout_mode = sequence.get("readout_mode")
        if readout_mode is not None and not re.fullmatch(
            SCRIPT_TOKEN, str(readout_mode)
        ):
            raise ValueError(
                f"Sequence {index}: readout mode cannot contain spaces or control"
                " characters."
            )


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


class WENDELSTEINAPI(FollowUpAPI):
    """SkyPortal interface to the Wendelstein 2m (Fraunhofer) telescope."""

    generate_script = staticmethod(generate_script)

    @staticmethod
    async def submit(request, session, **kwargs):
        """Record a request and the script it produces.

        Nothing is sent upstream: the telescope takes no queue, so the script
        is fetched from ``/api/followup_request/{id}/script`` and run by the
        observer.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        from ..models import Allocation, FacilityTransaction, FollowupRequest

        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )

        # Raises on a payload no script can be built from, so a request never
        # reaches the observer in a state that fails at the telescope.
        generate_script(request, request.allocation.instrument)
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
    async def delete(request, session, **kwargs):
        """Delete a request.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        from ..models import FollowupRequest

        obj_internal_key = request.obj.internal_key
        last_modified_by_id = request.last_modified_by_id

        await session.execute(
            FollowupRequest.__table__.delete().where(
                FollowupRequest.id == request.id,
            )
        )

        push_followup_refresh(obj_internal_key, last_modified_by_id, **kwargs)

    @staticmethod
    async def update(request, session, **kwargs):
        """Re-validate an edited request, whose script is rebuilt on download.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        from ..models import Allocation, FollowupRequest

        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )
        generate_script(request, request.allocation.instrument)
        request.status = "submitted"

        push_followup_refresh(
            request.obj.internal_key, request.last_modified_by_id, **kwargs
        )

    @staticmethod
    def custom_json_schema(instrument, user, **kwargs):
        """The request form, whose filter menus come from the instrument."""
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
                "object_name": {
                    "title": "Object name in the script",
                    "type": "string",
                    "description": "Defaults to the SkyPortal object id.",
                    "pattern": f"^{SCRIPT_TOKEN}$",
                },
                "program_id": {
                    "title": "Program id",
                    "type": ["string", "null"],
                    "pattern": f"^{SCRIPT_TOKEN}$",
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
                    "pattern": f"^{SCRIPT_TOKEN}$",
                },
                "end_date": {
                    "type": "string",
                    "title": "End Date (UT)",
                    "default": (Time.now() + TimeDelta(7, format="jd")).isot,
                    "pattern": f"^{SCRIPT_TOKEN}$",
                },
                "comment": {
                    "type": "string",
                    "title": "Note to the observer",
                },
            },
            "required": [
                "sequences",
                "dither_size",
                "priority",
                "start_date",
                "end_date",
            ],
        }

    ui_json_schema = {"comment": {"ui:widget": "textarea"}}

    alias_lookup = {
        "dither_size": "Dither size",
        "readout_mode": "Readout mode",
        "exposure_count": "Exposures",
        "program_id": "Program id",
    }
