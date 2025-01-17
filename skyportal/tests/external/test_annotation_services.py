import uuid

import pytest

from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_irsa_wise(public_group, upload_data_token):
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
        "POST",
        f"sources/{obj_id}/annotations/irsa",
        token=upload_data_token,
        data={"crossmatchRadius": 10},
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{obj_id}/annotations",
        token=upload_data_token,
    )

    assert status == 200

    assert all(
        "ra" in d["data"]
        and d["data"]["ra"] == 229.9620821
        and "dec" in d["data"]
        and d["data"]["dec"] == 34.8442227
        and "w1mpro" in d["data"]
        and d["data"]["w1mpro"] == 13.197
        and "w2mpro" in d["data"]
        and d["data"]["w2mpro"] == 13.198
        and "w3mpro" in d["data"]
        and d["data"]["w3mpro"] == 12.517
        and "w4mpro" in d["data"]
        and d["data"]["w4mpro"] == 9.399
        for d in data["data"]
    )


@pytest.mark.flaky(reruns=3)
def test_vizier_quasar(public_group, upload_data_token):
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
        "POST",
        f"sources/{obj_id}/annotations/vizier",
        token=upload_data_token,
        data={"crossmatchRadius": 2},
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{obj_id}/annotations",
        token=upload_data_token,
    )

    assert status == 200

    assert all(
        "z" in d["data"] and d["data"]["z"] == 0.8450000286102295 for d in data["data"]
    )


@pytest.mark.flaky(reruns=3)
def test_datalab_photoz(annotation_token, public_source, public_group):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations/datalab",
        token=annotation_token,
        data={"crossmatchRadius": 10},
    )
    assert status in [200, 400]

    # datalab goes down sometimes
    if status == 400:
        return

    status, data = api(
        "GET",
        f"sources/{public_source.id}/annotations",
        token=annotation_token,
    )

    assert status == 200

    assert any(
        "ra" in d["data"]
        and d["data"]["ra"] == 0.0006352685989817
        and "dec" in d["data"]
        and d["data"]["dec"] == 0.0018217386016298
        and "flux_z" in d["data"]
        and d["data"]["flux_z"] == 0.536531
        and "z_phot_l95" in d["data"]
        and d["data"]["z_phot_l95"] == 0.39111
        and "z_phot_std" in d["data"]
        and d["data"]["z_phot_std"] == 0.559162
        and "z_phot_median" in d["data"]
        and d["data"]["z_phot_median"] == 1.040012
        and "type" in d["data"]
        and d["data"]["type"] == "REX"
        for d in data["data"]
    )
