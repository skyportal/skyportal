import uuid
import pytest
from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_irsa_wise(annotation_token, public_source, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 229.9620403,
            "dec": 34.8442757,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )

    status, data = api(
        'POST',
        f'sources/{obj_id}/annotations/irsa',
        token=annotation_token,
        data={'crossmatchRadius': 10},
    )
    assert status == 200

    status, data = api(
        'GET',
        f'sources/{obj_id}/annotations',
        token=annotation_token,
    )

    assert status == 200

    assert all(
        [
            'ra' in d['data']
            and d['data']['ra'] == 229.9620821
            and 'dec' in d['data']
            and d['data']['dec'] == 34.8442227
            and 'w1mpro' in d['data']
            and d['data']['w1mpro'] == 13.197
            and 'w2mpro' in d['data']
            and d['data']['w2mpro'] == 13.198
            and 'w3mpro' in d['data']
            and d['data']['w3mpro'] == 12.517
            and 'w4mpro' in d['data']
            and d['data']['w4mpro'] == 9.399
            for d in data['data']
        ]
    )


@pytest.mark.flaky(reruns=2)
def test_vizier_quasar(
    annotation_token, public_source, public_group, upload_data_token
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 000.0006286,
            "dec": 35.5178439,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )

    status, data = api(
        'POST',
        f'sources/{obj_id}/annotations/vizier',
        token=annotation_token,
        data={'crossmatchRadius': 2},
    )
    assert status == 200

    status, data = api(
        'GET',
        f'sources/{obj_id}/annotations',
        token=annotation_token,
    )

    assert status == 200

    assert all(
        [
            'z' in d['data'] and d['data']['z'] == 0.8450000286102295
            for d in data['data']
        ]
    )
