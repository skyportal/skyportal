import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import api, assert_api_fail, client


def test_create_page(view_only_token, manage_sources_token, public_source):
    sp = client(manage_sources_token)
    with pytest.raises(SkyPortalError, match="HTTP 401: Unauthorized") as err:
        client(view_only_token).post_public_source_page(public_source.id, {})
    assert err.value.status_code == 401

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={"": {}},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Options are required")

    with pytest.raises(SkyPortalError, match="Source not found") as err:
        sp.post_public_source_page(public_source.id[:1], {})
    assert err.value.status_code == 404

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={
            "options": {},
            "release_id": "",
        },
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Invalid release ID")

    with pytest.raises(SkyPortalError, match="Release not found") as err:
        sp.post_public_source_page(public_source.id, {}, release_id=0)
    assert err.value.status_code == 404

    public_source_page_id = sp.post_public_source_page(public_source.id, {}).id

    pages = sp.fetch_public_source_pages(public_source.id)
    assert any(item.id == public_source_page_id for item in pages)


def test_create_page_groups_and_streams(
    super_admin_token, manage_sources_token, public_source
):
    sp = client(manage_sources_token)
    assert len(sp.fetch_photometry(public_source.id)) > 0

    assert len(sp.fetch_spectra(public_source.id)) > 0

    # Add summary to source
    client(super_admin_token).update_source(
        public_source.id, summary="This is a summary"
    )
    assert len(sp.fetch_source(public_source.id).summary) > 0

    # No classifications
    assert len(sp.fetch_classifications(public_source.id)) == 0

    # No groups and streams select and all includes to true
    public_source_page_id = sp.post_public_source_page(
        public_source.id,
        {
            "include_summary": True,
            "include_photometry": True,
            "include_spectroscopy": True,
            "include_classifications": True,
            "groups": [],
            "streams": [],
        },
    ).id
    pages = sp.fetch_public_source_pages(public_source.id)
    public_source_page = next(
        item for item in pages if item.id == public_source_page_id
    )
    assert public_source_page.options.summary == "public"
    assert public_source_page.options.photometry == "public"
    assert public_source_page.options.spectroscopy == "public"
    assert public_source_page.options.classifications == "no data"

    # No groups and streams select and all includes to false
    public_source_page_id = sp.post_public_source_page(
        public_source.id,
        {
            "include_summary": False,
            "include_photometry": False,
            "include_spectroscopy": False,
            "include_classifications": False,
            "groups": [],
            "streams": [],
        },
    ).id
    pages = sp.fetch_public_source_pages(public_source.id)
    public_source_page = next(
        item for item in pages if item.id == public_source_page_id
    )
    assert public_source_page.options.summary == "private"
    assert public_source_page.options.photometry == "private"
    assert public_source_page.options.spectroscopy == "private"
    assert public_source_page.options.classifications == "private"

    # Bad groups and streams select
    public_source_page_id = sp.post_public_source_page(
        public_source.id,
        {
            "include_summary": True,
            "include_photometry": True,
            "include_spectroscopy": True,
            "include_classifications": True,
            "groups": [0],
            "streams": [0],
        },
    ).id
    pages = sp.fetch_public_source_pages(public_source.id)
    public_source_page = next(
        item for item in pages if item.id == public_source_page_id
    )
    # No data found for this group and stream because they don't exist
    assert public_source_page.options.photometry == "no data"
    assert public_source_page.options.spectroscopy == "no data"
    assert public_source_page.options.classifications == "no data"
    # Summary is still public because it is not link to group or stream
    assert public_source_page.options.summary == "public"


def test_delete_page(view_only_token, manage_sources_token, public_source):
    sp = client(manage_sources_token)
    public_source_page_id = sp.post_public_source_page(public_source.id, {}).id

    with pytest.raises(SkyPortalError, match="HTTP 401: Unauthorized") as err:
        client(view_only_token).delete_public_source_page(public_source_page_id)
    assert err.value.status_code == 401

    sp.delete_public_source_page(public_source_page_id)

    with pytest.raises(SkyPortalError, match="Public source page not found") as err:
        sp.delete_public_source_page(public_source_page_id)
    assert err.value.status_code == 404
