# These tests can be run against a hosted instance and interact only with the
# server through the public-facing web interface (rather than injecting
# fixture data directly into the database). Used for testing broadly that a
# server or Docker image was started successfully.

from skyportal.models import Source, DBSession


def test_remote(driver):
    # TODO expand to cover the basics of all site functionality
    # (c.f. `test_pipeline_sequentially` from `cesium_web`)
    Source.query.delete()
    DBSession.commit()
    driver.get("/")
    assert 'localhost' in driver.current_url
    driver.wait_for_xpath('//div[contains(.,"Welcome to SkyPortal.")]')
