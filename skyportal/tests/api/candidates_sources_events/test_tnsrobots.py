import uuid

from skyportal.tests import api


def test_post_and_delete_tns_robot(
    public_group,
    super_admin_token,
    view_only_token,
    super_admin_user,
    view_only_user,
    public_source,
    ztf_camera,
):
    # GET ALL TNS ROBOTS
    status, data = api('GET', 'tns_robot', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    initial_count = len(data['data'])

    # first, add a private group
    status, data = api(
        'POST', 'groups', data={'name': str(uuid.uuid4())}, token=super_admin_token
    )
    assert status == 200
    private_group_id = data['data']['id']

    bot_name = str(uuid.uuid4())
    request_data = {
        'owner_group_ids': [private_group_id],
        'bot_name': bot_name,
        'bot_id': 10,
        'source_group_id': 200,
        '_altdata': '{"api_key": "test_key"}',
    }

    # ADD A TNS ROBOT WITHOUT SPECIFYING ANY INSTRUMENTS (SHOULD FAIL)
    status, data = api('PUT', 'tns_robot', data=request_data, token=super_admin_token)
    assert status == 400
    assert (
        "At least one instrument must be specified for TNS reporting" in data['message']
    )

    # ADD A TNS ROBOT WITH INSTRUMENTS BUT THAT ARE NOT ON TNS (SHOULD FAIL)
    request_data['instrument_ids'] = [ztf_camera.id]
    status, data = api('PUT', 'tns_robot', data=request_data, token=super_admin_token)
    assert status == 400
    assert (
        f"Instrument {ztf_camera.name} not supported for TNS reporting"
        in data['message']
    )

    # POST AN INSTRUMENT WHICH NAME IS SUPPORTED BY TNS, like ZTF
    status, data = api(
        'POST',
        'instrument',
        data={'name': 'ZTF', 'telescope_id': ztf_camera.telescope_id, "type": "imager"},
        token=super_admin_token,
    )
    assert status == 200
    assert 'data' in data
    assert 'id' in data['data']
    ztf_instrument_id = data['data']['id']

    # ADD A TNS ROBOT WITH INSTRUMENTS
    request_data['instrument_ids'] = [ztf_instrument_id]
    status, data = api('PUT', 'tns_robot', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    # GET ALL TNS ROBOTS
    status, data = api('GET', 'tns_robot', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']) == initial_count + 1

    # GET THE TNS ROBOT
    status, data = api('GET', f'tns_robot/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['groups']) == 1

    for key in request_data:
        if key == '_altdata':
            continue
        if key == 'instrument_ids':
            for instrument_id in request_data[key]:
                assert any(
                    [i['id'] == instrument_id for i in data['data']['instruments']]
                )
            continue
        assert data['data'][key] == request_data[key]

    # GET ALL TNS ROBOTS WITH VIEW ONLY TOKEN (should not see the robot)
    status, data = api('GET', 'tns_robot', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']) == 0

    # GET THE TNS ROBOT WITH VIEW ONLY TOKEN (should not see the robot)
    status, data = api('GET', f'tns_robot/{id}', token=view_only_token)
    assert status == 400
    assert "No TNS robot with" in data['message']

    # ADD A GROUP TO THE ROBOT
    status, data = api(
        'PUT',
        f'tns_robot/{id}/group',
        data={'group_id': public_group.id},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # GET THE TNS ROBOT AGAIN, SHOULD HAVE THE NEW GROUP
    status, data = api('GET', f'tns_robot/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['groups']) == 2

    # EDIT THE ROBOT, TO GIVE IT OWNERSHIP AND TO SET AUTO_REPORT TO TRUE
    status, data = api(
        'PUT',
        f'tns_robot/{id}/group/{public_group.id}',
        data={'owner': True, 'auto_report': True},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # GET THE TNS ROBOT AGAIN, SHOULD HAVE THE NEW GROUP EDITED
    status, data = api('GET', f'tns_robot/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    group = [g for g in data['data']['groups'] if g['group_id'] == public_group.id]
    assert len(group) == 1
    assert group[0]['owner'] is True
    assert group[0]['auto_report'] is True

    # TRY ADDING A COAUTHOR WITH NO AFFILIATIONS TO THE ROBOT
    status, data = api(
        'POST',
        f'tns_robot/{id}/coauthor/{super_admin_user.id}',
        token=super_admin_token,
    )
    assert status == 400
    assert "has no affiliation(s), required to be a coauthor of" in data['message']

    # add an affiliation to the user
    status, data = api(
        'PATCH',
        f'internal/profile/{super_admin_user.id}',
        data={'affiliations': ['CIT']},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # now add the coauthor
    status, data = api(
        'POST',
        f'tns_robot/{id}/coauthor/{super_admin_user.id}',
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # GET THE TNS ROBOT AGAIN, SHOULD HAVE THE NEW COAUTHOR
    status, data = api('GET', f'tns_robot/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['coauthors']) == 1
    assert data['data']['coauthors'][0]['user_id'] == super_admin_user.id

    # TRY ADDING THE VIEWONLY USER AS AN AUTOREPORTER OF THE TNS ROBOT PUBLIC GROUP
    # will fail (no affiliation)
    status, data = api(
        'POST',
        f'tns_robot/{id}/group/{public_group.id}/autoreporter',
        data={'user_ids': [view_only_user.id]},
        token=super_admin_token,
    )
    assert status == 400
    assert "has no affiliation(s), required to be an autoreporter of" in data['message']

    # add an affiliation to the user
    status, data = api(
        'PATCH',
        f'internal/profile/{view_only_user.id}',
        data={'affiliations': ['CIT']},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # now add the autoreporter
    status, data = api(
        'POST',
        f'tns_robot/{id}/group/{public_group.id}/autoreporter',
        data={'user_ids': [view_only_user.id]},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # GET THE TNS ROBOT AGAIN, SHOULD HAVE THE NEW AUTOREPORTER
    status, data = api('GET', f'tns_robot/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['groups']) == 2
    group = [g for g in data['data']['groups'] if g['group_id'] == public_group.id]
    assert len(group) == 1
    assert len(group[0]['autoreporters']) == 1
    assert group[0]['autoreporters'][0]['user_id'] == view_only_user.id

    # SUBMIT THE PUBLIC SOURCE TO TNS
    request_data = {
        'tnsrobotID': id,
        'reporters': "test reporter string",
        'remarks': "test remark string",
        'archival': False,
    }
    status, data = api(
        'POST',
        f'sources/{public_source.id}/tns',
        data=request_data,
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # GET THE TNS ROBOT SUBMISSIONS
    status, data = api('GET', f'tns_robot/{id}/submissions', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    tnsrobot_id = data['data']['tnsrobot_id']
    assert tnsrobot_id == id
    submissions = data['data']['submissions']
    assert len(submissions) >= 1
    assert submissions[0]['obj_id'] == public_source.id
    assert submissions[0]['custom_reporting_string'] == "test reporter string"
    assert submissions[0]['custom_remarks_string'] == "test remark string"
    assert submissions[0]['archival'] is False
    assert "pending" in submissions[0]['status']

    # REMOVE THE COAUTHOR
    status, data = api(
        'DELETE',
        f'tns_robot/{id}/coauthor/{super_admin_user.id}',
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # REMOVE THE AUTOREPORTER
    status, data = api(
        'DELETE',
        f'tns_robot/{id}/group/{public_group.id}/autoreporter/{view_only_user.id}',
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # GET THE TNS ROBOT AGAIN, SHOULD HAVE NO AUTOREPORTERS AND NO COAUTHORS
    status, data = api('GET', f'tns_robot/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['groups']) == 2
    group = [g for g in data['data']['groups'] if g['group_id'] == public_group.id]
    assert len(group) == 1
    assert len(group[0]['autoreporters']) == 0
    assert len(data['data']['coauthors']) == 0

    # DELETE THE PUBLIC GROUP
    status, data = api(
        'DELETE', f'tns_robot/{id}/group/{public_group.id}', token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    # TRY DELETING THE TNSROBOT PRIVATE GROUP (should fail as we always need at least one owner group)
    status, data = api(
        'DELETE', f'tns_robot/{id}/group/{private_group_id}', token=super_admin_token
    )
    assert status == 400
    assert (
        "Cannot delete the only tnsrobot_group owning this robot, add another group as an owner first."
        in data['message']
    )

    status, data = api("DELETE", f"tns_robot/{id}", token=super_admin_token)
    assert status == 200
    assert data['status'] == "success"
