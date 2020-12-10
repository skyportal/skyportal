import uuid
from skyportal.tests import api
from skyportal.model_util import create_token


def test_add_objects_to_list(user, public_candidate, public_candidate2):

    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        'PUT',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]["listing_id"]  # get the list item ID

    status, data = api(
        'PUT',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate2.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]["listing_id"]  # get the list item ID

    # get the list back, should include only two items
    status, data = api('GET', f'listing/{user.id}?list_name=favorites', token=token_id)

    assert status == 200
    new_list = data["data"]

    items = [item["id"] for item in new_list]

    assert set(items) == {item1, item2}

    # try to put a listing to a non-existing object
    fake_obj_id = str(uuid.uuid4())

    status, data = api(
        'PUT',
        'listing',
        data={'user_id': user.id, 'obj_id': fake_obj_id, 'list_name': 'favorites'},
        token=token_id,
    )

    assert status == 400
    assert 'does not exist' in data["message"]


def test_double_posting(user, public_candidate):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        'POST',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200
    listing_id1 = data['data']['listing_id']

    # try posting the same listing again!
    status, data = api(
        'POST',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 400

    # doing a PUT instead of POST should be fine (simply ignored)
    status, data = api(
        'PUT',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200
    listing_id2 = data['data']['listing_id']

    assert listing_id1 == listing_id2  # check the PUT returns the same identifier


def test_add_remove_objects(user, public_candidate, public_candidate2):

    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        'PUT',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )
    assert status == 200
    item1 = data["data"]["listing_id"]  # get the list item ID

    status, data = api(
        'PUT',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate2.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]["listing_id"]  # get the list item ID

    status, data = api('DELETE', f'listing/{item1}', token=token_id)

    assert status == 200

    # get the list back, should include only one item
    status, data = api('GET', f'listing/{user.id}?list_name=favorites', token=token_id)

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
        'PUT',
        'listing',
        data={'user_id': user.id, 'obj_id': public_candidate.id, 'list_name': list1},
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]["listing_id"]  # get the list item ID

    list2 = str(uuid.uuid4())
    status, data = api(
        'PUT',
        'listing',
        data={'user_id': user.id, 'obj_id': public_candidate2.id, 'list_name': list2},
        token=token_id,
    )

    assert status == 200

    # get the list back, should include only one item that matches list1
    status, data = api('GET', f'listing/{user.id}?listName={list1}', token=token_id)

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
        'PUT',
        'listing',
        data={'user_id': user.id, 'obj_id': public_candidate.id, 'list_name': list1},
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]["listing_id"]  # get the list item ID

    status, data = api(
        'PUT',
        'listing',
        data={'user_id': user.id, 'obj_id': public_candidate2.id, 'list_name': list1},
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]["listing_id"]  # get the list item ID

    list2 = str(uuid.uuid4())
    status, data = api(
        'PATCH',
        f'listing/{item2}',
        data={'user_id': user.id, 'obj_id': public_candidate2.id, 'list_name': list2},
        token=token_id,
    )

    assert status == 200

    # get the list back, should include only one item that matches list2
    status, data = api('GET', f'listing/{user.id}?listName={list2}', token=token_id)
    print(data["data"])
    assert status == 200
    new_list = data["data"]

    assert len(new_list) == 1

    assert new_list[0]['id'] == item2  # the listing ID is the same

    assert new_list[0]['user_id'] == user.id  # user stays the same
    assert new_list[0]['obj_id'] == public_candidate2.id  # obj id is new
    assert new_list[0]['list_name'] == list2  # list name is new

    # try to patch with an invalid user id
    status, data = api(
        'PATCH',
        f'listing/{item1}',
        data={'user_id': user2.id, 'obj_id': public_candidate2.id, 'list_name': list2},
        token=token_id,
    )

    assert status == 400
    assert 'Insufficient permission' in data['message']


def test_listings_user_permissions(
    user, user2, super_admin_user, public_candidate, public_candidate2
):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        'PUT',
        'listing',
        data={
            'user_id': user.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]["listing_id"]  # get the list item ID

    # try to add this to a different user
    status, data = api(
        'PATCH',
        f'listing/{item1}',
        data={
            'user_id': user2.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 400
    assert 'Insufficient permission' in data['message']

    # setup a token for the super user
    super_token_id = create_token(
        ACLs=["Upload data"], user_id=super_admin_user.id, name=str(uuid.uuid4())
    )

    # try to add this to a different user, but with super admin privileges
    status, data = api(
        'PATCH',
        f'listing/{item1}',
        data={
            'user_id': user2.id,
            'obj_id': public_candidate.id,
            'list_name': 'favorites',
        },
        token=super_token_id,
    )

    assert status == 200

    # get the list back, should include only one item that matches user2
    status, data = api(
        'GET', f'listing/{user2.id}?listName=favorites', token=super_token_id
    )

    assert status == 200
    new_list = data["data"]

    assert len(new_list) == 1

    assert new_list[0]['id'] == item1  # the listing ID is the same

    assert new_list[0]['obj_id'] == public_candidate.id  # obj stays the same
