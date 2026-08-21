import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.taxonomies import TaxonomyPost, TaxonomyPut
from tdtax import __version__, taxonomy

from skyportal.tests import api, client


def test_add_retrieve_delete_taxonomy(taxonomy_token, public_group):
    sp = client(taxonomy_token)
    name = str(uuid.uuid4())
    taxonomy_id = sp.post_taxonomy(
        TaxonomyPost(
            name=name,
            hierarchy=taxonomy,
            group_ids=[public_group.id],
            provenance=f"tdtax_{__version__}",
            version=__version__,
            is_latest=True,
        )
    ).taxonomy_id

    fetched = sp.fetch_taxonomy(taxonomy_id)
    assert fetched.name == name
    assert fetched.version == __version__

    sp.delete_taxonomy(taxonomy_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_taxonomy(taxonomy_id)
    assert err.value.status_code == 400


def test_add_bad_taxonomy(taxonomy_token, public_group):
    with pytest.raises(
        SkyPortalError, match="Hierarchy does not validate against the schema."
    ) as err:
        client(taxonomy_token).post_taxonomy(
            TaxonomyPost(
                name=str(uuid.uuid4()),
                hierarchy={"Silly": "taxonomy", "bad": True},
                group_ids=[public_group.id],
                provenance="Nope",
                version="0.0.1bad",
                is_latest=True,
            )
        )
    assert err.value.status_code == 400


def test_latest_taxonomy(taxonomy_token, public_group):
    sp = client(taxonomy_token)
    # add one, then add another with the same name
    name = str(uuid.uuid4())
    old_taxonomy_id = sp.post_taxonomy(
        TaxonomyPost(
            name=name,
            hierarchy=taxonomy,
            group_ids=[public_group.id],
            provenance=f"tdtax_{__version__}",
            version=__version__,
        )
    ).taxonomy_id
    assert sp.fetch_taxonomy(old_taxonomy_id).is_latest

    new_taxonomy_id = sp.post_taxonomy(
        TaxonomyPost(
            name=name,
            hierarchy=taxonomy,
            group_ids=[public_group.id],
            provenance=f"tdtax_{__version__}",
            version="new version",
        )
    ).taxonomy_id
    assert sp.fetch_taxonomy(new_taxonomy_id).is_latest

    # the first one we added should now have isLatest == False
    assert not sp.fetch_taxonomy(old_taxonomy_id).is_latest

    sp.delete_taxonomy(new_taxonomy_id)
    sp.delete_taxonomy(old_taxonomy_id)


def test_get_many_taxonomies(taxonomy_token, public_group):
    sp = client(taxonomy_token)
    n_tax = 5
    ids = []
    names = []
    for _ in range(n_tax):
        name = "test taxonomy" + str(uuid.uuid4())
        ids.append(
            sp.post_taxonomy(
                TaxonomyPost(
                    name=name,
                    hierarchy=taxonomy,
                    group_ids=[public_group.id],
                    provenance=f"tdtax_{__version__}",
                    version=__version__,
                    is_latest=True,
                )
            ).taxonomy_id
        )
        names.append(name)

    # make sure we can retrieve those taxonomies
    for _taxonomy in sp.fetch_taxonomies():
        assert _taxonomy.id in ids
        assert _taxonomy.name == names[ids.index(_taxonomy.id)]


def test_taxonomy_group_view(
    taxonomy_token_two_groups, taxonomy_token, public_group, public_group2
):
    name = "test taxonomy" + str(uuid.uuid4())
    taxonomy_id = (
        client(taxonomy_token_two_groups)
        .post_taxonomy(
            TaxonomyPost(
                name=name,
                hierarchy=taxonomy,
                group_ids=[public_group2.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    assert client(taxonomy_token_two_groups).fetch_taxonomy(taxonomy_id).id == (
        taxonomy_id
    )

    # this token is not apart of group 2
    with pytest.raises(SkyPortalError, match="is not available to user") as err:
        client(taxonomy_token).fetch_taxonomy(taxonomy_id)
    assert err.value.status_code == 400


def test_update_taxonomy(taxonomy_token, public_group):
    sp = client(taxonomy_token)
    name = str(uuid.uuid4())
    taxonomy_id = sp.post_taxonomy(
        TaxonomyPost(
            name=name,
            hierarchy=taxonomy,
            group_ids=[public_group.id],
            provenance=f"tdtax_{__version__}",
            version=__version__,
            is_latest=True,
        )
    ).taxonomy_id

    fetched = sp.fetch_taxonomy(taxonomy_id)
    assert fetched.name == name
    assert fetched.version == __version__

    name2 = str(uuid.uuid4())
    sp.update_taxonomy(taxonomy_id, TaxonomyPut(name=name2))

    fetched = sp.fetch_taxonomy(taxonomy_id)
    assert fetched.name == name2
    assert fetched.version == __version__

    # raw api: TaxonomyPut has no hierarchy field by design (the hierarchy
    # cannot be edited); this asserts the server rejects such an attempt
    status, data = api(
        "PUT",
        f"taxonomy/{taxonomy_id}",
        data={"hierarchy": taxonomy},
        token=taxonomy_token,
    )
    assert status == 400
