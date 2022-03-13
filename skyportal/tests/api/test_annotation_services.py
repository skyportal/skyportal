import pytest
from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_irsa_wise(annotation_token, public_source, public_group):
    status, data = api(
        'POST',
        f'sources/{public_source.id}/annotations/irsa',
        token=annotation_token,
        data={'crossmatchRadius': 30},
    )
    assert status == 200

    status, data = api(
        'GET',
        f'sources/{public_source.id}/annotations',
        token=annotation_token,
    )

    assert status == 200

    assert any(
        [
            'ra' in d['data']
            and d['data']['ra'] == 0.0070215
            and 'dec' in d['data']
            and d['data']['dec'] == 0.0022575
            and 'w1mpro' in d['data']
            and d['data']['w1mpro'] == 17.11
            and 'w2mpro' in d['data']
            and d['data']['w2mpro'] == 16.751
            and 'w3mpro' in d['data']
            and d['data']['w3mpro'] == 12.129
            and 'w4mpro' in d['data']
            and d['data']['w4mpro'] == 9.07
            for d in data['data']
        ]
    )
