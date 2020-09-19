import time
import json
import requests
from datetime import datetime, timedelta

from lxml import etree
from suds import Client

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()

class SinstroRequest:

    """An XML structure for LCO 1m Sinistro requests."""

    def _build_payload(self, request):
        """Payload header for LCO 1m Sinistro queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload:
            payload for Sinistro requests.
        """


        # Constraints used for scheduling this observation
        constraints = {
            'max_airmass': request.payload["maximum_airmass"],
            'min_lunar_distance': 30
        }

        # The target of the observation
        target = {
            'name': request.obj.id,
            'type': 'ICRS',
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'epoch': 2000
        }

        exposure_type = request.payload["exposure_type"]
        exposure_type_split = exposure_type.split("x")
        exp_count = int(exposure_type_split[0])
        exp_time = int(exposure_type_split[1][:-1])

        # The configurations for this request. In this example we are taking 2 exposures with different filters.
        configurations = []
        for filt in request.payload["observation_type"]:
            configurations.append({'type': 'EXPOSE',
                                  'instrument_type': '1M0-SCICAM-SINISTRO',
                                  'constraints': constraints,
                                  'target': target,
                                  'acquisition_config': {},
                                  'guiding_config': {},
                                  'instrument_configs': [
                                      {
                                          'exposure_time': exp_time,
                                          'exposure_count': exp_count,
                                          'optical_elements':
                                              {
                                                  'filter': '%sp' % filt
                                              }
                                       }
                                  ]
                              })

        tstart = request.payload["start_date"] + ' 00:00:00'
        tend = request.payload["end_date"] + ' 00:00:00'

        windows = [{
            'start': tstart,
            'end': tend
        }]
    
        # The telescope class that should be used for this observation
        location = {
            'telescope_class': '1m0'
        }
   
        altdata = request.allocation.load_altdata()
 
        # The full RequestGroup, with additional meta-data
        requestgroup = {
                'name': '%s' % (request.obj.id),  # The title
                'proposal': altdata["PROPOSAL_ID"],
                'ipp_value': 1.05,
                'operator': 'SINGLE',
                'observation_type': 'NORMAL',
                'requests': [{
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }]
            }
    
        return requestgroup


class SpectralRequest:

    """An XML structure for LCO 2m Spectral requests."""

    def _build_payload(self, request):
        """Payload header for LCO 2m Spectral queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload:
            payload for Spectral requests.
        """


        # Constraints used for scheduling this observation
        constraints = {
            'max_airmass': request.payload["maximum_airmass"],
            'min_lunar_distance': request.payload["minimum_lunar_distance"]   
        }

        # The target of the observation
        target = {
            'name': request.obj.id,
            'type': 'ICRS',
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'epoch': 2000
        }

        exposure_type = request.payload["exposure_type"]
        exposure_type_split = exposure_type.split("x")
        exp_count = int(exposure_type_split[0])
        exp_time = int(exposure_type_split[1][:-1])

        configurations = []
        for filt in request.payload["observation_type"]:
            configurations.append({'type': 'EXPOSE',
                                  'instrument_type': '2M0-SCICAM-SPECTRAL',
                                  'constraints': constraints,
                                  'target': target,
                                  'acquisition_config': {},
                                  'guiding_config': {},
                                  'instrument_configs': [
                                      {
                                          'exposure_time': exp_time,
                                          'exposure_count': exp_count,
                                          'optical_elements':
                                              {
                                                  'filter': '%sp' % filt
                                              }
                                       }
                                  ]
                              })

        tstart = request.payload["start_date"] + ' 00:00:00'
        tend = request.payload["end_date"] + ' 00:00:00'

        windows = [{
            'start': tstart,
            'end': tend
        }]
    
        # The telescope class that should be used for this observation
        location = {
            'telescope_class': '2m0'
        }
   
        altdata = request.allocation.load_altdata()
 
        # The full RequestGroup, with additional meta-data
        requestgroup = {
                'name': '%s' % (request.obj.id),  # The title
                'proposal': altdata["PROPOSAL_ID"],
                'ipp_value': 1.05,
                'operator': 'SINGLE',
                'observation_type': 'NORMAL',
                'requests': [{
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }]
            }
    
        return requestgroup

class FloydsRequest:

    """An XML structure for LCO 2m Floyds requests."""

    def _build_payload(self, request):
        """Payload header for LCO 2m Floyds queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload:
            payload for Floyds requests.
        """


        # Constraints used for scheduling this observation
        constraints = {
            'max_airmass': request.payload["maximum_airmass"],
            'min_lunar_distance': request.payload["minimum_lunar_distance"]
        }

        # The target of the observation
        target = {
            'name': request.obj.id,
            'type': 'ICRS',
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'epoch': 2000
        }

        # The telescope class that should be used for this observation
        location = {
            'telescope_class': '2m0'
        }

        exposure_type = request.payload["exposure_type"]
        exposure_type_split = exposure_type.split("x")
        exp_count = int(exposure_type_split[0])
        exp_time = int(exposure_type_split[1][:-1])

        configurations = [
        {   
            'type': 'LAMP_FLAT',
            'instrument_type': '2M0-FLOYDS-SCICAM',
            'constraints': constraints,
            'target': target,
            'acquisition_config': {},
            'guiding_config': {
                'mode': 'OFF',
                'optional': False},
            'instrument_configs': [
                {
                    'exposure_time': 50,
                    'exposure_count': 1,
                    'rotator_mode': 'VFLOAT',
                    'optical_elements': {
                        'slit': 'slit_1.6as'
                    }
                }
            ]
        },
        {  
            'type': 'ARC',
            'instrument_type': '2M0-FLOYDS-SCICAM',
            'constraints': constraints,
            'target': target,
            'acquisition_config': {},
            'guiding_config': {
                'mode': 'OFF',
                'optional': False},
            'instrument_configs': [
                {
                    'exposure_time': 60,
                    'exposure_count': 1,
                    'rotator_mode': 'VFLOAT',
                    'optical_elements': {
                        'slit': 'slit_1.6as'
                    }
                }
            ]
        },
        {
            'type': 'SPECTRUM',
            'instrument_type': '2M0-FLOYDS-SCICAM',
            'constraints': constraints,
            'target': target,
            'acquisition_config': {
                'mode': 'WCS'
            },
            'guiding_config': {
                'mode': 'ON',
                'optional': False
            },
            'instrument_configs': [
                {
                    'exposure_time': exp_time,
                    'exposure_count': exp_count,
                    'rotator_mode': 'VFLOAT',
                    'optical_elements': {
                        'slit': 'slit_1.6as'
                    }
                }
            ]
        },
        {
            'type': 'ARC',
            'instrument_type': '2M0-FLOYDS-SCICAM',
            'constraints': constraints,
            'target': target,
            'acquisition_config': {},
            'guiding_config': {
                'mode': 'OFF',
                'optional': False},
            'instrument_configs': [
                {
                    'exposure_time': 60,
                    'exposure_count': 1,
                    'rotator_mode': 'VFLOAT',
                    'optical_elements': {
                        'slit': 'slit_1.6as'
                    }
                }
            ]
        },
        {
            'type': 'LAMP_FLAT',
            'instrument_type': '2M0-FLOYDS-SCICAM',
            'constraints': constraints,
            'target': target,
            'acquisition_config': {},
            'guiding_config': {
                'mode': 'OFF',
                'optional': False},
            'instrument_configs': [
                {
                    'exposure_time': 50,
                    'exposure_count': 1,
                    'rotator_mode': 'VFLOAT',
                    'optical_elements': {
                        'slit': 'slit_1.6as'
                    }
                }
            ]
        }]
    
        tstart = request.payload["start_date"] + ' 00:00:00'
        tend = request.payload["end_date"] + ' 00:00:00'

        windows = [{
            'start': tstart,
            'end': tend
        }]   

        altdata = request.allocation.load_altdata()

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            'name': '%s' % (request.obj.id),  # The title
            'proposal': altdata["PROPOSAL_ID"], 
            'ipp_value': 1.05,
            'operator': 'SINGLE',
            'observation_type': 'NORMAL',
            'requests': [{
                'configurations': configurations,
                'windows': windows,
                'location': location,
            }]
        }
    
        return requestgroup


class LCOAPI(FollowUpAPI):

    """An interface to LCO operations."""

    @staticmethod
    def delete(request):

        """Delete a follow-up request from LCO queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, FollowupRequest, FacilityTransaction

        req = (
            DBSession()
            .query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )

        # this happens for failed submissions
        # just go ahead and delete
        if len(req.transactions) == 0:
            DBSession().query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            DBSession().commit()
            return

        altdata = request.allocation.load_altdata()
        if not altdata:
            return

        contnt = req.transactions[0].response["content"]
        content = json.loads(content)
        uid = content["id"]

        r = requests.post(
            'https://observe.lco.global/api/requestgroups/{}/cancel/'.format(uid),
            headers={'Authorization': 'Token {}'.format(altdata["API_TOKEN"])}
        )

        r.raise_for_status()
        request.status = "deleted"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)


    @staticmethod
    def update(request):

        """Update a follow-up request from LCO queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to update from the queue and the SkyPortal database.
        """

        from ..models import DBSession, FollowupRequest, FacilityTransaction

        req = (
            DBSession()
            .query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )

        # this happens for failed submissions
        # just go ahead and delete
        if len(req.transactions) == 0:
            DBSession().query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            DBSession().commit()
            return

        altdata = request.allocation.load_altdata()
        if not altdata:
            return

        content = req.transactions[0].response["content"]
        content = json.loads(content)
        uid = content["id"]

        r = requests.get(
            'https://observe.lco.global/api/requestgroups/{}/'.format(uid),
            headers={'Authorization': 'Token {}'.format(altdata["API_TOKEN"])}
        )

        r.raise_for_status()

        content = req.transactions[0].response["content"]
        content = json.loads(content)
       
        if content["state"] == "COMPLETED":
            request.status = "complete"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)


class SinistroAPI(LCOAPI):

    """An interface to LCO Sinistro operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LCO's Sinistro.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.load_altdata()
        if not altdata:
            return

        ltreq = SinstroRequest()
        requestgroup = ltreq._build_payload(request)

        r = requests.post(
            'https://observe.lco.global/api/requestgroups/',
            headers={'Authorization': 'Token {}'.format(altdata["API_TOKEN"])},
            json=requestgroup  # Make sure you use json!
        )

        r.raise_for_status()

        if r.status_code == 201:
            request.status = 'submitted'
        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    _instrument_configs = {}

    _instrument_type = 'Sinstro'
    _observation_types = ['r', 'gr', 'gri', 'griz', 'grizy']
    _exposure_types = {
        'r': ['1x180s', '1x300s', '3x300s'],
        'gr': ['1x180s', '1x300s', '3x300s'],
        'gri': ['1x180s', '1x300s', '3x300s'],
        'griz': ['1x180s', '1x300s', '3x300s'],
        'grizy': ['1x180s', '1x300s', '3x300s'],
    }
    _instrument_configs[_instrument_type] = {}
    _instrument_configs[_instrument_type]["observation"] = _observation_types
    _instrument_configs[_instrument_type]["exposure"] = _exposure_types

    _instrument_types = list(_instrument_configs.keys())

    _dependencies = {}
    _dependencies["instrument_type"] = {}
    _dependencies["instrument_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        oneOf = {
            "properties": {
                "instrument_type": {"enum": [_instrument_type]},
                "observation_type": {
                    "enum": _instrument_configs[_instrument_type]["observation"]
                },
            }
        }
        _dependencies["instrument_type"]["oneOf"].append(oneOf)

    _dependencies["observation_type"] = {}
    _dependencies["observation_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        for _observation_type in _instrument_configs[_instrument_type]["observation"]:
            oneOf = {
                "properties": {
                    "observation_type": {"enum": [_observation_type]},
                    "exposure_type": {
                        "enum": _instrument_configs[_instrument_type]["exposure"][
                            _observation_type
                        ]
                    },
                }
            }
            _dependencies["observation_type"]["oneOf"].append(oneOf)

    form_json_schema = {
        "type": "object",
        "properties": {
            "instrument_type": {
                "type": "string",
                "enum": _instrument_types,
                "default": "Sinistro",
            },
            "start_date": {
                "type": "string",
                "format": "date",
                "default": datetime.utcnow().date().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "title": "End Date (UT)",
                "default": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
            },
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
            },
            "minimum_lunar_distance": {
                "title": "Maximum Seeing [arcsec] (0-180)",
                "type": "number",
                "default": 30.0,
            },
        },
        "required": [
            "instrument_type",
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance"
        ],
        "dependencies": _dependencies,
    }

    ui_json_schema = {}


class SpectralAPI(LCOAPI):

    """An interface to LCO Spectral operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LCO's Spectral.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.load_altdata()
        if not altdata:
            return

        ltreq = SpectralRequest()
        requestgroup = ltreq._build_payload(request)

        r = requests.post(
            'https://observe.lco.global/api/requestgroups/',
            headers={'Authorization': 'Token {}'.format(altdata["API_TOKEN"])},
            json=requestgroup  # Make sure you use json!
        )

        r.raise_for_status()

        if r.status_code == 201:
            request.status = 'submitted'
        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    _instrument_configs = {}

    _instrument_type = 'Spectral'
    _observation_types = ['r', 'gr', 'gri', 'griz', 'grizy']
    _exposure_types = {
        'r': ['1x180s', '1x300s', '3x300s'],
        'gr': ['1x180s', '1x300s', '3x300s'],
        'gri': ['1x180s', '1x300s', '3x300s'],
        'griz': ['1x180s', '1x300s', '3x300s'],
        'grizy': ['1x180s', '1x300s', '3x300s'],
    }
    _instrument_configs[_instrument_type] = {}
    _instrument_configs[_instrument_type]["observation"] = _observation_types
    _instrument_configs[_instrument_type]["exposure"] = _exposure_types

    _instrument_types = list(_instrument_configs.keys())

    _dependencies = {}
    _dependencies["instrument_type"] = {}
    _dependencies["instrument_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        oneOf = {
            "properties": {
                "instrument_type": {"enum": [_instrument_type]},
                "observation_type": {
                    "enum": _instrument_configs[_instrument_type]["observation"]
                },
            }
        }
        _dependencies["instrument_type"]["oneOf"].append(oneOf)

    _dependencies["observation_type"] = {}
    _dependencies["observation_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        for _observation_type in _instrument_configs[_instrument_type]["observation"]:
            oneOf = {
                "properties": {
                    "observation_type": {"enum": [_observation_type]},
                    "exposure_type": {
                        "enum": _instrument_configs[_instrument_type]["exposure"][
                            _observation_type
                        ]
                    },
                }
            }
            _dependencies["observation_type"]["oneOf"].append(oneOf)

    form_json_schema = {
        "type": "object",
        "properties": {
            "instrument_type": {
                "type": "string",
                "enum": _instrument_types,
                "default": "Spectral",
            },
            "start_date": {
                "type": "string",
                "format": "date",
                "default": datetime.utcnow().date().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "title": "End Date (UT)",
                "default": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
            },
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
            },
            "minimum_lunar_distance": {
                "title": "Maximum Seeing [arcsec] (0-180)",
                "type": "number",
                "default": 30.0,
            },
        },
        "required": [
            "instrument_type",
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance"
        ],
        "dependencies": _dependencies,
    }

    ui_json_schema = {}


class FloydsAPI(LCOAPI):

    """An interface to LCO Floyds operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LCO's Floyds.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.load_altdata()
        if not altdata:
            return

        ltreq = FloydsRequest()
        requestgroup = ltreq._build_payload(request)

        r = requests.post(
            'https://observe.lco.global/api/requestgroups/',
            headers={'Authorization': 'Token {}'.format(altdata["API_TOKEN"])},
            json=requestgroup  # Make sure you use json!
        )

        r.raise_for_status()

        if r.status_code == 201:
            request.status = 'submitted'
        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    _instrument_configs = {}

    _instrument_type = 'Floyds'
    _observation_types = ['spectra']
    _exposure_types = {
        'spectra': ['1x180s', '1x300s', '1x600s']
    }
    _instrument_configs[_instrument_type] = {}
    _instrument_configs[_instrument_type]["observation"] = _observation_types
    _instrument_configs[_instrument_type]["exposure"] = _exposure_types

    _instrument_types = list(_instrument_configs.keys())

    _dependencies = {}
    _dependencies["instrument_type"] = {}
    _dependencies["instrument_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        oneOf = {
            "properties": {
                "instrument_type": {"enum": [_instrument_type]},
                "observation_type": {
                    "enum": _instrument_configs[_instrument_type]["observation"]
                },
            }
        }
        _dependencies["instrument_type"]["oneOf"].append(oneOf)

    _dependencies["observation_type"] = {}
    _dependencies["observation_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        for _observation_type in _instrument_configs[_instrument_type]["observation"]:
            oneOf = {
                "properties": {
                    "observation_type": {"enum": [_observation_type]},
                    "exposure_type": {
                        "enum": _instrument_configs[_instrument_type]["exposure"][
                            _observation_type
                        ]
                    },
                }
            }
            _dependencies["observation_type"]["oneOf"].append(oneOf)

    form_json_schema = {
        "type": "object",
        "properties": {
            "instrument_type": {
                "type": "string",
                "enum": _instrument_types,
                "default": "Floyds",
            },
            "start_date": {
                "type": "string",
                "format": "date",
                "default": datetime.utcnow().date().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "title": "End Date (UT)",
                "default": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
            },
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
            },
            "minimum_lunar_distance": {
                "title": "Maximum Seeing [arcsec] (0-180)",
                "type": "number",
                "default": 30.0,
            },
        },
        "required": [
            "instrument_type",
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance"
        ],
        "dependencies": _dependencies,
    }

    ui_json_schema = {}
