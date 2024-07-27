from skyportal.tests import api, assert_api, assert_api_fail


def test_source_with_zero_public_pages(view_only_token, public_source):
    status, data = api(
        "GET", f"public_pages/source/{public_source.id}", token=view_only_token
    )
    assert_api(status, data)
    assert len(data["data"]) == 0


def test_non_group_manage_sources_cannot_create_page(view_only_token, public_source):
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={},
        token=view_only_token,
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")


def test_group_manage_sources_create_page_no_data(manage_sources_token, public_source):
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")


def test_group_manage_sources_create_page_with_data(
    manage_sources_token, public_source
):
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={'options': {}},
        token=manage_sources_token,
    )
    assert_api(status, data)

    status, data = api(
        "GET", f"public_pages/source/{public_source.id}", token=manage_sources_token
    )
    assert_api(status, data)
    assert len(data["data"]) == 1


def test_non_group_manage_sources_cannot_delete_page(
    view_only_token, manage_sources_token, public_source
):
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={'options': {}},
        token=manage_sources_token,
    )
    assert_api(status, data)

    status, data = api(
        "GET", f"public_pages/source/{public_source.id}", token=view_only_token
    )
    assert_api(status, data)
    assert len(data["data"]) == 1
    page_id = data["data"][0]["id"]

    status, data = api(
        "DELETE", f"public_pages/source/{page_id}", token=view_only_token
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")


def test_group_manage_sources_delete_page(manage_sources_token, public_source):
    status, data = api(
        "POST",
        f"public_pages/source/{public_source.id}",
        data={'options': {}},
        token=manage_sources_token,
    )
    assert_api(status, data)

    status, data = api(
        "GET", f"public_pages/source/{public_source.id}", token=manage_sources_token
    )
    assert_api(status, data)
    assert len(data["data"]) == 1
    page_id = data["data"][0]["id"]

    status, data = api(
        "DELETE", f"public_pages/source/{page_id}", token=manage_sources_token
    )
    assert_api(status, data)

    status, data = api(
        "GET", f"public_pages/source/{public_source.id}", token=manage_sources_token
    )
    assert_api(status, data)
    assert len(data["data"]) == 0
