import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.listings import ListingPost

from skyportal.model_util import create_token
from skyportal.tests import client


def test_add_objects_to_list(user, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )
    sp = client(token_id)

    item1 = sp.post_listing(
        ListingPost(
            user_id=user.id,
            obj_id=public_candidate.id,
            list_name="favorites",
        )
    ).id  # get the list item ID

    item2 = sp.post_listing(
        ListingPost(
            user_id=user.id,
            obj_id=public_candidate2.id,
            list_name="favorites",
        )
    ).id  # get the list item ID

    # get the list back, should include only two items
    new_list = sp.fetch_listings(user_id=user.id, list_name="favorites")

    items = [item.id for item in new_list]

    assert set(items) == {item1, item2}

    # try to post a listing to a non-existing object
    fake_obj_id = str(uuid.uuid4())

    with pytest.raises(SkyPortalError) as err:
        sp.post_listing(
            ListingPost(user_id=user.id, obj_id=fake_obj_id, list_name="favorites")
        )
    assert err.value.status_code == 400


def test_double_posting(user, public_candidate):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )
    sp = client(token_id)

    sp.post_listing(
        ListingPost(
            user_id=user.id,
            obj_id=public_candidate.id,
            list_name="favorites",
        )
    )

    # try posting the same listing again!
    with pytest.raises(SkyPortalError) as err:
        sp.post_listing(
            ListingPost(
                user_id=user.id,
                obj_id=public_candidate.id,
                list_name="favorites",
            )
        )
    assert err.value.status_code == 400


def test_add_remove_objects(user, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )
    sp = client(token_id)

    item1 = sp.post_listing(
        ListingPost(
            user_id=user.id,
            obj_id=public_candidate.id,
            list_name="favorites",
        )
    ).id  # get the list item ID

    item2 = sp.post_listing(
        ListingPost(
            user_id=user.id,
            obj_id=public_candidate2.id,
            list_name="favorites",
        )
    ).id  # get the list item ID

    sp.delete_listing(item1)

    # get the list back, should include only one item
    new_list = sp.fetch_listings(user_id=user.id, list_name="favorites")

    items = [item.id for item in new_list]

    assert set(items) == {item2}


def test_add_objects_to_different_lists(user, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )
    sp = client(token_id)

    list1 = str(uuid.uuid4())

    item1 = sp.post_listing(
        ListingPost(user_id=user.id, obj_id=public_candidate.id, list_name=list1)
    ).id  # get the list item ID

    list2 = str(uuid.uuid4())
    sp.post_listing(
        ListingPost(user_id=user.id, obj_id=public_candidate2.id, list_name=list2)
    )

    # get the list back, should include only one item that matches list1
    new_list = sp.fetch_listings(user_id=user.id, list_name=list1)

    items = [item.id for item in new_list]

    assert set(items) == {item1}


def test_patching_listing(user, user2, public_candidate, public_candidate2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )
    sp = client(token_id)

    list1 = str(uuid.uuid4())

    item1 = sp.post_listing(
        ListingPost(user_id=user.id, obj_id=public_candidate.id, list_name=list1)
    ).id  # get the list item ID

    item2 = sp.post_listing(
        ListingPost(user_id=user.id, obj_id=public_candidate2.id, list_name=list1)
    ).id  # get the list item ID

    list2 = str(uuid.uuid4())
    sp.update_listing(
        item2, user_id=user.id, obj_id=public_candidate2.id, list_name=list2
    )

    # get the list back, should include only one item that matches list2
    new_list = sp.fetch_listings(user_id=user.id, list_name=list2)
    print(new_list)

    assert len(new_list) == 1

    assert new_list[0].id == item2  # the listing ID is the same

    assert new_list[0].user_id == user.id  # user stays the same
    assert new_list[0].obj_id == public_candidate2.id  # obj id is new
    assert new_list[0].list_name == list2  # list name is new

    # try to patch with an invalid user id
    with pytest.raises(SkyPortalError, match="Insufficient permission") as err:
        sp.update_listing(
            item1, user_id=user2.id, obj_id=public_candidate2.id, list_name=list2
        )
    assert err.value.status_code == 400


def test_listings_user_permissions(
    user,
    user2,
    super_admin_user,
    super_admin_token,
    upload_data_token,
    public_candidate,
    public_candidate2,
):
    sp = client(upload_data_token)
    sp_admin = client(super_admin_token)

    item1 = sp.post_listing(
        ListingPost(
            user_id=user.id,
            obj_id=public_candidate.id,
            list_name="favorites",
        )
    ).id  # get the list item ID

    # try to transfer ownership to a different user
    with pytest.raises(SkyPortalError, match="Insufficient permissions") as err:
        sp.update_listing(
            item1,
            user_id=user2.id,
            obj_id=public_candidate.id,
            list_name="favorites",
        )
    assert err.value.status_code == 400

    # try to post to a different user
    with pytest.raises(
        SkyPortalError, match="Only admins can add listings to other users' accounts"
    ) as err:
        sp.post_listing(
            ListingPost(
                user_id=user2.id,
                obj_id=public_candidate.id,
                list_name="favorites",
            )
        )
    assert err.value.status_code == 400

    # try to add this to a different user, but with super admin privileges
    sp_admin.update_listing(
        item1,
        user_id=user2.id,
        obj_id=public_candidate.id,
        list_name="favorites",
    )

    # get the list back, should include only one item that matches user2
    new_list = sp_admin.fetch_listings(user_id=user2.id, list_name="favorites")

    assert len(new_list) == 1
    assert new_list[0].id == item1  # the listing ID is the same
    assert new_list[0].obj_id == public_candidate.id  # obj stays the same

    # try to patch with only partial data inputs
    # bring this listing back to first user with super token permission
    sp_admin.update_listing(item1, user_id=user.id)

    # change the object id only
    sp.update_listing(item1, obj_id=public_candidate2.id)

    # change the list name only
    sp.update_listing(item1, list_name="new_listing")

    # get the list back, should include only one item that matches user2
    new_list = sp_admin.fetch_listings(user_id=user.id, list_name="new_listing")

    assert len(new_list) == 1
    assert new_list[0].id == item1  # the listing ID is the same
    assert new_list[0].obj_id == public_candidate2.id  # obj was updated
    assert new_list[0].user_id == user.id  # user was returned to original
    assert new_list[0].list_name == "new_listing"  # new listing name


def test_invalid_listing_name_fails(user, upload_data_token, public_candidate):
    sp = client(upload_data_token)

    # we cannot post a listing with an empty string
    with pytest.raises(
        SkyPortalError, match="must begin with alphanumeric/underscore"
    ) as err:
        sp.post_listing(
            ListingPost(user_id=user.id, obj_id=public_candidate.id, list_name="")
        )
    assert err.value.status_code == 400

    # we cannot post a listing with a non-alphanumeric first letter
    with pytest.raises(
        SkyPortalError, match="must begin with alphanumeric/underscore"
    ) as err:
        sp.post_listing(
            ListingPost(user_id=user.id, obj_id=public_candidate.id, list_name=" ")
        )
    assert err.value.status_code == 400

    # we cannot post a listing with a non-alphanumeric first letter
    with pytest.raises(
        SkyPortalError, match="must begin with alphanumeric/underscore"
    ) as err:
        sp.post_listing(
            ListingPost(user_id=user.id, obj_id=public_candidate.id, list_name="-")
        )
    assert err.value.status_code == 400

    # this is ok
    listing_id = sp.post_listing(
        ListingPost(
            user_id=user.id,
            obj_id=public_candidate.id,
            list_name="favorites",
        )
    ).id

    # we cannot post a listing with a non-alphanumeric first letter
    with pytest.raises(
        SkyPortalError, match="must begin with alphanumeric/underscore"
    ) as err:
        sp.update_listing(
            listing_id, user_id=user.id, obj_id=public_candidate.id, list_name=""
        )
    assert err.value.status_code == 400
