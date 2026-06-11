import json
import os
import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api

analysis_port = 6802


def test_analysis_start(
    page, user, public_source, analysis_service_token, public_group
):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps({}),
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

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator('//*[text()="External Analysis"]').first).to_be_visible()

    page.locator('//div[@data-testid="analysisServiceSelect"]').first.click()
    # select this run's service (its name is a unique uuid) to populate the form
    page.locator(f'//li[contains(., "{name}")]').first.click()
    page.locator(
        '//div[@data-testid="analysis-service-request-form"]//*[@type="submit"]'
    ).first.click()
    expect(
        page.locator(
            f"//*[text()='Sending data to analysis service {name} to start the analysis.']"
        ).first
    ).to_be_visible()


def test_analysis_with_file_input_start(
    page, user, public_source, analysis_service_token, public_group
):
    name = str(uuid.uuid4())
    optional_analysis_parameters = {
        "image_data": {"type": "file", "required": "True", "description": "Image data"},
        "fluxcal_data": {"type": "file", "description": "Fluxcal data"},
        "centroid_X": {"type": "number"},
        "centroid_Y": {"type": "number"},
        "spaxel_buffer": {"type": "number"},
    }
    post_data = {
        "name": name,
        "display_name": "Spectral_Cube_Analysis",
        "description": "Spectral_Cube_Analysis description",
        "version": "1.0",
        "contact_name": "Michael Coughlin",
        "url": "http://localhost:7003/analysis/spectral_cube_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "spectrum_fitting",
        "input_data_types": [],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator('//*[text()="External Analysis"]').first).to_be_visible()

    page.locator('//div[@data-testid="analysisServiceSelect"]').first.click()
    page.locator(f'//li[text()="{name}"]').first.click()

    page.locator('//input[@id="root_image_data"]').first.set_input_files(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "../data",
            "spectral_cube_analysis.fits",
        )
    )

    expect(page.locator("ul.file-info li").first).to_be_visible()
    page.locator(
        '//div[@data-testid="analysis-service-request-form"]//*[@type="submit"]'
    ).first.click()
    expect(
        page.locator(
            f"//*[text()='Sending data to analysis service {name} to start the analysis.']"
        ).first
    ).to_be_visible()
