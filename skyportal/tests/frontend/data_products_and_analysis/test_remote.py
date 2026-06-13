# These tests can be run against a hosted instance and interact only with the
# server through the public-facing web interface (rather than injecting
# fixture data directly into the database). Used for testing broadly that a
# server or Docker image was started successfully.

from playwright.sync_api import expect

from skyportal.models import DBSession, Source


def test_remote(page):
    # TODO expand to cover the basics of all site functionality
    # (c.f. `test_pipeline_sequentially` from `cesium_web`)
    Source.query.delete()
    DBSession.commit()
    page.goto("/")
    assert "localhost" in page.url
    expect(page.locator('//p[contains(.,"New Sources")]').first).to_be_visible()
