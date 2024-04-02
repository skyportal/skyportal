import os
import time

import numpy as np

from skyportal.tests import api


def test_add_and_retrieve_comment_on_gcn(
    comment_token, upload_data_token, public_group, super_admin_token
):
    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    gcnevent_id = data['data']['gcnevent_id']

    # wait for event to load
    n_times = 0
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}

    n_times_2 = 0
    for n_times_2 in range(26):
        status, data = api(
            'GET',
            'localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

    status, data = api(
        'POST',
        f'gcn_event/{gcnevent_id}/comments',
        data={
            'text': 'Comment text',
            'group_ids': [public_group.id],
        },
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api(
        'GET', f'gcn_event/{gcnevent_id}/comments/{comment_id}', token=comment_token
    )

    assert status == 200
    assert data['data']['text'] == 'Comment text'

    # delete the event
    status, data = api(
        'DELETE', 'gcn_event/2019-04-25T08:18:05', token=super_admin_token
    )


def test_delete_comment_on_gcn(comment_token, public_group, super_admin_token):
    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    gcnevent_id = data['data']['gcnevent_id']

    status, data = api(
        'POST',
        f'gcn_event/{gcnevent_id}/comments',
        data={'text': 'Comment text'},
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api(
        'GET', f'gcn_event/{gcnevent_id}/comments/{comment_id}', token=comment_token
    )
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    # try to delete using the wrong object ID
    status, data = api(
        'DELETE',
        f'gcn_event/{gcnevent_id}zzz/comments/{comment_id}',
        token=comment_token,
    )
    assert status == 400
    assert (
        "Comment resource ID does not match resource ID given in path"
        in data["message"]
    )

    status, data = api(
        'DELETE',
        f'gcn_event/{gcnevent_id}/comments/{comment_id}',
        token=comment_token,
    )
    assert status == 200

    status, data = api(
        'GET', f'gcn_event/{gcnevent_id}/comments/{comment_id}', token=comment_token
    )
    assert status == 403

    # delete the event
    status, data = api(
        'DELETE', 'gcn_event/2019-04-25T08:18:05', token=super_admin_token
    )
