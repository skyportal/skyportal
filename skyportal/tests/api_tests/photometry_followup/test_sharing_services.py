import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.groups import GroupPost
from skyportal_py.instruments import InstrumentPost
from skyportal_py.profile import ProfilePatch
from skyportal_py.sharing_services import (
    SharingServicePost,
    SharingServiceSubmissionPost,
)

from skyportal.tests import client


def test_post_and_delete_sharing_service(
    public_group,
    super_admin_token,
    view_only_token,
    super_admin_user,
    view_only_user,
    public_source,
    ztf_camera,
):
    sp = client(super_admin_token)

    # get all external sharing services
    initial_count = len(sp.fetch_sharing_services())

    # first, add a private group
    private_group_id = sp.post_group(GroupPost(name=str(uuid.uuid4()))).id

    request_data = SharingServicePost(
        name=str(uuid.uuid4()),
        owner_group_ids=[private_group_id],
        tns_bot_name=str(uuid.uuid4()),
        tns_bot_id=10,
        tns_source_group_id=200,
        tns_altdata={"api_key": "test_key"},
    )

    # add an external sharing service without specifying any instruments (should fail)
    with pytest.raises(
        SkyPortalError, match="At least one instrument must be specified for sharing"
    ) as err:
        sp.post_sharing_service(request_data)
    assert err.value.status_code == 400

    # add an external sharing service with instruments that are not valid (should fail)
    request_data.instrument_ids = [ztf_camera.id]
    with pytest.raises(SkyPortalError) as err:
        sp.post_sharing_service(request_data)
    assert err.value.status_code == 400
    assert f"Instrument {ztf_camera.name} not supported for sharing" in str(err.value)

    # post an instrument which name is supported for sharing, like ZTF
    ztf_instrument_id = sp.post_instrument(
        InstrumentPost(name="ZTF", telescope_id=ztf_camera.telescope_id, type="imager")
    ).id

    # add an external sharing service with instruments
    request_data.instrument_ids = [ztf_instrument_id]
    id = sp.post_sharing_service(request_data).id

    # get all external sharing services
    assert len(sp.fetch_sharing_services()) == initial_count + 1

    # get the external sharing service
    service = sp.fetch_sharing_service(id)
    assert len(service.groups) == 1

    assert service.name == request_data.name
    assert service.owner_group_ids == request_data.owner_group_ids
    assert service.tns_bot_name == request_data.tns_bot_name
    assert service.tns_bot_id == request_data.tns_bot_id
    assert service.tns_source_group_id == request_data.tns_source_group_id
    for instrument_id in request_data.instrument_ids:
        assert any(i.id == instrument_id for i in service.instruments)

    # get all sharing services with view only token (should not see it)
    assert len(client(view_only_token).fetch_sharing_services()) == 0

    # get the sharing service with view only token (should not see it)
    with pytest.raises(SkyPortalError, match="No sharing service with") as err:
        client(view_only_token).fetch_sharing_service(id)
    assert err.value.status_code == 400

    # add a group to the sharing service
    sp.update_sharing_service_group(id, public_group.id)

    # get the sharing service again, should have the new group
    assert len(sp.fetch_sharing_service(id).groups) == 2

    # edit the sharing service, to give it ownership and to set auto_share_to_tns to True
    sp.update_sharing_service_group(
        id, public_group.id, owner=True, auto_share_to_tns=True
    )

    # get the sharing service again, should have the new group edited
    service = sp.fetch_sharing_service(id)
    group = [g for g in service.groups if g.group_id == public_group.id]
    assert len(group) == 1
    assert group[0].owner is True
    assert group[0].auto_share_to_tns is True
    assert group[0].auto_share_to_hermes is False

    # try adding a coauthor with no affiliations to the sharing service
    with pytest.raises(SkyPortalError) as err:
        sp.post_sharing_service_coauthor(id, super_admin_user.id)
    assert err.value.status_code == 400
    assert "has no affiliation(s), required to be a coauthor" in str(err.value)

    # add an affiliation to the user
    sp.update_profile(ProfilePatch(affiliations=["CIT"]))

    # now add the coauthor
    sp.post_sharing_service_coauthor(id, super_admin_user.id)

    # get the sharing service again, should have the new coauthor
    service = sp.fetch_sharing_service(id)
    assert len(service.coauthors) == 1
    assert service.coauthors[0].user_id == super_admin_user.id

    # try adding the viewonly user as an auto_publisher of the sharing service public group, will fail (no affiliation)
    with pytest.raises(SkyPortalError) as err:
        sp.post_sharing_service_auto_publishers(
            id, public_group.id, [view_only_user.id]
        )
    assert err.value.status_code == 400
    assert "has no affiliation(s), required to be an auto_publisher of" in str(
        err.value
    )

    # add an affiliation to the user
    client(super_admin_token).update_profile(
        ProfilePatch(affiliations=["CIT"]), user_id=view_only_user.id
    )

    # now add the auto_publisher
    sp.post_sharing_service_auto_publishers(id, public_group.id, [view_only_user.id])

    # get the sharing service again, should have the new auto_publisher
    service = sp.fetch_sharing_service(id)
    assert len(service.groups) == 2
    group = [g for g in service.groups if g.group_id == public_group.id]
    assert len(group) == 1
    assert len(group[0].auto_publishers) == 1
    assert group[0].auto_publishers[0].user_id == view_only_user.id

    # publish the public source but don't specify the service to publish to (hermes or tns), should fail
    with pytest.raises(
        SkyPortalError,
        match="Either publish to TNS or publish to Hermes must be set to True",
    ) as err:
        sp.post_sharing_service_submission(
            SharingServiceSubmissionPost(
                obj_id=public_source.id,
                sharing_service_id=id,
                publishers="test publisher string",
                remarks="test remark string",
                archival=False,
            )
        )
    assert err.value.status_code == 400

    # publish the public source to Hermes and TNS, should fail because hermes token is not set in config
    with pytest.raises(
        SkyPortalError, match="This instance is not configured to use Hermes"
    ) as err:
        sp.post_sharing_service_submission(
            SharingServiceSubmissionPost(
                sharing_service_id=id,
                obj_id=public_source.id,
                publish_to_hermes=True,
                publish_to_tns=True,
                publishers="test publisher string",
                remarks="test remark string",
                archival=False,
            )
        )
    assert err.value.status_code == 400

    # publish the public source to TNS
    sp.post_sharing_service_submission(
        SharingServiceSubmissionPost(
            sharing_service_id=id,
            obj_id=public_source.id,
            publish_to_tns=True,
            publishers="test publisher string",
            remarks="test remark string",
            archival=False,
        )
    )

    # get the submission from the sharing service
    page = sp.fetch_sharing_service_submissions(sharing_service_id=id)
    assert page.sharing_service_id == id
    submissions = page.submissions
    assert len(submissions) >= 1
    assert submissions[0].obj_id == public_source.id
    assert submissions[0].custom_publishing_string == "test publisher string"
    assert submissions[0].custom_remarks_string == "test remark string"
    assert submissions[0].archival is False
    # TNS status should be pending
    assert "pending" in submissions[0].tns_status
    # Hermes status should be None
    assert submissions[0].hermes_status is None

    # remove the coauthor
    sp.delete_sharing_service_coauthor(id, super_admin_user.id)

    # remove the auto_publisher
    sp.delete_sharing_service_auto_publishers(id, public_group.id, [view_only_user.id])

    # get the sharing service again, should have no auto publishers and no coauthors
    service = sp.fetch_sharing_service(id)
    assert len(service.groups) == 2
    group = [g for g in service.groups if g.group_id == public_group.id]
    assert len(group) == 1
    assert len(group[0].auto_publishers) == 0
    assert len(service.coauthors) == 0

    # delete the public group
    sp.delete_sharing_service_group(id, public_group.id)

    # try deleting the sharing service group (should fail as we always need at least one owner group)
    with pytest.raises(
        SkyPortalError,
        match="Cannot delete the only group owning this sharing service, add another group as an owner first.",
    ) as err:
        sp.delete_sharing_service_group(id, private_group_id)
    assert err.value.status_code == 400

    sp.delete_sharing_service(id)
