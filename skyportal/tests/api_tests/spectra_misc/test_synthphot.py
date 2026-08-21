import datetime
import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.instruments import InstrumentPost
from skyportal_py.spectra import SpectrumPost
from skyportal_py.telescopes import TelescopePost

from skyportal.tests import client


def test_synthetic_photometry(super_admin_token, public_source, public_group):
    sp = client(super_admin_token)
    telescope_name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=telescope_name,
            nickname=telescope_name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="spectrograph",
            telescope_id=telescope_id,
        )
    ).id

    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at=str(datetime.datetime.now()),
            instrument_id=instrument_id,
            wavelengths=[1000, 3000, 5000, 7000, 9000],
            fluxes=[232.1, 234.2, 232.1, 235.3, 232.1],
            units="erg/s/cm/cm/AA",
            group_ids=[public_group.id],
        )
    ).id

    filters = ["ztfg", "ztfr", "ztfi"]
    sp.post_synthetic_photometry(spectrum_id, filters)

    # Check for single GET call as well
    source = sp.fetch_source(public_source.id, include_photometry=True)
    assert source.id == public_source.id
    for filt in filters:
        assert any(p.filter == filt for p in source.photometry)

    filters = ["f140w", "f153m", "f160w"]
    with pytest.raises(SkyPortalError, match="outside spectral range") as err:
        sp.post_synthetic_photometry(spectrum_id, filters)
    assert err.value.status_code == 400
