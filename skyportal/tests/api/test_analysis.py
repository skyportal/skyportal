import uuid
import json

from skyportal.tests import api


def test_post_new_analysis_service(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'contact_email': "vr@ls.st",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'

    analysis_service_id = data['data']['id']
    status, data = api(
        'GET', f'analysis_service/{analysis_service_id}', token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'
    for key in post_data:
        if key != 'group_ids':
            assert data['data'][key] == post_data[key]
        else:
            assert sorted(g["id"] for g in data['data']['groups']) == sorted(
                post_data["group_ids"]
            )

    status, data = api(
        'DELETE',
        f'analysis_service/{analysis_service_id}',
        token=analysis_service_token,
    )
    assert status == 200
    assert data['status'] == 'success'


def test_update_analysis_service(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'contact_email': "vr@ls.st",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'

    analysis_service_id = data['data']['id']

    new_post_data = {'version': "2.0", 'timeout': 120.0}

    status, data = api(
        'PATCH',
        f'analysis_service/{analysis_service_id}',
        data=new_post_data,
        token=analysis_service_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET', f'analysis_service/{analysis_service_id}', token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'

    for key in new_post_data:
        assert data['data'][key] == new_post_data[key]

    status, data = api(
        'DELETE',
        f'analysis_service/{analysis_service_id}',
        token=analysis_service_token,
    )
    assert status == 200
    assert data['status'] == 'success'


def test_get_two_analysis_services(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'contact_email': "vr@ls.st",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'
    analysis_service_id = data['data']['id']

    name_1 = str(uuid.uuid4())
    post_data_1 = {
        'name': name_1,
        'display_name': "another test analysis service name",
        'description': "Another test analysis service description",
        'version': "1.1",
        'contact_name': "Henrietta Swan Leavitt",
        'contact_email': "hsl@harvard.edu",
        'url': f"http://localhost:5000/analysis/{name_1}",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['spectra'],
        'timeout': 1200.0,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data_1, token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'
    analysis_service_id_1 = data['data']['id']

    status, data = api('GET', 'analysis_service', token=analysis_service_token)
    assert status == 200
    assert data['status'] == 'success'

    as_ids = [a['id'] for a in data['data']]
    assert {analysis_service_id, analysis_service_id_1} == set(as_ids)

    for as_id in [analysis_service_id, analysis_service_id_1]:
        status, data = api(
            'DELETE', f'analysis_service/{as_id}', token=analysis_service_token
        )
        assert status == 200
        assert data['status'] == 'success'


def test_missing_required_analysis_service_parameter(
    analysis_service_token, public_group
):
    # Do not send `analysis_type` as required

    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'authentication_type': "none",
        'url': f"http://localhost:5000/analysis/{name}",
        'contact_name': "Vera Rubin",
        'input_data_types': ['photometry', 'redshift'],
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 400
    assert "Invalid/missing parameters" in data['message']


def test_duplicate_analysis_service(analysis_service_token, public_group):

    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )

    assert status == 200
    assert data['status'] == 'success'
    analysis_service_id = data['data']['id']

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 400
    assert "duplicate key value violates unique constraint" in data['message']

    status, data = api(
        'DELETE',
        f'analysis_service/{analysis_service_id}',
        token=analysis_service_token,
    )
    assert status == 200
    assert data['status'] == 'success'


def test_bad_url(analysis_service_token, public_group):

    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'url': f"my_code_{name}.py",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )

    assert status == 400
    assert "a valid `url` is required" in data['message']


def test_bad_authentication_type(analysis_service_token, public_group):

    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "oauth2",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )

    assert status == 400
    assert (
        "`authentication_type` must be one of: none, header_token," in data['message']
    )


def test_authentication_credentials(analysis_service_token, public_group):

    name = str(uuid.uuid4())

    authinfo = {'header_token': {"Authorization": "Bearer MY_TOKEN"}}

    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "header_token",
        '_authinfo': json.dumps(authinfo),
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 200
    analysis_service_id = data['data']['id']
    status, data = api(
        'GET', f'analysis_service/{analysis_service_id}', token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'

    # do the credentials match?
    data['data']["authinfo"] = authinfo

    status, data = api(
        'DELETE',
        f'analysis_service/{analysis_service_id}',
        token=analysis_service_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # Send auth info but for the wrong authentication type
    name = str(uuid.uuid4())
    authinfo = {'header_token': {"Authorization": "Bearer MY_TOKEN"}}
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "api_key",
        '_authinfo': json.dumps(authinfo),
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 400
    assert """`_authinfo` must contain a key for "api_key".""" in data["message"]


def test_add_and_retrieve_analysis_service_group_access(
    analysis_service_token_two_groups,
    public_group2,
    public_group,
    analysis_service_token,
):

    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'contact_email': "vr@ls.st",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group2.id],
    }

    status, data = api(
        'POST',
        'analysis_service',
        data=post_data,
        token=analysis_service_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    analysis_service_id = data['data']['id']

    # This token does not belong to public_group2
    status, data = api(
        'GET', f'analysis_service/{analysis_service_id}', token=analysis_service_token
    )
    assert status == 403

    # Both tokens should be able to view this analysis service
    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'contact_email': "vr@ls.st",
        'url': f"http://localhost:5000/analysis/{name}",
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group.id, public_group2.id],
    }
    status, data = api(
        'POST',
        'analysis_service',
        data=post_data,
        token=analysis_service_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    analysis_service_id = data['data']['id']

    status, data = api(
        'GET', f'analysis_service/{analysis_service_id}', token=analysis_service_token
    )
    assert status == 200
    status, data = api(
        'GET',
        f'analysis_service/{analysis_service_id}',
        token=analysis_service_token_two_groups,
    )
    assert status == 200
