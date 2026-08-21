import time
import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.public_pages import PublicReleasePost, PublicReleaseUpdate
from skyportal_py.source_groups import SourceGroupsPost
from skyportal_py.sources import SourcePost

from skyportal.tests import api, assert_api, assert_api_fail, client


def test_create_release(
    view_only_token, manage_sources_token, public_source, public_group
):
    sp = client(manage_sources_token)
    link_name = str(uuid.uuid4())
    with pytest.raises(SkyPortalError, match="HTTP 401: Unauthorized") as err:
        client(view_only_token).post_public_release(
            PublicReleasePost(
                name="Name", link_name=link_name, group_ids=[public_group.id]
            )
        )
    assert err.value.status_code == 401

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "public_pages/release",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "public_pages/release",
        data={"false_data": "false"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Name is required")

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Link name is required")

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "public_pages/release",
        data={"name": "Name", "link_name": "Link name"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")

    with pytest.raises(SkyPortalError, match="Specify at least one group") as err:
        sp.post_public_release(
            PublicReleasePost(name="Name", link_name="Link name", group_ids=[])
        )
    assert err.value.status_code == 400

    error_validation_link_name = (
        "Link name must contain only alphanumeric characters, dashes, underscores, periods, "
        "or plus signs"
    )
    with pytest.raises(SkyPortalError, match=error_validation_link_name) as err:
        sp.post_public_release(
            PublicReleasePost(name="Name", link_name="Link name", group_ids=[0])
        )
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError, match=error_validation_link_name) as err:
        sp.post_public_release(
            PublicReleasePost(name="Name", link_name="Link_name_é", group_ids=[0])
        )
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError) as err:
        sp.post_public_release(
            PublicReleasePost(name="Name", link_name="Aa0_Zz9-.+", group_ids=[0])
        )
    assert err.value.status_code == 400
    assert str(err.value) != error_validation_link_name
    assert str(err.value) == "Invalid groups"

    release_id = sp.post_public_release(
        PublicReleasePost(
            name="Name",
            link_name=link_name,
            group_ids=[public_group.id],
        )
    ).id

    releases = sp.fetch_public_releases()
    release = next(r for r in releases if r.id == release_id)
    assert release.is_visible is True
    assert release.auto_publish_enabled is False
    assert release.group_ids == [public_group.id]

    with pytest.raises(SkyPortalError, match="This link name is already in use") as err:
        sp.post_public_release(
            PublicReleasePost(
                name="Name",
                link_name=link_name,
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400


def test_update_release(
    view_only_token, manage_sources_token, public_source, public_group
):
    sp = client(manage_sources_token)
    link_name = str(uuid.uuid4())
    release_id = sp.post_public_release(
        PublicReleasePost(
            name="Name",
            link_name=link_name,
            group_ids=[public_group.id],
        )
    ).id

    with pytest.raises(SkyPortalError, match="HTTP 401: Unauthorized") as err:
        client(view_only_token).update_public_release(
            release_id, PublicReleaseUpdate(name="Name", group_ids=[public_group.id])
        )
    assert err.value.status_code == 401

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "No data provided")

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={"false_data": "false"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Name is required")

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "PATCH",
        f"public_pages/release/{release_id}",
        data={"name": "Name"},
        token=manage_sources_token,
    )
    assert_api_fail(status, data, 400, "Specify at least one group")

    with pytest.raises(SkyPortalError, match="Specify at least one group") as err:
        sp.update_public_release(
            release_id, PublicReleaseUpdate(name="Name", group_ids=[])
        )
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError, match="Invalid groups") as err:
        sp.update_public_release(
            release_id, PublicReleaseUpdate(name="Name", group_ids=[0])
        )
    assert err.value.status_code == 400

    releases = sp.fetch_public_releases()
    release = next(r for r in releases if r.id == release_id)
    assert release.is_visible is True
    assert release.auto_publish_enabled is False

    sp.update_public_release(
        release_id,
        PublicReleaseUpdate(
            name="Name",
            group_ids=[public_group.id],
            is_visible=False,
            auto_publish_enabled=True,
        ),
    )

    releases = sp.fetch_public_releases()
    release = next(r for r in releases if r.id == release_id)
    assert release.is_visible is False
    assert release.auto_publish_enabled is True
    assert release.link_name == link_name

    # raw api: PublicReleaseUpdate omits link_name by design (it is immutable server-side)
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

    releases = sp.fetch_public_releases()
    release = next(r for r in releases if r.id == release_id)
    assert release.link_name != "new_link_name"
    assert release.link_name == link_name


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
    release_id = (
        client(manage_sources_token)
        .post_public_release(
            PublicReleasePost(
                name="Name",
                link_name=link_name,
                group_ids=[public_group.id],
                auto_publish_enabled=False,
            )
        )
        .id
    )

    # create a source in the same group
    source_id = str(uuid.uuid4())
    client(super_admin_token).post_source(
        SourcePost(
            id=source_id,
            ra=26.5,
            dec=28.3,
            redshift=0.5,
            group_ids=[public_group.id],
        )
    )

    # check that the source have not been published
    pages = client(view_only_token).fetch_public_source_pages(source_id)
    assert len(pages) == 0

    # update the release to auto_publish_enabled to true
    client(manage_sources_token).update_public_release(
        release_id,
        PublicReleaseUpdate(
            name="Name",
            group_ids=[public_group.id],
            auto_publish_enabled=True,
        ),
    )

    # create a new source in the same group
    new_source_id = str(uuid.uuid4())
    client(super_admin_token).post_source(
        SourcePost(
            id=new_source_id,
            ra=26.5,
            dec=28.3,
            redshift=0.5,
            group_ids=[public_group.id],
        )
    )

    # check that the new source have been published
    for n_times in range(3):
        pages = client(view_only_token).fetch_public_source_pages(new_source_id)
        if len(pages) == 1:
            assert pages[0].release_link_name == link_name
            break
        time.sleep(2)
    assert n_times < 2

    # Update the source by first unregister it to the release group.
    client(upload_data_token).post_source_groups(
        SourceGroupsPost(
            obj_id=new_source_id,
            unsave_group_ids=[public_group.id],
        )
    )

    # check that the automatically published source have been deleted
    for n_times in range(3):
        pages = client(view_only_token).fetch_public_source_pages(new_source_id)
        if len(pages) == 0:
            break
        time.sleep(2)
    assert n_times < 2

    # Update the source by register it back to the release group.
    client(upload_data_token).post_source_groups(
        SourceGroupsPost(
            obj_id=new_source_id,
            invite_group_ids=[public_group.id],
        )
    )

    for n_time in range(3):
        # check that the new source have been published
        pages = client(view_only_token).fetch_public_source_pages(new_source_id)

        if len(pages) == 1:
            assert pages[0].release_link_name == link_name
            break
        else:
            time.sleep(2)
    assert n_time < 2

    client(view_only_token).delete_obj(source_id)

    client(view_only_token).delete_obj(new_source_id)


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
    client(manage_sources_token).post_public_release(
        PublicReleasePost(
            name="Name",
            link_name=link_name,
            group_ids=[public_group.id],
            auto_publish_enabled=True,
        )
    )

    # Update the source by first unregister it to the release group.
    client(upload_data_token).post_source_groups(
        SourceGroupsPost(
            obj_id=public_source.id,
            unsave_group_ids=[public_group.id],
        )
    )

    # check that no source have been already published in the release
    pages = client(view_only_token).fetch_public_source_pages(public_source.id)
    assert all(x.release_link_name != link_name for x in pages)

    # Update the source by register it back to the release group.
    client(upload_data_token).post_source_groups(
        SourceGroupsPost(
            obj_id=public_source.id,
            invite_group_ids=[public_group.id],
        )
    )

    for n_time in range(3):
        # check that the source have been published
        pages = client(view_only_token).fetch_public_source_pages(public_source.id)

        if any(x.release_link_name == link_name for x in pages):
            break
        else:
            time.sleep(2)
    assert n_time < 2


def test_delete_release(
    view_only_token, manage_sources_token, public_source, public_group
):
    link_name = str(uuid.uuid4())
    release_id = (
        client(manage_sources_token)
        .post_public_release(
            PublicReleasePost(
                name="Name",
                link_name=link_name,
                group_ids=[public_group.id],
            )
        )
        .id
    )

    # raw api: intentionally malformed request (no release ID) the typed client can't produce
    status, data = api("DELETE", "public_pages/release/", token=view_only_token)
    assert_api_fail(status, data, 405, "HTTP 405: Method Not Allowed")

    with pytest.raises(SkyPortalError, match="HTTP 401: Unauthorized") as err:
        client(view_only_token).delete_public_release(release_id)
    assert err.value.status_code == 401

    client(manage_sources_token).delete_public_release(release_id)

    with pytest.raises(SkyPortalError, match="Release not found") as err:
        client(manage_sources_token).delete_public_release(release_id)
    assert err.value.status_code == 404
