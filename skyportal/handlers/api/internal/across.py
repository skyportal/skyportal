import asyncio
from datetime import UTC, datetime, timedelta, timezone

import aiohttp
import numpy as np
import sqlalchemy as sa
from astropy import time as ap_time
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ....models import Instrument, Obj, Telescope
from ....utils.parse import get_list_typed
from ...base import BaseHandler

env, cfg = load_env()

# NASA ACROSS public API (unauthenticated GET). See
# https://across.sciencecloud.nasa.gov and https://api.across.sciencecloud.nasa.gov/v1/docs
ACROSS_API_URL = (
    cfg.get("across.api_url") or "https://api.across.sciencecloud.nasa.gov/v1"
).rstrip("/")
# hi_res=true routinely exceeds the ACROSS gateway timeout; low-res is fast.
ACROSS_HI_RES = bool(cfg.get("across.hi_res", False))
ACROSS_TIMEOUT = float(cfg.get("across.request_timeout", 20.0))

DEFAULT_MIN_VIS = 300  # seconds; ignore windows shorter than 5 minutes
MAX_TELESCOPES = 8
MAX_WINDOW_DAYS = 14  # long windows time out on the ACROSS side

# Ground visibility (astroplan): source below the airmass limit at night,
# matching the airmass/hours-below panels so the two agree.
GROUND_MAX_AIRMASS = float(cfg.get("misc.hours_below_airmass_threshold", 2.9) or 2.9)
GROUND_STEP_MINUTES = 10


def _parse_windows(payload):
    """Normalize an ACROSS visibility payload to a list of window dicts."""
    windows = []
    for w in payload.get("visibility_windows", []):
        begin = w["window"]["begin"]["datetime"]
        end = w["window"]["end"]["datetime"]
        duration_s = w.get("max_visibility_duration")
        if duration_s is None:
            duration_s = (
                datetime.fromisoformat(end) - datetime.fromisoformat(begin)
            ).total_seconds()
        reason = w.get("constraint_reason") or {}
        windows.append(
            {
                "begin": begin,
                "end": end,
                "duration_hr": float(duration_s) / 3600.0,
                "start_reason": reason.get("start_reason"),
                "end_reason": reason.get("end_reason"),
            }
        )
    return windows


def _merge(intervals):
    """Merge overlapping (begin, end) datetime intervals."""
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _intersect(a, b):
    a, b = _merge(a), _merge(b)
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if end > start:
            out.append((start, end))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def _joint_windows(single):
    """Locally intersect per-facility windows. Requires 2+ with windows."""
    have = [s for s in single if s["windows"]]
    if len(have) < 2:
        return []
    sets = [
        [
            (
                datetime.fromisoformat(w["begin"]),
                datetime.fromisoformat(w["end"]),
            )
            for w in s["windows"]
        ]
        for s in have
    ]
    current = _merge(sets[0])
    for s in sets[1:]:
        current = _intersect(current, s)
        if not current:
            break
    return [
        {
            "begin": b.isoformat(),
            "end": e.isoformat(),
            "duration_hr": (e - b).total_seconds() / 3600.0,
            "start_reason": None,
            "end_reason": None,
        }
        for b, e in current
    ]


def _compute_ground_windows(telescopes, ra, dec, begin, end):
    """Blocking astroplan visibility (source above GROUND_MIN_ALTITUDE at night)
    for ground telescopes, over a time grid. Runs in a thread executor.
    Returns {telescope_id: {"windows": [...], "error": str|None}}."""
    import astropy.units as u
    from astroplan import (
        AirmassConstraint,
        AtNightConstraint,
        FixedTarget,
        Observer,
        is_event_observable,
    )
    from astropy.coordinates import SkyCoord

    target = FixedTarget(coord=SkyCoord(ra * u.deg, dec * u.deg))
    n_steps = int((end - begin).total_seconds() / (GROUND_STEP_MINUTES * 60)) + 1
    times = ap_time.Time(begin) + np.arange(n_steps) * GROUND_STEP_MINUTES * u.min
    grid = [t.replace(tzinfo=None) for t in times.datetime]
    # Airmass below the site limit while the Sun is down, matching the airmass
    # panels (AtNightConstraint default: Sun below the horizon).
    constraints = [
        AirmassConstraint(max=GROUND_MAX_AIRMASS),
        AtNightConstraint(),
    ]

    out = {}
    for tel in telescopes:
        try:
            observer = Observer(
                longitude=tel["lon"] * u.deg,
                latitude=tel["lat"] * u.deg,
                elevation=(tel["elevation"] or 0.0) * u.m,
            )
            mask = is_event_observable(constraints, observer, target, times=times)[0]
            windows = []
            run_start = None
            for i, ok in enumerate(mask):
                if ok and run_start is None:
                    run_start = grid[i]
                elif not ok and run_start is not None:
                    run_end = grid[i - 1]
                    windows.append((run_start, run_end))
                    run_start = None
            if run_start is not None:
                windows.append((run_start, grid[-1]))
            out[tel["id"]] = {
                "windows": [
                    {
                        "begin": b.isoformat(),
                        "end": e.isoformat(),
                        "duration_hr": (e - b).total_seconds() / 3600.0,
                        "start_reason": "Airmass/night",
                        "end_reason": "Airmass/night",
                    }
                    for b, e in windows
                    if (e - b).total_seconds() >= DEFAULT_MIN_VIS
                ],
                "error": None,
            }
        except Exception as e:
            out[tel["id"]] = {"windows": [], "error": str(e)}
    return out


class AcrossInstrumentsHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        description: |
            List the SkyPortal instruments backed by a NASA ACROSS instrument
            (i.e. with an `across_id`), for use in ACROSS visibility queries.
            Populate these with tools/load_across_instruments.py.
        tags:
            - sources
        responses:
            200:
              content:
                application/json:
                  schema:
                    type: object
            400:
              content:
                application/json:
                  schema: Error
        """
        async with self.AsyncSession() as session:
            stmt = (
                Instrument.select(session.user_or_token)
                .where(Instrument.across_id.isnot(None))
                .options(sa.orm.joinedload(Instrument.telescope))
            )
            instruments = (await session.scalars(stmt)).unique().all()
            data = [
                {
                    "id": inst.id,
                    "name": inst.name,
                    "telescope_id": inst.telescope_id,
                    "telescope_name": inst.telescope.name if inst.telescope else None,
                }
                for inst in instruments
            ]
            data.sort(key=lambda x: (x["telescope_name"] or "", x["name"]))
            return self.success(data=data)


class AcrossJointVisibilityHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str):
        """
        ---
        description: |
            Compute single- and joint-observatory visibility windows for a
            source across a set of SkyPortal telescopes. Ground telescopes are
            computed locally (source above 30 deg at night); ACROSS-backed
            (space) telescopes use the NASA ACROSS visibility calculator. Joint
            windows (when every selected facility can observe simultaneously)
            are the local intersection of the per-facility windows.
        tags:
            - sources
        parameters:
            - in: path
              name: obj_id
              required: true
              schema:
                type: string
            - in: query
              name: telescopeIds
              required: true
              schema:
                type: array
              description: SkyPortal telescope IDs (ground and/or ACROSS-backed).
            - in: query
              name: begin
              schema:
                type: string
              description: ISO start time (default now).
            - in: query
              name: end
              schema:
                type: string
              description: ISO end time (default begin + 3 days).
        responses:
            200:
              content:
                application/json:
                  schema:
                    type: object
            400:
              content:
                application/json:
                  schema: Error
        """
        telescopes_arg = self.get_query_argument("telescopeIds", None)
        if not telescopes_arg:
            return self.error("telescopeIds is required")
        try:
            telescope_ids = get_list_typed(
                telescopes_arg, int, "Invalid telescopeIds format"
            )
        except Exception as e:
            return self.error(str(e))
        if len(telescope_ids) > MAX_TELESCOPES:
            return self.error(f"At most {MAX_TELESCOPES} telescopes may be selected")

        begin_arg = self.get_query_argument("begin", None)
        end_arg = self.get_query_argument("end", None)
        try:
            begin = (
                ap_time.Time(begin_arg, format="isot").datetime
                if begin_arg
                else datetime.now(UTC).replace(tzinfo=None)
            )
            end = (
                ap_time.Time(end_arg, format="isot").datetime
                if end_arg
                else begin + timedelta(days=3)
            )
        except ValueError as e:
            return self.error(f"Invalid time format: {e.args[0]}")
        if begin.tzinfo is not None:
            begin = begin.astimezone(UTC).replace(tzinfo=None)
        if end.tzinfo is not None:
            end = end.astimezone(UTC).replace(tzinfo=None)
        if end <= begin:
            return self.error("end must be after begin")
        if (end - begin) > timedelta(days=MAX_WINDOW_DAYS):
            return self.error(
                f"Time window may not exceed {MAX_WINDOW_DAYS} days "
                "(the ACROSS calculator times out on longer ranges)"
            )

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Could not load object with ID {obj_id}")
            ra, dec = obj.ra, obj.dec

            telescopes = (
                await session.scalars(
                    Telescope.select(session.user_or_token)
                    .where(Telescope.id.in_(telescope_ids))
                    .options(sa.orm.selectinload(Telescope.instruments))
                )
            ).all()

            ground, space = [], []  # ground: dicts; space: (tel, across_id)
            for tel in telescopes:
                across_inst = next((i for i in tel.instruments if i.across_id), None)
                if across_inst is not None:
                    space.append((tel, across_inst.across_id))
                elif tel.fixed_location and tel.lat is not None and tel.lon is not None:
                    ground.append(
                        {
                            "id": tel.id,
                            "name": tel.nickname or tel.name,
                            "lat": tel.lat,
                            "lon": tel.lon,
                            "elevation": tel.elevation,
                        }
                    )
            # preserve request order with a name/kind lookup
            order = {tid: idx for idx, tid in enumerate(telescope_ids)}
            names = {tel.id: (tel.nickname or tel.name) for tel in telescopes}

        if not ground and not space:
            return self.error(
                "None of the selected telescopes support visibility "
                "(need a fixed location or an ACROSS instrument)"
            )

        base_params = {
            "ra": ra,
            "dec": dec,
            "date_range_begin": begin.replace(microsecond=0).isoformat(),
            "date_range_end": end.replace(microsecond=0).isoformat(),
            "hi_res": "true" if ACROSS_HI_RES else "false",
            "min_visibility_duration": DEFAULT_MIN_VIS,
        }
        timeout = aiohttp.ClientTimeout(total=ACROSS_TIMEOUT)

        async def fetch_space(http, tel, across_id):
            try:
                async with http.get(
                    f"{ACROSS_API_URL}/tools/visibility-calculator/windows/{across_id}",
                    params=base_params,
                    headers={"accept": "application/json"},
                ) as r:
                    r.raise_for_status()
                    payload = await r.json()
                return tel.id, {"windows": _parse_windows(payload), "error": None}
            except Exception as e:
                return tel.id, {"windows": [], "error": str(e)}

        single = []
        try:
            # Ground (astroplan, in executor) and space (ACROSS HTTP) in parallel.
            ground_future = (
                IOLoop.current().run_in_executor(
                    None, _compute_ground_windows, ground, ra, dec, begin, end
                )
                if ground
                else None
            )
            space_results = {}
            if space:
                async with aiohttp.ClientSession(timeout=timeout) as http:
                    for tid, res in await asyncio.gather(
                        *[fetch_space(http, tel, aid) for tel, aid in space]
                    ):
                        space_results[tid] = res
            ground_results = await ground_future if ground_future else {}
        except Exception as e:
            return self.error(f"Visibility computation failed: {e}")

        merged = {**ground_results, **space_results}
        kinds = {
            **{t["id"]: "ground" for t in ground},
            **{t.id: "space" for t, _ in space},
        }
        for tid in sorted(merged, key=lambda t: order.get(t, 0)):
            single.append(
                {
                    "id": tid,
                    "name": names.get(tid),
                    "kind": kinds.get(tid),
                    "windows": merged[tid]["windows"],
                    "error": merged[tid]["error"],
                }
            )

        return self.success(
            data={
                "begin": begin.isoformat(),
                "end": end.isoformat(),
                "single": single,
                "joint": _joint_windows(single),
                "ground_max_airmass": GROUND_MAX_AIRMASS,
            }
        )
