from skyportal.tests import api, assert_api, assert_api_fail


# Test get method
def test_no_releases(view_only_token, public_source):
    status, data = api("GET", "public_pages/release", token=view_only_token)
    assert_api(status, data)
    assert data["data"] == []


# Test post method
def test_non_group_manage_sources_cannot_create_release(view_only_token, public_source):
    status, data = api(
        "POST",
        "public_pages/release",
        data={},
        token=view_only_token,
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")


def test_group_manage_sources_create_release_no_data(
    manage_sources_token, public_source
):
    status, data = api(
        "POST",
        "public_pages/release",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")


def test_group_manage_sources_create_release_no_precise_data(
    manage_sources_token, public_source
):
    status, data = api(
        "POST",
        "public_pages/release",
        data={"false_data": "false"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Name is required")

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Link name is required")

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link_name"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link_name", "group_ids": []},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")


def test_group_manage_sources_create_release_with_bad_link_name(
    manage_sources_token, public_source
):
    error_link_name_validation_message = (
        "Link name must contain only alphanumeric characters, dashes, underscores, "
        "periods, or plus signs"
    )
    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link name", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, error_link_name_validation_message)

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link_name_é", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, error_link_name_validation_message)

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Aa0_Zz9-.+", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data)
    assert not data["message"] == error_link_name_validation_message


def test_group_manage_sources_create_release_with_bad_group(
    manage_sources_token, public_source
):
    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link_name", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Invalid groups")


# Test delete method
def test_non_group_manage_sources_cannot_delete_release(
    view_only_token, manage_sources_token, public_source
):
    status, data = api("DELETE", f"public_pages/source/{0}", token=view_only_token)
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")
