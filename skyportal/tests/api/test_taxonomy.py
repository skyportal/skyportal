from skyportal.tests import api

from tdtax import taxonomy, __version__


def test_add_retrieve_delete_taxonomy(taxonomy_token, public_group):
    status, data = api('POST', 'taxonomy',
                       data={
                             'name': "test taxonomy",
                             'hierarchy': taxonomy,
                             'group_ids': [public_group.id],
                             'provenance': f"tdtax_{__version__}",
                             'version': __version__,
                             'isLatest': True
                             },
                       token=taxonomy_token)
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api('GET', f'taxonomy/{taxonomy_id}', token=taxonomy_token)

    assert status == 200
    assert data['data']['name'] == 'test taxonomy'
    assert data['data']['version'] == __version__

    status, data = api('DELETE', f'taxonomy/{taxonomy_id}', token=taxonomy_token)
    assert status == 200


def test_add_bad_taxonomy(taxonomy_token, public_group):
    status, data = api('POST', 'taxonomy',
                       data={
                             'name': "test bad taxonomy",
                             'hierarchy': {"Silly": "taxonomy", "bad": True},
                             'group_ids': [public_group.id],
                             'provenance': "Nope",
                             'version': "0.0.1bad",
                             'isLatest': True
                             },
                       token=taxonomy_token)

    assert status == 400
    assert data['message'] == "Hierarchy does not validate against the schema."


def test_latest_taxonomy(taxonomy_token, public_group):

    # add one, then add another with the same namer
    status, data = api('POST', 'taxonomy',
                       data={
                             'name': "test taxonomy",
                             'hierarchy': taxonomy,
                             'group_ids': [public_group.id],
                             'provenance': f"tdtax_{__version__}",
                             'version': __version__
                             },
                       token=taxonomy_token)
    assert status == 200
    old_taxonomy_id = data['data']['taxonomy_id']
    status, data = api('GET', f'taxonomy/{old_taxonomy_id}',
                       token=taxonomy_token)
    assert status == 200
    assert data['data']['isLatest']

    status, data = api('POST', 'taxonomy',
                       data={
                             'name': "test taxonomy",
                             'hierarchy': taxonomy,
                             'group_ids': [public_group.id],
                             'provenance': f"tdtax_{__version__}",
                             'version': "new version"
                             },
                       token=taxonomy_token)
    assert status == 200
    new_taxonomy_id = data['data']['taxonomy_id']

    # the first one we added should now have isLatest == False
    status, data = api('GET', f'taxonomy/{old_taxonomy_id}',
                       token=taxonomy_token)
    assert status == 200
    assert not data['data']['isLatest']

    status, data = api('DELETE', f'taxonomy/{new_taxonomy_id}', token=taxonomy_token)
    status, data = api('DELETE', f'taxonomy/{old_taxonomy_id}', token=taxonomy_token)

