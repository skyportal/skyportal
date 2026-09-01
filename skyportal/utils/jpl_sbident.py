"""Identify known small bodies at a sky position and time, via JPL's
Small-Body Identification API.

The API answers per *field of view*, not per position: one call covers a region
at an instant, and every known body predicted to fall inside it comes back with
its offset from the field centre. A call is therefore no dearer for a group of
candidates in one exposure than for a single one, which is where a large queue
would get cheaper.

Two passes are available. The first is a coarse screen -- a 30" field still
returns thousands of rows -- so only the second pass answers "is there a minor
planet *here*". It is correspondingly slow (minutes, not seconds), which is why
this is driven from a queue rather than from a request handler.

MPC's MPChecker answers the same question, but its own error responses state
that use outside their web form is unsupported, so it is not something to build
a service on.
"""

import requests

from baselayer.log import make_log

log = make_log("jpl_sbident")

API_URL = "https://ssd-api.jpl.nasa.gov/sb_ident.api"

# The precise pass is minutes of work on JPL's side; a request handler would be
# long gone before it answers.
DEFAULT_TIMEOUT = 300

# Half-width of the field asked about, in degrees. Wide enough to cover the
# position uncertainty of a detection plus a body's motion within an exposure,
# narrow enough that the answer is about this candidate.
DEFAULT_HALF_WIDTH_DEG = 0.0084  # 30 arcsec

# Beyond this the match is a different object that happens to share the field.
DEFAULT_MATCH_ARCSEC = 10.0

# Asking from the wrong place moves the answer: at main-belt distances the
# parallax between two points on Earth reaches roughly 9 arcsec, the size of the
# match radius above, so the site can both invent a match and hide one. 500 is
# geocentric, used when the telescope has no code recorded.
GEOCENTRIC_OBSCODE = "500"


async def obscode_for_survey(session, survey):
    """The MPC observatory code a survey observes from.

    Read from the telescope rather than a table here: an instrument is named for
    its survey and already carries the code its observations are reported under.
    Falls back to geocentric when it is unset, which is wrong by about the match
    radius -- so a telescope used for identification wants its code filled in.
    """
    import sqlalchemy as sa

    from ..models import Instrument, Telescope

    obscode = await session.scalar(
        sa.select(Telescope.mpc_obscode)
        .join(Instrument, Instrument.telescope_id == Telescope.id)
        .where(Instrument.name == survey)
    )
    return obscode or GEOCENTRIC_OBSCODE


class JPLSBIdentError(Exception):
    """The identification could not be completed."""


def _sexagesimal(degrees, is_ra):
    """Degrees as the hyphen-separated sexagesimal the API expects."""
    value = degrees / 15.0 if is_ra else degrees
    sign = "-" if value < 0 else ("+" if not is_ra else "")
    value = abs(value)
    units = int(value)
    minutes_full = (value - units) * 60
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60
    return f"{sign}{units:02d}-{minutes:02d}-{seconds:05.2f}"


def _parse_offset(value):
    """An offset column as arcsec.

    The API writes large offsets in a shortened exponential form ("-3.E3") that
    float() accepts, and small ones plainly ("199."). A blank or unparseable
    entry is not an offset, so it is dropped rather than guessed at.
    """
    try:
        return abs(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def parse_matches(payload, max_arcsec=DEFAULT_MATCH_ARCSEC):
    """Bodies from a response that fall within `max_arcsec` of the field centre.

    Reads the second pass, the only one whose positions are refined enough to
    mean anything at these separations. Returns them nearest first.
    """
    rows = payload.get("data_second_pass") or []
    fields = payload.get("fields_second") or []
    try:
        name_at = fields.index("Object name")
        offset_at = next(
            i for i, f in enumerate(fields) if f.startswith("Dist. from center Norm")
        )
    except (ValueError, StopIteration):
        raise JPLSBIdentError(f"Unexpected response columns: {fields}")

    magnitude_at = next(
        (i for i, f in enumerate(fields) if f.startswith("Visual magnitude")), None
    )

    matches = []
    for row in rows:
        offset = _parse_offset(row[offset_at]) if offset_at < len(row) else None
        if offset is None or offset > max_arcsec:
            continue
        match = {"name": str(row[name_at]).strip(), "offset_arcsec": round(offset, 3)}
        if magnitude_at is not None and magnitude_at < len(row):
            try:
                match["magnitude"] = float(row[magnitude_at])
            except (TypeError, ValueError):
                pass
        matches.append(match)
    return sorted(matches, key=lambda m: m["offset_arcsec"])


def identify(
    ra,
    dec,
    obs_time,
    obscode="500",
    half_width_deg=DEFAULT_HALF_WIDTH_DEG,
    max_arcsec=DEFAULT_MATCH_ARCSEC,
    timeout=DEFAULT_TIMEOUT,
    session=None,
):
    """Known small bodies within `max_arcsec` of (ra, dec) at `obs_time`.

    ra, dec are degrees; obs_time is a datetime. `obscode` is the observatory the
    position was measured from -- a body's apparent place depends on it, and 500
    (geocentric) is only right when the real site is unknown.
    """
    params = {
        "sb-kind": "a",
        "mpc-code": obscode,
        "obs-time": obs_time.strftime("%Y-%m-%d_%H:%M:%S"),
        "fov-ra-center": _sexagesimal(ra, is_ra=True),
        "fov-dec-center": _sexagesimal(dec, is_ra=False),
        "fov-ra-hwidth": f"{half_width_deg}",
        "fov-dec-hwidth": f"{half_width_deg}",
        # The first pass is a screen, not an answer; asking for it back would be
        # thousands of rows to discard.
        "two-pass": "true",
        "suppress-first-pass": "true",
    }
    http = session or requests
    try:
        response = http.get(API_URL, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        raise JPLSBIdentError(f"JPL did not answer within {timeout}s")
    except Exception as e:
        raise JPLSBIdentError(f"JPL request failed: {e}")

    if response.status_code != 200:
        raise JPLSBIdentError(f"JPL returned {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        raise JPLSBIdentError("JPL returned a body that is not JSON")

    return parse_matches(payload, max_arcsec=max_arcsec)


def enqueue_identification(obj_id, user_id, obs_time, group_ids=None, **kwargs):
    """Ask the identification service to check an object.

    Returns True when the service accepted it. A refusal is logged rather than
    raised: an identification is an annotation nobody is waiting on, so failing
    to queue one must not fail whatever prompted it.
    """
    from baselayer.app.env import load_env

    _, cfg = load_env()
    url = f"http://{cfg['hosts.jpl_sbident_queue']}:{cfg['ports.jpl_sbident_queue']}"
    payload = {
        "obj_id": obj_id,
        "user_id": user_id,
        "obs_time": obs_time.isoformat()
        if hasattr(obs_time, "isoformat")
        else obs_time,
        "group_ids": list(group_ids or []),
        **kwargs,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        log(f"{obj_id}: identification queue refused the request ({response.text})")
    except Exception as e:
        log(f"{obj_id}: could not reach the identification queue ({e})")
    return False
