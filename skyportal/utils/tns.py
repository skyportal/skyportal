from skyportal.app_utils import get_app_base_url

import astropy.units as u
from astropy.table import Table
from astropy.coordinates import SkyCoord
from astropy.time import Time
import json
import requests
import sqlalchemy as sa
import urllib

from baselayer.app.env import load_env
from baselayer.log import make_log

from ..models import Instrument

env, cfg = load_env()

app_url = get_app_base_url()

TNS_URL = cfg['app.tns_endpoint']
search_url = urllib.parse.urljoin(TNS_URL, 'api/get/search')

log = make_log('tns')

# IDs here: https://www.wis-tns.org/api/values

TNS_INSTRUMENT_IDS = {
    'DECam': 172,
    'EFOSC2': 30,
    'Goodman': 136,
    'SEDM': 225,
    'SPRAT': 156,
    'ZTF': 196,
}
TNS_FILTER_IDS = {
    'sdssu': 20,
    'sdssg': 21,
    'sdssr': 22,
    'sdssi': 23,
    'sdssz': 24,
    'desu': 20,
    'desg': 21,
    'desr': 22,
    'desi': 23,
    'desz': 24,
    'desy': 81,
    'ztfg': 110,
    'ztfr': 111,
    'ztfi': 112,
}
INSTRUMENT_TNS_IDS = {v: k for k, v in TNS_INSTRUMENT_IDS.items()}


def get_IAUname(api_key, headers, obj_id=None, ra=None, dec=None, radius=5):
    """Query TNS to get IAU name (if exists)
    Parameters
    ----------
    objname : str
        Name of the object to query TNS for
    headers : str
        TNS query headers
    obj_id : str
        Object name to search for
    ra : float
        Right ascension of object to search for
    dec : float
        Declination of object to search for
    radius : float
        Radius of object to search for
    Returns
    -------
    list
        IAU prefix, IAU name
    """

    if obj_id is not None:
        req_data = {
            "ra": "",
            "dec": "",
            "radius": "",
            "units": "",
            "objname": "",
            "objname_exact_match": 0,
            "internal_name": obj_id.replace('_', ' '),
            "internal_name_exact_match": 0,
            "objid": "",
        }
    elif ra is not None and dec is not None:
        c = SkyCoord(ra=ra * u.degree, dec=dec * u.degree, frame='icrs')
        req_data = {
            "ra": c.ra.to_string(unit=u.hour, sep=':', pad=True),
            "dec": c.dec.to_string(unit=u.degree, sep=':', alwayssign=True, pad=True),
            "radius": f"{radius}",
            "units": "arcsec",
            "objname": "",
            "objname_exact_match": 0,
            "internal_name": "",
            "internal_name_exact_match": 0,
            "objid": "",
        }
    else:
        raise ValueError('Must define obj_id or ra/dec.')

    data = {'api_key': api_key, 'data': json.dumps(req_data)}
    r = requests.post(search_url, headers=headers, data=data)
    json_response = json.loads(r.text)
    reply = json_response['data']['reply']

    if len(reply) > 0:
        return reply[0]['prefix'], reply[0]['objname']
    else:
        return None, None


def post_tns(
    obj_ids,
    tnsrobot_id,
    user_id,
    reporters="",
    archival=False,
    archival_comment="",
    timeout=2,
):

    request_body = {
        'obj_ids': obj_ids,
        'tnsrobot_id': tnsrobot_id,
        'user_id': user_id,
        'reporters': reporters,
        'archival': archival,
        'archival_comment': archival_comment,
    }

    tns_microservice_url = f'http://127.0.0.1:{cfg["ports.tns_queue"]}'

    resp = requests.post(tns_microservice_url, json=request_body, timeout=timeout)
    if resp.status_code != 200:
        log(
            f'TNS request failed for {str(request_body["obj_ids"])} by user ID {request_body["user_id"]}: {resp.content}'
        )


def read_tns_spectrum(spectrum, session):

    try:
        tab = Table.read(spectrum["asciifile"], format="ascii")
        tab.rename_column('col1', 'wavelengths')
        tab.rename_column('col2', 'fluxes')
        if len(tab.columns) == 3:
            tab.rename_column('col3', 'errors')
    except Exception:
        tab = Table.read(spectrum["asciifile"], format="fits")

    data = tab.to_pandas().to_dict(orient='list')
    data["observed_at"] = Time(spectrum["jd"], format="jd").isot
    data["origin"] = "TNS"

    tns_instrument_id = spectrum["instrument"]["id"]
    if tns_instrument_id not in INSTRUMENT_TNS_IDS:
        raise ValueError(f'Cannot find TNS ID mapping for {tns_instrument_id}')
    inst_name = INSTRUMENT_TNS_IDS[tns_instrument_id]

    instrument = session.scalars(
        sa.select(Instrument).where(Instrument.name == inst_name)
    ).first()
    if instrument is None:
        raise ValueError(f'Cannot find instrument with name {inst_name}')
    data["instrument_id"] = instrument.id

    return data
