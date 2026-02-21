import uuid

from skyportal.model_util import create_token
from skyportal.tests import api, assert_api, assert_api_fail


def test_add_objects_to_list(user, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]["id"]  # get the list item ID

    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate2.id,
            "list_name": "favorites",
        },
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]["id"]  # get the list item ID

    # get the list back, should include only two items
    status, data = api("GET", f"listing/{user.id}?listName=favorites", token=token_id)

    assert status == 200
    new_list = data["data"]

    items = [item["id"] for item in new_list]

    assert set(items) == {item1, item2}

    # try to post a listing to a non-existing object
    fake_obj_id = str(uuid.uuid4())

    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": fake_obj_id, "list_name": "favorites"},
        token=token_id,
    )

    assert status == 400


def test_double_posting(user, public_candidate):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=token_id,
    )

    assert status == 200

    # try posting the same listing again!
    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=token_id,
    )

    assert status == 400


def test_add_remove_objects(user, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=token_id,
    )
    assert status == 200
    item1 = data["data"]["id"]  # get the list item ID

    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate2.id,
            "list_name": "favorites",
        },
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]["id"]  # get the list item ID

    status, data = api("DELETE", f"listing/{item1}", token=token_id)

    assert status == 200

    # get the list back, should include only one item
    status, data = api("GET", f"listing/{user.id}?listName=favorites", token=token_id)

    assert status == 200
    new_list = data["data"]

    items = [item["id"] for item in new_list]

    assert set(items) == {item2}


def test_add_objects_to_different_lists(user, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    list1 = str(uuid.uuid4())

    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": public_candidate.id, "list_name": list1},
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]["id"]  # get the list item ID

    list2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": public_candidate2.id, "list_name": list2},
        token=token_id,
    )

    assert status == 200

    # get the list back, should include only one item that matches list1
    status, data = api("GET", f"listing/{user.id}?listName={list1}", token=token_id)

    assert status == 200
    new_list = data["data"]

    items = [item["id"] for item in new_list]

    assert set(items) == {item1}


def test_patching_listing(user, user2, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    list1 = str(uuid.uuid4())

    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": public_candidate.id, "list_name": list1},
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]["id"]  # get the list item ID

    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": public_candidate2.id, "list_name": list1},
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]["id"]  # get the list item ID

    list2 = str(uuid.uuid4())
    status, data = api(
        "PATCH",
        f"listing/{item2}",
        data={"user_id": user.id, "obj_id": public_candidate2.id, "list_name": list2},
        token=token_id,
    )

    assert status == 200

    # get the list back, should include only one item that matches list2
    status, data = api("GET", f"listing/{user.id}?listName={list2}", token=token_id)
    print(data["data"])
    assert status == 200
    new_list = data["data"]

    assert len(new_list) == 1

    assert new_list[0]["id"] == item2  # the listing ID is the same

    assert new_list[0]["user_id"] == user.id  # user stays the same
    assert new_list[0]["obj_id"] == public_candidate2.id  # obj id is new
    assert new_list[0]["list_name"] == list2  # list name is new

    # try to patch with an invalid user id
    status, data = api(
        "PATCH",
        f"listing/{item1}",
        data={"user_id": user2.id, "obj_id": public_candidate2.id, "list_name": list2},
        token=token_id,
    )

    assert status == 400
    assert "Insufficient permission" in data["message"]


def test_listings_user_permissions(
    user,
    user2,
    super_admin_user,
    super_admin_token,
    upload_data_token,
    public_candidate,
    public_candidate2,
):
    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=upload_data_token,
    )

    assert_api(status, data)
    item1 = data["data"]["id"]  # get the list item ID

    # try to transfer ownership to a different user
    status, data = api(
        "PATCH",
        f"listing/{item1}",
        data={
            "user_id": user2.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=upload_data_token,
    )

    assert_api_fail(status, data, 400, "Insufficient permissions")

    # try to post to a different user
    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user2.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=upload_data_token,
    )
    assert_api_fail(
        status, data, 400, "Only admins can add listings to other users' accounts"
    )

    # try to add this to a different user, but with super admin privileges
    status, data = api(
        "PATCH",
        f"listing/{item1}",
        data={
            "user_id": user2.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=super_admin_token,
    )

    assert_api(status, data)

    # get the list back, should include only one item that matches user2
    status, data = api(
        "GET", f"listing/{user2.id}?listName=favorites", token=super_admin_token
    )

    assert_api(status, data)
    new_list = data["data"]

    assert len(new_list) == 1
    assert new_list[0]["id"] == item1  # the listing ID is the same
    assert new_list[0]["obj_id"] == public_candidate.id  # obj stays the same

    # try to patch with only partial data inputs
    # bring this listing back to first user with super token permission
    status, data = api(
        "PATCH",
        f"listing/{item1}",
        data={"user_id": user.id},
        token=super_admin_token,
    )

    assert_api(status, data)

    # change the object id only
    status, data = api(
        "PATCH",
        f"listing/{item1}",
        data={"obj_id": public_candidate2.id},
        token=upload_data_token,
    )

    assert_api(status, data)

    # change the list name only
    status, data = api(
        "PATCH",
        f"listing/{item1}",
        data={"list_name": "new_listing"},
        token=upload_data_token,
    )

    assert_api(status, data)

    # get the list back, should include only one item that matches user2
    status, data = api(
        "GET", f"listing/{user.id}?listName=new_listing", token=super_admin_token
    )

    assert_api(status, data)
    new_list = data["data"]

    assert len(new_list) == 1
    assert new_list[0]["id"] == item1  # the listing ID is the same
    assert new_list[0]["obj_id"] == public_candidate2.id  # obj was updated
    assert new_list[0]["user_id"] == user.id  # user was returned to original
    assert new_list[0]["list_name"] == "new_listing"  # new listing name


def test_invalid_listing_name_fails(user, upload_data_token, public_candidate):
    # we cannot post a listing with an empty string
    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": public_candidate.id, "list_name": ""},
        token=upload_data_token,
    )

    assert status == 400
    assert "must begin with alphanumeric/underscore" in data["message"]

    # we cannot post a listing with a non-alphanumeric first letter
    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": public_candidate.id, "list_name": " "},
        token=upload_data_token,
    )

    assert status == 400
    assert "must begin with alphanumeric/underscore" in data["message"]

    # we cannot post a listing with a non-alphanumeric first letter
    status, data = api(
        "POST",
        "listing",
        data={"user_id": user.id, "obj_id": public_candidate.id, "list_name": "-"},
        token=upload_data_token,
    )

    assert status == 400
    assert "must begin with alphanumeric/underscore" in data["message"]

    # this is ok
    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": user.id,
            "obj_id": public_candidate.id,
            "list_name": "favorites",
        },
        token=upload_data_token,
    )

    assert status == 200
    listing_id = data["data"]["id"]

    # we cannot post a listing with a non-alphanumeric first letter
    status, data = api(
        "PATCH",
        f"listing/{listing_id}",
        data={"user_id": user.id, "obj_id": public_candidate.id, "list_name": ""},
        token=upload_data_token,
    )

    assert status == 400
    assert "must begin with alphanumeric/underscore" in data["message"]
