import time

from lxml import etree
from suds import Client
from dateutil.parser import parse
from datetime import datetime

from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.io import ascii

from . import FollowUpAPI
from baselayer.app.access import auth_or_token
import requests


LT_SETTINGS = {
    'USERNAME': '',
    'PASSWORD': '',
    'LT_HOST': '',
    'LT_PORT': '',
    'DEBUG': True,
    'MAX_AIRMASS': 2.0,
    'MAX_SEEING': 1.2,
    'MAX_SKYBRI': 1.0,
    'PHOTOMETRIC': 'light',
    'IOO_BINNING': '2x2',
}

info = ascii.read('.lt.access', format='csv')
LT_SETTINGS['USERNAME'] = info['USERNAME'][0]
LT_SETTINGS['PASSWORD'] = info['PASSWORD'][0]
LT_SETTINGS['LT_HOST'] = info['LT_HOST'][0]
LT_SETTINGS['LT_PORT'] = info['LT_PORT'][0]
print(LT_SETTINGS)

LT_XML_NS = 'http://www.rtml.org/v3.1a'
LT_XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
LT_SCHEMA_LOCATION = 'http://www.rtml.org/v3.1a http://telescope.livjm.ac.uk/rtml/RTML-nightly.xsd'


class LTRequest():

    def is_valid(self):
        super().is_valid()
        errors = LTFacility.validate_observation(self, self.observation_payload())
        if errors:
            self.add_error(None, errors)
        return not errors

    def _build_prolog(self):
        namespaces = {
            'xsi': LT_XSI_NS,
        }
        schemaLocation = etree.QName(LT_XSI_NS, 'schemaLocation')
        uid = format(str(int(time.time())))
        return etree.Element('RTML', {schemaLocation: LT_SCHEMA_LOCATION}, xmlns=LT_XML_NS,
                             mode='request', uid=uid, version='3.1a', nsmap=namespaces)

    def _build_project(self, payload, request):
        project = etree.Element('Project',
                                ProjectID=request.payload["LT_proposalID"])
        contact = etree.SubElement(project, 'Contact')
        etree.SubElement(contact, 'Username').text = request.payload["LT_username"]
        etree.SubElement(contact, 'Name').text = ''
        payload.append(project)

    def _build_constraints(self, request):
        airmass_const = etree.Element('AirmassConstraint', maximum=str(LT_SETTINGS['MAX_AIRMASS']))

        sky_const = etree.Element('SkyConstraint')
        etree.SubElement(sky_const, 'Flux').text = str(LT_SETTINGS['MAX_SKYBRI'])
        etree.SubElement(sky_const, 'Units').text = 'magnitudes/square-arcsecond'

        seeing_const = etree.Element('SeeingConstraint',
                                     maximum=(str(LT_SETTINGS['MAX_SEEING'])),
                                     units='arcseconds')

        photom_const = etree.Element('ExtinctionConstraint')
        etree.SubElement(photom_const, 'Clouds').text = LT_SETTINGS['PHOTOMETRIC']

        date_const = etree.Element('DateTimeConstraint', type='include')
        start = request.payload["start_date"] + 'T00:00+00:00'
        end = request.payload["end_date"] + 'T00:00+00:00'
        etree.SubElement(date_const, 'DateTimeStart', system='UT', value=start)
        etree.SubElement(date_const, 'DateTimeEnd', system='UT', value=end)

        return [airmass_const, sky_const, seeing_const, photom_const, date_const]

    def _build_target(self, request):
        target = etree.Element('Target', name=request.obj.id)
        c = SkyCoord(ra=request.obj.ra*u.degree,
                     dec=request.obj.dec*u.degree)
        coordinates = etree.SubElement(target, 'Coordinates')
        ra = etree.SubElement(coordinates, 'RightAscension')
        etree.SubElement(ra, 'Hours').text = str(int(c.ra.hms.h))
        etree.SubElement(ra, 'Minutes').text = str(int(c.ra.hms.m))
        etree.SubElement(ra, 'Seconds').text = str(c.ra.hms.s)

        dec = etree.SubElement(coordinates, 'Declination')
        sign = '+' if c.dec.signed_dms.sign == 1.0 else '-'
        etree.SubElement(dec, 'Degrees').text = sign + str(int(c.dec.signed_dms.d))
        etree.SubElement(dec, 'Arcminutes').text = str(int(c.dec.signed_dms.m))
        etree.SubElement(dec, 'Arcseconds').text = str(c.dec.signed_dms.s)
        etree.SubElement(coordinates, 'Equinox').text = 'J2000'
        return target

    def _build_inst_schedule(self, payload, request):

        if request.payload["instrument_type"] == "IOO":
            exposure_type = request.payload["exposure_type"]
            exposure_type_split = exposure_type.split("x")
            exp_count = int(exposure_type_split[0])
            exp_time = int(exposure_type_split[1][:-1])
            for filt in request.payload["observation_type"]:
                payload.append(self._build_IOO_schedule(request, 
                                                        filt,
                                                        exp_time,
                                                        exp_count))
        elif request.payload["instrument_type"] == "SPRAT":
            self._build_SPRAT_schedule(payload, request)

    def _build_IOO_schedule(self, request, filt, exp_time, exp_count):
        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name="IO:O", type="camera")
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Filter', type=filt)
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = LT_SETTINGS['IOO_BINNING'].split('x')[0]
        etree.SubElement(binning, 'Y', units='pixels').text = LT_SETTINGS['IOO_BINNING'].split('x')[1]
        exposure = etree.SubElement(schedule, 'Exposure', count=str(exp_count))
        etree.SubElement(exposure, 'Value', units='seconds').text = str(exp_time)
        schedule.append(self._build_target(request))
        for const in self._build_constraints(request):
            schedule.append(const)
        return schedule

    def _build_SPRAT_schedule(self, payload, request):

        grating = request.payload["observation_type"]
        exposure_type = request.payload["exposure_type"]
        exposure_type_split = exposure_type.split("x")
        exp_count = int(exposure_type_split[0])
        exp_time = int(exposure_type_split[1][:-1])

        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name="Sprat", type="spectrograph")
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Grating', name=grating)
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = '1'
        etree.SubElement(binning, 'Y', units='pixels').text = '1'
        exposure = etree.SubElement(schedule, 'Exposure', count=str(exp_count))
        etree.SubElement(exposure, 'Value', units='seconds').text = str(exp_time)
        schedule.append(self._build_target(request))
        for const in self._build_constraints(request):
            schedule.append(const)
        payload.append(schedule)


class LTAPI(FollowUpAPI):

    """An interface that User-contributed remote facility APIs must provide."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):
        ltreq = LTRequest()
        observation_payload = ltreq._build_prolog()
        ltreq._build_project(observation_payload, request)
        ltreq._build_inst_schedule(observation_payload, request)

        if LT_SETTINGS['DEBUG']:
            f = open("created.rtml", "w")
            f.write(etree.tostring(observation_payload,
                                   encoding="unicode", pretty_print=True))
            f.close()
            return [0]
        else:
            headers = {
                'Username': LT_SETTINGS['username'],
                'Password': LT_SETTINGS['password']
            }
            url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http', LT_SETTINGS['LT_HOST'],
                                                                     LT_SETTINGS['LT_PORT'])
            client = Client(url=url, headers=headers)
            # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
            response = client.service.handle_rtml(observation_payload).replace('encoding="ISO-8859-1"', '')
            response_rtml = etree.fromstring(response)
            mode = response_rtml.get('mode')
            if mode == 'reject':
                self.dump_request_response(observation_payload, response_rtml)
            obs_id = response_rtml.get('uid')
            return [obs_id]

    def validate(self, observation_payload):
        if LT_SETTINGS['DEBUG']:
            return []
        else:
            headers = {
                'Username': LT_SETTINGS['username'],
                'Password': LT_SETTINGS['password']
            }
            url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http',
                                                                     LT_SETTINGS['LT_HOST'],
                                                                     LT_SETTINGS['LT_PORT'])
            client = Client(url=url, headers=headers)
            validate_payload = etree.fromstring(observation_payload)
            # Change the payload to an inquiry mode document to test connectivity.
            validate_payload.set('mode', 'inquiry')
            # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing

            try:
                response = client.service.handle_rtml(validate_payload).replace('encoding="ISO-8859-1"', '')
            except:
                return ['Error with connection to Liverpool Telescope',
                        'This could be due to incorrect credentials, or IP / Port settings',
                        'Occassionally, this could be due to the rebooting of systems at the Telescope Site',
                        'Please retry at another time.',
                        'If the problem persists please contact ltsupport_astronomer@ljmu.ac.uk']

            response_rtml = etree.fromstring(response)
            if response_rtml.get('mode') == 'offer':
                return []
            elif response_rtml.get('mode') == 'reject':
                return ['Error with RTML submission to Liverpool Telescope',
                        'This can occassionally happen due to systems rebooting at the Telescope Site',
                        'Please retry at another time.',
                        'If the problem persists please contact ltsupport_astronomer@ljmu.ac.uk']


    _instrument_configs = {}

    _instrument_type = 'IOO'
    _observation_types = ['r', 'gr', 'gri', 'griz', 'ugriz']
    _exposure_types = {'r': ['1x120s', '2x150s'], 
                       'gr': ['1x120s', '2x150s'], 
                       'gri': ['1x120s', '2x150s'],
                       'griz': ['1x120s', '2x150s'], 
                       'ugriz': ['1x120s', '2x150s']} 
    _instrument_configs[_instrument_type] = {}
    _instrument_configs[_instrument_type]["observation"] = _observation_types
    _instrument_configs[_instrument_type]["exposure"] = _exposure_types

    _instrument_type = 'SPRAT'
    _observation_types = ['blue', 'red']
    _exposure_types = {'blue': ['1x300s', '2x300s', '1x600s', '2x600s'],
                       'red': ['1x300s', '2x300s']}
    _instrument_configs[_instrument_type] = {}
    _instrument_configs[_instrument_type]["observation"] = _observation_types
    _instrument_configs[_instrument_type]["exposure"] = _exposure_types

    _instrument_types = list(_instrument_configs.keys())

    _dependencies = {}
    _dependencies["instrument_type"] = {}
    _dependencies["instrument_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        oneOf = {"properties": {"instrument_type": {"enum": [_instrument_type]},
                                "observation_type": {"enum": _instrument_configs[_instrument_type]["observation"]}
                               }
                }
        _dependencies["instrument_type"]["oneOf"].append(oneOf)

    _dependencies["observation_type"] = {}
    _dependencies["observation_type"]["oneOf"] = []
    for _instrument_type in _instrument_types:
        for _observation_type in _instrument_configs[_instrument_type]["observation"]:
            oneOf = {"properties": {"observation_type": {"enum": [_observation_type]},
                                    "exposure_type": {"enum": _instrument_configs[_instrument_type]["exposure"][_observation_type]}
                                   }
                    }
            _dependencies["observation_type"]["oneOf"].append(oneOf)

    form_json_schema = {
        "type": "object",
        "properties": {
            "instrument_type": {
                "type": "string",
                "enum": _instrument_types,
                "default": "IOO",
            },
            "priority": {
                "type": "string",
                "enum": ["1", "5"],
                "default": "1",
            },
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "LT_proposalID": {"type": "string"},
            "LT_username": {"type": "string"},
            "LT_password": {"type": "string"}
        },
        "required": ["instrument_type", "priority", "start_date", "end_date"],
        "dependencies": _dependencies 
    }

    ui_json_schema = {}
