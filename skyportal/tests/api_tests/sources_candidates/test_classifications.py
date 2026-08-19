import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.classifications import ClassificationPost, ClassificationUpdate
from skyportal_py.taxonomies import TaxonomyPost
from tdtax import __version__, taxonomy

from skyportal.tests import client


def test_add_bad_classification(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    with pytest.raises(SkyPortalError, match="is not in the allowed classes") as err:
        client(classification_token).post_classification(
            ClassificationPost(
                obj_id=public_source.id,
                classification="Fried Green Tomato",
                origin="SCoPe",
                taxonomy_id=taxonomy_id,
                probability=1.0,
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError, match="outside the allowable range") as err:
        client(classification_token).post_classification(
            ClassificationPost(
                obj_id=public_source.id,
                classification="RRab",
                origin="SCoPe",
                taxonomy_id=taxonomy_id,
                probability=10.0,
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400


def test_add_and_retrieve_classification_group_id(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    sp = client(classification_token)
    classification_id = sp.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            origin="SCoPe",
            taxonomy_id=taxonomy_id,
            probability=1.0,
            group_ids=[public_group.id],
        )
    ).classification_id

    fetched = sp.fetch_classification(classification_id)
    assert fetched.classification == "Algol"
    assert fetched.probability == 1.0
    assert fetched.origin == "SCoPe"

    data = sp.fetch_classifications_query(num_per_page=100).classifications
    assert [d.classification == "Algol" for d in data]
    assert [d.origin == "SCoPe" for d in data]
    assert [d.probability == 1.0 for d in data]
    assert [d.obj_id == public_source.id for d in data]


def test_add_and_retrieve_classification_no_group_id(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    sp = client(classification_token)
    classification_id = sp.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            origin="SCoPe",
            taxonomy_id=taxonomy_id,
        )
    ).classification_id

    assert sp.fetch_classification(classification_id).classification == "Algol"


def test_cannot_add_classification_without_permission(
    taxonomy_token, view_only_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_classification(
            ClassificationPost(
                obj_id=public_source.id,
                classification="Algol",
                origin="SCoPe",
                taxonomy_id=taxonomy_id,
            )
        )
    assert err.value.status_code == 401


def test_update_classification_probability_records_edit(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    sp = client(classification_token)
    classification_id = sp.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=1.0,
            group_ids=[public_group.id],
        )
    ).classification_id

    # Zeroing the probability updates the existing classification in place
    # rather than posting a new one
    sp.update_classification(
        classification_id,
        ClassificationUpdate(
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=0,
        ),
    )

    classifications = sp.fetch_classifications(public_source.id)
    assert len(classifications) == 1
    assert classifications[0].id == classification_id
    assert classifications[0].probability == 0

    edits = classifications[0].edits
    assert len(edits) == 1
    assert edits[0].old_probability == 1.0
    assert edits[0].new_probability == 0

    # An update that doesn't change the probability adds no edit
    sp.update_classification(
        classification_id,
        ClassificationUpdate(
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=0,
        ),
    )

    classifications = sp.fetch_classifications(public_source.id)
    assert len(classifications[0].edits) == 1


def test_delete_classification(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    sp = client(classification_token)
    classification_id = sp.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            origin="SCoPe",
            taxonomy_id=taxonomy_id,
        )
    ).classification_id

    fetched = sp.fetch_classification(classification_id)
    assert fetched.classification == "Algol"
    assert fetched.origin == "SCoPe"

    sp.delete_classification(classification_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_classification(classification_id)
    assert err.value.status_code == 400


def test_obj_classifications(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    sp = client(classification_token)
    classification_id = sp.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            origin="SCoPe",
            taxonomy_id=taxonomy_id,
        )
    ).classification_id

    classifications = sp.fetch_classifications(public_source.id)
    assert classifications[0].classification == "Algol"
    assert classifications[0].origin == "SCoPe"
    assert classifications[0].id == classification_id
    assert len(classifications) == 1

    assert public_source.id in sp.fetch_sources_by_classification()


def test_add_and_retrieve_multiple_classifications(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    client(classification_token).post_classifications(
        [
            ClassificationPost(
                obj_id=public_source.id,
                classification="Algol",
                origin="SCoPe",
                taxonomy_id=taxonomy_id,
                probability=1.0,
                group_ids=[public_group.id],
            ),
            ClassificationPost(
                obj_id=public_source.id,
                classification="Time-domain Source",
                origin="SCoPe",
                taxonomy_id=taxonomy_id,
                probability=1.0,
                group_ids=[public_group.id],
            ),
        ]
    )

    data = (
        client(classification_token)
        .fetch_classifications_query(num_per_page=100)
        .classifications
    )
    assert any(d.classification == "Algol" for d in data)
    assert any(d.classification == "Time-domain Source" for d in data)


def test_obj_classifications_vote(
    taxonomy_token, classification_token, public_source, public_group
):
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    sp = client(classification_token)
    classification_id = sp.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            origin="SCoPe",
            taxonomy_id=taxonomy_id,
        )
    ).classification_id

    sp.post_classification_vote(classification_id, 1)

    classifications = sp.fetch_classifications(public_source.id)
    assert classifications[0].classification == "Algol"
    assert classifications[0].origin == "SCoPe"
    assert classifications[0].id == classification_id
    assert len(classifications) == 1
    assert len(classifications[0].votes) == 1
    assert classifications[0].votes[0].vote == 1

    sp.delete_classification_vote(classification_id)

    classifications = sp.fetch_classifications(public_source.id)
    assert classifications[0].classification == "Algol"
    assert classifications[0].origin == "SCoPe"
    assert classifications[0].id == classification_id
    assert len(classifications) == 1
    assert len(classifications[0].votes) == 0
