from skyportal.tests import api

# Obj.internal_key anonymizes objects in websocket refresh messages. It must only
# reach clients that can already see the object (via source/candidate responses,
# which the frontend's ws-invalidation keys on), and must not leak through other
# serializations. See skyportal issue #2585.


def test_internal_key_present_on_source_detail(view_only_token, public_source):
    status, data = api("GET", f"sources/{public_source.id}", token=view_only_token)
    assert status == 200
    assert data["data"]["internal_key"] == public_source.internal_key


def test_internal_key_present_on_sources_list(view_only_token, public_source):
    status, data = api(
        "GET", "sources", params={"sourceID": public_source.id}, token=view_only_token
    )
    assert status == 200
    row = next(s for s in data["data"]["sources"] if s["id"] == public_source.id)
    assert row["internal_key"] == public_source.internal_key


def test_internal_key_present_on_candidate(view_only_token, public_candidate):
    status, data = api(
        "GET", f"candidates/{public_candidate.id}", token=view_only_token
    )
    assert status == 200
    assert data["data"]["internal_key"] == public_candidate.internal_key


def test_internal_key_not_leaked_via_spectra(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/spectra", token=upload_data_token
    )
    assert status == 200
    spectra = data["data"]["spectra"]
    assert len(spectra) > 0
    for spectrum in spectra:
        assert "internal_key" not in spectrum
        assert "obj_internal_key" not in spectrum
