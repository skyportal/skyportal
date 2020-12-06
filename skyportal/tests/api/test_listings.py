import uuid
from skyportal.tests import api
from skyportal.model_util import create_token


def test_add_objects_to_list(
    user, upload_data_token, public_candidate, public_candidate2
):

    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        'PUT',
        f'listing?user_id={user.id}&obj_id={public_candidate.id}&list_name=favorites',
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]  # get the list item ID

    status, data = api(
        'PUT',
        f'listing?user_id={user.id}&obj_id={public_candidate2.id}&list_name=favorites',
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]  # get the list item ID

    # get the list back, should include only two items
    status, data = api(
        'GET', f'listing?user_id={user.id}&list_name=favorites', token=token_id
    )

    assert status == 200
    new_list = data["data"]

    items = [item["id"] for item in new_list]

    assert set(items) == set([item1, item2])


def test_add_remove_objects(
    user, upload_data_token, public_candidate, public_candidate2
):

    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    status, data = api(
        'PUT',
        f'listing?user_id={user.id}&obj_id={public_candidate.id}&list_name=favorites',
        token=token_id,
    )
    assert status == 200
    item1 = data["data"]  # get the list item ID

    status, data = api(
        'PUT',
        f'listing?user_id={user.id}&obj_id={public_candidate2.id}&list_name=favorites',
        token=token_id,
    )

    assert status == 200
    item2 = data["data"]  # get the list item ID

    status, data = api('DELETE', f'listing/{item1}', token=token_id)

    assert status == 200

    # get the list back, should include only two items
    status, data = api(
        'GET', f'listing?user_id={user.id}&list_name=favorites', token=token_id
    )

    assert status == 200
    new_list = data["data"]

    items = [item["id"] for item in new_list]

    assert set(items) == set([item2])


def test_add_objects_to_different_lists(
    user, upload_data_token, public_candidate, public_candidate2
):

    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )

    list1 = uuid.uuid4()
    status, data = api(
        'PUT',
        f'listing?user_id={user.id}&obj_id={public_candidate.id}&list_name={list1}',
        token=token_id,
    )

    assert status == 200
    item1 = data["data"]  # get the list item ID

    list2 = uuid.uuid4()
    status, data = api(
        'PUT',
        f'listing?user_id={user.id}&obj_id={public_candidate2.id}&list_name={list2}',
        token=token_id,
    )

    assert status == 200

    # get the list back, should include only two items
    status, data = api(
        'GET', f'listing?user_id={user.id}&list_name={list1}', token=token_id
    )

    assert status == 200
    new_list = data["data"]

    items = [item["id"] for item in new_list]

    assert set(items) == set([item1])
