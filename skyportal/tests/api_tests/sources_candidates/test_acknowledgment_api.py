"""The acknowledgment endpoint must reflect what a source actually used."""

import sqlalchemy as sa

from skyportal.models import DBSession, Instrument
from skyportal.tests import api


def get_block(obj_id, token):
    status, data = api("GET", f"sources/{obj_id}/acknowledgment", token=token)
    assert status == 200
    return data["data"]


def test_bare_source_gets_the_site_sentence_only(
    public_source_no_data, upload_data_token
):
    """`public_source` ships with photometry, so use the one without any."""
    block = get_block(public_source_no_data.id, upload_data_token)
    assert block["text"]
    assert block["components"]["facilities"] == []
    assert block["components"]["programs"] == []


def test_photometry_adds_its_facility(
    public_source, ztf_camera, upload_data_token, public_group
):
    status, _ = api(
        "POST",
        "photometry",
        data={
            "obj_id": public_source.id,
            "mjd": 59801.3,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200

    block = get_block(public_source.id, upload_data_token)
    facilities = block["components"]["facilities"]
    assert ztf_camera.name in [f["instrument"] for f in facilities]
    # Named in the prose, not just listed in the components.
    assert ztf_camera.name in block["text"]


def test_instrument_acknowledgment_is_used_verbatim(
    public_source, ztf_camera, upload_data_token, public_group
):
    """A facility that has its own sentence must be cited with it, not just named."""
    sentence = "Based on observations obtained with the Samuel Oschin Telescope"
    session = DBSession()
    instrument = session.scalar(
        sa.select(Instrument).where(Instrument.id == ztf_camera.id)
    )
    instrument.acknowledgment = sentence
    session.commit()

    try:
        status, _ = api(
            "POST",
            "photometry",
            data={
                "obj_id": public_source.id,
                "mjd": 59802.3,
                "instrument_id": ztf_camera.id,
                "filter": "ztfg",
                "group_ids": [public_group.id],
                "mag": 12.4,
                "magerr": 0.3,
                "limiting_mag": 22,
                "magsys": "ab",
            },
            token=upload_data_token,
        )
        assert status == 200

        block = get_block(public_source.id, upload_data_token)
        assert sentence + "." in block["text"]
        # The generic "Data were obtained with ..." phrasing must not also appear
        # for a facility that supplied its own wording.
        assert f"Data were obtained with {ztf_camera.name}" not in block["text"]
    finally:
        session = DBSession()
        instrument = session.scalar(
            sa.select(Instrument).where(Instrument.id == ztf_camera.id)
        )
        instrument.acknowledgment = None
        session.commit()


def test_unknown_source_is_rejected(upload_data_token):
    status, _ = api(
        "GET", "sources/does-not-exist/acknowledgment", token=upload_data_token
    )
    assert status == 400


def test_telescope_acknowledgment_round_trips(super_admin_token):
    """The telescope endpoints use strict bodies, so the field must be declared."""
    import uuid

    name = str(uuid.uuid4())
    sentence = "Based on observations obtained with the Samuel Oschin Telescope"
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": name,
            "nickname": name[:10],
            "diameter": 1.2,
            "robotic": True,
            "fixed_location": False,
            "acknowledgment": sentence,
        },
        token=super_admin_token,
    )
    assert status == 200
    telescope_id = data["data"]["id"]

    status, data = api("GET", f"telescope/{telescope_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["acknowledgment"] == sentence

    updated = sentence + " (updated)"
    status, _ = api(
        "PUT",
        f"telescope/{telescope_id}",
        data={"acknowledgment": updated},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"telescope/{telescope_id}", token=super_admin_token)
    assert data["data"]["acknowledgment"] == updated


def test_selection_narrows_the_text_but_not_the_components(
    public_source, ztf_camera, upload_data_token, public_group
):
    """The dialog shows everything detected while citing only what is ticked."""
    status, _ = api(
        "POST",
        "photometry",
        data={
            "obj_id": public_source.id,
            "mjd": 59803.3,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200

    full = get_block(public_source.id, upload_data_token)
    assert ztf_camera.name in full["text"]

    # Deselect every instrument: the facility drops out of the prose, but is
    # still offered in the components so it can be ticked back on.
    instrument_id = next(
        f["id"]
        for f in full["components"]["facilities"]
        if f["instrument"] == ztf_camera.name
    )
    status, data = api(
        "GET",
        f"sources/{public_source.id}/acknowledgment"
        f"?exclude_instrument_ids={instrument_id}",
        token=upload_data_token,
    )
    assert status == 200
    narrowed = data["data"]
    assert ztf_camera.name not in narrowed["text"]
    assert ztf_camera.name in [
        f["instrument"] for f in narrowed["components"]["facilities"]
    ]
