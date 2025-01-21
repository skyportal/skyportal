import time
import uuid

from skyportal.tests import api, assert_api, assert_api_fail


def test_create_release(
    view_only_token, manage_sources_token, public_source, public_group
):
    link_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "public_pages/release",
        data={},
        token=view_only_token,
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")

    status, data = api(
        "POST",
        "public_pages/release",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

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
        data={"name": "Name", "link_name": "Link name"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link name", "group_ids": []},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")

    error_validation_link_name = (
        "Link name must contain only alphanumeric characters, dashes, underscores, periods, "
        "or plus signs"
    )
    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link name", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, error_validation_link_name)

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link_name_é", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, error_validation_link_name)

    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Aa0_Zz9-.+", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400)
    assert data["message"] != error_validation_link_name
    assert data["message"] == "Invalid groups"

    status, data = api(
        "POST",
        "public_pages/release",
        data={
            "name": "Name",
            "link_name": link_name,
            "group_ids": [public_group.id],
        },
        token=manage_sources_token,
    )
    assert_api(status, data)
    release_id = data["data"]["id"]

    status, data = api("GET", "public_pages/release", token=manage_sources_token)
    assert_api(status, data)
    release = next(r for r in data["data"] if r["id"] == release_id)
    assert release["is_visible"] is True
    assert release["auto_publish_enabled"] is False
    assert release["group_ids"] == [public_group.id]

    status, data = api(
        "POST",
        "public_pages/release",
        data={
            "name": "Name",
            "link_name": link_name,
            "group_ids": [public_group.id],
        },
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "This link name is already in use")


def test_update_release(
    view_only_token, manage_sources_token, public_source, public_group
):
    link_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "public_pages/release",
        data={
            "name": "Name",
            "link_name": link_name,
            "group_ids": [public_group.id],
        },
        token=manage_sources_token,
    )
    assert_api(status, data)
    release_id = data["data"]["id"]

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={},
        token=view_only_token,
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={"false_data": "false"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Name is required")

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={"name": "Name"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={"name": "Name", "group_ids": []},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={"name": "Name", "group_ids": [0]},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Invalid groups")

    status, data = api("GET", "public_pages/release", token=manage_sources_token)
    assert_api(status, data)
    release = next(r for r in data["data"] if r["id"] == release_id)
    assert release["is_visible"] is True
    assert release["auto_publish_enabled"] is False

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={
            "name": "Name",
            "group_ids": [public_group.id],
            "is_visible": False,
            "auto_publish_enabled": True,
        },
        token=manage_sources_token,
    )
    assert_api(status, data)

    status, data = api("GET", "public_pages/release", token=manage_sources_token)
    assert_api(status, data)
    release = next(r for r in data["data"] if r["id"] == release_id)
    assert release["is_visible"] is False
    assert release["auto_publish_enabled"] is True
    assert release["link_name"] == link_name

    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={
            "name": "Name",
            "group_ids": [public_group.id],
            "link_name": "new_link_name",
        },
        token=manage_sources_token,
    )
    assert_api(status, data)

    status, data = api("GET", "public_pages/release", token=manage_sources_token)
    assert_api(status, data)
    release = next(r for r in data["data"] if r["id"] == release_id)
    assert release["link_name"] != "new_link_name"
    assert release["link_name"] == link_name


def test_auto_publish_enabled_and_delete_sources_in_same_group_when_create_or_update_source(
    super_admin_token,
    view_only_token,
    upload_data_token,
    manage_sources_token,
    public_source,
    public_group,
):
    link_name = str(uuid.uuid4())
    # create a release with auto_publish_enabled to false
    status, data = api(
        "POST",
        "public_pages/release",
        data={
            "name": "Name",
            "link_name": link_name,
            "group_ids": [public_group.id],
            "auto_publish_enabled": False,
        },
        token=manage_sources_token,
    )
    assert_api(status, data)
    release_id = data["data"]["id"]

    # create a source in the same group
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": 26.5,
            "dec": 28.3,
            "redshift": 0.5,
            "group_ids": [public_group.id],
        },
        token=super_admin_token,
    )
    assert_api(status, data)

    # check that the source have not been published
    status, data = api(
        "GET",
        f"public_pages/source/{source_id}",
        token=view_only_token,
    )
    assert_api(status, data)
    assert len(data["data"]) == 0

    # update the release to auto_publish_enabled to true
    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={
            "name": "Name",
            "group_ids": [public_group.id],
            "auto_publish_enabled": True,
        },
        token=manage_sources_token,
    )
    assert_api(status, data)

    # create a new source in the same group
    new_source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": new_source_id,
            "ra": 26.5,
            "dec": 28.3,
            "redshift": 0.5,
            "group_ids": [public_group.id],
        },
        token=super_admin_token,
    )
    assert_api(status, data)

    # check that the new source have been published
    for n_times in range(3):
        status, data = api(
            "GET",
            f"public_pages/source/{new_source_id}",
            token=view_only_token,
        )
        assert_api(status, data)
        if len(data["data"]) == 1:
            assert data["data"][0]["release_link_name"] == link_name
            break
        time.sleep(2)
    assert n_times < 2

    # Update the source by first unregister it to the release group.
    status, data = api(
        "POST",
        "source_groups",
        data={
            "objId": new_source_id,
            "unsaveGroupIds": [public_group.id],
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    # check that the automatically published source have been deleted
    for n_times in range(3):
        status, data = api(
            "GET",
            f"public_pages/source/{new_source_id}",
            token=view_only_token,
        )
        assert_api(status, data)
        if len(data["data"]) == 0:
            break
        time.sleep(2)
    assert n_times < 2

    # Update the source by register it back to the release group.
    status, data = api(
        "POST",
        "source_groups",
        data={
            "objId": new_source_id,
            "inviteGroupIds": [public_group.id],
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    for n_time in range(3):
        # check that the new source have been published
        status, data = api(
            "GET",
            f"public_pages/source/{new_source_id}",
            token=view_only_token,
        )
        assert_api(status, data)

        if len(data["data"]) == 1:
            assert data["data"][0]["release_link_name"] == link_name
            break
        else:
            time.sleep(2)
    assert n_time < 2

    status, data = api(
        "DELETE",
        f"objs/{source_id}",
        token=view_only_token,
    )
    assert_api(status, data)

    status, data = api(
        "DELETE",
        f"objs/{new_source_id}",
        token=view_only_token,
    )
    assert_api(status, data)


def test_auto_publish_enabled_and_delete_sources_in_same_group_when_update_source_with_photometry(
    super_admin_token,
    view_only_token,
    upload_data_token,
    manage_sources_token,
    public_source,
    public_group,
):
    link_name = str(uuid.uuid4())
    # create a release with auto_publish_enabled to true
    status, data = api(
        "POST",
        "public_pages/release",
        data={
            "name": "Name",
            "link_name": link_name,
            "group_ids": [public_group.id],
            "auto_publish_enabled": True,
        },
        token=manage_sources_token,
    )
    assert_api(status, data)

    # Update the source by first unregister it to the release group.
    status, data = api(
        "POST",
        "source_groups",
        data={
            "objId": public_source.id,
            "unsaveGroupIds": [public_group.id],
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    # check that no source have been already published in the release
    status, data = api(
        "GET",
        f"public_pages/source/{public_source.id}",
        token=view_only_token,
    )
    assert_api(status, data)
    assert all(x["release_link_name"] != link_name for x in data["data"])

    # Update the source by register it back to the release group.
    status, data = api(
        "POST",
        "source_groups",
        data={
            "objId": public_source.id,
            "inviteGroupIds": [public_group.id],
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    for n_time in range(3):
        # check that the source have been published
        status, data = api(
            "GET",
            f"public_pages/source/{public_source.id}",
            token=view_only_token,
        )
        assert_api(status, data)

        if any(x["release_link_name"] == link_name for x in data["data"]):
            break
        else:
            time.sleep(2)
    assert n_time < 2


def test_delete_release(
    view_only_token, manage_sources_token, public_source, public_group
):
    link_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "public_pages/release",
        data={
            "name": "Name",
            "link_name": link_name,
            "group_ids": [public_group.id],
        },
        token=manage_sources_token,
    )
    assert_api(status, data)
    release_id = data["data"]["id"]

    status, data = api("DELETE", "public_pages/release/", token=view_only_token)
    assert_api_fail(status, data, 405, "HTTP 405: Method Not Allowed")

    status, data = api(
        "DELETE", f"public_pages/release/{release_id}", token=view_only_token
    )
    assert_api_fail(status, data, 401, "HTTP 401: Unauthorized")

    status, data = api(
        "DELETE", f"public_pages/release/{release_id}", token=manage_sources_token
    )
    assert_api(status, data)

    status, data = api(
        "DELETE", f"public_pages/release/{release_id}", token=manage_sources_token
    )
    assert_api_fail(status, data, 404, "Release not found")
