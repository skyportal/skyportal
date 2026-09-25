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
# Wide enough to see an object sitting outside a stale prediction: 2019 SS77
# was recovered 92 arcsec away, against its own quoted 249 arcsec uncertainty.
DEFAULT_HALF_WIDTH_DEG = 0.1  # 360 arcsec

# Beyond this the match is a different object that happens to share the field.
# A cone alone cannot identify: whether a hit is ours is decided by how its
# separation behaves across the arc, not by a constant.
DEFAULT_MATCH_ARCSEC = 360.0

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
    # JPL returns no positional uncertainty, but it does return sky motion, and
    # motion is what separates a stale ephemeris from a neighbour.
    ra_rate_at = next(
        (i for i, f in enumerate(fields) if f.startswith("RA rate")), None
    )
    dec_rate_at = next(
        (i for i, f in enumerate(fields) if f.startswith("Dec rate")), None
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
        for key, index in (("ra_rate", ra_rate_at), ("dec_rate", dec_rate_at)):
            if index is not None and index < len(row):
                try:
                    match[key] = float(row[index])
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


# Epochs queried when the track is longer than this. Querying every epoch of a
# long arc is slow and tells you nothing the ends and middle do not.
MAX_EPOCHS_QUERIED = 3


def _sample_epochs(detections, limit=MAX_EPOCHS_QUERIED):
    rows = sorted(detections, key=lambda d: d["jd"])
    if len(rows) <= limit:
        return rows
    return [rows[0], rows[len(rows) // 2], rows[-1]]


# A stale ephemeris keeps a near-constant separation across the arc; two
# different objects drift apart. 2019 SS77 held 91.85 then 91.46 arcsec over
# three days while both moved ~470 arcsec/day.
MAX_OFFSET_DRIFT_ARCSEC = 20.0
# Sky motion agreeing this well is corroboration, not proof: asteroids in one
# field move alike, and a neighbour matched to 0.2 arcsec/h.
MAX_RATE_DIFFERENCE_ARCSEC_PER_HOUR = 3.0
# Below this a hit is simply where it was predicted to be, and the offset test
# has nothing to say.
CLOSE_ENOUGH_ARCSEC = 10.0


def _track_rates(detections):
    """The track's own sky motion in arcsec/hour, from its ends."""
    rows = sorted(detections, key=lambda d: d["jd"])
    if len(rows) < 2:
        return None, None
    first, last = rows[0], rows[-1]
    hours = (last["jd"] - first["jd"]) * 24.0
    if hours <= 0:
        return None, None
    import numpy as np

    mean_dec = np.radians((first["dec"] + last["dec"]) / 2)
    d_ra = (((last["ra"] - first["ra"] + 180) % 360) - 180) * np.cos(mean_dec) * 3600
    d_dec = (last["dec"] - first["dec"]) * 3600
    return float(d_ra / hours), float(d_dec / hours)


def identify_across_arc(matches_by_epoch, detections):
    """Group per-epoch hits by object and judge each against the whole arc.

    A cone cannot identify on its own. What does is how a candidate's
    separation behaves along the track: flat means our detections and the
    prediction are the same object seen through a stale orbit, drifting means
    they are two objects that happened to be near each other once.
    """
    by_name = {}
    for epoch_jd, matches in matches_by_epoch:
        for match in matches:
            by_name.setdefault(match["name"], []).append({**match, "jd": epoch_jd})

    track_ra_rate, track_dec_rate = _track_rates(detections)
    verdicts = []
    for name, hits in by_name.items():
        offsets = [h["offset_arcsec"] for h in hits]
        drift = max(offsets) - min(offsets)
        nearest = min(offsets)
        rates = [h for h in hits if h.get("ra_rate") is not None]
        rate_difference = None
        if rates and track_ra_rate is not None:
            rate_difference = max(
                abs(h["ra_rate"] - track_ra_rate) + abs(h["dec_rate"] - track_dec_rate)
                for h in rates
            )

        # One epoch says nothing about drift, so proximity is all there is.
        if len(hits) < 2:
            identified = nearest <= CLOSE_ENOUGH_ARCSEC
            reason = (
                f"within {nearest:.0f} arcsec of the prediction"
                if identified
                # The evidence is that it left the field, not the epoch count.
                else f"seen once at {nearest:.0f} arcsec, so it drifted out of "
                "the cone between epochs"
            )
        elif nearest <= CLOSE_ENOUGH_ARCSEC:
            identified, reason = True, "where it was predicted to be"
        elif drift <= MAX_OFFSET_DRIFT_ARCSEC:
            identified = True
            reason = (
                f"separation held near {nearest:.0f} arcsec across the arc, which a "
                "different object would not do"
            )
        else:
            identified = False
            reason = f"separation drifted by {drift:.0f} arcsec, so a different object"

        verdicts.append(
            {
                "name": name,
                "identified": identified,
                "nearest_arcsec": round(nearest, 2),
                "offset_drift_arcsec": round(drift, 2),
                "rate_difference_arcsec_per_hour": (
                    round(rate_difference, 2) if rate_difference is not None else None
                ),
                # bool(), not the numpy one the arithmetic produces: this goes
                # out as JSON.
                "motion_agrees": bool(
                    rate_difference is not None
                    and rate_difference <= MAX_RATE_DIFFERENCE_ARCSEC_PER_HOUR
                ),
                "epochs": len(hits),
                "reason": reason,
            }
        )
    return sorted(verdicts, key=lambda v: v["nearest_arcsec"])


def check_known_object(detections, obs_time_for, obscode="500", control=None, **kwargs):
    """Whether a track is a known minor planet, and whether to believe a "no".

    A silent query failure reads as "undiscovered", which is the worst answer
    this can give: it invites someone to submit a known object as a discovery.
    So a negative is only reported as one when a control observation, whose
    object is known to be there, comes back positive on the same code path.

    ``control`` is {"ra", "dec", "jd", "expect"} for a detection whose object
    JPL should find. Without one the result is returned unverified rather than
    as a clean negative.
    """
    per_epoch, errors = [], []
    for row in _sample_epochs(detections):
        try:
            found = identify(
                row["ra"],
                row["dec"],
                obs_time_for(row["jd"]),
                obscode=obscode,
                **kwargs,
            )
        except JPLSBIdentError as e:
            errors.append(str(e))
            continue
        per_epoch.append((row["jd"], found))

    # Judged against the whole arc, not a radius: a known object can sit far
    # outside a stale prediction and still be the object.
    candidates = identify_across_arc(per_epoch, detections)
    identified = [c for c in candidates if c["identified"]]
    nearby = [c for c in candidates if not c["identified"]]

    if identified:
        return {
            "known": True,
            "verified": True,
            "matches": identified,
            "nearby": nearby,
            "errors": errors,
            "reason": f"{identified[0]['name']}: {identified[0]['reason']}",
        }

    if errors:
        return {
            "known": None,
            "verified": False,
            "matches": [],
            "nearby": nearby,
            "errors": errors,
            "reason": f"JPL could not be queried: {errors[0]}",
        }

    if control is None:
        return {
            "known": None,
            "verified": False,
            "matches": [],
            "nearby": nearby,
            "errors": [],
            "reason": "no control observation, so a negative cannot be trusted",
        }

    try:
        found = identify(
            control["ra"],
            control["dec"],
            obs_time_for(control["jd"]),
            obscode=obscode,
            **kwargs,
        )
    except JPLSBIdentError as e:
        return {
            "known": None,
            "verified": False,
            "matches": [],
            "errors": [str(e)],
            "reason": f"the control query failed, so a negative proves nothing: {e}",
        }

    expected = str(control.get("expect") or "").strip().lower()
    hit = (
        [m for m in found if expected in str(m.get("name", "")).strip().lower()]
        if expected
        else found
    )
    if not hit:
        return {
            "known": None,
            "verified": False,
            "matches": [],
            "nearby": nearby,
            "errors": [],
            "reason": (
                "the control found nothing where a known object was expected, so "
                "this negative is a broken query rather than a discovery"
            ),
        }

    return {
        "known": False,
        "verified": True,
        "matches": [],
        "nearby": nearby,
        "errors": [],
        "reason": "no known small body, and the control confirmed the query works",
    }
