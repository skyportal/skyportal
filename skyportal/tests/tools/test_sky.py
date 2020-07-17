import numpy as np
from astropy.time import Time


def test_airmass(public_source, ztf_camera):
    telescope = ztf_camera.telescope
    times = Time(np.linspace(58000, 59000), format='mjd')
    airmass_calc = public_source.airmass(telescope, times)
    airmass_true = np.asarray([np.inf, np.inf, 4.259917450786537,
                               np.inf, 1.7869997087619442, np.inf,
                               1.290905161637478, np.inf,
                               1.1974586801911271, np.inf,
                               1.3723658116877935, np.inf,
                               2.096562416708359, np.inf,
                               7.438387758506691, 13.363224561907067,
                               np.inf, 2.3656233357751506, np.inf,
                               1.4392303135320286, np.inf,
                               1.206854025593942, np.inf,
                               1.2549876733727305, np.inf,
                               1.6503274398889038, np.inf,
                               3.3861055727264118, np.inf, np.inf,
                               3.716774181803253, np.inf,
                               1.7057972192674362, np.inf,
                               1.2692835565701281, np.inf,
                               1.201773923401473, np.inf,
                               1.4083315964524334, np.inf,
                               2.2389891804553934, np.inf,
                               9.963125094158245, 9.250267629036953,
                               np.inf, 2.204282485422739, np.inf,
                               1.3996274818640069, np.inf,
                               1.2005171979211768])
    np.testing.assert_allclose(airmass_calc, airmass_true)


def test_airmass_single(public_source, ztf_camera):
    telescope = ztf_camera.telescope
    times = Time(59000, format='mjd')
    airmass_calc = public_source.airmass(telescope, times)
    np.testing.assert_allclose(airmass_calc, 1.2005171979211768)


def test_altitude(public_source, ztf_camera):
    telescope = ztf_camera.telescope
    times = Time(np.linspace(58000, 59000), format='mjd')
    airmass_calc = public_source.altitude(telescope, times).value
    airmass_true = np.asarray([-8.236471205478335, -2.4545891949233756,
                               13.326802219762435, -23.74557916152537,
                               33.92767084312363, -42.959308181645206,
                               50.70728372038899, -55.41584605114044,
                               56.567587555021746, -53.09656119636098,
                               46.70290093160975, -37.9700704087155,
                               28.367457029348937, -17.883570472982335,
                               7.308359004302709, 3.6098292922763755,
                               -14.244411774446405, 24.869209668119726,
                               -34.72965130147986, 43.93579830565533,
                               -51.14565469192363, 55.89564715643906,
                               -56.225574836441474, 52.76420934533121,
                               -45.77979496074616, 37.20534251455628,
                               -27.26010603174954, 16.977678586727993,
                               -6.154734130046218, -4.538229003092764,
                               15.389072752599379, -25.732842728787002,
                               35.795464613813444, -44.57413579009122,
                               51.92024388077538, -55.927548597147954,
                               56.256198677708994, -52.02567586219354,
                               45.165235761101464, -36.14139378811532,
                               26.39831994573107, -15.824184113158143,
                               5.223815732733556, 5.701900776026573,
                               -16.295480151057205, 26.85173507328798,
                               -36.56327857873727, 45.526309946450226,
                               -52.280628412384736, 56.34639121561762])
    np.testing.assert_allclose(airmass_calc, airmass_true)
