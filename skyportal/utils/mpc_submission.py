"""ADES PSV for a track, in the form the Minor Planet Center accepts.

Written against the submission that became MPC track BOOM01: 19 ZTF detections
over a 13-day arc, acknowledged 2026-09-24.
"""

from astropy.time import Time

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


def _header(observatory, telescope, submitter, observers, measurers):
    lines = [
        "# version=2022",
        "# observatory",
        f"! mpcCode {observatory['mpc_code']}",
        "# submitter",
        f"! name {submitter}",
        "# observers",
        f"! name {observers}",
        "# measurers",
        f"! name {measurers}",
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
