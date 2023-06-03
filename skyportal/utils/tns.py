from skyportal.app_utils import get_app_base_url

import astropy.units as u
from astropy.table import Table
from astropy.time import Time
from astropy.coordinates import SkyCoord
import json
import pandas as pd
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
    'ALFOSC': 41,
    'ATLAS': [159, 160, 255, 167],
    'DECam': 172,
    'EFOSC2': 30,
    'Goodman': 136,
    'SEDM': 225,
    'SPRAT': 156,
    'ZTF': 196,
}

SNCOSMO_TO_TNSFILTER = {
    'atlasc': 71,
    'atlaso': 72,
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

TNSFILTER_TO_SNCOSMO = {v: k for k, v in SNCOSMO_TO_TNSFILTER.items()}


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


def read_tns_photometry(photometry, session):

    tns_instrument_id = photometry["instrument"]["id"]
    inst_name = None
    for key, value in TNS_INSTRUMENT_IDS.items():
        if type(value) == list:
            if tns_instrument_id in value:
                inst_name = key
        else:
            if tns_instrument_id == value:
                inst_name = key
    if inst_name is None:
        raise ValueError(f'Cannot find TNS ID mapping for {tns_instrument_id}')

    instrument = session.scalars(
        sa.select(Instrument).where(Instrument.name == inst_name)
    ).first()
    if instrument is None:
        raise ValueError(f'Cannot find instrument with name {inst_name}')

    flux_unit = photometry['flux_unit']
    if not flux_unit['name'] == 'ABMag':
        raise ValueError(f"Cannot understand flux_unit name: {flux_unit['name']}")

    tns_filter_id = photometry["filters"]["id"]
    if tns_filter_id not in TNSFILTER_TO_SNCOSMO:
        raise ValueError(f'Cannot find TNS ID mapping for {tns_filter_id}')
    filter_name = TNSFILTER_TO_SNCOSMO[tns_filter_id]

    if filter_name not in instrument.filters:
        raise ValueError(f'{filter_name} not in {instrument.nickname}')

    if photometry['limflux'] == '':
        data_out = {
            'mjd': [Time(photometry['jd'], format='jd').mjd],
            'mag': None,
            'magerr': None,
            'limiting_mag': [photometry['flux']],
            'filter': [filter_name],
            'magsys': ['ab'],
        }
    else:
        data_out = {
            'mjd': [Time(photometry['jd'], format='jd').mjd],
            'mag': [photometry['flux']],
            'magerr': [photometry['fluxerr']],
            'limiting_mag': [photometry['limflux']],
            'filter': [filter_name],
            'magsys': ['ab'],
        }

    df = pd.DataFrame.from_dict(data_out)

    return df, instrument.id


def read_tns_spectrum(spectrum, session):

    try:
        tab = Table.read(spectrum["asciifile"], format="ascii")
        tab.rename_column(tab.columns[0].name, 'wavelengths')
        tab.rename_column(tab.columns[1].name, 'fluxes')
        if len(tab.columns) == 3:
            tab.rename_column(tab.columns[2].name, 'errors')
    except Exception:
        tab = Table.read(spectrum["asciifile"], format="fits")

    data = tab.to_pandas().to_dict(orient='list')
    data["observed_at"] = Time(spectrum["jd"], format="jd").isot
    data["origin"] = "TNS"

    tns_instrument_id = spectrum["instrument"]["id"]
    inst_name = None
    for key, value in TNS_INSTRUMENT_IDS.items():
        if type(value) == list:
            if tns_instrument_id in value:
                inst_name = key
        else:
            if tns_instrument_id == value:
                inst_name = key
    if inst_name is None:
        raise ValueError(f'Cannot find TNS ID mapping for {tns_instrument_id}')

    instrument = session.scalars(
        sa.select(Instrument).where(Instrument.name == inst_name)
    ).first()
    if instrument is None:
        raise ValueError(f'Cannot find instrument with name {inst_name}')
    data["instrument_id"] = instrument.id

    return data
