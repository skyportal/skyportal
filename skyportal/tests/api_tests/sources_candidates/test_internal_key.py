from skyportal_py.spectra import SpectrumPost

from skyportal.tests import client

# Obj.internal_key anonymizes objects in websocket refresh messages. It must only
# reach clients that can already see the object (via source/candidate responses,
# which the frontend's ws-invalidation keys on), and must not leak through other
# serializations. See skyportal issue #2585.


def test_internal_key_present_on_source_detail(view_only_token, public_source):
    source = client(view_only_token).fetch_source(public_source.id)
    assert source.internal_key == public_source.internal_key


def test_internal_key_present_on_sources_list(view_only_token, public_source):
    page = client(view_only_token).fetch_sources(source_id=public_source.id)
    row = next(s for s in page.sources if s.id == public_source.id)
    assert row.internal_key == public_source.internal_key


def test_internal_key_present_on_candidate(view_only_token, public_candidate):
    candidate = client(view_only_token).fetch_candidate(public_candidate.id)
    assert candidate.internal_key == public_candidate.internal_key


def test_internal_key_not_leaked_via_spectra(
    upload_data_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    )

    spectra = sp.fetch_spectra(public_source.id)
    assert len(spectra) > 0
    # Spectrum forbids extra fields, so validation alone would reject leaked keys.
    for spectrum in spectra:
        assert not hasattr(spectrum, "internal_key")
        assert not hasattr(spectrum, "obj_internal_key")
