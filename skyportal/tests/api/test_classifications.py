import uuid

from skyportal.tests import api

from tdtax import taxonomy, __version__


def test_add_bad_classification(taxonomy_token, classification_token, public_source, public_group):

    status, data = api('POST', 'taxonomy',
                       data={'name': "test taxonomy" + str(uuid.uuid4()),
                             'hierarchy': taxonomy,
                             'group_ids': [public_group.id],
                             'provenance': f"tdtax_{__version__}",
                             'version': __version__,
                             'isLatest': True
                            },
                       token=taxonomy_token)
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api('POST', 'classification', data={'obj_id': public_source.id,
                        'classification': 'Fried Green Tomato',
                        'taxonomy_id': taxonomy_id,
                        'probability': 1.0,
                        'group_ids': [public_group.id]},
                       token=classification_token)
    assert "is not in the allowed classes" in data["message"]
    assert status == 400

    status, data = api('POST', 'classification', data={'obj_id': public_source.id,
                        'classification': 'RRab',
                        'taxonomy_id': taxonomy_id,
                        'probability': 10.0,
                        'group_ids': [public_group.id]},
                       token=classification_token)
    assert "outside the allowable range" in data["message"]
    assert status == 400


def test_add_and_retrieve_classification_group_id(taxonomy_token, classification_token, public_source, public_group):

    status, data = api('POST', 'taxonomy',
                   data={
                         'name': "test taxonomy" + str(uuid.uuid4()),
                         'hierarchy': taxonomy,
                         'group_ids': [public_group.id],
                         'provenance': f"tdtax_{__version__}",
                         'version': __version__,
                         'isLatest': True
                         },
                   token=taxonomy_token)
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api('POST', 'classification', data={'obj_id': public_source.id,
                        'classification': 'Algol',
                        'taxonomy_id': taxonomy_id,
                        'probability': 1.0,
                        'group_ids': [public_group.id]},
                       token=classification_token)
    assert status == 200
    classification_id = data['data']['classification_id']

    status, data = api('GET', f'classification/{classification_id}', token=classification_token)

    assert status == 200
    assert data['data']['classification'] == 'Algol'
    assert data['data']['probability'] == 1.0


def test_add_and_retrieve_classification_no_group_id(taxonomy_token, classification_token, public_source, public_group):

    status, data = api('POST', 'taxonomy',
                   data={
                         'name': "test taxonomy" + str(uuid.uuid4()),
                         'hierarchy': taxonomy,
                         'group_ids': [public_group.id],
                         'provenance': f"tdtax_{__version__}",
                         'version': __version__,
                         'isLatest': True
                         },
                   token=taxonomy_token)
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api('POST', 'classification', data={'obj_id': public_source.id,
                        'classification': 'Algol',
                        'taxonomy_id': taxonomy_id},
                       token=classification_token)
    assert status == 200
    classification_id = data['data']['classification_id']

    status, data = api('GET', f'classification/{classification_id}', token=classification_token)

    assert status == 200
    assert data['data']['classification'] == 'Algol'


def test_cannot_add_classification_without_permission(taxonomy_token, view_only_token, public_source, public_group):
    status, data = api('POST', 'taxonomy',
                   data={
                         'name': "test taxonomy" + str(uuid.uuid4()),
                         'hierarchy': taxonomy,
                         'group_ids': [public_group.id],
                         'provenance': f"tdtax_{__version__}",
                         'version': __version__,
                         'isLatest': True
                         },
                   token=taxonomy_token)
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api('POST', 'classification', data={'obj_id': public_source.id,
                        'classification': 'Algol', 'taxonomy_id': taxonomy_id},
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_delete_classification(taxonomy_token, classification_token, public_source, public_group):
    status, data = api('POST', 'taxonomy',
                   data={
                         'name': "test taxonomy" + str(uuid.uuid4()),
                         'hierarchy': taxonomy,
                         'group_ids': [public_group.id],
                         'provenance': f"tdtax_{__version__}",
                         'version': __version__,
                         'isLatest': True
                         },
                   token=taxonomy_token)
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api('POST', 'classification', data={'obj_id': public_source.id,
                        'classification': 'Algol',
                        'taxonomy_id': taxonomy_id},
                       token=classification_token)
    assert status == 200
    classification_id = data['data']['classification_id']

    status, data = api('GET', f'classification/{classification_id}', token=classification_token)
    assert status == 200
    assert data['data']['classification'] == 'Algol'

    status, data = api('DELETE', f'classification/{classification_id}', token=classification_token)
    assert status == 200

    status, data = api('GET', f'classification/{classification_id}', token=classification_token)
    assert status == 400
