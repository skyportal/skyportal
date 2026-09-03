"""Positions over time for a NEOCP candidate, from JPL Scout's ephemeris mode.

A Scout candidate arrives with one nominal position and a single uncertainty,
which is enough to place it on the sky only when that uncertainty is small. It
often is not: an object with a few hours of arc can carry a plane-of-sky sigma
of degrees, and it moves while you look at it. This asks Scout where the object
is as a function of time instead, so a chart or a pointing can use the position
for the moment it is wanted.

Fetched on demand rather than stored: Scout re-fits as new astrometry arrives,
so a saved track for a fast mover is wrong within the hour.
"""

from datetime import UTC, datetime, timedelta

import requests

from baselayer.log import make_log

log = make_log("scout_ephemeris")

API_URL = "https://ssd-api.jpl.nasa.gov/scout.api"

# JPL caps a mode-E response at 500 rows and refuses a longer span outright, so
# the window is clamped to fit rather than being sent and rejected.
MAX_RECORDS = 500

DEFAULT_HOURS = 3.0
DEFAULT_STEP_MINUTES = 1
DEFAULT_TIMEOUT = 120

# Enough of a window to bracket one moment; a chart needs a position, not a track.
STEP_LOOKUP_HOURS = 0.1

# Geocentric. A NEO close enough to matter has a parallax between sites that is
# large compared with a good Scout uncertainty, so pass the real observatory
# when the answer is for a specific telescope.
GEOCENTRIC_OBSCODE = "500"

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class ScoutEphemerisError(Exception):
    """The ephemeris could not be retrieved or understood."""


def _as_float(value):
    """A Scout numeric field as a float; every value in the payload is a string."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def record_count(hours, step_minutes):
    """Rows a window would produce, which is what the API's cap applies to."""
    if step_minutes <= 0:
        raise ScoutEphemerisError("step_minutes must be positive")
    return int((float(hours) * 60.0) // float(step_minutes)) + 1


def clamp_window(hours, step_minutes):
    """`hours` shortened, if needed, to stay inside the API's row cap."""
    if record_count(hours, step_minutes) <= MAX_RECORDS:
        return float(hours)
    allowed = (MAX_RECORDS - 1) * float(step_minutes) / 60.0
    log(
        f"ephemeris window {hours}h at {step_minutes}m exceeds {MAX_RECORDS} rows; "
        f"shortening to {allowed:.2f}h"
    )
    return allowed


def parse_ephemeris(payload):
    """The `eph` array as flat rows, nearest-in-time first as JPL returns them.

    Each row carries the median position and `sigma-pos`, the plane-of-sky
    1-sigma in arcminutes -- the number that says whether a finder chart at this
    position means anything.
    """
    rows = payload.get("eph")
    if not isinstance(rows, list):
        raise ScoutEphemerisError("Scout response has no ephemeris rows")

    parsed = []
    for row in rows:
        median = row.get("median") or {}
        ra, dec = _as_float(median.get("ra")), _as_float(median.get("dec"))
        if ra is None or dec is None:
            continue
        sigma_limits = row.get("sigma-limits") or {}
        parsed.append(
            {
                "time": row.get("time"),
                "ra": ra,
                "dec": dec,
                # Plane-of-sky 1-sigma, arcminutes.
                "sigma_pos_arcmin": _as_float(row.get("sigma-pos")),
                "vmag": _as_float(median.get("vmag")),
                # Sky-motion rate in arcsec/min and its position angle.
                "rate_arcsec_per_min": _as_float(median.get("rate")),
                "position_angle": _as_float(median.get("pa")),
                "ra_sigma_limits": sigma_limits.get("ra"),
                "dec_sigma_limits": sigma_limits.get("dec"),
            }
        )
    if not parsed:
        raise ScoutEphemerisError("Scout returned no usable ephemeris rows")
    return parsed


def fetch_ephemeris(
    tdes,
    start=None,
    hours=DEFAULT_HOURS,
    step_minutes=DEFAULT_STEP_MINUTES,
    obs_code=GEOCENTRIC_OBSCODE,
    timeout=DEFAULT_TIMEOUT,
    session=None,
):
    """Positions for `tdes` from `start` (default now) over `hours`.

    `tdes` is the NEOCP designation, not an Obj id: the id is slugified for use
    in a URL and cannot be mapped back.
    """
    if not tdes:
        raise ScoutEphemerisError("A NEOCP designation is required")

    hours = clamp_window(hours, step_minutes)
    start = start or datetime.now(UTC).replace(tzinfo=None)
    stop = start + timedelta(hours=hours)
    params = {
        "tdes": str(tdes),
        "eph-start": start.strftime(TIME_FORMAT),
        "eph-stop": stop.strftime(TIME_FORMAT),
        "eph-step": f"{int(step_minutes)}m",
        "obs-code": str(obs_code or GEOCENTRIC_OBSCODE),
    }

    http = session or requests
    try:
        response = http.get(API_URL, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        raise ScoutEphemerisError(f"JPL Scout did not answer within {timeout}s")
    except Exception as e:
        raise ScoutEphemerisError(f"JPL Scout request failed: {e}")

    if response.status_code != 200:
        raise ScoutEphemerisError(f"JPL Scout returned {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        raise ScoutEphemerisError("JPL Scout returned a body that is not JSON")

    return parse_ephemeris(payload)


def ephemeris_at(track, when):
    """The row of `track` closest in time to `when`.

    Rows are a minute apart by default, so the nearest one is a better position
    than the discovery-time nominal for anything that moves.
    """
    if not track:
        return None
    if when is None:
        return track[0]

    def offset(row):
        stamp = row.get("time")
        if not stamp:
            return None
        try:
            return abs((datetime.fromisoformat(str(stamp)) - when).total_seconds())
        except ValueError:
            return None

    timed = [(offset(row), row) for row in track]
    timed = [(delta, row) for delta, row in timed if delta is not None]
    if not timed:
        return track[0]
    return min(timed, key=lambda pair: pair[0])[1]


def position_at(tdes, when, obs_code=GEOCENTRIC_OBSCODE, timeout=DEFAULT_TIMEOUT):
    """Where `tdes` is at `when`, as (ra, dec, sigma_pos_arcmin).

    A short window is asked for and its first row taken: JPL will not start an
    ephemeris more than 30 days out, and one row either side of the moment is
    all a chart needs.
    """
    track = fetch_ephemeris(
        tdes,
        start=when,
        hours=STEP_LOOKUP_HOURS,
        step_minutes=DEFAULT_STEP_MINUTES,
        obs_code=obs_code,
        timeout=timeout,
    )
    row = ephemeris_at(track, when)
    if row is None:
        raise ScoutEphemerisError(f"No ephemeris row near {when} for {tdes}")
    return row["ra"], row["dec"], row.get("sigma_pos_arcmin")


def tdes_from_annotation(data):
    """The NEOCP designation an ingested Scout annotation refers to.

    Ingestion records `tdes` directly; older rows predate that and are read from
    the Scout object URL they all carry.
    """
    if not isinstance(data, dict):
        return None
    tdes = data.get("tdes")
    if tdes:
        return str(tdes)
    url = data.get("url")
    if url:
        tail = str(url).rstrip("/").rsplit("/", 1)[-1].strip()
        if tail:
            return tail
    return None
