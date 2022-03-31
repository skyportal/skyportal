import datetime

import uuid
from skyportal.tests import api


def test_synthetic_photometry(
    super_admin_token, public_source, public_group, upload_data_token
):
    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': name,
            'nickname': name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'spectrograph',
            'telescope_id': telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': instrument_id,
            'wavelengths': [1000, 3000, 5000, 7000, 9000],
            'fluxes': [232.1, 234.2, 232.1, 235.3, 232.1],
            'units': 'erg/s/cm/cm/AA',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data['data']['id']

    status, data = api(
        'POST',
        f'spectra/synthphot/{spectrum_id}',
        data={
            'filters': ['ztfg', 'ztfr', 'ztfi'],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
