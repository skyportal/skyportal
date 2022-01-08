import requests
from astropy.time import Time
import time

def api(method, endpoint, data=None, params=None, host=None, token=None, raw_response=False):
    headers = {'Authorization': f'token {token}'}
    response = requests.request(method, endpoint, json=data, headers=headers)
    return response

def get_all_group_ids(token):
    groups = api("GET","http://91.162.240.183:31000/api/groups",token=token)
    
    data =[]
    if groups.status_code==200: data = [group['id'] for group in groups.json()['data']['all_groups']]
    return groups.status_code, data

def get_group_ids_and_name(token):
    groups = api("GET","http://91.162.240.183:31000/api/groups",token=token)
    
    data = {}
    if groups.status_code==200: data = {group['name']:group['id'] for group in groups.json()['data']['user_accessible_groups']}
    return groups.status_code, data

def get_all_instruments(token):
    instruments = api("GET","http://91.162.240.183:31000/api/instrument",token=token)
    
    data = {}
    if instruments.status_code==200: data = {instrument['name']:instrument['id'] for instrument in instruments.json()['data']}
    return instruments.status_code, data

def get_all_source_ids(token):
    sources = api("GET","http://91.162.240.183:31000/api/sources",token=token)
    
    data = []
    if sources.status_code==200: data = [source['id'] for source in sources.json()['data']['sources']]
    return sources.status_code, data

def get_all_candidate_ids(token):
    candidates = api("GET","http://91.162.240.183:31000/api/candidates",token=token)

    return candidates.status_code, [candidate['id'] for candidate in candidates.json()['data']['candidates']]
    
    data = []
    if candidates.status_code==200: data = [candidate['id'] for candidate in candidates.json()['data']['candidates']]
    return candidates.status_code, data

def get_all_streams(token):
    streams = api("GET","http://91.162.240.183:31000/api/streams",token=token)

    return streams.status_code, streams['data']

    if streams.status_code==200: data = [stream['id'] for stream in streams.json()['data']['streams']]
    return streams.status_code, data

def classification_exists_for_objs(object_id, token):
    classifications = api("GET","http://91.162.240.183:31000/api/sources/{}/classifications".format(object_id),token=token)
    return classifications.json()['data'] != []

def classification_id_for_objs(object_id, token):
    classifications = api("GET","http://91.162.240.183:31000/api/sources/{}/classifications".format(object_id),token=token)
    
    data = {}
    if classifications.status_code==200: data = {'id': classifications.json()['data'][0]['id'], 'author_id': classifications.json()['data'][0]['author_id']}
    return classifications.status_code, data

def post_source(ztf_id, ra, dec, group_ids, token):
    data = {
            "ra": ra,
            "dec": dec,
            "id": ztf_id,
            #"ra_dis": 0,
            #"dec_dis": 0,
            #"ra_err": 0,
            #"dec_err": 0,
            #"offset": 0,
            #"redshift": 0,
            #"redshift_error": 0,
            #"altdata": null,
            #"dist_nearest_source": 0,
            #"mag_nearest_source": 0,
            #"e_mag_nearest_source": 0,
            #"transient": true,
            #"varstar": true,
            #"is_roid": true,
            #"score": 0,
            #"origin": "string",
            #"alias": null,
            #"detect_photometry_count": 0,
            "group_ids": group_ids
            }

    response = api('POST', "http://91.162.240.183:31000/api/sources", data,token=token)
    if response.status_code in (200, 400): print(f'JSON response: {response.json()}')
    return response.status_code, response.json()['data']['id'] if response.json()['data'] != {} else {}

def post_candidate(ztf_id, ra, dec, filter_ids, passed_at, token):
    data = {
            "ra": ra,
            "dec": dec,
            "id": ztf_id,
            #"ra_dis": 0,
            #"dec_dis": 0,
            #"ra_err": 0,
            #"dec_err": 0,
            #"offset": 0,
            #"redshift": 0,
            #"redshift_error": 0,
            #"altdata": null,
            #"dist_nearest_source": 0,
            #"mag_nearest_source": 0,
            #"e_mag_nearest_source": 0,
            #"transient": true,
            #"varstar": true,
            #"is_roid": true,
            #"score": 0,
            #"origin": "string",
            #"alias": null,
            #"detect_photometry_count": 0,
            "filter_ids": filter_ids,
            #"passing_alert_id": 0,
            "passed_at": passed_at
            }
    response = api('POST', "http://91.162.240.183:31000/api/candidates", data,token=token)
    if response.status_code in (200, 400): print(f'JSON response: {response.json()}')
    return response.status_code, response.json()['data']['ids'] if response.json()['data'] != {} else {}

def post_photometry(ztf_id, mjd, instrument_id, filter, mag, magerr, limiting_mag, magsys, ra, dec, group_ids, stream_ids, token):
    data = {
            "ra": ra,
            #"ra_unc": 0,
            "magerr": magerr,
            "magsys": magsys,
            "group_ids": group_ids,
            #"altdata": None,
            "mag": mag,
            "mjd": mjd,
            #"origin": None,
            "filter": filter,
            "limiting_mag": limiting_mag,
            #"limiting_mag_nsigma": 0,
            #"dec_unc": 0,
            "stream_ids": stream_ids,
            #"assignment_id": None,
            "dec": dec,
            "instrument_id": instrument_id,
            "obj_id": ztf_id
            }

    response = api('POST', "http://91.162.240.183:31000/api/photometry", data,token=token)

    print(f'HTTP code: {response.status_code}, {response.reason}')
    #if response.status_code in (200, 400): print(f'JSON response: {response.json()}')
    return response.status_code, response.json()['data']['ids'] if response.json()['data'] != {} else {}
    
def post_classification(object_id, classification, probability, taxonomy_id, group_ids, token):
    data = {
        "classification": classification,
        "taxonomy_id": taxonomy_id,
        "probability": probability,
        "obj_id": object_id,
        "group_ids": group_ids
        }

    response = api('POST', "http://91.162.240.183:31000/api/classification", data,token=token)

    print(f'HTTP code: {response.status_code}, {response.reason}')
    #return response.status_code, response.json()['data']['classification_id'] if response.json()['data'] != {} else {}
    return response.status_code, response.json()

def post_user(username, token):
    data = {
        #"first_name": first_name,
        #"last_name": last_name,
        #"contact_email": contact_email,
        #"oauth_uid": oauth_uid,
        #"contact_phone": contact_phone,
        #"roles": roles,
        #"groupIDsAndAdmin": groupIDsAndAdmin,
        "username": username
    }
    
    response = api('POST', "http://91.162.240.183:31000/api/user", data,token=token)
    
    print(f'HTTP code: {response.status_code}, {response.reason}')
    return response.status_code, response.json()['data']['id'] if response.json()['data'] != {} else {}

def post_streams(name, token):
    data = {
        "name": name
    }

    response = api('POST', "http://91.162.240.183:31000/api/streams", data,token=token)  
    return response.status_code, response.json()['data']['id'] if response.json()['data'] != {} else None

def post_filters(name, stream_id, group_id, token):
    data = {
        "name": name,
        'stream_id': stream_id,
        'group_id': group_id
    }

    response = api('POST', "http://91.162.240.183:31000/api/filters", data,token=token)  
    return response.status_code, response.json()['data']['id'] if response.json()['data'] != {} else None

def post_telescopes(name, nickname, diameter, token):
    data = {
    "name": name,
    "nickname": nickname,
    "diameter": diameter
    }
    response = api('POST', "http://91.162.240.183:31000/api/telescope", data,token=token)
    return response.status_code, response.json()['data']['id'] if response.json()['data'] != {} else None

def post_instruments(name, type, telescope_id, filters, token):
    data = {
    "name":name,
    "type": "imager",
    "filters": filters,
    "telescope_id": telescope_id
    }
    response = api('POST', "http://91.162.240.183:31000/api/instrument", data,token=token)
    return response.status_code, response.json()['data']['id'] if response.json()['data'] != {} else {}

def post_fink_group(topic, token):
    data = {
        "name" : topic,
        "group_admins": [1],
        }
    response = api('POST', "http://91.162.240.183:31000/api/groups", data,token=token)
    print(f'HTTP code: {response.status_code}, {response.reason}, group posting')
    return response.status_code, response.json()['data']['id'] if response.json()['data'] != {} else None
    
    
def post_taxonomy(name, hierarchy, version, token):
    data = {
        "name": name,
        "hierarchy": hierarchy,
        #"group_ids": group_ids
        "version": version,
        #"provenance": provenance,
        #"isLatest": true
        }
    response = api('POST', "http://91.162.240.183:31000/api/taxonomy", data,token=token)
    print(f'HTTP code: {response.status_code}, {response.reason}')
    return response.status_code, response.json()['data']['taxonomy_id'] if response.json()['data'] != {} else None

def update_classification(object_id, classification, probability, taxonomy_id, group_ids, token):
    data_classification = classification_id_for_objs(object_id, token)[1]
    classification_id, author_id = data_classification['id'], data_classification['author_id']

    data = {
        "obj_id": object_id,
        "classification": classification,
        "probability": probability,
        "taxonomy_id": taxonomy_id,
        "group_ids": group_ids,
        "author_id": author_id,
        "author_name": "fink_client"
        }
    
    response = api('PUT', "http://91.162.240.183:31000/api/classification/{}".format(classification_id), data,token=token)
    return response.status_code

def from_fink_to_skyportal(classification, probability, ztf_id, mjd, instrument, filter, mag, magerr, limiting_mag, magsys, ra, dec,token):   
    instruments = get_all_instruments(token=token)[1]
    groups_dict = get_group_ids_and_name(token=token)[1]
    group_ids = list(groups_dict.values())
    id_fink = 1
    if classification not in list(groups_dict.keys()):
        id_fink = post_fink_group(classification, token=token)[1]
    else:
        id_fink = groups_dict[classification]
    instrument_id = None
    for existing_instrument in instruments.keys():
        if instrument in existing_instrument.upper():
            instrument_id = instruments[existing_instrument]
    if instrument_id is not None:
        source_ids = get_all_source_ids(token=token)[1]
        if ztf_id not in source_ids:
            print('this source doesnt exist yet')
            post_source(ztf_id, ra, dec, [id_fink], token=token)
        candidate_ids = get_all_candidate_ids(token=token)
        if ztf_id not in candidate_ids:
            print('this candidate doesnt exist yet')
            passed_at = Time(mjd, format='mjd').isot
            id_filter = 1
            ids = post_candidate(ztf_id, ra, dec, [id_filter], passed_at, token=token)
        time.sleep(2)
        post_photometry(ztf_id, mjd, instrument_id, filter, mag, magerr, limiting_mag, magsys, ra, dec, [id_fink], [1], token=token)
        taxonomy_id = 1
        if classification_exists_for_objs(ztf_id, token=token):
            update_classification(ztf_id, classification, probability, taxonomy_id, [id_fink], token=token)
        else:
            print('this classification doesnt exist yet')
            post_classification(ztf_id, classification, probability, taxonomy_id, [id_fink], token=token)
    else:
        print('error: instrument named {} does not exist'.format(instrument))