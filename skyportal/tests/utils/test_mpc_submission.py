"""The PSV a vetted track is submitted to the MPC as.

Checked against the submission that became MPC track BOOM01: the 19 data lines
below are the ones the MPC acknowledged on 2026-09-24.
"""

import pytest
from astropy.time import Time

from skyportal.utils.mpc_submission import (
    NotSubmittable,
    obs_time,
    psv_submission,
)

SUBMITTED = """BOOM01|CCD|I41|2026-09-10T08:47:57.998Z|8.980389|+48.596773|Gaia3|19.71|r
BOOM01|CCD|I41|2026-09-11T07:44:10.997Z|8.858301|+48.705185|Gaia3|20.24|g
BOOM01|CCD|I41|2026-09-12T09:18:40.997Z|8.712771|+48.817289|Gaia3|19.83|r
BOOM01|CCD|I41|2026-09-16T08:46:04.002Z|8.108341|+49.150555|Gaia3|19.59|i
BOOM01|CCD|I41|2026-09-23T07:50:56.999Z|6.855218|+49.397193|Gaia3|19.69|r"""

OBSERVATORY = {"mpc_code": "I41"}
TELESCOPE = {
    "name": "Zwicky Transient Facility",
    "design": "Schmidt",
    "aperture": "1.2",
    "detector": "ZTFCam",
}
SUBMITTER = "Q.-Z. Ye"
OBSERVERS = "Z. T. F. Collaboration"
MEASURERS = "A. Le Calloch, T. Culino, M. Coughlin, Q.-Z. Ye"


def detections_from_submitted():
    """Rebuild the detections from the submitted lines, at full JD precision."""
    rows = []
    for line in SUBMITTED.splitlines():
        _, _, _, obs, ra, dec, _, mag, band = line.split("|")
        rows.append(
            {
                "jd": Time(obs.rstrip("Z"), format="isot", scale="utc").jd,
                "ra": float(ra),
                "dec": float(dec),
                "mag": float(mag),
                "band": band,
            }
        )
    return rows


def submission(**overrides):
    kwargs = {
        "detections": detections_from_submitted(),
        "track_id": "BOOM01",
        "observatory": OBSERVATORY,
        "telescope": TELESCOPE,
        "submitter": SUBMITTER,
        "observers": OBSERVERS,
        "measurers": MEASURERS,
    }
    kwargs.update(overrides)
    return psv_submission(**kwargs)


def test_the_data_lines_match_what_the_mpc_accepted():
    produced = [line for line in submission().splitlines() if line.startswith("BOOM01")]
    assert produced == SUBMITTED.splitlines()


def test_the_column_line_uses_trksub():
    # permID is reserved for the permanent numbers of known objects; the MPC
    # rejects a new track that claims one.
    header = [line for line in submission().splitlines() if line.startswith("trkSub")]
    assert header == ["trkSub|mode|stn|obsTime|ra|dec|astCat|mag|band"]
    assert "permID" not in submission()


def test_declination_carries_its_sign():
    assert "|+48.596773|" in submission()


def test_detections_are_written_in_time_order():
    rows = detections_from_submitted()
    out = submission(detections=list(reversed(rows)))
    times = [
        line.split("|")[3] for line in out.splitlines() if line.startswith("BOOM01")
    ]
    assert times == sorted(times)


def test_a_rounded_jd_is_refused():
    # 1e-5 day is 0.86 s. Submitting astrometry timed that coarsely is an error
    # nobody can see in the output, so it is refused at the door.
    rows = detections_from_submitted()
    rows[0]["jd"] = round(rows[0]["jd"], 5)
    with pytest.raises(NotSubmittable, match="rounded past"):
        submission(detections=rows)


def test_an_empty_track_is_refused():
    with pytest.raises(NotSubmittable, match="at least one"):
        submission(detections=[])


def test_a_detection_without_a_position_is_refused():
    rows = detections_from_submitted()
    rows[1]["dec"] = None
    with pytest.raises(NotSubmittable, match="missing dec"):
        submission(detections=rows)


def test_the_timestamp_keeps_milliseconds():
    assert obs_time(2461293.8666435) == "2026-09-10T08:47:57.998Z"
