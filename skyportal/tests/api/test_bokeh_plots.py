import os
from skyportal.tests import api
import numpy as np
import datetime
from bokeh.util import serialization


def black_body(la, temp):
    """
    get the amount of radiation expected from a black body
    of the given temperature "temp", at the given wavelengths "la".

    Parameters
    ----------
    la : float array or scalar
        wavelength(s) where the radiation should be calculated.
    temp : float scalar
        temperature of the black body.

    Returns
    -------
    float array
        return the radiation (in units of Watts per steradian per m^2 per nm)
    """
    const = (
        0.014387773538277204  # h*c/k_b = 6.62607004e-34 * 299792458 / 1.38064852e-23
    )
    amp = 1.1910429526245744e-25  # 2*h*c**2 * (nm / m) = 2*6.62607004e-34 * 299792458**2 / 1e9 the last term is units
    la = la * 1e-9  # convert wavelength from nm to m

    return amp / (la ** 5 * (np.exp(const / (la * temp)) - 1))


def get_plot_data(data):
    """
    Parse the dictionary "data" received from a GET request
    to api/internal/plot/spectroscopy/<obj_id> and recover
    the underlying data for all spectra in the plot.

    Parameters
    ----------
    data : dict
       A dictionary loaded from the JSON file sent by the plotting API call.

    Returns
    -------
    list
        Returns a list of dictionaries with the flux, wavelength, etc.,
        one dictionary per spectrum.
        Note that the plot outputs several repeated versions of each spectrum,
        i.e., one for the step plot, one for the line plot with the tooltip,
        one for the smoothed spectrum. Each one is a separate dictionary.
    """
    objects = []
    for doc in data['data']['bokehJSON']['doc']['roots']['references']:
        if 'data' in doc['attributes']:
            new_obj = {}
            # go over each attribute with data and look for these keys
            for key in ['wavelength', 'flux', 'flux_original', 'x', 'y']:
                if key in doc['attributes']['data']:
                    array = doc['attributes']['data'][key]
                    if type(array) == list:
                        new_obj[key] = np.array(array)
                    else:
                        new_obj[key] = serialization.decode_base64_dict(array)

            # tooltip data that's duplicated so we only need to get the first item in each array
            for key in [
                'id',
                'telescope',
                'instrument',
                'origin',
                'date_observed',
                'pi',
                'annotations',
                'altdata',
            ]:
                if key in doc['attributes']['data']:
                    new_obj[key] = doc['attributes']['data'][key][0]

            if 'telescope' in new_obj:

                objects.append(new_obj)

    return objects


def test_spectrum_plot(upload_data_token, public_source, public_group, lris):

    wavelength = np.arange(400, 650, 1, dtype=float)
    flux = black_body(wavelength, 5700)
    flux_noisy = flux + np.random.normal(0, 100, wavelength.shape)
    wavelength = wavelength
    normfactor = np.median(np.abs(flux_noisy))
    flux /= normfactor
    flux_noisy /= normfactor

    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': list(wavelength),
            'fluxes': list(flux_noisy),
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == flux_noisy[0]
    assert data['data']['obj_id'] == public_source.id

    # get the JSON specifications for making a spectrum plot
    status, data = api(
        'GET',
        f'internal/plot/spectroscopy/{public_source.id}',
        token=upload_data_token,
        params={'smoothing': True},
    )

    spectra = get_plot_data(data)
    spectra = [s for s in spectra if s['id'] == spectrum_id]
    smooth_spectrum = [
        s for s in spectra if not np.array_equal(s['flux'], s['flux_original'])
    ]

    assert len(smooth_spectrum) == 1
    smooth_spectrum = smooth_spectrum[0]

    chi2_original = np.nansum((smooth_spectrum['flux_original'] - flux) ** 2) / len(
        flux
    )
    chi2_smoothed = np.nansum((smooth_spectrum['flux'] - flux) ** 2) / len(flux)

    assert (
        chi2_original > chi2_smoothed * 5
    )  # should be about 10 times smaller (use 5 as margin of error)


def test_spectrum_smooth_nan(upload_data_token, public_source, public_group, lris):
    observed_at = str(datetime.datetime.now())
    filename = f'{os.path.dirname(__file__)}/../data/spectrum_with_nan.txt'
    with open(filename, 'r') as f:
        status, data = api(
            'POST',
            'spectrum/ascii',
            data={
                'obj_id': str(public_source.id),
                'observed_at': observed_at,
                'instrument_id': lris.id,
                'group_ids': [public_group.id],
                'fluxerr_column': None,
                'ascii': f.read(),
                'filename': filename,
            },
            token=upload_data_token,
        )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data['data']['id']

    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 1.0587752819225242
    assert data['data']['obj_id'] == public_source.id

    # get the JSON specifications for making a spectrum plot
    status, data = api(
        'GET',
        f'internal/plot/spectroscopy/{public_source.id}',
        token=upload_data_token,
        params={'smoothing': True},
    )

    spectra = get_plot_data(data)
    spectra = [s for s in spectra if s['id'] == spectrum_id]
    smooth_spectrum = [
        s
        for s in spectra
        if not np.array_equal(s['flux'], s['flux_original'], equal_nan=True)
    ]

    assert len(smooth_spectrum) == 1
    smooth_spectrum = smooth_spectrum[0]

    # original flux should have one NaN, smoothed flux should not have any NaNs
    assert np.sum(np.isnan(smooth_spectrum['flux_original'])) == 1
    assert np.sum(np.isnan(smooth_spectrum['flux'])) == 0
