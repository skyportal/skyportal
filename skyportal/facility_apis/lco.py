import time
import json
from datetime import datetime, timedelta

from lxml import etree
from suds import Client

from astropy.coordinates import SkyCoord
from astropy import units as u

from . import FollowUpAPI
from baselayer.app.env import load_env

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
                                          'exposure_time': exposure_time,
                                          'exposure_count': 1,
                                          'optical_elements':
                                              {
                                                  'filter': '%sp' % filt
                                              }
                                       }
                                  ]
                              })
        windows = [{
            'start': tstart,
            'end': tend
        }]
    
        # The telescope class that should be used for this observation
        location = {
            'telescope_class': '1m0'
        }
    
        # The full RequestGroup, with additional meta-data
        requestgroup = {
                'name': '%s' % (objname),  # The title
                'proposal': PROPOSAL_ID,
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
                                          'exposure_time': exposure_time,
                                          'exposure_count': 1,
                                          'optical_elements':
                                              {
                                                  'filter': '%sp' % filt
                                              }
                                       }
                                  ]
                              })
        windows = [{
            'start': tstart,
            'end': tend
        }]
    
        # The telescope class that should be used for this observation
        location = {
            'telescope_class': '2m0'
        }
    
        # The full RequestGroup, with additional meta-data
        requestgroup = {
                'name': '%s' % (objname),  # The title
                'proposal': PROPOSAL_ID,
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
                        'exposure_time': exposure_time,
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
        
            windows = [{
                'start': tstart,
                'end': tend
            }]
        
            # The full RequestGroup, with additional meta-data
            requestgroup = {
                'name': objname,
                'proposal': PROPOSAL_ID,
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

    """An interface to LT operations."""

    @staticmethod
    def delete(request):

        """Delete a follow-up request from LT queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, FollowupRequest

        req = (
            DBSession()
            .query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )
        # this happens for failed submissions
        # just go ahead and delete
        if len(req.http_requests) == 0:
            DBSession().query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            DBSession().commit()
            return

        content = req.http_requests[0].content
        response_rtml = etree.fromstring(content)
        uid = response_rtml.get('uid')

        headers = {
            'Username': request.allocation.load_altdata()["username"],
            'Password': request.allocation.load_altdata()["password"],
        }
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format(
            'http', cfg['app.lt_host'], cfg['app.lt_port']
        )

        namespaces = {
            'xsi': LT_XSI_NS,
        }
        schemaLocation = etree.QName(LT_XSI_NS, 'schemaLocation')
        cancel_payload = etree.Element(
            'RTML',
            {schemaLocation: LT_SCHEMA_LOCATION},
            mode='abort',
            uid=format(str(uid)),
            version='3.1a',
            nsmap=namespaces,
        )
        project = etree.SubElement(
            cancel_payload, 'Project', ProjectID=request.payload["LT_proposalID"]
        )
        contact = etree.SubElement(project, 'Contact')
        etree.SubElement(contact, 'Username').text = request.allocation.load_altdata()["username"]
        etree.SubElement(contact, 'Name').text = request.allocation.load_altdata()["username"]
        etree.SubElement(contact, 'Communication')
        cancel = etree.tostring(cancel_payload, encoding='unicode', pretty_print=True)

        client = Client(url=url, headers=headers)
        # Send cancel_payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
        response = client.service.handle_rtml(cancel).replace(
            'encoding="ISO-8859-1"', ''
        )
        response_rtml = etree.fromstring(response)
        mode = response_rtml.get('mode')
        uid = response_rtml.get('uid')
        if mode == 'confirm':
            DBSession().query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            DBSession().commit()


class SinstroAPI(LCOAPI):

    """An interface to LT IOO operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LT's IOO.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        """

        from ..models import DBSession

        ltreq = SinstroRequest()
        observation_payload = ltreq._build_prolog()
        ltreq._build_project(observation_payload, request)
        ltreq._build_inst_schedule(observation_payload, request)

        f = open("created.rtml", "w")
        f.write(etree.tostring(observation_payload, encoding="unicode", pretty_print=True))
        f.close()

        print(request.allocation.load_altdata()["username"],
              request.allocation.load_altdata()["password"])

        headers = {
            'Username': request.allocation.load_altdata()["username"],
            'Password': request.allocation.load_altdata()["password"],
        }
        print(headers)
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format(
            'http', cfg['app.lt_host'], cfg['app.lt_port']
        )
        client = Client(url=url, headers=headers)
        full_payload = etree.tostring(
            observation_payload, encoding="unicode", pretty_print=True
        )
        # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
        response = client.service.handle_rtml(full_payload).replace(
            'encoding="ISO-8859-1"', ''
        )
        response_rtml = etree.fromstring(response)
        mode = response_rtml.get('mode')
 
        print(full_payload, response)
        print(stop)
        if mode == 'confirm':
            return response
            #message = FollowupRequestHTTPRequest(
            #    content=response, origin='skyportal', request=request,
            #)
            #DBSession().add(message)
            #DBSession().add(request)
            #DBSession().commit()

    _instrument_configs = {}

    _instrument_type = 'Sinstro'
    _observation_types = ['r', 'gr', 'gri', 'griz', 'grizy']
    _exposure_types = {
        'r': ['1x180s', '1x300s', '3x300s'],
        'gr': ['1x180s', '3x300s', '3x300s'],
        'gri': ['1x180s', '2x150s', '3x300s'],
        'griz': ['1x180s', '2x150s', '3x300s'],
        'grizy': ['1x180s', '2x150s', '3x300s'],
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
            "LT_proposalID": {"type": "string"},
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
            "priority",
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance"
        ],
        "dependencies": _dependencies,
    }

    ui_json_schema = {}


class SpectralAPI(LCOAPI):

    """An interface to LT IOI operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LT's IOI.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        """

        from ..models import DBSession

        ltreq = IOIRequest()
        observation_payload = ltreq._build_prolog()
        ltreq._build_project(observation_payload, request)
        ltreq._build_inst_schedule(observation_payload, request)

        headers = {
            'Username': request.allocation.load_altdata()["username"],
            'Password': request.allocation.load_altdata()["password"],
        }
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format(
            'http', cfg['app.lt_host'], cfg['app.lt_port']
        )
        client = Client(url=url, headers=headers)
        full_payload = etree.tostring(
            observation_payload, encoding="unicode", pretty_print=True
        )
        # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
        response = client.service.handle_rtml(full_payload).replace(
            'encoding="ISO-8859-1"', ''
        )
        response_rtml = etree.fromstring(response)
        mode = response_rtml.get('mode')
        if mode == 'confirm':
            return response

    _instrument_configs = {}

    _instrument_type = 'Spectral'
    _observation_types = ['r', 'gr', 'gri', 'griz', 'grizy']
    _exposure_types = {
        'r': ['1x180s', '1x300s', '3x300s'],
        'gr': ['1x180s', '3x300s', '3x300s'],
        'gri': ['1x180s', '2x150s', '3x300s'],
        'griz': ['1x180s', '2x150s', '3x300s'],
        'grizy': ['1x180s', '2x150s', '3x300s'],
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
            "priority",
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance"
        ],
        "dependencies": _dependencies,
    }

    ui_json_schema = {}


class FloydsAPI(LTAPI):

    """An interface to LT SPRAT operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LT's SPRAT.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        """

        from ..models import DBSession

        ltreq = SPRATRequest()
        observation_payload = ltreq._build_prolog()
        ltreq._build_project(observation_payload, request)
        ltreq._build_inst_schedule(observation_payload, request)

        headers = {
            'Username': request.allocation.load_altdata()["username"],
            'Password': request.allocation.load_altdata()["password"],
        }
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format(
            'http', cfg['app.lt_host'], cfg['app.lt_port']
        )
        client = Client(url=url, headers=headers)
        full_payload = etree.tostring(
            observation_payload, encoding="unicode", pretty_print=True
        )
        # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
        response = client.service.handle_rtml(full_payload).replace(
            'encoding="ISO-8859-1"', ''
        )
        response_rtml = etree.fromstring(response)
        mode = response_rtml.get('mode')
        if mode == 'confirm':
            return response
            #message = FollowupRequestHTTPRequest(
            #    content=response, origin='skyportal', request=request,
            #)
            #DBSession().add(message)
            #DBSession().add(request)
            #DBSession().commit()

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
            "LT_proposalID": {"type": "string"},
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
            "priority",
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance"
        ],
        "dependencies": _dependencies,
    }

    ui_json_schema = {}
