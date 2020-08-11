from skyportal.tests import api


def test_token_user_add_new_observing_run(lris, upload_data_token,
                                          red_transients_group):
    run_details = {'instrument_id': lris.id,
                   'pi': 'Danny Goldstein',
                   'observers': 'D. Goldstein, P. Nugent',
                   'group_id': red_transients_group.id,
                   'calendar_date': '2020-02-16'}

    status, data = api('POST', 'observing_run',
                       data=run_details,
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    run_id = data['data']['id']

    status, data = api('GET', f'observing_run/{run_id}',
                       token=upload_data_token)

    assert status == 200
    assert data['status'] == 'success'
    for key in run_details:
        assert data['data'][key] == run_details[key]


def test_super_admin_user_delete_nonowned_observing_run(lris, upload_data_token,
                                                        super_admin_token,
                                                        red_transients_group):
    run_details = {'instrument_id': lris.id,
                   'pi': 'Danny Goldstein',
                   'observers': 'D. Goldstein, P. Nugent',
                   'group_id': red_transients_group.id,
                   'calendar_date': '2020-02-16'}

    status, data = api('POST', 'observing_run',
                       data=run_details,
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    run_id = data['data']['id']

    status, data = api('DELETE', f'observing_run/{run_id}',
                       token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'


def test_unauthorized_user_delete_nonowned_observing_run(lris, upload_data_token,
                                                         manage_sources_token,
                                                         red_transients_group):
    run_details = {'instrument_id': lris.id,
                   'pi': 'Danny Goldstein',
                   'observers': 'D. Goldstein, P. Nugent',
                   'group_id': red_transients_group.id,
                   'calendar_date': '2020-02-16'}

    status, data = api('POST', 'observing_run',
                       data=run_details,
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    run_id = data['data']['id']

    status, data = api('DELETE', f'observing_run/{run_id}',
                       token=manage_sources_token)

    assert status == 400
    assert data['status'] == 'error'


def test_authorized_user_modify_owned_observing_run(lris, upload_data_token,
                                                    red_transients_group):
    run_details = {'instrument_id': lris.id,
                   'pi': 'Danny Goldstein',
                   'observers': 'D. Goldstein, P. Nugent',
                   'group_id': red_transients_group.id,
                   'calendar_date': '2020-02-16'}

    status, data = api('POST', 'observing_run',
                       data=run_details,
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    run_id = data['data']['id']

    new_date = {'calendar_date': '2020-02-17'}
    run_details.update(new_date)

    status, data = api('PUT', f'observing_run/{run_id}',
                       data=new_date,
                       token=upload_data_token)

    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'observing_run/{run_id}',
                       token=upload_data_token)

    assert status == 200
    assert data['status'] == 'success'
    for key in run_details:
        assert data['data'][key] == run_details[key]


def test_unauthorized_user_modify_unowned_observing_run(lris, upload_data_token,
                                                        manage_sources_token,
                                                        red_transients_group):
    run_details = {'instrument_id': lris.id,
                   'pi': 'Danny Goldstein',
                   'observers': 'D. Goldstein, P. Nugent',
                   'group_id': red_transients_group.id,
                   'calendar_date': '2020-02-16'}

    status, data = api('POST', 'observing_run',
                       data=run_details,
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    run_id = data['data']['id']

    new_date = {'calendar_date': '2020-02-17'}
    run_details.update(new_date)

    status, data = api('PUT', f'observing_run/{run_id}',
                       data=new_date,
                       token=manage_sources_token)

    assert status == 400
    assert data['status'] == 'error'

