import json
import uuid

from skyportal.handlers.public.report import cache as report_cache
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
    cache_key = f"gcn_{report['id']}"
    report_cache[cache_key] = dict_to_bytes(
        {"published": True, "html": "<html></html>", "plot": None}
    )
    try:
        response = session.get(url)
        assert response.status_code == 400
        assert "not yet published" in response.json()["message"]
    finally:
        del report_cache[cache_key]
