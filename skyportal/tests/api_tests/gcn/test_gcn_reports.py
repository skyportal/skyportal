import json
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import undefer

from skyportal.handlers.public.report import cache as report_cache
from skyportal.models import DBSession, GcnReport
from skyportal.tests import api, cfg, retry_until, session
from skyportal.utils.cache import dict_to_bytes


def _report_data(report):
    data = report["data"]
    return json.loads(data) if isinstance(data, str) else data


def _create_report(token, dateobs, **params):
    """Post a GCN report and return it once its data has been generated."""
    status, data = api(
        "POST",
        f"gcn_event/{dateobs}/report",
        data={"reportName": str(uuid.uuid4()), **params},
        token=token,
    )
    assert status == 200, data
    report_id = data["data"]["id"]

    def report_ready():
        status, data = api(
            "GET", f"gcn_event/{dateobs}/report/{report_id}", token=token
        )
        assert status == 200, data
        assert _report_data(data["data"]).get("status") != "pending"
        return data["data"]

    report = retry_until(report_ready, timeout=120)
    report_data = _report_data(report)
    assert report_data.get("status") != "error", report_data
    return report


def test_unpublished_report_data_edit_stays_private(
    super_admin_token, public_group, gcn_GW190425
):
    dateobs = gcn_GW190425.dateobs.strftime("%Y-%m-%dT%H:%M:%S")
    report = _create_report(
        super_admin_token,
        dateobs,
        groupId=public_group.id,
        startDate="2019-04-25T08:18:05",
        endDate="2019-04-28T08:18:05",
        localizationName="bayestar.fits.gz",
    )
    assert not report["published"]

    status, data = api(
        "PATCH",
        f"gcn_event/{dateobs}/report/{report['id']}",
        data={"data": _report_data(report)},
        token=super_admin_token,
    )
    assert status == 200, data

    url = f"http://localhost:{cfg['ports.app']}/public/reports/gcn/{report['id']}"
    response = session.get(url)
    assert response.status_code == 400
    assert "not yet published" in response.json()["message"]

    # a stale entry marked published must not be served for an unpublished report
    cache_key = f"gcn_v2_{report['id']}"
    report_cache[cache_key] = dict_to_bytes(
        {"published": True, "html": "<html></html>", "plot": None}
    )
    try:
        response = session.get(url)
        assert response.status_code == 400
        assert "not yet published" in response.json()["message"]
    finally:
        del report_cache[cache_key]


def test_report_photometry_omits_groups_and_annotations(
    super_admin_token, upload_data_token, public_group, ztf_camera, gcn_GRB180116A
):
    # this position lies inside the GRB180116A fixture localization
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 229.9620403,
            "dec": 34.8442757,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200, data
    for mjd_offset in (0.5, 1):
        status, data = api(
            "POST",
            "photometry",
            data={
                "obj_id": obj_id,
                "mjd": 58134.025611226854 + mjd_offset,
                "instrument_id": ztf_camera.id,
                "flux": 12.24,
                "fluxerr": 0.031,
                "zp": 25.0,
                "magsys": "ab",
                "filter": "ztfg",
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200, data

    report = _create_report(
        super_admin_token,
        "2018-01-16T00:36:53",
        groupId=public_group.id,
        startDate="2018-01-16T00:36:53",
        endDate="2018-01-23T00:36:53",
        localizationName="Test",
        numberDetections=1,
        showSources=True,
    )
    source = next(s for s in _report_data(report)["sources"] if s["id"] == obj_id)
    assert len(source["photometry"]) == 2
    # report data is rendered on the public report page
    for point in source["photometry"]:
        assert "groups" not in point
        assert "annotations" not in point

    # the public page leaves them out even of report data stored with them
    sentinel = str(uuid.uuid4())
    db_report = DBSession().scalar(
        sa.select(GcnReport)
        .where(GcnReport.id == report["id"])
        .options(undefer(GcnReport.data))
    )
    stored = _report_data({"data": db_report.data})
    stored_source = next(s for s in stored["sources"] if s["id"] == obj_id)
    stored_source["photometry"][0]["groups"] = [{"name": sentinel}]
    stored_source["photometry"][0]["annotations"] = [{"origin": sentinel}]
    db_report.data = json.dumps(stored)
    DBSession().commit()

    url = f"http://localhost:{cfg['ports.app']}/public/reports/gcn/{report['id']}"
    try:
        # publishing renders the page and caches it before responding
        status, data = api(
            "PATCH",
            f"gcn_event/2018-01-16T00:36:53/report/{report['id']}",
            data={"published": True},
            token=super_admin_token,
        )
        assert status == 200, data

        response = session.get(url)
        assert response.status_code == 200
        assert obj_id in response.text
        assert sentinel not in response.text
    finally:
        del report_cache[f"gcn_v2_{report['id']}"]
