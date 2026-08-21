from datetime import timedelta
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from skyportal_py import SkyPortalError
from skyportal_py.assignments import AssignmentPost
from skyportal_py.candidates import (
    ScanReportPassedFiltersRange,
    ScanReportPost,
    ScanReportSavedCandidatesRange,
)
from skyportal_py.followup_requests import FollowupRequestPost
from skyportal_py.gcn_events import GcnEventObjPost, GcnEventPost

from skyportal.handlers.api.candidate.scan_report_item import _followup_request_type
from skyportal.models import (
    Candidate,
    DBSession,
    GroupUser,
    PhotStat,
    ScanReport,
    Source,
    SuperObj,
)
from skyportal.tests import client
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
    public_group2,
    user,
    upload_data_token,
    public_group_sedm_allocation,
    red_transients_run,
    cleanup_reports,
):
    now = utcnow_naive()
    sp = client(upload_data_token)

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
    # Also currently saved to a second group outside the report's own group_ids,
    # to confirm "groups_saved_to" isn't limited to the report's scope. `user`
    # must belong to it too, or Source.select(mode="read") filters it out.
    DBSession.add(GroupUser(user_id=user.id, group_id=public_group2.id))
    DBSession.add(
        Source(
            obj_id=obj.id,
            group_id=public_group2.id,
            saved_by_id=user.id,
            saved_at=now,
        )
    )
    DBSession.commit()

    # A follow-up request (SEDM is an imaging spectrograph -> "spectroscopy").
    sp.post_followup_request(
        FollowupRequestPost(
            allocation_id=public_group_sedm_allocation.id,
            obj_id=obj.id,
            payload={
                "priority": 3,
                "start_date": "3010-09-01",
                "end_date": "3012-09-01",
                "observation_type": "IFU",
                "exposure_time": 300,
                "maximum_airmass": 2,
                "maximum_fwhm": 1.2,
            },
        )
    )

    # An observing-run assignment.
    sp.post_assignment(
        AssignmentPost(run_id=red_transients_run.id, obj_id=obj.id, priority="5")
    )

    # A human comment left by the scanner (browser comments are non-bot), which the
    # report should auto-fill (#5526).
    comment_text = "looks like a promising transient"
    CommentFactory(
        obj=obj, author=user, groups=[public_group], text=comment_text, bot=False
    )

    # Detections are read from PhotStat (not raw photometry): a fainter first
    # detection, a brighter peak, and a later last detection, all ZTF filters.
    # ObjFactory already creates a PhotStat (obj_id is unique), so update it
    # rather than inserting a second one.
    photstat = DBSession().scalar(sa.select(PhotStat).where(PhotStat.obj_id == obj.id))
    if photstat is None:
        photstat = PhotStat(obj_id=obj.id)
        DBSession.add(photstat)
    photstat.first_detected_mjd = 60000.0
    photstat.first_detected_mag = 18.9
    photstat.first_detected_filter = "ztfg"
    photstat.peak_mag_per_filter = {"ztfg": 18.9, "ztfr": 16.4}
    photstat.peak_mjd_per_filter = {"ztfg": 60000.0, "ztfr": 60010.0}
    photstat.last_detected_mjd = 60020.0
    photstat.last_detected_mag = 17.2
    photstat.last_detected_filter = "ztfi"
    DBSession.commit()

    sp.post_scan_report(
        ScanReportPost(
            group_ids=[public_group.id],
            passed_filters_range=ScanReportPassedFiltersRange(
                start_date=(now - timedelta(days=1)).isoformat(),
                end_date=(now + timedelta(days=1)).isoformat(),
            ),
            saved_candidates_range=ScanReportSavedCandidatesRange(
                start_saved_date=(now - timedelta(days=1)).isoformat(),
                end_saved_date=(now + timedelta(days=1)).isoformat(),
            ),
        )
    )

    report_id = sp.fetch_scan_reports().reports[0].id
    cleanup_reports.append(report_id)

    items = sp.fetch_scan_report_items(report_id)
    item = next(item for item in items if item.obj_id == obj.id)

    # The scanner's comment is auto-filled into the report item (#5526).
    assert item.data["comment"] == comment_text

    followups = item.data["followups"]
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

    assignments = item.data["assignments"]
    assert assignments is not None
    assignment = next(
        a for a in assignments if a["instrument"] == red_transients_run.instrument.name
    )
    assert assignment["priority"] == "5"
    assert assignment["status"] is not None
    assert assignment["requester"] == user.username

    # First/peak/last detection per survey (mag, mjd, filter, days-ago), from PhotStat.
    detections = item.data["detections_by_survey"]
    assert detections is not None
    survey_detections = detections["ZTF"]
    assert survey_detections["first"]["mag"] == 18.9
    assert survey_detections["first"]["filter"] == "ztfg"
    assert survey_detections["peak"]["mag"] == 16.4
    assert survey_detections["peak"]["filter"] == "ztfr"
    assert survey_detections["last"]["mag"] == 17.2
    assert survey_detections["last"]["filter"] == "ztfi"
    assert survey_detections["first"]["days_ago"] > 0
    assert survey_detections["peak"]["days_ago"] > 0
    assert survey_detections["last"]["days_ago"] > 0

    # Every group the obj is currently an active Source of, including
    # `public_group2` which isn't part of this report's own group_ids/window.
    assert sorted(item.data["groups_saved_to"]) == sorted(
        [public_group.name, public_group2.name]
    )


def test_scan_report_item_includes_associated_objs(
    public_filter,
    public_group,
    user,
    upload_data_token,
    cleanup_reports,
):
    now = utcnow_naive()
    sp = client(upload_data_token)

    obj = ObjFactory(groups=[public_group])
    # Another survey's detection of the same physical object (e.g. LSST), with
    # its own alias, linked via a SuperObj -- distinct from `obj`'s own alias.
    # Note the alias/id don't need to start with "lsst": survey is inferred from
    # the photometry filter/band (see `_survey_of`), not the obj's name.
    assoc_obj = ObjFactory(groups=[public_group], alias=["LSST_123"])
    DBSession.add(SuperObj(objs=[obj, assoc_obj]))
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

    # The associated obj's own detections (LSST filter), so they should surface
    # under a distinct "LSST" key in the report item's detections_by_survey,
    # alongside `obj`'s own (ZTF) survey.
    assoc_photstat = DBSession().scalar(
        sa.select(PhotStat).where(PhotStat.obj_id == assoc_obj.id)
    )
    if assoc_photstat is None:
        assoc_photstat = PhotStat(obj_id=assoc_obj.id)
        DBSession.add(assoc_photstat)
    assoc_photstat.first_detected_mjd = 60005.0
    assoc_photstat.first_detected_mag = 19.5
    assoc_photstat.first_detected_filter = "lsstg"
    assoc_photstat.last_detected_mjd = 60025.0
    assoc_photstat.last_detected_mag = 18.1
    assoc_photstat.last_detected_filter = "lssti"
    DBSession.commit()

    sp.post_scan_report(
        ScanReportPost(
            group_ids=[public_group.id],
            passed_filters_range=ScanReportPassedFiltersRange(
                start_date=(now - timedelta(days=1)).isoformat(),
                end_date=(now + timedelta(days=1)).isoformat(),
            ),
            saved_candidates_range=ScanReportSavedCandidatesRange(
                start_saved_date=(now - timedelta(days=1)).isoformat(),
                end_saved_date=(now + timedelta(days=1)).isoformat(),
            ),
        )
    )

    report_id = sp.fetch_scan_reports().reports[0].id
    cleanup_reports.append(report_id)

    items = sp.fetch_scan_report_items(report_id)
    item = next(item for item in items if item.obj_id == obj.id)

    associated_objs = item.data["associated_objs"]
    assert associated_objs is not None
    assoc = next(a for a in associated_objs if a["obj_id"] == assoc_obj.id)
    assert assoc["aliases"] == ["LSST_123"]

    # The associated obj's own (LSST) detections are merged into
    # detections_by_survey under their own survey key, alongside `obj`'s (ZTF).
    detections = item.data["detections_by_survey"]
    assert detections is not None
    assert "LSST" in detections
    assert detections["LSST"]["first"]["mag"] == 19.5
    assert detections["LSST"]["first"]["filter"] == "lsstg"
    assert detections["LSST"]["last"]["mag"] == 18.1
    assert detections["LSST"]["last"]["filter"] == "lssti"


def test_scan_report_item_includes_previous_mag(
    public_filter,
    public_group,
    user,
    upload_data_token,
    cleanup_reports,
):
    now = utcnow_naive()
    sp = client(upload_data_token)

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

    # Two clear detections in the same filter, well past ObjFactory's own random
    # points (mjd ~58000), so these are unambiguously the last two in that filter:
    # the older one is what "previous mag" should report.
    PhotometryFactory(
        obj_id=obj.id,
        filter="ztfg",
        mjd=60500.0,
        flux=1000.0,
        fluxerr=1.0,
        groups=[public_group],
    )
    current_point = PhotometryFactory(
        obj_id=obj.id,
        filter="ztfg",
        mjd=60600.0,
        flux=2000.0,
        fluxerr=1.0,
        groups=[public_group],
    )
    DBSession.commit()

    # PhotStat's incremental after_insert hook isn't guaranteed to process two
    # same-flush inserts in mjd order, so set "last detected" explicitly rather
    # than depend on it -- this test is about the report's previous-mag query
    # against real Photometry rows, not about PhotStat's own update ordering.
    photstat = DBSession().scalar(sa.select(PhotStat).where(PhotStat.obj_id == obj.id))
    photstat.last_detected_mjd = current_point.mjd
    photstat.last_detected_mag = current_point.mag
    photstat.last_detected_filter = current_point.filter
    DBSession.commit()

    sp.post_scan_report(
        ScanReportPost(
            group_ids=[public_group.id],
            passed_filters_range=ScanReportPassedFiltersRange(
                start_date=(now - timedelta(days=1)).isoformat(),
                end_date=(now + timedelta(days=1)).isoformat(),
            ),
            saved_candidates_range=ScanReportSavedCandidatesRange(
                start_saved_date=(now - timedelta(days=1)).isoformat(),
                end_saved_date=(now + timedelta(days=1)).isoformat(),
            ),
        )
    )

    report_id = sp.fetch_scan_reports().reports[0].id
    cleanup_reports.append(report_id)

    items = sp.fetch_scan_report_items(report_id)
    item = next(item for item in items if item.obj_id == obj.id)

    assert item.data["current_mjd"] == 60600.0
    assert item.data["current_filter"] == "ztfg"
    assert item.data["previous_mjd"] == 60500.0
    assert item.data["previous_filter"] == "ztfg"
    assert item.data["previous_mag"] is not None
    assert item.data["previous_mag"] != item.data["current_mag"]


def test_scan_report_rolling_window(
    public_filter,
    public_group,
    user,
    upload_data_token,
    cleanup_reports,
):
    now = utcnow_naive()
    sp = client(upload_data_token)

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
    sp.post_scan_report(
        ScanReportPost(
            group_ids=[public_group.id],
            passed_filters_window_hours=48,
            saved_candidates_window_hours=48,
        )
    )

    report_id = sp.fetch_scan_reports().reports[0].id
    cleanup_reports.append(report_id)

    items = sp.fetch_scan_report_items(report_id)
    assert any(item.obj_id == obj.id for item in items)


def test_scan_report_item_comment_only_from_scanner(
    public_filter,
    public_group,
    user,
    upload_data_token,
    super_admin_user,
    cleanup_reports,
):
    now = utcnow_naive()
    sp = client(upload_data_token)

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

    sp.post_scan_report(
        ScanReportPost(
            group_ids=[public_group.id],
            passed_filters_range=ScanReportPassedFiltersRange(
                start_date=(now - timedelta(days=1)).isoformat(),
                end_date=(now + timedelta(days=1)).isoformat(),
            ),
            saved_candidates_range=ScanReportSavedCandidatesRange(
                start_saved_date=(now - timedelta(days=1)).isoformat(),
                end_saved_date=(now + timedelta(days=1)).isoformat(),
            ),
        )
    )

    report_id = sp.fetch_scan_reports().reports[0].id
    cleanup_reports.append(report_id)

    items = sp.fetch_scan_report_items(report_id)
    item = next(item for item in items if item.obj_id == obj.id)

    # No comment by the scanner -> comment stays empty; followups/assignments empty too.
    assert item.data["comment"] is None
    assert item.data["followups"] is None
    assert item.data["assignments"] is None


def _generate_report(token, group_id, now, **extra):
    """Generate a report over a window wide enough to include `now`."""
    client(token).post_scan_report(
        ScanReportPost(
            group_ids=[group_id],
            passed_filters_range=ScanReportPassedFiltersRange(
                start_date=(now - timedelta(days=1)).isoformat(),
                end_date=(now + timedelta(days=1)).isoformat(),
            ),
            saved_candidates_range=ScanReportSavedCandidatesRange(
                start_saved_date=(now - timedelta(days=1)).isoformat(),
                end_saved_date=(now + timedelta(days=1)).isoformat(),
            ),
            **extra,
        )
    )


def _report_items(token):
    sp = client(token)
    report_id = sp.fetch_scan_reports().reports[0].id
    return report_id, sp.fetch_scan_report_items(report_id)


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

    client(super_admin_token).post_gcn_event(
        GcnEventPost(
            dateobs=dateobs.isoformat(),
            skymap={"ra": 120.0, "dec": 20.0, "error": 0.5},
            tags=["Einstein Probe"],
        )
    )

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

    client(super_admin_token).post_gcn_event_source(
        dateobs.isoformat(),
        GcnEventObjPost(
            source_id=objs["matched"].id,
            status="rejected",
            explanation="rock",
            localization_name="120.00000_20.00000_0.50000",
            localization_cumprob=0.95,
            start_date=(dateobs - timedelta(days=1)).isoformat(),
            end_date=(dateobs + timedelta(days=31)).isoformat(),
        ),
    )

    # Unscoped: both objects are in the report, and neither carries gcn_match.
    _generate_report(upload_data_token, public_group.id, now)
    report_id, items = _report_items(upload_data_token)
    cleanup_reports.append(report_id)
    ids = {item.obj_id for item in items}
    assert {objs["matched"].id, objs["unrelated"].id} <= ids
    assert all(item.data.get("gcn_match") is None for item in items)

    # Scoped to the event: only the associated object, with its verdict.
    _generate_report(
        upload_data_token,
        public_group.id,
        now,
        gcn_event_dateobs=dateobs.isoformat(),
    )
    report_id, items = _report_items(upload_data_token)
    cleanup_reports.append(report_id)

    ids = {item.obj_id for item in items}
    assert objs["matched"].id in ids
    assert objs["unrelated"].id not in ids, "unassociated object leaked into the report"

    item = next(i for i in items if i.obj_id == objs["matched"].id)
    match = item.data["gcn_match"]
    assert match["status"] == "rejected"
    assert match["explanation"] == "rock"


def test_scan_report_rejects_inaccessible_gcn_event(
    public_group, upload_data_token, cleanup_reports
):
    """Scoping to an event the user cannot read is refused, not silently ignored."""
    now = utcnow_naive()
    with pytest.raises(SkyPortalError, match="not found or not accessible") as err:
        _generate_report(
            upload_data_token,
            public_group.id,
            now,
            gcn_event_dateobs=(now - timedelta(days=900)).isoformat(),
        )
    assert err.value.status_code == 400


def _followup_request_case(
    api_classname, instrument_type="imager", instrument_name="Test", payload=None
):
    allocation = SimpleNamespace(types=[])
    instrument = SimpleNamespace(
        name=instrument_name, type=instrument_type, api_classname=api_classname
    )
    return _followup_request_type(allocation, instrument, payload)


def test_followup_request_type_classification():
    """Distinguish photometry vs spectroscopy requests, per Instrument.api_classname
    and (for API classes that submit both) the request payload -- not just
    instrument.type, which is too coarse for e.g. LCO's per-camera API split."""
    # allocation.types takes precedence over everything else.
    assert (
        _followup_request_type(
            SimpleNamespace(types=["forced_photometry"]),
            SimpleNamespace(name="ATLAS", type="imager", api_classname="ATLASAPI"),
        )
        == "forced_photometry"
    )

    # SEDM: IFU vs any other (imaging) choice, from observation_type/observation_choices.
    assert (
        _followup_request_case(
            "SEDMAPI",
            instrument_name="SEDM",
            payload={"observation_type": "IFU"},
        )
        == "spectroscopy"
    )
    assert (
        _followup_request_case(
            "SEDMAPI",
            instrument_name="SEDM",
            payload={"observation_choices": ["3-shot (gri)"]},
        )
        == "photometry"
    )

    # SEDMv2: observation_choice is "IFU" or a filter (g/r/i/z).
    assert (
        _followup_request_case("SEDMV2API", payload={"observation_choice": "IFU"})
        == "spectroscopy"
    )
    assert (
        _followup_request_case("SEDMV2API", payload={"observation_choice": "g"})
        == "photometry"
    )

    # MMT (Binospec/MMIRS): same API class submits both, split by observation_type.
    for api_classname in ("BINOSPECAPI", "MMIRSAPI"):
        assert (
            _followup_request_case(
                api_classname, payload={"observation_type": "Spectroscopy"}
            )
            == "spectroscopy"
        )
        assert (
            _followup_request_case(
                api_classname, payload={"observation_type": "Imaging"}
            )
            == "photometry"
        )

    # Swift UVOT/XRT: obs_type is one of Spectroscopy/Light Curve/Position/Timing.
    assert (
        _followup_request_case("UVOTXRTAPI", payload={"obs_type": "Spectroscopy"})
        == "spectroscopy"
    )
    assert (
        _followup_request_case("UVOTXRTAPI", payload={"obs_type": "Light Curve"})
        == "photometry"
    )

    # Photometry-only and spectroscopy-only API classes ignore the payload entirely.
    assert (
        _followup_request_case("PS1API", payload={"observation_type": "Spectroscopy"})
        == "photometry"
    )
    assert (
        _followup_request_case("FLOYDSAPI", payload={"observation_type": "Imaging"})
        == "spectroscopy"
    )

    # An API class not in either set falls back to instrument.type.
    assert (
        _followup_request_case("SOMEOTHERAPI", instrument_type="spectrograph")
        == "spectroscopy"
    )
    assert (
        _followup_request_case("SOMEOTHERAPI", instrument_type="imager") == "photometry"
    )
