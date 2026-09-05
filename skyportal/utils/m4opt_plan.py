"""Observation plans from M4OPT, as an alternative to gwemopt.

M4OPT schedules by solving a MILP rather than greedily, and needs a solver
(SCIP, Gurobi or CPLEX) that SkyPortal does not depend on. It is therefore run
as a subprocess against its own environment rather than imported, which also
keeps a solver that hangs or dies out of the app process.
"""

__all__ = [
    "M4OPTError",
    "generate_m4opt_plan",
    "m4opt_enabled",
    "read_schedule",
    "mission_for",
    "publish_plan",
    "run_m4opt",
    "schedule_rows",
]

import os
import subprocess
import tempfile
from pathlib import Path

import astropy.units as u
import ligo.skymap.io
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import QTable
from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()
log = make_log("m4opt")


class M4OPTError(Exception):
    """M4OPT could not produce a schedule."""


def _config():
    return cfg.get("app.m4opt") or {}


def m4opt_enabled():
    return bool(_config().get("enabled"))


def mission_for(instrument_name):
    """The M4OPT mission modelling this instrument, or None if unmapped.

    M4OPT models a specific telescope (its field of regard, optics and sky
    grid), so an instrument it has no mission for cannot be scheduled with it.
    """
    missions = _config().get("missions") or {}
    return missions.get(instrument_name)


def write_skymap(localization, path, event_time):
    """Write a localization as the multi-order FITS file M4OPT reads.

    M4OPT takes the trigger time from the sky map's `gps_time` header rather
    than from an argument, so it has to be written even though SkyPortal knows
    it independently.
    """
    ligo.skymap.io.write_sky_map(
        str(path), localization.table, moc=True, gps_time=event_time.gps
    )
    return path


def run_m4opt(
    localization,
    mission,
    *,
    start_time,
    end_time,
    event_time,
    bandpasses=(),
    visits=None,
    exposure_time=None,
    max_fields=None,
    workdir=None,
):
    """Run `m4opt schedule` and return the schedule table it wrote.

    Times are absolute; M4OPT works relative to the event, so the window is
    passed as a delay from the trigger plus a deadline.
    """
    config = _config()
    delay = (start_time - event_time).to(u.s)
    deadline = (end_time - event_time).to(u.s)
    if deadline <= delay:
        raise M4OPTError("The observing window ends before it starts.")

    with tempfile.TemporaryDirectory(dir=workdir) as tmp:
        skymap_path = write_skymap(
            localization, Path(tmp) / "skymap.multiorder.fits", event_time
        )
        schedule_path = Path(tmp) / "schedule.ecsv"

        command = [
            config.get("executable") or "m4opt",
            "schedule",
            str(skymap_path),
            str(schedule_path),
            f"--mission={mission}",
            f"--delay={delay.value}s",
            f"--deadline={deadline.value}s",
            f"--nside={config.get('nside', 128)}",
            f"--timelimit={config.get('timelimit', 300)}s",
            f"--max-fields={int(max_fields or config.get('max_fields', 50))}",
        ]
        # Repeat the option rather than joining: M4OPT cycles visits through
        # the list and groups them into single-bandpass blocks.
        command.extend(f"--bandpass={bandpass}" for bandpass in bandpasses)
        if visits:
            command.append(f"--visits={int(visits)}")
        if exposure_time:
            # A fixed exposure means the adaptive path is off, where M4OPT's
            # open-source solver is weakest.
            command.append(f"--exptime-min={float(exposure_time)}s")
            command.append(f"--exptime-max={float(exposure_time)}s")
            command.append("--no-appmag-dist")
        command.extend(config.get("extra_args") or [])

        env = None
        if solver := config.get("solver"):
            # Explicit, so an incidentally-installed solver cannot take over.
            env = {**os.environ, "M4OPT_SOLVER": str(solver)}

        log(f"Running: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=config.get("subprocess_timeout", 3600),
                env=env,
            )
        except FileNotFoundError as e:
            raise M4OPTError(f"M4OPT executable not found: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise M4OPTError("M4OPT timed out before writing a schedule.") from e

        if result.returncode != 0:
            raise M4OPTError(
                f"M4OPT exited {result.returncode}: {result.stderr.strip()[-2000:]}"
            )
        if not schedule_path.exists():
            raise M4OPTError("M4OPT reported success but wrote no schedule.")
        return read_schedule(schedule_path)


def _bandpass(row, table):
    """The band of one observation, or "" for a schedule with no bands."""
    if "bandpass" not in table.colnames:
        return ""
    value = row["bandpass"]
    return "" if value is np.ma.masked else str(value)


def read_schedule(path):
    """Read a schedule M4OPT wrote.

    QTable, not Table: durations have to come back as quantities, or converting
    them to seconds meets a dimensionless float instead.
    """
    return QTable.read(path, format="ascii.ecsv")


def schedule_rows(table, fields, *, separation=None):
    """Pair each observation in an M4OPT schedule with the field it points at.

    Yields `(field, obstime, exposure_time, bandpass)`. Missions with their own
    sky grid identifiers report one per observation, which is the same number
    SkyPortal stores and so joins exactly. Missions that generate their grid
    geometrically report none, and those fall back to matching on position.
    """
    observations = table[table["action"] == "observe"]
    if len(observations) == 0:
        return

    if "field_id" in table.colnames:
        # Not field_index + 1: ZTF's identifiers have gaps, so the grid row and
        # the identifier disagree over most of the sky.
        by_field_id = {int(field.field_id): field for field in fields}
        for row in observations:
            field = by_field_id.get(int(row["field_id"]))
            if field is None:
                log(f"Instrument has no field {row['field_id']}; dropping it.")
                continue
            yield (
                field,
                Time(row["start_time"]).datetime,
                float(u.Quantity(row["duration"]).to_value(u.s)),
                _bandpass(row, table),
            )
        return

    if separation is None:
        separation = float(_config().get("match_separation_deg", 1.0))
    field_coords = SkyCoord(
        [field.ra for field in fields] * u.deg,
        [field.dec for field in fields] * u.deg,
    )
    targets = SkyCoord(observations["target_coord"])
    index, offset, _ = targets.match_to_catalog_sky(field_coords)

    for row, field_index, sep in zip(observations, np.atleast_1d(index), offset):
        if sep.to_value(u.deg) > separation:
            log(
                f"No field within {separation} deg of {row['target_coord']}; "
                "dropping that exposure."
            )
            continue
        yield (
            fields[int(field_index)],
            Time(row["start_time"]).datetime,
            float(u.Quantity(row["duration"]).to_value(u.s)),
            _bandpass(row, table),
        )


def publish_plan(session, plans, requests):
    """Recompute the plan statistics and tell the front end, as gwemopt does.

    Imported here rather than at module scope: observation_plan imports this
    module back, so importing it eagerly closes a cycle.
    """
    from baselayer.app.flow import Flow

    from .observation_plan import generate_observation_plan_statistics

    generate_observation_plan_statistics(
        [plan.id for plan in plans], [request.id for request in requests], session
    )
    Flow().push(
        "*",
        "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
        payload={"gcnEvent_dateobs": requests[0].gcnevent.dateobs},
    )


def generate_m4opt_plan(session, plans, requests):
    """Fill in observation plans with M4OPT and mark them complete.

    Mirrors the tail of `generate_plan`: same PlannedObservation rows, same
    statistics and refresh, so the rest of SkyPortal cannot tell which
    scheduler produced a plan.
    """
    import sqlalchemy as sa

    from ..models import InstrumentField, PlannedObservation

    ids = ",".join(str(plan.id) for plan in plans)
    try:
        for plan, request in zip(plans, requests):
            instrument = request.instrument
            mission = mission_for(instrument.name)
            if mission is None:
                raise M4OPTError(
                    f"M4OPT has no mission configured for {instrument.name}."
                )

            payload = request.payload or {}
            event_time = Time(request.gcnevent.dateobs, format="datetime", scale="utc")
            table = run_m4opt(
                request.localization,
                mission,
                start_time=Time(payload["start_date"], format="iso", scale="utc"),
                end_time=Time(payload["end_date"], format="iso", scale="utc"),
                event_time=event_time,
                bandpasses=[
                    f.strip()
                    for f in (payload.get("filters") or "").split(",")
                    if f.strip()
                ],
                visits=payload.get("visits"),
                max_fields=payload.get("max_fields"),
                exposure_time=payload.get("exposure_time"),
            )

            fields = (
                session.scalars(
                    sa.select(InstrumentField).where(
                        InstrumentField.instrument_id == instrument.id
                    )
                )
                .unique()
                .all()
            )
            if not fields:
                raise M4OPTError(f"{instrument.name} has no fields to schedule.")

            overhead = (instrument.configuration_data or {}).get(
                "overhead_per_exposure", 0.0
            )
            planned = [
                PlannedObservation(
                    obstime=obstime,
                    dateobs=request.gcnevent.dateobs,
                    field_id=field.id,
                    exposure_time=exposure_time,
                    weight=1.0,
                    filt=bandpass or (payload.get("filters") or "").split(",")[0],
                    instrument_id=instrument.id,
                    planned_observation_id=index,
                    observation_plan_id=plan.id,
                    overhead_per_exposure=overhead,
                )
                for index, (field, obstime, exposure_time, bandpass) in enumerate(
                    schedule_rows(table, fields)
                )
            ]
            if not planned:
                raise M4OPTError("M4OPT returned a schedule with no observations.")

            session.add_all(planned)
            plan.status = "complete"
            session.merge(plan)

        session.commit()
        log(f"Finished M4OPT plan(s) for ID(s): {ids}")

        publish_plan(session, plans, requests)
    except Exception as e:
        log(f"Failed to generate M4OPT plan(s) for ID(s): {ids}: {e}")
        session.rollback()
        for request in requests:
            request.status = f"failed: {e}"
            session.merge(request)
        for plan in plans:
            plan.status = "failed"
            session.merge(plan)
        session.commit()
