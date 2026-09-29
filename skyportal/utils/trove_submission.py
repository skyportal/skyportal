"""Sending a source and its photometry to TROVE (astro-trove.github.io).

TROVE is a TOM, and its upload endpoint takes a list of targets each carrying
optional photometry. It upserts on the target name, so re-sending a source adds
points rather than failing, which is what makes this safe to repeat as a light
curve grows.
"""

import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log
from skyportal.models import Obj
from skyportal.utils.http import serialize_requests_response

log = make_log("trove_submission_utils")

env, cfg = load_env()

TROVE_URL = cfg.get("app.trove.endpoint")
TROVE_TEST_URL = cfg.get("app.trove.test_endpoint")

# TROVE scores each target on upload, which measures at 25-30s apiece. A
# timeout still leaves the target created, so a tight one reports a false error.
DEFAULT_TIMEOUT = 180
MJD_TO_JD = 2400000.5

# Only ever PUBLIC: nothing here is private to the instance sending it, and a
# value TROVE does not expect would be rejected or silently widen access.
PERMISSIONS = "PUBLIC"
TARGET_TYPE = "SIDEREAL"
EPOCH = 2000


class TroveSubmissionError(Exception):
    """A submission that did not reach TROVE, with the reason."""


def source_label(telescope_nickname, instrument_name):
    """TROVE's `telescope` field, which it stores as the datum's provenance."""
    parts = [
        str(part).strip()
        for part in (telescope_nickname, instrument_name)
        if part and str(part).strip()
    ]
    return "-".join(parts)


def photometry_point(point, filter_map=None, source_labels=None):
    """One SkyPortal photometry point in TROVE's shape, or None if unusable.

    A detection carries magnitude and error; a non-detection carries the limit
    it establishes. Sending a non-detection as a magnitude would put an upper
    limit on the light curve as though it were a measurement.
    """
    mjd = point.get("mjd")
    if mjd is None:
        return None

    # SkyPortal's filters are already sncosmo bandpass names, so they travel
    # unchanged unless TROVE asks for something else.
    band = point.get("filter")
    if filter_map:
        band = filter_map.get(band, band)

    # Serialized photometry names no telescope, so the label is resolved by the
    # caller from the instrument; the bare instrument name is the fallback.
    label = (source_labels or {}).get(point.get("instrument_id"))

    row = {
        "jd": float(mjd) + MJD_TO_JD,
        "telescope": label or point.get("instrument_name") or "",
        "filter": band or "",
    }

    magnitude = point.get("mag")
    if magnitude is not None:
        row["magnitude"] = float(magnitude)
        if point.get("magerr") is not None:
            row["error"] = float(point["magerr"])
        return row

    limit = point.get("limiting_mag")
    if limit is not None:
        row["limit"] = float(limit)
        return row

    # Neither a measurement nor a limit says nothing, and TROVE would store an
    # entry with no value at all.
    return None


def target_payload(
    obj_id, ra, dec, photometry=None, filter_map=None, source_labels=None
):
    """One target in TROVE's upload shape."""
    if ra is None or dec is None:
        raise TroveSubmissionError(f"{obj_id} has no position to send")

    points = [
        row
        for row in (
            photometry_point(p, filter_map, source_labels) for p in photometry or []
        )
        if row is not None
    ]
    payload = {
        "name": obj_id,
        "ra": float(ra),
        "dec": float(dec),
        "permissions": PERMISSIONS,
        "type": TARGET_TYPE,
        "epoch": EPOCH,
    }
    if points:
        payload["photometry"] = points
    return payload


def post_targets(endpoint, username, password, targets, timeout=DEFAULT_TIMEOUT):
    """POST targets to TROVE's upload endpoint, returning its response body.

    The endpoint takes a list even for one target, and authenticates with the
    credentials of a real TROVE account rather than a bot token.
    """
    if not targets:
        raise TroveSubmissionError("nothing to send")
    if not (username and password):
        raise TroveSubmissionError("TROVE credentials are not configured")

    url = f"{str(endpoint).rstrip('/')}/api/target/upload"
    try:
        response = requests.post(
            url,
            json=list(targets),
            auth=(username, password),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        raise TroveSubmissionError(f"TROVE did not answer within {timeout}s") from None
    except Exception as e:
        raise TroveSubmissionError(f"could not reach TROVE: {e}") from None

    if response.status_code >= 400:
        raise TroveSubmissionError(
            f"TROVE returned {response.status_code}: "
            f"{response.text[:300] if response.text else 'no body'}"
        )
    try:
        return response.json()
    except ValueError:
        return {"status": response.status_code}


def submit_to_trove(submission_request, sharing_service, user, photometry, session):
    """Send one submission request's source and photometry to TROVE."""
    flow = Flow()
    # Snapshot ids up front: the flow push below also runs on error paths, and
    # these ORM attrs expire once we commit before the HTTP call.
    sharing_service_id = sharing_service.id
    user_id = submission_request.user_id
    obj_id = submission_request.obj_id
    response = None
    try:
        # Testing mode goes to TROVE's test deployment rather than sending nothing,
        # so the whole path is exercised without touching the real database.
        testing = sharing_service.testing
        endpoint = TROVE_TEST_URL if testing else TROVE_URL
        if not endpoint:
            setting = "test_endpoint" if testing else "endpoint"
            raise ValueError(
                f"TROVE endpoint is not configured. Please set 'app.trove.{setting}' in the configuration."
            )

        obj = session.scalar(Obj.select(user).where(Obj.id == obj_id))
        if obj is None:
            raise ValueError(f"No object found with ID {obj_id}.")

        # The instrument carries its telescope, so the provenance label needs
        # no extra query.
        source_labels = {
            p.instrument_id: source_label(
                p.instrument.telescope.nickname, p.instrument.name
            )
            for p in photometry
        }
        target = target_payload(
            obj.id,
            obj.ra,
            obj.dec,
            [p.to_dict_public() for p in photometry],
            source_labels=source_labels,
        )
        submission_request.trove_payload = target

        altdata = sharing_service.trove_altdata or {}
        username = altdata.get("username")
        password = altdata.get("password")

        # Commit so the DB connection is released before the TROVE HTTP call
        # (no idle-in-transaction).
        session.commit()

        response = post_targets(endpoint, username, password, [target])
        where = "TROVE test server" if testing else "TROVE"
        status = f"Successfully submitted {obj_id} to {where}."
        notif_text = status
        log(
            f"Successfully submitted {obj_id} to {where} for sharing service {sharing_service_id}"
        )
    except Exception as e:
        log(str(e))
        status = f"Error: {e}"
        notif_text = f"TROVE error: {e}"

    if isinstance(response, requests.models.Response):
        submission_request.trove_response = serialize_requests_response(response)

    try:
        flow.push(
            "*",
            "skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS",
            payload={"sharing_service_id": sharing_service_id},
        )
        flow.push(
            user_id=user_id,
            action_type="baselayer/SHOW_NOTIFICATION",
            payload={
                "note": notif_text,
                "type": "error" if "Error:" in status else "info",
                "duration": 8000,
            },
        )
    except Exception:
        pass

    submission_request.trove_status = status
    session.commit()
