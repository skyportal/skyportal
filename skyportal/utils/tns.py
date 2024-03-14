import json
import time
import urllib

import astropy.units as u
import pandas as pd
import requests
import sqlalchemy as sa
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.time import Time
from bs4 import BeautifulSoup

from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.app_utils import get_app_base_url

from ..models import Instrument

env, cfg = load_env()

app_url = get_app_base_url()

TNS_URL = cfg['app.tns.endpoint']
search_url = urllib.parse.urljoin(TNS_URL, 'api/get/search')
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')
object_url = urllib.parse.urljoin(TNS_URL, 'api/get/object')

log = make_log('tns_utils')

# IDs here: https://www.wis-tns.org/api/values

TNS_INSTRUMENT_IDS = {
    'alfosc': 41,
    'asas-sn': 195,
    'atlas': [153, 159, 160, 255, 256, 167],
    'decam': 172,
    'efosc2': 30,
    'gaia': 163,
    'goodman': 136,
    'goto': [218, 264, 265, 266],
    'ps1': [98, 154, 155, 257],
    'sedm': [149, 225],
    'sprat': 156,
    'ztf': 196,
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
    'gaia::g': 75,
    'gotol': 121,
    'gotor': 122,
    'gotog': 123,
    'gotob': 124,
    'ps1::g': 56,
    'ps1::r': 57,
    'ps1::i': 58,
    'ps1::z': 59,
    'ps1::w': 26,
    'ztfg': 110,
    'ztfr': 111,
    'ztfi': 112,
}

TNSFILTER_TO_SNCOSMO = {v: k for k, v in SNCOSMO_TO_TNSFILTER.items()}

# here we store regex patterns, to validate that a source name is in the correct format
# for a given TNS source group. Used to not submit incorrect sources to TNS.
TNS_SOURCE_GROUP_NAMING_CONVENTIONS = {
    # ZTF: ZTF + 2 digits + 7 lowercase characters
    48: r"ZTF\d{2}[a-z]{7}",
}


def get_recent_TNS(api_key, headers, public_timestamp, get_data=True):
    """Query TNS to get IAU name (if exists)
    Parameters
    ----------
    api_key : str
        TNS api key
    headers : str
        TNS query headers
    public_timestamp : str
        Start date in ISO format.
    Returns
    -------
    List[dict]
        Source entries of id, ra, and dec.
    """

    req_data = {
        "ra": "",
        "dec": "",
        "radius": "",
        "units": "",
        "objname": "",
        "internal_name": "",
        "public_timestamp": public_timestamp,
        "objid": "",
    }

    data = {'api_key': api_key, 'data': json.dumps(req_data)}
    status_code = 429
    n_retries = 0
    r = None
    while status_code == 429 and n_retries < 24:
        r = requests.post(search_url, headers=headers, data=data)
        status_code = r.status_code
        if status_code == 429:
            log(
                f'TNS request rate limited: {str(r.json())}.  Waiting 30 seconds to try again.'
            )
            time.sleep(30)
            n_retries += 1
        elif status_code != 200:
            log(f'TNS request failed: {str(r.json())}.')
            return []

    if r is None:
        log('TNS request failed: no response.')
        return []
    if status_code != 200:
        log(f'TNS request failed: {str(r.json())}.')
        return []
    try:
        json_response = json.loads(r.text)
        reply = json_response['data']['reply']
    except Exception as e:
        log(f'TNS request failed: {str(e)}.')
        return []

    sources = []
    log(f'Found {len(reply)} recent sources from TNS since {str(public_timestamp)}')
    for i, obj in enumerate(reply):
        if get_data:
            data = {
                'api_key': api_key,
                'data': json.dumps(
                    {
                        "objname": obj["objname"],
                    }
                ),
            }

            r = requests.post(
                object_url,
                headers=headers,
                data=data,
                allow_redirects=True,
                stream=True,
                timeout=10,
            )

            count = 0
            count_limit = 5
            while r.status_code == 429 and count < count_limit:
                log(
                    f'TNS request rate limited: {str(r.json())}.  Waiting 30 seconds to try again.'
                )
                time.sleep(30)
                r = requests.post(object_url, headers=headers, data=data)
                count += 1

            if count == count_limit:
                raise ValueError('TNS request failed: request rate exceeded.')

            if r.status_code == 200:
                source_data = r.json().get("data", dict()).get("reply", dict())
                if source_data:
                    sources.append(
                        {
                            'id': obj["objname"],
                            'ra': source_data['radeg'],
                            'dec': source_data['decdeg'],
                        }
                    )
            if i % 10 == 0 and get_data:
                log(f'Fetched data of {i+1}/{len(reply)} recent TNS sources')
        else:
            sources.append(
                {
                    'id': obj['objname'],
                    'prefix': obj['prefix'],
                }
            )
    return sources


def get_IAUname(api_key, headers, obj_id=None, ra=None, dec=None, radius=2.0):
    """Query TNS to get IAU name (if exists)
    Parameters
    ----------
    api_key : str
        TNS api key
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

    count = 0
    count_limit = 24  # 6 * 4 * 10 = 4 minutes of retries
    while r.status_code == 429 and count < count_limit:
        log(
            f'TNS request rate limited: {str(r.json())}.  Waiting 10 seconds to try again.'
        )
        time.sleep(10)
        r = requests.post(search_url, headers=headers, data=data)
        count += 1

    if r.status_code not in [200, 429, 401]:
        raise ValueError(f'TNS request failed: {str(r.json())}')

    if r.status_code == 401:
        raise ValueError('TNS request failed: invalid TNSRobot API key.')

    if count == count_limit:
        raise ValueError('TNS request failed: request rate exceeded.')

    reply = r.json().get("data", dict()).get("reply", [])
    if len(reply) > 0:
        # it should be ordered from oldest to newest, so we take the last one
        # which should be the most recent existing source within the radius
        # ideally we want to use the closest, but this TNS endpont doesn't return position or distances
        return reply[-1]['prefix'], reply[-1]['objname']
    else:
        return None, None


def get_internal_names(api_key, headers, tns_name=None):
    """Query TNS to get internal names of an object

    Parameters
    ----------
    api_key : str
        TNS api key
    headers : str
        TNS query headers
    tns_name : str
        Name of the object to query TNS for

    Returns
    -------
    list
        Internal names of the object
    """
    data = {
        'api_key': api_key,
        'data': json.dumps(
            {
                "objname": tns_name,
            }
        ),
    }

    status_code = 429
    n_retries = 0
    r = None
    while n_retries < 24:  # 6 * 4 * 10 = 4 minutes of retries
        r = requests.post(
            object_url,
            headers=headers,
            data=data,
            allow_redirects=True,
            stream=True,
            timeout=10,
        )
        status_code = r.status_code
        if status_code == 429:
            n_retries += 1
            log(
                f'TNS request rate limited: {str(r.json())}.  Waiting 10 seconds to try again.'
            )
            time.sleep(10)
        else:
            break

    if not isinstance(r, requests.Response):
        raise ValueError('TNS request failed: no response received.')

    if r.status_code not in [200, 429, 401]:
        raise ValueError(f'TNS request failed: {str(r.json())}')

    if status_code == 401:
        raise ValueError('TNS request failed: invalid TNSRobot API key.')

    if n_retries == 24:
        raise ValueError('TNS request failed: request rate exceeded.')

    internal_names = []
    try:
        reply = json.loads(r.text)
        internal_names = reply["data"]["reply"]["internal_names"]
        # comma separated list of internal names, starting with a comma (so we fiter out the first empty string after splitting)
        internal_names = list(filter(None, map(str.strip, internal_names.split(","))))
    except Exception as e:
        raise ValueError(
            f'Failed to parse TNS response to retrieve internal names: {str(e)}'
        )

    return internal_names


def get_tns(
    obj_id=None,
    radius=2.0,
    user_id=None,
    timeout=2,
):
    """Get TNS data for an object

    Parameters
    ----------
    obj_id : str, optional
        TNS object id, by default None
    radius : float, optional
        Radius to search around the object, by default 2.0
    user_id : str, optional
        User ID, by default None
    timeout : int, optional
        Timeout for the request, by default 2
    Returns
    -------
    dict
        TNS data
    """
    if obj_id is None:
        raise ValueError('obj_id')

    request_body = {
        'obj_id': obj_id,
        'radius': radius,
        'user_id': user_id,
    }

    tns_microservice_url = f'http://127.0.0.1:{cfg["ports.tns_retrieval_queue"]}'

    resp = requests.post(tns_microservice_url, json=request_body, timeout=timeout)
    if resp.status_code != 200:
        log(
            f'TNS request failed for {str(request_body["obj_id"])} by user ID {request_body["user_id"]}: {resp.content}'
        )


def read_tns_photometry(photometry, session):
    """Read TNS photometry data

    Parameters
    ----------
    photometry : dict
        TNS photometry data
    session : Session
        Database session

    Returns
    -------
    dict
        Formatted photometry data
    """
    tns_instrument_id = photometry["instrument"]["id"]
    inst_name = None
    for key, value in TNS_INSTRUMENT_IDS.items():
        if isinstance(value, list):
            if tns_instrument_id in value:
                inst_name = key
        else:
            if tns_instrument_id == value:
                inst_name = key
    if inst_name is None:
        raise ValueError(f'Cannot find TNS ID mapping for {tns_instrument_id}')

    instrument = session.scalars(
        sa.select(Instrument).where(sa.func.lower(Instrument.name) == inst_name)
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
        raise ValueError(f'{filter_name} not in {instrument.name}')

    if photometry['limflux'] == '':
        data_out = {
            'mjd': [Time(photometry['jd'], format='jd').mjd],
            'mag': [photometry['flux']],
            'magerr': [photometry['fluxerr']]
            if photometry['fluxerr'] not in ['', None]
            else 0.0,
            'limiting_mag': [photometry['flux']],
            'filter': [filter_name],
            'magsys': ['ab'],
        }
    else:
        data_out = {
            'mjd': [Time(photometry['jd'], format='jd').mjd],
            'mag': None,
            'magerr': None,
            'limiting_mag': [photometry['limflux']],
            'filter': [filter_name],
            'magsys': ['ab'],
        }

    df = pd.DataFrame.from_dict(data_out)

    return df, instrument.id


def read_tns_spectrum(spectrum, session):
    """Read TNS spectrum data

    Parameters
    ----------
    spectrum : dict
        TNS spectrum data
    session : Session
        Database session

    Returns
    -------
    dict
        Formatted spectrum data
    """
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
        if isinstance(value, list):
            if tns_instrument_id in value:
                inst_name = key
        else:
            if tns_instrument_id == value:
                inst_name = key
    if inst_name is None:
        raise ValueError(f'Cannot find TNS ID mapping for {tns_instrument_id}')

    instrument = session.scalars(
        sa.select(Instrument).where(sa.func.lower(Instrument.name) == inst_name)
    ).first()
    if instrument is None:
        raise ValueError(f'Cannot find instrument with name {inst_name}')
    data["instrument_id"] = instrument.id

    return data


def get_objects_from_soup(soup):
    """Get objects from a TNS search result page

    Parameters
    ----------
    soup : BeautifulSoup
        The soup of a TNS search result page

    Returns
    -------
    list
        A list of dictionaries with the keys 'name', 'ra', and 'dec'
    """
    objects = []
    try:
        table = soup.find('table', attrs={'class': 'results-table'})
        table_rows = table.find('tbody').find_all('tr')
    except Exception:
        return objects  # no objects found in that soup
    for row in table_rows:
        try:
            # if the row doesnt have the class class="row-odd public odd" then skip it
            if not {"public", "odd"}.issubset(set(row.attrs.get('class', []))):
                continue
            name = str(
                row.find('td', attrs={'class': 'cell-name'}).find('a').contents[0]
            )
            ra = row.find('td', attrs={'class': 'cell-ra'}).text
            dec = row.find('td', attrs={'class': 'cell-decl'}).text
            if name is None or ra is None or dec is None:
                continue
            objects.append({'name': name, 'ra': ra, 'dec': dec})
        except Exception:
            continue
    return objects


def get_objects_from_page(
    headers, page=1, discovered_period_value=5, discovered_period_units='days'
):
    """Get objects from a TNS search result page

    Parameters
    ----------
    headers : dict
        Headers to use for the request
    page : int, optional
        Page number, by default 1
    discovered_period_value : int, optional
        Discovered period value, by default 5
    discovered_period_units : str, optional
        Discovered period units, by default 'days'

    Returns
    -------
    list
        A list of dictionaries with the keys 'name', 'ra', and 'dec'
    """
    url = (
        search_frontend_url
        + f"?discovered_period_value={discovered_period_value}&discovered_period_units={discovered_period_units}&page={page}"
    )
    n_retries = 0
    objects = []
    total_pages = page
    next_page = True
    while n_retries < 6:
        try:
            response = requests.get(
                url, headers=headers, allow_redirects=True, stream=True, timeout=10
            )
            if response.status_code != 200:
                raise Exception(
                    f"Request failed with status code {response.status_code}"
                )
            text = response.text
            soup = BeautifulSoup(text, 'html.parser')
            objects = get_objects_from_soup(soup)
            try:
                total_pages = len(
                    soup.find('ul', attrs={'class': 'pager'}).find_all(
                        'li', attrs={'class': 'pager-item'}
                    )
                )
            except Exception:
                pass
            break
        except Exception:
            n_retries += 1
            time.sleep(15)
            continue

    next_page = page < int(total_pages)
    return objects, next_page


def get_tns_objects(headers, discovered_period_value=5, discovered_period_units='days'):
    """Get all objects from TNS

    Parameters
    ----------
    headers : dict
        Headers to use for the request
    discovered_period_value : int, optional
        Discovered period value, by default 5
    discovered_period_units : str, optional
        Discovered period units, by default 'days'

    Returns
    -------
    list
        A list of dictionaries with the keys 'name', 'ra', and 'dec'
    """
    all_objects = []
    page = 0
    next_page = True
    while next_page:
        try:
            objects, next_page = get_objects_from_page(
                headers, page, discovered_period_value, discovered_period_units
            )
            all_objects.extend(objects)
            page += 1
        except Exception:
            pass
        time.sleep(1)
    return all_objects
