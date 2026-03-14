import uuid

from skyportal.tests import api


def test_post_and_delete_sharing_service(
    public_group,
    super_admin_token,
    view_only_token,
    super_admin_user,
    view_only_user,
    public_source,
    ztf_camera,
):
    # get all external sharing services
    status, data = api("GET", "sharing_service", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    initial_count = len(data["data"])

    # first, add a private group
    status, data = api(
        "POST", "groups", data={"name": str(uuid.uuid4())}, token=super_admin_token
    )
    assert status == 200
    private_group_id = data["data"]["id"]

    request_data = {
        "name": str(uuid.uuid4()),
        "owner_group_ids": [private_group_id],
        "tns_bot_name": str(uuid.uuid4()),
        "tns_bot_id": 10,
        "tns_source_group_id": 200,
        "_tns_altdata": '{"api_key": "test_key"}',
    }

    # add an external sharing service without specifying any instruments (should fail)
    status, data = api(
        "PUT", "sharing_service", data=request_data, token=super_admin_token
    )
    assert status == 400
    assert "At least one instrument must be specified for sharing" in data["message"]

    # add an external sharing service with instruments that are not valid (should fail)
    request_data["instrument_ids"] = [ztf_camera.id]
    status, data = api(
        "PUT", "sharing_service", data=request_data, token=super_admin_token
    )
    assert status == 400
    assert f"Instrument {ztf_camera.name} not supported for sharing" in data["message"]

    # post an instrument which name is supported for sharing, like ZTF
    status, data = api(
        "POST",
        "instrument",
        data={"name": "ZTF", "telescope_id": ztf_camera.telescope_id, "type": "imager"},
        token=super_admin_token,
    )
    assert status == 200
    assert "data" in data
    assert "id" in data["data"]
    ztf_instrument_id = data["data"]["id"]

    # add an external sharing service with instruments
    request_data["instrument_ids"] = [ztf_instrument_id]
    status, data = api(
        "PUT", "sharing_service", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    # get all external sharing services
    status, data = api("GET", "sharing_service", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == initial_count + 1

    # get the external sharing service
    status, data = api("GET", f"sharing_service/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 1

    for key in request_data:
        if key == "_tns_altdata":
            continue
        if key == "instrument_ids":
            for instrument_id in request_data[key]:
                assert any(
                    i["id"] == instrument_id for i in data["data"]["instruments"]
                )
            continue
        assert data["data"][key] == request_data[key]

    # get all sharing services with view only token (should not see it)
    status, data = api("GET", "sharing_service", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 0

    # get the sharing service with view only token (should not see it)
    status, data = api("GET", f"sharing_service/{id}", token=view_only_token)
    assert status == 400
    assert "No sharing service with" in data["message"]

    # add a group to the sharing service
    status, data = api(
        "PUT",
        f"sharing_service/{id}/group",
        data={"group_id": public_group.id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # get the sharing service again, should have the new group
    status, data = api("GET", f"sharing_service/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 2

    # edit the sharing service, to give it ownership and to set auto_share_to_tns to True
    status, data = api(
        "PUT",
        f"sharing_service/{id}/group/{public_group.id}",
        data={"owner": True, "auto_share_to_tns": True},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # get the sharing service again, should have the new group edited
    status, data = api("GET", f"sharing_service/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    group = [g for g in data["data"]["groups"] if g["group_id"] == public_group.id]
    assert len(group) == 1
    assert group[0]["owner"] is True
    assert group[0]["auto_share_to_tns"] is True
    assert group[0]["auto_share_to_hermes"] is False

    # try adding a coauthor with no affiliations to the sharing service
    status, data = api(
        "POST",
        f"sharing_service/{id}/coauthor/{super_admin_user.id}",
        token=super_admin_token,
    )
    assert status == 400
    assert "has no affiliation(s), required to be a coauthor" in data["message"]

    # add an affiliation to the user
    status, data = api(
        "PATCH",
        f"internal/profile/{super_admin_user.id}",
        data={"affiliations": ["CIT"]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # now add the coauthor
    status, data = api(
        "POST",
        f"sharing_service/{id}/coauthor/{super_admin_user.id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # get the sharing service again, should have the new coauthor
    status, data = api("GET", f"sharing_service/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["coauthors"]) == 1
    assert data["data"]["coauthors"][0]["user_id"] == super_admin_user.id

    # try adding the viewonly user as an auto_publisher of the sharing service public group, will fail (no affiliation)
    status, data = api(
        "POST",
        f"sharing_service/{id}/group/{public_group.id}/auto_publisher",
        data={"user_ids": [view_only_user.id]},
        token=super_admin_token,
    )
    assert status == 400
    assert (
        "has no affiliation(s), required to be an auto_publisher of" in data["message"]
    )

    # add an affiliation to the user
    status, data = api(
        "PATCH",
        f"internal/profile/{view_only_user.id}",
        data={"affiliations": ["CIT"]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # now add the auto_publisher
    status, data = api(
        "POST",
        f"sharing_service/{id}/group/{public_group.id}/auto_publisher",
        data={"user_ids": [view_only_user.id]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # get the sharing service again, should have the new auto_publisher
    status, data = api("GET", f"sharing_service/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 2
    group = [g for g in data["data"]["groups"] if g["group_id"] == public_group.id]
    assert len(group) == 1
    assert len(group[0]["auto_publishers"]) == 1
    assert group[0]["auto_publishers"][0]["user_id"] == view_only_user.id

    # publish the public source but don't specify the service to publish to (hermes or tns), should fail
    request_data = {
        "obj_id": public_source.id,
        "sharing_service_id": id,
        "publishers": "test publisher string",
        "remarks": "test remark string",
        "archival": False,
    }
    status, data = api(
        "POST",
        f"sharing_service/submission",
        data=request_data,
        token=super_admin_token,
    )
    assert status == 400
    assert (
        "Either publish to TNS or publish to Hermes must be set to True"
        in data["message"]
    )

    # publish the public source to Hermes and TNS, should fail because hermes token is not set in config
    request_data = {
        "sharing_service_id": id,
        "obj_id": public_source.id,
        "publish_to_hermes": True,
        "publish_to_tns": True,
        "publishers": "test publisher string",
        "remarks": "test remark string",
        "archival": False,
    }
    status, data = api(
        "POST",
        f"sharing_service/submission",
        data=request_data,
        token=super_admin_token,
    )
    assert status == 400
    assert "This instance is not configured to use Hermes" in data["message"]

    # publish the public source to TNS
    request_data = {
        "sharing_service_id": id,
        "obj_id": public_source.id,
        "publish_to_tns": True,
        "publishers": "test publisher string",
        "remarks": "test remark string",
        "archival": False,
    }
    status, data = api(
        "POST",
        f"sharing_service/submission",
        data=request_data,
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # get the submission from the sharing service
    status, data = api(
        "GET",
        f"sharing_service/submission",
        params={"sharing_service_id": id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["sharing_service_id"] == id
    submissions = data["data"]["submissions"]
    assert len(submissions) >= 1
    assert submissions[0]["obj_id"] == public_source.id
    assert submissions[0]["custom_publishing_string"] == "test publisher string"
    assert submissions[0]["custom_remarks_string"] == "test remark string"
    assert submissions[0]["archival"] is False
    # TNS status should be pending
    assert "pending" in submissions[0]["tns_status"]
    # Hermes status should be None
    assert submissions[0]["hermes_status"] is None

    # remove the coauthor
    status, data = api(
        "DELETE",
        f"sharing_service/{id}/coauthor/{super_admin_user.id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # remove the auto_publisher
    status, data = api(
        "DELETE",
        f"sharing_service/{id}/group/{public_group.id}/auto_publisher/{view_only_user.id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # get the sharing service again, should have no auto publishers and no coauthors
    status, data = api("GET", f"sharing_service/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 2
    group = [g for g in data["data"]["groups"] if g["group_id"] == public_group.id]
    assert len(group) == 1
    assert len(group[0]["auto_publishers"]) == 0
    assert len(data["data"]["coauthors"]) == 0

    # delete the public group
    status, data = api(
        "DELETE",
        f"sharing_service/{id}/group/{public_group.id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # try deleting the sharing service group (should fail as we always need at least one owner group)
    status, data = api(
        "DELETE",
        f"sharing_service/{id}/group/{private_group_id}",
        token=super_admin_token,
    )
    assert status == 400
    assert (
        "Cannot delete the only group owning this sharing service, add another group as an owner first."
        in data["message"]
    )

    status, data = api("DELETE", f"sharing_service/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
