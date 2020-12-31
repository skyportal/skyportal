import pytest
import numpy as np
from astropy.time import Time
from astroplan import FixedTarget
from skyportal.models import Obj
from astropy.coordinates.name_resolve import NameResolveError

ads_down = False

try:
    pole_star = FixedTarget.from_name('Polaris')
except NameResolveError:
    ads_down = True

try:
    horizon_star = FixedTarget.from_name('Skat')
except NameResolveError:
    ads_down = True

if not ads_down:
    # roughly sunset to sunrise on July 22 2020 (UTC; for palomar observatory)
    night_times = Time(
        [f'2020-07-22 {h:02d}:00:00.000' for h in range(3, 13)], format='iso'
    )

    # taken from http://www.briancasey.org/artifacts/astro/airmass.cgi?
    pole_star_airmass = np.asarray(
        [1.851, 1.850, 1.846, 1.841, 1.834, 1.826, 1.818, 1.810, 1.802, 1.796]
    )

    horizon_star_airmass = np.asarray(
        [np.inf, np.inf, np.inf, 8.222, 3.238, 2.152, 1.728, 1.556, 1.533, 1.647]
    )

    star_dict = {
        'polaris': {'target': pole_star, 'airmass': pole_star_airmass},
        'skat': {'target': horizon_star, 'airmass': horizon_star_airmass},
    }


@pytest.mark.skipif(ads_down, reason='Star data server is down.')
@pytest.mark.parametrize('star', ['polaris', 'skat'])
def test_airmass(ztf_camera, star):
    star_obj = star_dict[star]['target']
    star_obj = Obj(ra=star_obj.ra.deg, dec=star_obj.dec.deg)
    telescope = ztf_camera.telescope
    airmass_calc = star_obj.airmass(telescope, night_times)

    # departure from plane-parallel becomes significant
    airmass_islarge = airmass_calc > 5

    # we use a somewhat large tolerance as brian casey's answers are calculated
    # using secz whereas ours are pickering (2002)
    np.testing.assert_allclose(
        airmass_calc[~airmass_islarge],
        star_dict[star]['airmass'][~airmass_islarge],
        rtol=5e-2,
        atol=0.02,
    )

    np.testing.assert_allclose(
        airmass_calc[airmass_islarge],
        star_dict[star]['airmass'][airmass_islarge],
        rtol=1e-1,
        atol=1.0,
    )


@pytest.mark.skipif(ads_down, reason='Star data server is down.')
def test_airmass_single(ztf_camera, public_source):
    telescope = ztf_camera.telescope
    time = night_times[-1]
    airmass_calc = public_source.airmass(telescope, time)

    # we use a somewhat large tolerance as brian casey's answers are calculated
    # using secz whereas ours are pickering (2002)
    np.testing.assert_allclose(airmass_calc, 1.198, rtol=5e-2, atol=0.02)
