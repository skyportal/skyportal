import os
import numpy as np
from astropy.time import Time

from skyportal.models import GcnEvent, Localization
from skyportal.tests import api


def test_gcn(super_admin_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('PUT', 'gcn/upload', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = Time("2019-04-25 08:18:05", format='iso').datetime

    event = GcnEvent.query.filter_by(dateobs=dateobs).one()
    assert event.dateobs == dateobs
    assert 'GW' in event.tags

    localization = Localization.query.filter_by(dateobs=dateobs).one()
    assert localization.dateobs == dateobs
    assert localization.localization_name == "bayestar.fits.gz"
    assert np.isclose(np.sum(localization.flat_2d), 1)

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('PUT', 'gcn/upload', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = Time("2018-01-16 00:36:53", format='iso').datetime
    event = GcnEvent.query.filter_by(dateobs=dateobs).one()
    assert event.dateobs == dateobs
    assert 'GRB' in event.tags

    localization = Localization.query.filter_by(dateobs=dateobs).one()
    assert localization.dateobs == dateobs
    assert localization.localization_name == "214.74000_28.14000_11.19000"
    assert np.isclose(np.sum(localization.flat_2d), 1)
