import gzip
import io

import numpy as np
import pytest
from astropy.io import fits

from skyportal.utils.archival_rv import (
    open_archive_fits,
    read_spectrum,
    trusted_fits_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.lamost.org/dr12/v2.0/spectrum/fits/123",
        "https://www.lamost.org@localhost/dr12/v2.0/spectrum/fits/123",
        "https://www.lamost.org/dr12/v2.0/spectrum/fits/123?url=http://localhost",
        "https://dr20.sdss.org/sas/dr20/prior-surveys/../private.fits",
        "https://data.desi.lbl.gov/public/dr1/spectro/redux/iron/healpix/main/bright/spectra.fits.gz",
    ],
)
def test_archive_locator_rejects_unrecognized_urls(url):
    assert not any(
        trusted_fits_url(url, kind) for kind in ("lamost", "boss", "apogee", "desi")
    )


def test_desi_exposure_returns_only_the_requested_fiber():
    target_id = 39633132135123560
    hdus = fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.BinTableHDU.from_columns(
                [
                    fits.Column(
                        name="TARGETID", format="K", array=[target_id - 1, target_id]
                    )
                ],
                name="FIBERMAP",
            ),
            fits.ImageHDU(np.array([4000.0, 4010.0, 4020.0]), name="WAVELENGTH"),
            fits.ImageHDU(np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), name="FLUX"),
            fits.ImageHDU(np.ones((2, 3)), name="IVAR"),
            fits.ImageHDU(np.array([[0, 0, 0], [0, 2, 0]]), name="MASK"),
        ]
    )
    url = (
        "https://data.desi.lbl.gov/public/dr1/spectro/redux/iron/"
        "exposures/20210418/00085351/cframe-b1-00085351.fits.gz?download=1"
    )
    assert trusted_fits_url(url, "desi")
    (trace,) = read_spectrum(hdus, "desi", {"target_id": str(target_id)}, url)
    assert trace == {
        "label": "B",
        "wavelengths": [4000.0, 4020.0],
        "fluxes": [4.0, 6.0],
    }
    with pytest.raises(ValueError, match="does not uniquely identify"):
        list(read_spectrum(hdus, "desi", {"target_id": str(target_id + 1)}, url))


def test_lamost_exposure_without_andmask():
    hdu = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="wavelength", format="D", array=[6500.0, 6501.0]),
            fits.Column(name="flux", format="D", array=[1.0, 2.0]),
            fits.Column(name="ivar", format="D", array=[2.0, 0.0]),
        ],
        name="R-123456",
    )
    url = "https://www.lamost.org/openapi/dr12/v2.0/mrs/spectrum/fits?obsid=123"
    (trace,) = read_spectrum(
        fits.HDUList([fits.PrimaryHDU(), hdu]),
        "lamost",
        {"extensions": ["R-123456"]},
        url,
    )
    assert trace["wavelengths"] == [6500.0]


def test_archive_reader_detects_gzip_without_filename():
    data = io.BytesIO()
    fits.PrimaryHDU(np.array([42])).writeto(data)
    with open_archive_fits(io.BytesIO(gzip.compress(data.getvalue()))) as hdus:
        assert hdus[0].data.tolist() == [42]
