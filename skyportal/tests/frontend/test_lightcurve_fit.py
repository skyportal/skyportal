import uuid
import json

import pytest

from skyportal.tests import api

analysis_port = 6802


@pytest.mark.flaky(reruns=2)
def test_lightcurve_fit(
    driver,
    analysis_service_token,
    analysis_token,
    public_group,
    public_source,
    super_admin_user,
):

    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'contact_email': "vr@ls.st",
        # this is the URL/port of the SN analysis service that will be running during testing
        'url': f"http://localhost:{analysis_port}/analysis/demo_analysis",
        'optional_analysis_parameters': json.dumps(optional_analysis_parameters),
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}/lightcurve_fit")
    driver.wait_for_xpath('//*[@id="root_test_parameters"]').click()
    driver.click_xpath(
        '//li[contains(text(), "test_value_1")]',
        scroll_parent=True,
    )
    driver.click_xpath('//*[text()="Submit"]')
    driver.wait_for_xpath(
        "//*[text()='Sending data to analysis service to start the analysis.']"
    )

    driver.get(f"/source/{public_source.id}/lightcurve_fit")

    driver.click_xpath('//*[text()="Analysis Requests"]')
    driver.wait_for_xpath("//*[text()='test_parameters']")
