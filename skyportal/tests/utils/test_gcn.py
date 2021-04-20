import os
import numpy as np
from astropy.time import Time

from skyportal.utils.gcn import GCNHandler
from skyportal.models import Event, Localization


def test_gcn():

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    GCNHandler(datafile)

    dateobs = Time("2019-04-25 08:18:05", format='iso').datetime

    event = Event.query.filter_by(dateobs=dateobs).one()
    assert event.dateobs == dateobs
    assert 'GW' in event.tags

    localization = Localization.query.filter_by(dateobs=dateobs).one()
    assert localization.dateobs == dateobs
    assert localization.localization_name == "bayestar.fits.gz"
    assert np.isclose(np.sum(localization.flat_2d), 1)
