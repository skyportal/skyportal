import os
from skyportal.tests import api
from glob import glob
import yaml
import numpy as np
import datetime


def test_token_user_post_get_spectrum_data(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2
    assert data['data']['obj_id'] == public_source.id


def test_token_user_post_spectrum_no_instrument_id(
    upload_data_token, public_source, public_group
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'

    # should be a marshamallow error, not a psycopg2 error
    # (see https://github.com/skyportal/skyportal/issues/1047)
    assert 'psycopg2' not in data['message']


def test_token_user_post_spectrum_all_groups(
    upload_data_token, public_source_two_groups, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source_two_groups.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': "all",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2
    assert data['data']['obj_id'] == public_source_two_groups.id


def test_token_user_post_spectrum_no_access(
    view_only_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=view_only_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_update_spectrum(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2

    status, data = api(
        'PUT',
        f'spectrum/{spectrum_id}',
        data={
            'fluxes': [222.2, 232.1, 235.3],
            'observed_at': str(datetime.datetime.now()),
            'wavelengths': [664, 665, 666],
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 222.2


def test_token_user_cannot_update_unowned_spectrum(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2

    status, data = api(
        'PUT',
        f'spectrum/{spectrum_id}',
        data={
            'fluxes': [222.2, 232.1, 235.3],
            'observed_at': str(datetime.datetime.now()),
            'wavelengths': [664, 665, 666],
        },
        token=manage_sources_token,
    )

    assert status == 400
    assert data['status'] == 'error'


def test_admin_can_update_unowned_spectrum_data(
    upload_data_token, super_admin_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2

    status, data = api(
        'PUT',
        f'spectrum/{spectrum_id}',
        data={
            'fluxes': [222.2, 232.1, 235.3],
            'observed_at': str(datetime.datetime.now()),
            'wavelengths': [664, 665, 666],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 222.2


def test_spectrum_owner_id_is_unmodifiable(
    upload_data_token,
    super_admin_user,
    super_admin_token,
    public_source,
    public_group,
    lris,
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2

    status, data = api(
        'PUT',
        f'spectrum/{spectrum_id}',
        data={'owner_id': super_admin_user.id},
        token=super_admin_token,
    )

    assert status == 400
    assert data['status'] == 'error'


def test_user_cannot_delete_unowned_spectrum_data(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2
    assert data['data']['obj_id'] == public_source.id

    status, data = api('DELETE', f'spectrum/{spectrum_id}', token=manage_sources_token)
    assert status == 400


def test_user_can_delete_owned_spectrum_data(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2
    assert data['data']['obj_id'] == public_source.id

    status, data = api('DELETE', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200

    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 400


def test_admin_can_delete_unowned_spectrum_data(
    upload_data_token, super_admin_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2
    assert data['data']['obj_id'] == public_source.id

    status, data = api('DELETE', f'spectrum/{spectrum_id}', token=super_admin_token)
    assert status == 200

    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 400


def test_jsonify_spectrum_header(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f'{os.path.dirname(__file__)}/../data/ZTF*.ascii.head'):
        with open(filename[:-5], 'r') as f:
            status, data = api(
                'POST',
                'spectrum/parse/ascii',
                data={
                    'fluxerr_column': 3
                    if 'ZTF20abpuxna_20200915_Keck1_v1.ascii' in filename
                    else 2
                    if 'P60' in filename
                    else None,
                    'ascii': f.read(),
                },
                token=upload_data_token,
            )
        assert status == 200
        assert data['status'] == 'success'

        answer = yaml.load(open(filename, 'r'), Loader=yaml.FullLoader)

        # check the header serialization
        for key in answer:
            # special keys
            if key not in ['COMMENT', 'END', 'HISTORY']:
                if isinstance(data['data']['altdata'][key], dict):
                    value = data['data']['altdata'][key]['value']
                else:
                    value = data['data']['altdata'][key]
                if isinstance(answer[key], (str, int)):
                    assert str(value) == str(answer[key])
                elif isinstance(answer[key], datetime.datetime):
                    assert datetime.datetime.fromisoformat(value) == answer[key]
                elif isinstance(answer[key], datetime.date):
                    assert datetime.datetime.fromisoformat(value).date() == answer[key]
                elif answer[key] is None:
                    assert value is None
                else:
                    np.testing.assert_allclose(value, answer[key])


def test_can_post_spectrum_no_groups(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['groups']) == 1


def test_can_post_spectrum_empty_groups_list(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['groups']) == 1


def test_jsonify_spectrum_data(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f'{os.path.dirname(__file__)}/../data/ZTF*.ascii'):
        with open(filename, 'r') as f:
            status, data = api(
                'POST',
                'spectrum/parse/ascii',
                data={
                    'fluxerr_column': 3
                    if 'ZTF20abpuxna_20200915_Keck1_v1.ascii' in filename
                    else 2
                    if 'P60' in filename
                    else None,
                    'ascii': f.read(),
                },
                token=upload_data_token,
            )
        assert status == 200
        assert data['status'] == 'success'

        answer = np.genfromtxt(filename, dtype=float, encoding='ascii')

        if answer.shape[-1] == 2:
            np.testing.assert_allclose(
                np.asarray(data['data']['wavelengths'], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['fluxes'], dtype=float), answer[:, 1]
            )

        elif answer.shape[-1] == 3:
            np.testing.assert_allclose(
                np.asarray(data['data']['wavelengths'], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['fluxes'], dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['errors'], dtype=float), answer[:, 2]
            )

        else:
            # this is the long one from Keck
            np.testing.assert_allclose(
                np.asarray(data['data']['wavelengths'], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['fluxes'], dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['errors'], dtype=float), answer[:, 3]
            )


def test_upload_bad_spectrum_from_ascii_file(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f'{os.path.dirname(__file__)}/../data/ZTF*.ascii.bad'):
        with open(filename, 'r') as f:
            content = f.read()
            observed_at = str(datetime.datetime.now())

            status, data = api(
                'POST',
                'spectrum/ascii',
                data={
                    'obj_id': str(public_source.id),
                    'observed_at': observed_at,
                    'instrument_id': lris.id,
                    'group_ids': [public_group.id],
                    'fluxerr_column': 3
                    if 'ZTF20abpuxna_20200915_Keck1_v1.ascii' in filename
                    else 2
                    if 'P60' in filename
                    else None,
                    'ascii': content,
                    'filename': filename,
                },
                token=upload_data_token,
            )

            assert status == 400
            assert data['status'] == 'error'


def test_token_user_post_to_foreign_group_and_retrieve(
    upload_data_token, public_source_two_groups, public_group2, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source_two_groups.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200


def test_parse_integer_spectrum_ascii(upload_data_token):

    status, data = api(
        'POST',
        'spectrum/parse/ascii',
        data={'ascii': '4000 0.01\n4500 0.02\n5000 0.005\n5500 0.006\n6000 0.01\n'},
        token=upload_data_token,
    )

    assert status == 200
    assert data['status'] == 'success'

    for wave in data['data']['wavelengths']:
        assert isinstance(wave, float)
