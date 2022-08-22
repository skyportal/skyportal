from astropy.time import Time
import lxml
import time

from skyportal.utils.gcn import get_dateobs
from skyportal.tests import api


def load_gcnevent(datafile, token):

    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}
    root = lxml.etree.fromstring(payload)

    dateobs = Time(get_dateobs(root)).isot

    RETRIES = 10

    # wait for the gcnevents to populate
    ntries = 0
    gcnevent_loaded = False

    while (ntries < RETRIES) and not gcnevent_loaded:
        status, data = api('POST', 'gcn_event', data=data, token=token)
        if status != 200:
            ntries = ntries + 1
            time.sleep(5)
            continue
        else:
            gcnevent_loaded = True
    assert data['status'] == 'success'

    gcnevent_id = data['data']['gcnevent_id']

    # wait for event to load
    nretries = 0
    gcnevent_loaded = False

    while (ntries < RETRIES) and not gcnevent_loaded:
        status, data = api('GET', f"gcn_event/{dateobs}", token=token)
        if status != 200:
            nretries = nretries + 1
            time.sleep(5)
            continue
        else:
            gcnevent_loaded = True
    assert data['status'] == 'success'

    return gcnevent_id
