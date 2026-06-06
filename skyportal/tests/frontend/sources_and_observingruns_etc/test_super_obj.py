"""Frontend (Playwright) test for meta-object (SuperObj) read-aggregation.

Links two sources under a SuperObj and verifies that the source page renders a
classification belonging to the *other* underlying source, tagged with a
clickable provenance chip pointing back to that source.
"""

import uuid

import sqlalchemy as sa
from playwright.sync_api import expect

from skyportal.models import DBSession, Obj, SuperObj
from skyportal.tests import api

SIMPLE_TAXONOMY = {
    "class": "Cepheid",
    "tags": ["giant/supergiant", "instability strip", "standard candle"],
    "other names": ["Cep", "CEP"],
    "subclasses": [
        {"class": "Anomolous", "other names": ["Anomolous Cepheid", "BLBOO"]},
    ],
}


def _link_super_obj(obj_ids):
    """Link the given Objs under a fresh SuperObj; return (super_obj_id, teardown)."""
    session = DBSession()
    objs = [session.scalar(sa.select(Obj).where(Obj.id == oid)) for oid in obj_ids]
    super_obj = SuperObj(name="meta-" + str(uuid.uuid4()))
    super_obj.objs = objs
    session.add(super_obj)
    session.commit()
    super_obj_id = super_obj.id

    def teardown():
        s = DBSession()
        so = s.scalar(sa.select(SuperObj).where(SuperObj.id == super_obj_id))
        if so is not None:
            so.objs = []
            s.commit()
            s.delete(so)
            s.commit()

    return super_obj_id, teardown


def test_super_obj_classification_provenance_on_source_page(
    page,
    user,
    upload_data_token,
    taxonomy_token,
    classification_token,
    public_group,
    public_source,
):
    """A classification on a linked source shows up on this source's page with a
    provenance chip linking back to the source it came from."""
    obj1 = public_source.id
    obj2 = f"{uuid.uuid4().hex[:10]}_meta2"

    status, _ = api(
        "POST",
        "sources",
        data={"id": obj2, "ra": 234.22, "dec": -22.33, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200

    tax_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": tax_name,
            "hierarchy": SIMPLE_TAXONOMY,
            "group_ids": [public_group.id],
            "version": "test0.1",
        },
        token=taxonomy_token,
    )
    assert status == 200, data
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": obj2,
            "classification": "Cepheid",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200, data

    _, teardown = _link_super_obj([obj1, obj2])
    try:
        page.goto(f"/become_user/{user.id}")
        page.goto(f"/source/{obj1}")
        expect(page.locator(f'//h6[text()="{obj1}"]').first).to_be_visible()

        # The aggregated classification from the linked source is shown ...
        expect(page.locator("//*[contains(text(), 'Cepheid')]").first).to_be_visible(
            timeout=20000
        )
        # ... tagged with a provenance chip linking back to that source.
        expect(
            page.locator(f'//a[contains(@href, "/source/{obj2}")]').first
        ).to_be_visible(timeout=20000)
    finally:
        teardown()
