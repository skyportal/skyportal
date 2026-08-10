from datetime import timedelta

import pytest
import sqlalchemy as sa

from skyportal.models import Candidate, DBSession, PhotStat, ScanReport, Source
from skyportal.tests import api
from skyportal.tests.fixtures import CommentFactory, ObjFactory
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

    # Detections are read from PhotStat (not raw photometry): a fainter first
    # detection and a brighter peak, both ZTF filters. ObjFactory already creates a
    # PhotStat (obj_id is unique), so update it rather than inserting a second one.
    photstat = DBSession().scalar(sa.select(PhotStat).where(PhotStat.obj_id == obj.id))
    if photstat is None:
        photstat = PhotStat(obj_id=obj.id)
        DBSession.add(photstat)
    photstat.first_detected_mjd = 60000.0
    photstat.first_detected_mag = 18.9
    photstat.first_detected_filter = "ztfg"
    photstat.peak_mag_per_filter = {"ztfg": 18.9, "ztfr": 16.4}
    photstat.peak_mjd_per_filter = {"ztfg": 60000.0, "ztfr": 60010.0}
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

    # First/peak detection per survey (mag, time, days-ago), from PhotStat.
    detections = item["data"]["detections_by_survey"]
    assert detections is not None
    survey_detections = detections["ZTF"]
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


def _generate_report(token, group_id, now, **extra):
    """Generate a report over a window wide enough to include `now`."""
    window = {
        "start_date": (now - timedelta(days=1)).isoformat(),
        "end_date": (now + timedelta(days=1)).isoformat(),
    }
    return api(
        "POST",
        "candidates/scan_reports",
        data={
            "group_ids": [group_id],
            "passed_filters_range": window,
            "saved_candidates_range": {
                "start_saved_date": (now - timedelta(days=1)).isoformat(),
                "end_saved_date": (now + timedelta(days=1)).isoformat(),
            },
            **extra,
        },
        token=token,
    )


def _report_items(token):
    status, data = api("GET", "candidates/scan_reports", token=token)
    assert status == 200, data
    report_id = data["data"]["reports"][0]["id"]
    status, data = api("GET", f"candidates/scan_reports/{report_id}/items", token=token)
    assert status == 200, data
    return report_id, data["data"]


def test_scan_report_scoped_to_gcn_event(
    public_filter,
    public_group,
    user,
    super_admin_token,
    upload_data_token,
    cleanup_reports,
):
    """A report restricted to a GCN event covers only objects associated with it,
    and carries the crossmatch measurements plus the scanner's verdict."""
    now = utcnow_naive()
    dateobs = (now - timedelta(days=2)).replace(microsecond=0)

    status, data = api(
        "POST",
        "gcn_event",
        data={
            "dateobs": dateobs.isoformat(),
            "skymap": {"ra": 120.0, "dec": 20.0, "error": 0.5},
            "tags": ["Einstein Probe"],
        },
        token=super_admin_token,
    )
    assert status == 200, data

    # `matched` is associated with the event; `unrelated` is not.
    objs = {}
    for key in ("matched", "unrelated"):
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
        objs[key] = obj
    DBSession.commit()

    status, data = api(
        "POST",
        f"sources_in_gcn/{dateobs.isoformat()}",
        data={
            "source_id": objs["matched"].id,
            "confirmed": False,
            "explanation": "rock",
            "localization_name": "120.00000_20.00000_0.50000",
            "localization_cumprob": 0.95,
            "start_date": (dateobs - timedelta(days=1)).isoformat(),
            "end_date": (dateobs + timedelta(days=31)).isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200, data

    # Unscoped: both objects are in the report, and neither carries gcn_match.
    status, data = _generate_report(upload_data_token, public_group.id, now)
    assert status == 200, data
    report_id, items = _report_items(upload_data_token)
    cleanup_reports.append(report_id)
    ids = {item["obj_id"] for item in items}
    assert {objs["matched"].id, objs["unrelated"].id} <= ids
    assert all(item["data"].get("gcn_match") is None for item in items)

    # Scoped to the event: only the associated object, with its verdict.
    status, data = _generate_report(
        upload_data_token,
        public_group.id,
        now,
        gcn_event_dateobs=dateobs.isoformat(),
    )
    assert status == 200, data
    report_id, items = _report_items(upload_data_token)
    cleanup_reports.append(report_id)

    ids = {item["obj_id"] for item in items}
    assert objs["matched"].id in ids
    assert objs["unrelated"].id not in ids, "unassociated object leaked into the report"

    item = next(i for i in items if i["obj_id"] == objs["matched"].id)
    match = item["data"]["gcn_match"]
    assert match["confirmed"] is False
    assert match["explanation"] == "rock"


def test_scan_report_rejects_inaccessible_gcn_event(
    public_group, upload_data_token, cleanup_reports
):
    """Scoping to an event the user cannot read is refused, not silently ignored."""
    now = utcnow_naive()
    status, data = _generate_report(
        upload_data_token,
        public_group.id,
        now,
        gcn_event_dateobs=(now - timedelta(days=900)).isoformat(),
    )
    assert status == 400, data
    assert "not found or not accessible" in data["message"]
