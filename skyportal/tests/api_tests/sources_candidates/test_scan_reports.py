from datetime import timedelta

import pytest

from skyportal.models import Candidate, DBSession, ScanReport, Source
from skyportal.tests import api
from skyportal.tests.fixtures import CommentFactory, ObjFactory, PhotometryFactory
from skyportal.utils.naive_datetime import utcnow_naive


@pytest.fixture()
def cleanup_reports():
    """Delete reports created via the API so the author user can be torn down.

    ScanReport.author_id is NOT NULL, so deleting the author (a fixture) would
    otherwise fail trying to null it out. Reports hang off group+author (not the
    obj), so they survive the obj teardown and must be removed explicitly.
    """
    report_ids = []
    yield report_ids
    session = DBSession()
    try:
        for report_id in report_ids:
            report = session.get(ScanReport, report_id)
            if report is not None:
                session.delete(report)
        session.commit()
    except Exception:
        session.rollback()


def test_scan_report_item_includes_followup_and_assignment(
    public_filter,
    public_group,
    user,
    upload_data_token,
    public_group_sedm_allocation,
    red_transients_run,
    cleanup_reports,
):
    now = utcnow_naive()

    # An obj that is both a candidate (passed the filter) and a saved source, in range.
    obj = ObjFactory(groups=[public_group])
    DBSession.add(
        Candidate(
            obj=obj,
            filter=public_filter,
            passed_at=now,
            uploader_id=user.id,
        )
    )
    DBSession.add(
        Source(
            obj_id=obj.id,
            group_id=public_group.id,
            saved_by_id=user.id,
            saved_at=now,
        )
    )
    DBSession.commit()

    # A follow-up request (SEDM is an imaging spectrograph -> "spectroscopy").
    status, data = api(
        "POST",
        "followup_request",
        data={
            "allocation_id": public_group_sedm_allocation.id,
            "obj_id": obj.id,
            "payload": {
                "priority": 3,
                "start_date": "3010-09-01",
                "end_date": "3012-09-01",
                "observation_type": "IFU",
                "exposure_time": 300,
                "maximum_airmass": 2,
                "maximum_fwhm": 1.2,
            },
        },
        token=upload_data_token,
    )
    assert status == 200, data

    # An observing-run assignment.
    status, data = api(
        "POST",
        "assignment",
        data={"run_id": red_transients_run.id, "obj_id": obj.id, "priority": "5"},
        token=upload_data_token,
    )
    assert status == 200, data

    # A human comment left by the scanner (browser comments are non-bot), which the
    # report should auto-fill (#5526).
    comment_text = "looks like a promising transient"
    CommentFactory(
        obj=obj, author=user, groups=[public_group], text=comment_text, bot=False
    )

    # Two detections on the same survey: the earlier/fainter one is the first
    # detection, the later/brighter one is the peak.
    survey = red_transients_run.instrument
    PhotometryFactory(
        obj_id=obj.id,
        instrument=survey,
        filter="ztfg",
        mjd=60000.0,
        flux=100.0,
        fluxerr=1.0,
        groups=[public_group],
    )
    PhotometryFactory(
        obj_id=obj.id,
        instrument=survey,
        filter="ztfr",
        mjd=60010.0,
        flux=1000.0,
        fluxerr=1.0,
        groups=[public_group],
    )
    DBSession.commit()

    window = {
        "start_date": (now - timedelta(days=1)).isoformat(),
        "end_date": (now + timedelta(days=1)).isoformat(),
    }
    status, data = api(
        "POST",
        "candidates/scan_reports",
        data={
            "group_ids": [public_group.id],
            "passed_filters_range": window,
            "saved_candidates_range": {
                "start_saved_date": (now - timedelta(days=1)).isoformat(),
                "end_saved_date": (now + timedelta(days=1)).isoformat(),
            },
        },
        token=upload_data_token,
    )
    assert status == 200, data

    status, data = api("GET", "candidates/scan_reports", token=upload_data_token)
    assert status == 200, data
    report_id = data["data"]["reports"][0]["id"]
    cleanup_reports.append(report_id)

    status, data = api(
        "GET", f"candidates/scan_reports/{report_id}/items", token=upload_data_token
    )
    assert status == 200, data
    item = next(item for item in data["data"] if item["obj_id"] == obj.id)

    # The scanner's comment is auto-filled into the report item (#5526).
    assert item["data"]["comment"] == comment_text

    followups = item["data"]["followups"]
    assert followups is not None
    followup = next(
        f
        for f in followups
        if f["instrument"] == public_group_sedm_allocation.instrument.name
    )
    assert followup["type"] == "spectroscopy"
    assert followup["priority"] == 3
    assert followup["status"] is not None
    assert followup["requester"] == user.username

    assignments = item["data"]["assignments"]
    assert assignments is not None
    assignment = next(
        a for a in assignments if a["instrument"] == red_transients_run.instrument.name
    )
    assert assignment["priority"] == "5"
    assert assignment["status"] is not None
    assert assignment["requester"] == user.username

    # First/peak detection per survey (mag, time, days-ago).
    detections = item["data"]["detections_by_survey"]
    assert detections is not None
    survey_detections = detections[survey.name]
    assert survey_detections["first"]["mag"] == 18.9
    assert survey_detections["peak"]["mag"] == 16.4
    assert survey_detections["first"]["days_ago"] > 0
    assert survey_detections["peak"]["days_ago"] > 0


def test_scan_report_rolling_window(
    public_filter,
    public_group,
    user,
    upload_data_token,
    cleanup_reports,
):
    now = utcnow_naive()

    obj = ObjFactory(groups=[public_group])
    DBSession.add(
        Candidate(obj=obj, filter=public_filter, passed_at=now, uploader_id=user.id)
    )
    DBSession.add(
        Source(
            obj_id=obj.id,
            group_id=public_group.id,
            saved_by_id=user.id,
            saved_at=now,
        )
    )
    DBSession.commit()

    # Rolling windows (hours) instead of absolute ranges — what a recurring caller uses.
    status, data = api(
        "POST",
        "candidates/scan_reports",
        data={
            "group_ids": [public_group.id],
            "passed_filters_window_hours": 48,
            "saved_candidates_window_hours": 48,
        },
        token=upload_data_token,
    )
    assert status == 200, data

    status, data = api("GET", "candidates/scan_reports", token=upload_data_token)
    assert status == 200, data
    report_id = data["data"]["reports"][0]["id"]
    cleanup_reports.append(report_id)

    status, data = api(
        "GET", f"candidates/scan_reports/{report_id}/items", token=upload_data_token
    )
    assert status == 200, data
    assert any(item["obj_id"] == obj.id for item in data["data"])


def test_scan_report_item_comment_only_from_scanner(
    public_filter,
    public_group,
    user,
    upload_data_token,
    super_admin_user,
    cleanup_reports,
):
    now = utcnow_naive()

    obj = ObjFactory(groups=[public_group])
    DBSession.add(
        Candidate(obj=obj, filter=public_filter, passed_at=now, uploader_id=user.id)
    )
    DBSession.add(
        Source(
            obj_id=obj.id,
            group_id=public_group.id,
            saved_by_id=user.id,
            saved_at=now,
        )
    )
    DBSession.commit()

    # A comment left by someone other than the report author must not be auto-filled.
    CommentFactory(
        obj=obj,
        author=super_admin_user,
        groups=[public_group],
        text="another user's note",
        bot=False,
    )
    DBSession.commit()

    window = {
        "start_date": (now - timedelta(days=1)).isoformat(),
        "end_date": (now + timedelta(days=1)).isoformat(),
    }
    status, data = api(
        "POST",
        "candidates/scan_reports",
        data={
            "group_ids": [public_group.id],
            "passed_filters_range": window,
            "saved_candidates_range": {
                "start_saved_date": (now - timedelta(days=1)).isoformat(),
                "end_saved_date": (now + timedelta(days=1)).isoformat(),
            },
        },
        token=upload_data_token,
    )
    assert status == 200, data

    status, data = api("GET", "candidates/scan_reports", token=upload_data_token)
    assert status == 200, data
    report_id = data["data"]["reports"][0]["id"]
    cleanup_reports.append(report_id)

    status, data = api(
        "GET", f"candidates/scan_reports/{report_id}/items", token=upload_data_token
    )
    assert status == 200, data
    item = next(item for item in data["data"] if item["obj_id"] == obj.id)

    # No comment by the scanner -> comment stays empty; followups/assignments empty too.
    assert item["data"]["comment"] is None
    assert item["data"]["followups"] is None
    assert item["data"]["assignments"] is None
