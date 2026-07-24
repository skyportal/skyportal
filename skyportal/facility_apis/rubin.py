import functools
import hashlib

import numpy as np
import pandas as pd
import requests
from astropy.time import Time
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.log import make_log

from . import MMAAPI

env, cfg = load_env()

log = make_log("facility_apis/rubin")

# Default public Rubin ObsLocTAP (IVOA Observation Locator TAP) service.
# Publishes the scheduler forecast and the record of executed visits; requires
# no authentication (see DMTN-263). Overridable per-allocation via
# altdata["endpoint"].
DEFAULT_OBSLOCTAP_URL = "https://usdf-rsp.slac.stanford.edu/obsloctap"

# Map an ObsLocTAP visit (bandpass given as em_min/em_max in meters) to an
# sncosmo LSST bandpass name using the band's effective wavelength (nm).
LSST_BAND_WAVELENGTHS_NM = {
    "lsstu": 368.0,
    "lsstg": 478.0,
    "lsstr": 622.0,
    "lssti": 754.0,
    "lsstz": 869.0,
    "lssty": 971.0,
}

# ObsLocTAP is a schedule/record: it carries no measured image depth. For the
# executed-observation ingestion (which requires a limiting magnitude) we fall
# back to the nominal LSST single-visit 5-sigma depths per band. These are
# design values, adequate for coverage/livetime bookkeeping, not photometry.
LSST_NOMINAL_M5 = {
    "lsstu": 23.9,
    "lsstg": 25.0,
    "lsstr": 24.7,
    "lssti": 24.0,
    "lsstz": 23.3,
    "lssty": 22.1,
}


def _visit_id(t_min, ra, dec, band):
    """Stable 56-bit id for a visit. ObsLocTAP has no unique per-visit key
    (obs_id repeats the survey name) and a scheduler batch can share one t_min
    across many pointings, so we key on (time, position, filter). Identical
    records collapse to one id (de-dup); distinct visits stay distinct."""
    key = f"{float(t_min):.8f}_{float(ra):.6f}_{float(dec):.6f}_{band}".encode()
    return int.from_bytes(hashlib.blake2b(key, digest_size=7).digest(), "big")


def _band_from_em(em_min, em_max):
    """Return the LSST sncosmo band name closest to a visit's central
    wavelength, given em_min/em_max in meters."""
    try:
        central_nm = 0.5 * (float(em_min) + float(em_max)) * 1e9
    except (TypeError, ValueError):
        return None
    return min(
        LSST_BAND_WAVELENGTHS_NM,
        key=lambda band: abs(LSST_BAND_WAVELENGTHS_NM[band] - central_nm),
    )


def fetch_obsloctap_schedule(endpoint, start_mjd, end_mjd):
    """Fetch ObsLocTAP visits between two MJDs.

    We page night-by-night (1-day MJD windows) and concatenate to bound each
    response size, mirroring ZTF's per-JD depot loop.

    Parameters
    ----------
    endpoint : str
        Base URL of the ObsLocTAP service (without trailing "/schedule").
    start_mjd, end_mjd : float
        Bounds of the requested window in MJD.

    Returns
    -------
    list of dict
        Raw ObsLocTAP obsplan records.
    """
    url = f"{endpoint.rstrip('/')}/schedule"
    records = []
    nights = np.arange(np.floor(start_mjd), np.ceil(end_mjd) + 1)
    for night in nights:
        try:
            r = requests.get(
                url,
                params={"start": float(night), "end": float(night) + 1},
                timeout=60,
            )
        except requests.RequestException as e:
            log(f"Error querying ObsLocTAP for MJD {night}: {e}")
            continue
        if r.status_code != 200:
            log(f"ObsLocTAP returned {r.status_code} for MJD {night}")
            continue
        try:
            night_records = r.json()
        except ValueError:
            log(f"Could not parse ObsLocTAP response for MJD {night}")
            continue
        if isinstance(night_records, list):
            records.extend(night_records)
    return records


def _visits_to_dataframe(records, statuses):
    """Filter ObsLocTAP records by execution status and normalize the columns
    both ingestion helpers share (position, time, band, exposure)."""
    rows = []
    for rec in records:
        if rec.get("execution_status") not in statuses:
            continue
        t_min = rec.get("t_min")
        if t_min is None:
            continue
        band = _band_from_em(rec.get("em_min"), rec.get("em_max"))
        rows.append(
            {
                "RA": rec.get("s_ra"),
                "Dec": rec.get("s_dec"),
                "t_min": float(t_min),
                "t_max": rec.get("t_max"),
                "exposure_time": rec.get("t_exptime"),
                "filter": band,
                "target_name": rec.get("target_name") or None,
            }
        )
    return pd.DataFrame(rows)


def fetch_rubin_executed(instrument_id, endpoint, start_mjd, end_mjd):
    """Fetch executed (Performed) Rubin visits and commit them as
    ExecutedObservations."""
    records = fetch_obsloctap_schedule(endpoint, start_mjd, end_mjd)
    df = _visits_to_dataframe(records, statuses={"Performed"})
    if df.empty:
        log(
            f"No performed Rubin observations for instrument {instrument_id} "
            f"between MJD {start_mjd} and {end_mjd}"
        )
        return

    df["observation_id"] = df.apply(
        lambda r: _visit_id(r["t_min"], r["RA"], r["Dec"], r["filter"]), axis=1
    )
    df["obstime"] = Time(df["t_min"].to_numpy(), format="mjd").jd
    df["limmag"] = df["filter"].map(LSST_NOMINAL_M5).fillna(0.0)
    df["processed_fraction"] = 1.0
    df = df.drop(columns=["t_min", "t_max"])

    from skyportal.handlers.api.observation import add_observations

    add_observations(instrument_id, df)


def fetch_rubin_queued(instrument_id, endpoint, start_date, end_date):
    """Fetch planned (Scheduled) Rubin visits and commit them as
    QueuedObservations."""
    start_mjd = Time(start_date, format="datetime").mjd
    end_mjd = Time(end_date, format="datetime").mjd
    records = fetch_obsloctap_schedule(endpoint, start_mjd, end_mjd)
    df = _visits_to_dataframe(records, statuses={"Scheduled", "Planned"})
    if df.empty:
        log(f"No queued Rubin observations for instrument {instrument_id}")
        return []

    # Keep only visits whose planned start falls in the requested window, and
    # drop records repeated across paged night windows.
    df = df[(df["t_min"] >= start_mjd) & (df["t_min"] <= end_mjd)]
    df = df.drop_duplicates(subset=["RA", "Dec", "t_min", "filter"])
    if df.empty:
        return []

    obstimes = Time(df["t_min"].to_numpy(), format="mjd")
    tmax = df["t_max"].where(df["t_max"].notna(), df["t_min"])
    validity_end = Time(tmax.to_numpy(dtype=float), format="mjd")

    df["instrument_id"] = instrument_id
    df["obstime"] = obstimes.datetime
    df["validity_window_start"] = obstimes.datetime
    df["validity_window_end"] = validity_end.datetime
    # One queue per UTC night, e.g. "Rubin 2026-07-24".
    df["queue_name"] = [f"Rubin {t.datetime.date().isoformat()}" for t in obstimes]
    df = df.drop(columns=["t_min", "t_max"])

    from skyportal.handlers.api.observation import add_queued_observations

    add_queued_observations(instrument_id, df)
    return sorted(set(df["queue_name"]))


class RUBINMMAAPI(MMAAPI):
    """Interface to Rubin planned/executed observations via ObsLocTAP.

    Unlike broker APIs that submit to a remote queue, this pulls the public
    Rubin schedule: ``queued`` ingests the scheduler forecast (planned visits)
    and ``retrieve`` ingests the record of executed (performed) visits. Both
    are anonymous — no allocation token is required.
    """

    @staticmethod
    async def retrieve(allocation, start_date, end_date):
        """Retrieve executed (performed) observations from Rubin ObsLocTAP.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation for the Rubin/LSST instrument.
        start_date : datetime.datetime
            Minimum observation time.
        end_date : datetime.datetime
            Maximum observation time.
        """
        altdata = allocation.altdata or {}
        endpoint = altdata.get("endpoint", DEFAULT_OBSLOCTAP_URL)

        start_mjd = Time(start_date, format="datetime").mjd
        end_mjd = Time(end_date, format="datetime").mjd
        if start_mjd > end_mjd:
            raise ValueError("start_date must be before end_date.")

        fetch_obs = functools.partial(
            fetch_rubin_executed,
            allocation.instrument.id,
            endpoint,
            start_mjd,
            end_mjd,
        )
        IOLoop.current().run_in_executor(None, fetch_obs)

    @staticmethod
    async def queued(allocation, start_date=None, end_date=None, queues_only=False):
        """Retrieve planned (scheduled) observations from Rubin ObsLocTAP.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation for the Rubin/LSST instrument.
        start_date : datetime.datetime
            Minimum planned observation time.
        end_date : datetime.datetime
            Maximum planned observation time.
        queues_only : bool
            If True, return queue names without committing observations.
        """
        altdata = allocation.altdata or {}
        endpoint = altdata.get("endpoint", DEFAULT_OBSLOCTAP_URL)

        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date are required.")

        if queues_only:
            # Peek at the current forecast to enumerate nightly queue names
            # without committing observations.
            start_mjd = Time(start_date, format="datetime").mjd
            end_mjd = Time(end_date, format="datetime").mjd
            records = fetch_obsloctap_schedule(endpoint, start_mjd, end_mjd)
            df = _visits_to_dataframe(records, statuses={"Scheduled", "Planned"})
            if df.empty:
                return []
            obstimes = Time(df["t_min"].to_numpy(), format="mjd")
            return sorted({f"Rubin {t.datetime.date().isoformat()}" for t in obstimes})

        fetch_obs = functools.partial(
            fetch_rubin_queued,
            allocation.instrument.id,
            endpoint,
            start_date,
            end_date,
        )
        IOLoop.current().run_in_executor(None, fetch_obs)
        return []

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "endpoint": {
                "type": "string",
                "title": "ObsLocTAP base URL",
                "default": DEFAULT_OBSLOCTAP_URL,
            },
        },
    }
