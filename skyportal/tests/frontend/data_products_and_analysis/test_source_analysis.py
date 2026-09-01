import json
import os
import re
import uuid

from playwright.sync_api import expect

from skyportal.tests import api

analysis_port = 6802


def _select_analysis_service(page, query):
    """Open the analysis-service Autocomplete, type `query` to filter, and click
    the matching option. Typing avoids the reopen-with-a-value filter trap and
    exercises the searchable dropdown."""
    search = page.locator('//div[@data-testid="analysisServiceSelect"]//input').first
    search.click()
    search.fill(query)
    # options are `<li role="option">` nested under grouped-by wrappers
    page.locator(f'//li[@role="option" and contains(., "{query}")]').first.click()


def test_analysis_start(
    page, user, public_source, analysis_service_token, public_group
):
    # public_source carries photometry (via ObjFactory), so a photometry-fitting
    # service is enabled for it.
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        # display_name carries the unique run id so the option is findable and we
        # verify the dropdown labels by display_name (not the machine name).
        "display_name": f"Test Analysis {name}",
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

    # select this run's service by its unique display_name to populate the form
    _select_analysis_service(page, name)
    # the confirmation notification is pushed over the websocket and dismisses
    # itself after 3s, so assert on the request the submit fires instead
    with page.expect_response(
        lambda response: (
            f"/api/obj/{public_source.id}/analysis/" in response.url
            and response.request.method == "POST"
        )
    ) as response_info:
        page.locator(
            '//div[@data-testid="analysis-service-request-form"]//*[@type="submit"]'
        ).first.click()
    assert response_info.value.status == 200


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
        "display_name": f"Spectral Cube {name}",
        "description": "Spectral_Cube_Analysis description",
        "version": "1.0",
        "contact_name": "Michael Coughlin",
        "url": "http://localhost:7003/analysis/spectral_cube_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "spectrum_fitting",
        # no required input data types -> not disabled on a photometry-less source
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

    _select_analysis_service(page, name)

    page.locator('//input[@id="root_image_data"]').first.set_input_files(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "../data",
            "spectral_cube_analysis.fits",
        )
    )

    expect(page.locator('//input[@id="root_image_data"]').first).to_have_value(
        re.compile(r"spectral_cube_analysis\.fits$")
    )
    # the confirmation notification is pushed over the websocket and dismisses
    # itself after 3s, so assert on the request the submit fires instead
    with page.expect_response(
        lambda response: (
            f"/api/obj/{public_source.id}/analysis/" in response.url
            and response.request.method == "POST"
        )
    ) as response_info:
        page.locator(
            '//div[@data-testid="analysis-service-request-form"]//*[@type="submit"]'
        ).first.click()
    assert response_info.value.status == 200


def test_analysis_service_dropdown_shows_display_name(
    page, user, public_source, analysis_service_token, public_group
):
    """The dropdown labels services by display_name, not the machine name."""
    name = str(uuid.uuid4())
    display_name = f"Human Readable {name}"
    post_data = {
        "name": name,
        "display_name": display_name,
        "description": "desc",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps({}),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }
    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator('//*[text()="External Analysis"]').first).to_be_visible()

    page.locator('//div[@data-testid="analysisServiceSelect"]//input').first.click()
    page.locator('//div[@data-testid="analysisServiceSelect"]//input').first.fill(name)
    # the option shows the display_name (which contains the unique id)
    expect(
        page.locator(f'//li[@role="option" and contains(., "{display_name}")]').first
    ).to_be_visible()


def test_analysis_service_disabled_without_required_photometry(
    page, user, public_source_no_data, analysis_service_token, public_group
):
    """A photometry-requiring service is disabled on a source with no photometry
    (public_source_no_data has none)."""
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": f"Needs Photometry {name}",
        "description": "desc",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps({}),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }
    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source_no_data.id}")
    expect(page.locator('//*[text()="External Analysis"]').first).to_be_visible()

    page.locator('//div[@data-testid="analysisServiceSelect"]//input').first.click()
    page.locator('//div[@data-testid="analysisServiceSelect"]//input').first.fill(name)
    # the option renders but is disabled (aria-disabled) because the source has
    # no photometry to feed the fit
    expect(
        page.locator(f'//li[@role="option" and contains(., "{name}")]').first
    ).to_have_attribute("aria-disabled", "true")
