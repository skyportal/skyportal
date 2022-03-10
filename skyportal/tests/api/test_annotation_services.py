import pytest
from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_datalab_photoz(annotation_token, public_source, public_group):
    status, data = api(
        'POST',
        f'sources/{public_source.id}/annotations/datalab',
        token=annotation_token,
        data={'crossmatchRadius': 10},
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
            and d['data']['ra'] == 0.0006243988887182
            and 'dec' in d['data']
            and d['data']['dec'] == 0.0018203440696039
            and 'flux_z' in d['data']
            and d['data']['flux_z'] == 0.36103
            and 'z_phot_l95' in d['data']
            and d['data']['z_phot_l95'] == 0.599632
            and 'z_phot_std' in d['data']
            and d['data']['z_phot_std'] == 0.565248
            and 'z_phot_median' in d['data']
            and d['data']['z_phot_median'] == 1.222793
            and 'type' in d['data']
            and d['data']['type'] == 'REX'
            for d in data['data']
        ]
    )


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
