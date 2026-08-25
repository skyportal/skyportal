from skyportal.tests import api, assert_api, assert_api_fail


def test_create_page(view_only_token, manage_sources_token, public_source):
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={},
        token=view_only_token,
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")

    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={"": {}},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Options are required")

    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id[:1]}",
        data={"options": {}},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 404, "Source not found")

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

    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={
            "options": {},
            "release_id": 0,
        },
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 404, "Release not found")

    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={"options": {}},
        token=manage_sources_token,
    )
    assert_api(status, data)
    public_source_page_id = data["data"]["id"]

    status, data = api(
        "GET", f"public_pages/source/{public_source.id}", token=manage_sources_token
    )
    assert_api(status, data)
    assert any(item["id"] == public_source_page_id for item in data["data"])


def test_create_page_groups_and_streams(
    super_admin_token, manage_sources_token, public_source
):
    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry",
        token=manage_sources_token,
    )
    assert_api(status, data)
    assert len(data["data"]) > 0

    status, data = api(
        "GET",
        f"sources/{public_source.id}/spectra",
        token=manage_sources_token,
    )
    assert_api(status, data)
    assert len(data["data"]) > 0

    # Add summary to source
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={"summary": "This is a summary"},
        token=super_admin_token,
    )
    assert_api(status, data)
    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        token=manage_sources_token,
    )
    assert_api(status, data)
    assert len(data["data"]["summary"]) > 0

    # No classifications
    status, data = api(
        "GET",
        f"sources/{public_source.id}/classifications",
        token=manage_sources_token,
    )
    assert_api(status, data)
    assert len(data["data"]) == 0

    # No groups and streams select and all includes to true
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={
            "options": {
                "include_summary": True,
                "include_photometry": True,
                "include_spectroscopy": True,
                "include_classifications": True,
                "groups": [],
                "streams": [],
            },
        },
        token=manage_sources_token,
    )
    public_source_page_id = data["data"]["id"]
    assert_api(status, data)
    status, data = api(
        "GET",
        f"public_pages/source/{public_source.id}",
        token=manage_sources_token,
    )
    assert_api(status, data)
    public_source_page = next(
        item for item in data["data"] if item["id"] == public_source_page_id
    )
    assert public_source_page["options"]["summary"] == "public"
    assert public_source_page["options"]["photometry"] == "public"
    assert public_source_page["options"]["spectroscopy"] == "public"
    assert public_source_page["options"]["classifications"] == "no data"

    # No groups and streams select and all includes to false
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={
            "options": {
                "include_summary": False,
                "include_photometry": False,
                "include_spectroscopy": False,
                "include_classifications": False,
                "groups": [],
                "streams": [],
            },
        },
        token=manage_sources_token,
    )
    assert_api(status, data)
    public_source_page_id = data["data"]["id"]
    status, data = api(
        "GET",
        f"public_pages/source/{public_source.id}",
        token=manage_sources_token,
    )
    public_source_page = next(
        item for item in data["data"] if item["id"] == public_source_page_id
    )
    assert public_source_page["options"]["summary"] == "private"
    assert public_source_page["options"]["photometry"] == "private"
    assert public_source_page["options"]["spectroscopy"] == "private"
    assert public_source_page["options"]["classifications"] == "private"

    # Bad groups and streams select
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={
            "options": {
                "include_summary": True,
                "include_photometry": True,
                "include_spectroscopy": True,
                "include_classifications": True,
                "groups": [0],
                "streams": [0],
            },
        },
        token=manage_sources_token,
    )
    assert_api(status, data)
    public_source_page_id = data["data"]["id"]
    status, data = api(
        "GET",
        f"public_pages/source/{public_source.id}",
        token=manage_sources_token,
    )
    public_source_page = next(
        item for item in data["data"] if item["id"] == public_source_page_id
    )
    # No data found for this group and stream because they don't exist
    assert public_source_page["options"]["photometry"] == "no data"
    assert public_source_page["options"]["spectroscopy"] == "no data"
    assert public_source_page["options"]["classifications"] == "no data"
    # Summary is still public because it is not link to group or stream
    assert public_source_page["options"]["summary"] == "public"


def test_delete_page(view_only_token, manage_sources_token, public_source):
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={"options": {}},
        token=manage_sources_token,
    )
    assert_api(status, data)
    public_source_page_id = data["data"]["id"]

    status, data = api(
        "DELETE", f"public_pages/source/{public_source_page_id}", token=view_only_token
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")

    status, data = api(
        "DELETE",
        f"public_pages/source/{public_source_page_id}",
        token=manage_sources_token,
    )
    assert_api(status, data)

    status, data = api(
        "DELETE",
        f"public_pages/source/{public_source_page_id}",
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 404, "Public source page not found")
