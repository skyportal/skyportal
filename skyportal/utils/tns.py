from skyportal.app_utils import get_app_base_url

import astropy.units as u
from astropy.coordinates import SkyCoord
import json
import requests
import urllib

from baselayer.app.env import load_env
from baselayer.log import make_log

env, cfg = load_env()

app_url = get_app_base_url()

TNS_URL = cfg['app.tns_endpoint']
search_url = urllib.parse.urljoin(TNS_URL, 'api/get/search')

log = make_log('tns')


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


def post_tns(obj_ids, tnsrobot_id, user_id, reporters="", timeout=2):

    request_body = {
        'obj_ids': obj_ids,
        'tnsrobot_id': tnsrobot_id,
        'user_id': user_id,
        'reporters': reporters,
    }

    tns_microservice_url = f'http://127.0.0.1:{cfg["ports.tns_queue"]}'

    resp = requests.post(tns_microservice_url, json=request_body, timeout=timeout)
    if resp.status_code != 200:
        log(
            f'TNS request failed for {str(request_body["obj_ids"])} by user ID {request_body["user_id"]}: {resp.content}'
        )
