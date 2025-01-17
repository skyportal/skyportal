import json
import time
import uuid

import numpy as np
import pytest

from skyportal.tests import api

analysis_port = 6802


@pytest.mark.flaky(reruns=3)
def test_analysis_page(
    driver,
    user,
    ztf_camera,
    analysis_service_token,
    analysis_token,
    upload_data_token,
    public_group,
):
    name = str(uuid.uuid4())
    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        # this is the URL/port of the SN analysis service that will be running during testing
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    obj_id = str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 90.0 * np.random.random()
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": ra,
            "dec": dec,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 59801.4,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 59801.3,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        f"obj/{obj_id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    max_attempts = 20
    analysis_status = "queued"

    while max_attempts > 0:
        if analysis_status not in ["queued", "pending"]:
            break
        status, data = api(
            "GET",
            f"obj/analysis/{analysis_id}",
            token=analysis_token,
        )
        assert status == 200
        assert data["data"]["analysis_service_id"] == analysis_service_id
        analysis_status = data["data"]["status"]

        max_attempts -= 1
        time.sleep(5)
    else:
        assert (
            False
        ), f"analysis was not started properly ({data['data']['status_message']})"

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{obj_id}/analysis/{analysis_id}")
    driver.wait_for_xpath(f'//span[text()="{analysis_status}"]')

    if analysis_status == "completed":
        driver.wait_for_xpath('//p[text()="Analysis Results"]')
