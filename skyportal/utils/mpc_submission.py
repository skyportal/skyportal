"""ADES PSV for a track, in the form the Minor Planet Center accepts.

Written against the submission that became MPC track BOOM01: 19 ZTF detections
over a 13-day arc, acknowledged 2026-09-24.
"""

import re

import requests
from astropy.time import Time

from .http import serialize_requests_response

MPC_SUBMIT_URL = "https://minorplanetcenter.net/submit_psv"

MPC_HEADER_FIELDS = (
    "observatory_code",
    "observers",
    "measurers",
    "telescope_name",
    "telescope_design",
    "telescope_aperture",
    "telescope_detector",
)

SUBMISSION_ID = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+_\w+")

# trkSub, not permID: permID is reserved for the permanent numbers of known
# objects, and the MPC rejects a new track that claims one.
COLUMNS = ("trkSub", "mode", "stn", "obsTime", "ra", "dec", "astCat", "mag", "band")

# A JD rounded to 5 decimals is only good to 0.86 s, which for a mover is a real
# astrometric error. Submit from the alert's own jd.
MIN_JD_DECIMALS = 6


class NotSubmittable(Exception):
    """The track cannot be written as a submission, with the reason."""


def obs_time(jd):
    """A detection's JD as the ADES UTC timestamp, to milliseconds."""
    return Time(float(jd), format="jd", scale="utc").isot + "Z"


def _names(names):
    return [f"! name {name.strip()}" for name in names.split(",") if name.strip()]


def _header(observatory, telescope, submitter, observers, measurers):
    lines = [
        "# version=2022",
        "# observatory",
        f"! mpcCode {observatory['mpc_code']}",
        "# submitter",
        f"! name {submitter}",
        "# observers",
        *_names(observers),
        "# measurers",
        *_names(measurers),
        "# telescope",
        f"! name {telescope['name']}",
        f"! design {telescope['design']}",
        f"! aperture {telescope['aperture']}",
        f"! detector {telescope['detector']}",
    ]
    return lines


def psv_submission(
    detections,
    track_id,
    observatory,
    telescope,
    submitter,
    observers,
    measurers,
    astrometric_catalog="Gaia3",
    mode="CCD",
):
    """The track as an ADES PSV document.

    Refuses a detection whose JD is too coarse to timestamp, rather than
    submitting astrometry with a timing error nobody can see in the output.
    """
    rows = sorted(detections, key=lambda d: d["jd"])
    if not rows:
        raise NotSubmittable("a submission needs at least one detection")

    for row in rows:
        for field in ("jd", "ra", "dec"):
            if row.get(field) is None:
                raise NotSubmittable(f"detection is missing {field}")
        if len(str(float(row["jd"])).split(".")[-1]) < MIN_JD_DECIMALS:
            raise NotSubmittable(
                f"jd {row['jd']} is rounded past {MIN_JD_DECIMALS} decimals, "
                "which cannot be timestamped to better than a second"
            )

    lines = _header(observatory, telescope, submitter, observers, measurers)
    lines.append("|".join(COLUMNS))
    for row in rows:
        mag = "" if row.get("mag") is None else f"{float(row['mag']):.2f}"
        lines.append(
            "|".join(
                [
                    track_id,
                    mode,
                    observatory["mpc_code"],
                    obs_time(row["jd"]),
                    f"{float(row['ra']):.6f}",
                    f"{float(row['dec']):+.6f}",
                    astrometric_catalog,
                    mag,
                    row.get("band") or "",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def default_submitter(user):
    """The name a user files under, as the MPC writes names: "Q. Ye"."""
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}. {user.last_name}"
    return user.username


def track_psv(track, sharing_service, submitter):
    """A broker's track as the PSV the sharing service files under ``submitter``."""
    header = sharing_service.mpc_altdata or {}
    missing = [field for field in MPC_HEADER_FIELDS if not header.get(field)]
    if missing:
        raise NotSubmittable(
            f"sharing service {sharing_service.name} is missing MPC {', '.join(missing)}"
        )
    return psv_submission(
        [{**d, "jd": d["obs_jd"]} for d in track["detections"]],
        track["id"],
        observatory={"mpc_code": header["observatory_code"]},
        telescope={
            "name": header["telescope_name"],
            "design": header["telescope_design"],
            "aperture": header["telescope_aperture"],
            "detector": header["telescope_detector"],
        },
        submitter=submitter,
        observers=header["observers"],
        measurers=header["measurers"],
    )


def ack_email(user, sharing_service):
    """Where the MPC sends its acknowledgement: the submitter, else the service."""
    email = user.contact_email or (sharing_service.mpc_altdata or {}).get("ack_email")
    if not email:
        raise NotSubmittable(
            "No address for the MPC acknowledgement: set a contact email on "
            "your profile or an ack_email on the sharing service"
        )
    return email


def submit_to_mpc(submission_request, sharing_service, user, session):
    """File a queued PSV with the MPC, or with its test endpoint when testing."""
    payload = submission_request.mpc_payload
    url = MPC_SUBMIT_URL + ("_test" if sharing_service.testing else "")
    response = requests.post(
        url,
        data={"ack": payload["track_id"], "ac2": ack_email(user, sharing_service)},
        files={"source": payload["psv"].encode()},
        timeout=120,
    )
    submission_request.mpc_response = serialize_requests_response(response)
    found = SUBMISSION_ID.search(response.text)
    if not response.ok or found is None:
        submission_request.mpc_status = (
            f"Error: the MPC returned {response.status_code} with no submission "
            f"ID: {response.text.strip()[:300]}"
        )
    else:
        submission_request.mpc_submission_id = found.group(0)
        submission_request.mpc_status = (
            "test submission" if sharing_service.testing else "submitted"
        )
    session.commit()
