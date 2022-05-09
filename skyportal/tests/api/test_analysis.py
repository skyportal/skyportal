import uuid

from skyportal.tests import api


def test_post_new_analysis_service(super_admin_token, public_group):
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
        'type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    analysis_service_id = data['data']['id']
    status, data = api(
        'GET', f'analysis_service/{analysis_service_id}', token=super_admin_token
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
