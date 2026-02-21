import uuid

from tdtax import __version__, taxonomy

from skyportal.tests import api


def test_add_retrieve_delete_taxonomy(taxonomy_token, public_group):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": name,
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

    status, data = api("GET", f"taxonomy/{taxonomy_id}", token=taxonomy_token)

    assert status == 200
    assert data["data"]["name"] == name
    assert data["data"]["version"] == __version__

    status, data = api("DELETE", f"taxonomy/{taxonomy_id}", token=taxonomy_token)
    assert status == 200

    status, data = api("GET", f"taxonomy/{taxonomy_id}", token=taxonomy_token)
    assert status == 400


def test_add_bad_taxonomy(taxonomy_token, public_group):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": str(uuid.uuid4()),
            "hierarchy": {"Silly": "taxonomy", "bad": True},
            "group_ids": [public_group.id],
            "provenance": "Nope",
            "version": "0.0.1bad",
            "isLatest": True,
        },
        token=taxonomy_token,
    )

    assert status == 400
    assert data["message"] == "Hierarchy does not validate against the schema."


def test_latest_taxonomy(taxonomy_token, public_group):
    # add one, then add another with the same name
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": name,
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
        },
        token=taxonomy_token,
    )
    assert status == 200
    old_taxonomy_id = data["data"]["taxonomy_id"]
    status, data = api("GET", f"taxonomy/{old_taxonomy_id}", token=taxonomy_token)
    assert status == 200
    assert data["data"]["isLatest"]

    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": name,
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": "new version",
        },
        token=taxonomy_token,
    )
    assert status == 200
    new_taxonomy_id = data["data"]["taxonomy_id"]
    status, data = api("GET", f"taxonomy/{new_taxonomy_id}", token=taxonomy_token)
    assert status == 200
    assert data["data"]["isLatest"]

    # the first one we added should now have isLatest == False
    status, data = api("GET", f"taxonomy/{old_taxonomy_id}", token=taxonomy_token)
    assert status == 200
    assert not data["data"]["isLatest"]

    status, data = api("DELETE", f"taxonomy/{new_taxonomy_id}", token=taxonomy_token)
    status, data = api("DELETE", f"taxonomy/{old_taxonomy_id}", token=taxonomy_token)


def test_get_many_taxonomies(taxonomy_token, public_group):
    n_tax = 5
    ids = []
    names = []
    for _ in range(n_tax):
        name = "test taxonomy" + str(uuid.uuid4())
        status, data = api(
            "POST",
            "taxonomy",
            data={
                "name": name,
                "hierarchy": taxonomy,
                "group_ids": [public_group.id],
                "provenance": f"tdtax_{__version__}",
                "version": __version__,
                "isLatest": True,
            },
            token=taxonomy_token,
        )
        assert status == 200
        ids.append(data["data"]["taxonomy_id"])
        names.append(name)

    status, data = api("GET", "taxonomy", token=taxonomy_token)
    assert status == 200
    assert isinstance(data["data"], list)

    # make sure we can retrieve those taxonomies
    for _taxonomy in data["data"]:
        assert _taxonomy["id"] in ids
        assert _taxonomy["name"] == names[ids.index(_taxonomy["id"])]


def test_taxonomy_group_view(
    taxonomy_token_two_groups, taxonomy_token, public_group, public_group2
):
    name = "test taxonomy" + str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": name,
            "hierarchy": taxonomy,
            "group_ids": [public_group2.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token_two_groups,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "GET", f"taxonomy/{taxonomy_id}", token=taxonomy_token_two_groups
    )
    assert status == 200

    # this token is not apart of group 2
    status, data = api("GET", f"taxonomy/{taxonomy_id}", token=taxonomy_token)
    assert status == 400
    assert "is not available to user" in data["message"]


def test_update_taxonomy(taxonomy_token, public_group):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": name,
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

    status, data = api("GET", f"taxonomy/{taxonomy_id}", token=taxonomy_token)

    assert status == 200
    assert data["data"]["name"] == name
    assert data["data"]["version"] == __version__

    name2 = str(uuid.uuid4())
    status, data = api(
        "PUT",
        f"taxonomy/{taxonomy_id}",
        data={
            "name": name2,
        },
        token=taxonomy_token,
    )
    assert status == 200

    status, data = api("GET", f"taxonomy/{taxonomy_id}", token=taxonomy_token)

    assert status == 200
    assert data["data"]["name"] == name2
    assert data["data"]["version"] == __version__

    name2 = str(uuid.uuid4())
    status, data = api(
        "PUT",
        f"taxonomy/{taxonomy_id}",
        data={
            "hierarchy": taxonomy,
        },
        token=taxonomy_token,
    )
    assert status == 400
