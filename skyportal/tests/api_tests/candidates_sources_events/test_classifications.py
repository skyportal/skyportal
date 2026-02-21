import uuid

from tdtax import __version__, taxonomy

from skyportal.tests import api


def test_add_bad_classification(
    taxonomy_token, classification_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "origin": "SCoPe",
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Fried Green Tomato",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert "is not in the allowed classes" in data["message"]
    assert status == 400

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "RRab",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
            "probability": 10.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert "outside the allowable range" in data["message"]
    assert status == 400


def test_add_and_retrieve_classification_group_id(
    taxonomy_token, classification_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200
    classification_id = data["data"]["classification_id"]

    status, data = api(
        "GET", f"classification/{classification_id}", token=classification_token
    )

    assert status == 200
    assert data["data"]["classification"] == "Algol"
    assert data["data"]["probability"] == 1.0
    assert data["data"]["origin"] == "SCoPe"

    params = {"numPerPage": 100}

    status, data = api(
        "GET", "classification", token=classification_token, params=params
    )

    assert status == 200
    data = data["data"]["classifications"]
    assert [d["classification"] == "Algol" for d in data]
    assert [d["origin"] == "SCoPe" for d in data]
    assert [d["probability"] == 1.0 for d in data]
    assert [d["obj_id"] == public_source.id for d in data]


def test_add_and_retrieve_classification_no_group_id(
    taxonomy_token, classification_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
        },
        token=classification_token,
    )
    assert status == 200
    classification_id = data["data"]["classification_id"]

    status, data = api(
        "GET", f"classification/{classification_id}", token=classification_token
    )

    assert status == 200
    assert data["data"]["classification"] == "Algol"


def test_cannot_add_classification_without_permission(
    taxonomy_token, view_only_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
        },
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"


def test_delete_classification(
    taxonomy_token, classification_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
        },
        token=classification_token,
    )
    assert status == 200
    classification_id = data["data"]["classification_id"]

    status, data = api(
        "GET", f"classification/{classification_id}", token=classification_token
    )
    assert status == 200
    assert data["data"]["classification"] == "Algol"
    assert data["data"]["origin"] == "SCoPe"

    status, data = api(
        "DELETE", f"classification/{classification_id}", token=classification_token
    )
    assert status == 200

    status, data = api(
        "GET", f"classification/{classification_id}", token=classification_token
    )
    assert status == 400


def test_obj_classifications(
    taxonomy_token, classification_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
        },
        token=classification_token,
    )
    assert status == 200
    classification_id = data["data"]["classification_id"]

    status, data = api(
        "GET", f"sources/{public_source.id}/classifications", token=classification_token
    )
    assert status == 200
    assert data["data"][0]["classification"] == "Algol"
    assert data["data"][0]["origin"] == "SCoPe"
    assert data["data"][0]["id"] == classification_id
    assert len(data["data"]) == 1

    status, data = api("GET", "classification/sources", token=classification_token)
    assert status == 200
    assert public_source.id in data["data"]


def test_add_and_retrieve_multiple_classifications(
    taxonomy_token, classification_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    data = {
        "classifications": [
            {
                "obj_id": public_source.id,
                "classification": "Algol",
                "origin": "SCoPe",
                "taxonomy_id": taxonomy_id,
                "probability": 1.0,
                "group_ids": [public_group.id],
            },
            {
                "obj_id": public_source.id,
                "classification": "Time-domain Source",
                "origin": "SCoPe",
                "taxonomy_id": taxonomy_id,
                "probability": 1.0,
                "group_ids": [public_group.id],
            },
        ]
    }

    status, data = api(
        "POST",
        "classification",
        data=data,
        token=classification_token,
    )
    assert status == 200

    params = {"numPerPage": 100}

    status, data = api(
        "GET", "classification", token=classification_token, params=params
    )

    assert status == 200
    data = data["data"]["classifications"]
    assert any(d["classification"] == "Algol" for d in data)
    assert any(d["classification"] == "Time-domain Source" for d in data)


def test_obj_classifications_vote(
    taxonomy_token, classification_token, public_source, public_group
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "origin": "SCoPe",
            "taxonomy_id": taxonomy_id,
        },
        token=classification_token,
    )
    assert status == 200
    classification_id = data["data"]["classification_id"]

    status, data = api(
        "POST",
        f"classification/votes/{classification_id}",
        data={
            "vote": 1,
        },
        token=classification_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/classifications", token=classification_token
    )
    assert status == 200
    assert data["data"][0]["classification"] == "Algol"
    assert data["data"][0]["origin"] == "SCoPe"
    assert data["data"][0]["id"] == classification_id
    assert len(data["data"]) == 1
    assert len(data["data"][0]["votes"]) == 1
    assert data["data"][0]["votes"][0]["vote"] == 1

    status, data = api(
        "DELETE",
        f"classification/votes/{classification_id}",
        token=classification_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/classifications", token=classification_token
    )
    assert status == 200
    assert data["data"][0]["classification"] == "Algol"
    assert data["data"][0]["origin"] == "SCoPe"
    assert data["data"][0]["id"] == classification_id
    assert len(data["data"]) == 1
    assert len(data["data"][0]["votes"]) == 0
