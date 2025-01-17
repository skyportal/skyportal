import os
import tempfile

import astropy.units as u
import numpy as np
import paramiko
from astroplan import Observer, is_always_observable
from astroplan.constraints import AltitudeConstraint
from astropy.coordinates import EarthLocation, SkyCoord, get_moon
from astropy.table import Table
from astropy.time import Time
from paramiko import SSHClient
from scp import SCPClient

from baselayer.log import make_log

from . import MMAAPI, GenericRequest

log = make_log('facility_apis/git')


def get_table(json_data, sunrise_hor=-12, horizon=20, priority=10000, domesleep=100):
    """Make .csv file in GIT toO format for a given .json file"""

    t = Table(rows=json_data['targets'])
    coords = SkyCoord(ra=t['ra'], dec=t['dec'], unit=(u.degree, u.degree))
    hanle = EarthLocation(
        lat=32.77889 * u.degree, lon=78.96472 * u.degree, height=4500 * u.m
    )
    iao = Observer(location=hanle, name="GIT", timezone="Asia/Kolkata")

    twilight_prime = (
        iao.sun_rise_time(Time.now(), which="next", horizon=sunrise_hor * u.deg)
        - 12 * u.hour
    )
    targets_rise_time = iao.target_rise_time(
        twilight_prime, coords, which="nearest", horizon=horizon * u.degree
    )
    targets_set_time = iao.target_set_time(
        targets_rise_time, coords, which="next", horizon=horizon * u.degree
    )
    rise_time_IST = np.array([(targets_rise_time + 5.5 * u.hour).isot])[0]
    set_time_IST = np.array([(targets_set_time + 5.5 * u.hour).isot])[0]
    tend = targets_set_time
    mooncoords = get_moon(tend, hanle)
    sep = mooncoords.separation(coords)
    dic = {}
    dic['x'] = [''] * len(t)
    dic['u'] = [''] * len(t)
    dic['g'] = [''] * len(t)
    dic['r'] = [''] * len(t)
    dic['i'] = [''] * len(t)
    dic['z'] = [''] * len(t)
    target = ['EMGW'] * len(t)

    for i in range(len(t)):
        filt = t[i]["filter"][-1]
        dic[filt][i] = f'1X{t[i]["exposure_time"]:d}'

    del t['request_id', 'program_pi', 'filter', 'exposure_time']
    t['field_id'].name = 'tile_id'
    t['dec'].name = 'Dec'
    domesleeparr = np.zeros(len(t)) + domesleep
    priority = np.zeros(len(t)) + priority
    minalt = AltitudeConstraint(min=horizon * u.degree)
    always_up = is_always_observable(
        minalt, iao, coords, Time(twilight_prime, twilight_prime + 12 * u.hour)
    )
    always_up_idx = np.where(always_up)[0]
    rise_time_IST[always_up_idx] = (twilight_prime + 5.5 * u.hour).isot
    set_time_IST[always_up_idx] = (twilight_prime + 24 * u.hour + 5.5 * u.hour).isot
    ras_format = []
    decs_format = []
    ras_format = coords.ra.to_string(u.hour, sep=':')
    decs_format = coords.dec.to_string(u.degree, sep=':')
    # Add columns
    t['domesleep'] = domesleeparr
    t['Priority'] = priority
    t['dec'] = decs_format
    t['rise_time_IST'] = rise_time_IST
    t['set_time_IST'] = set_time_IST
    t['moon_angle'] = sep
    t['RA'] = ras_format
    t['Target'] = target
    t['x'] = dic['x']
    t['u'] = dic['u']
    t['g'] = dic['g']
    t['r'] = dic['r']
    t['i'] = dic['i']
    t['z'] = dic['z']

    return t


class GROWTHINDIAMMAAPI(MMAAPI):

    """An interface to GROWTH-India MMA operations."""

    @staticmethod
    def send(request, session):
        """Submit an EventObservationPlan.

        Parameters
        ----------
        request : skyportal.models.ObservationPlanRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        req = GenericRequest()
        requestgroup = req._build_observation_plan_payload(request)

        payload = {
            'targets': requestgroup["targets"],
            'queue_name': requestgroup["queue_name"],
            'validity_window_mjd': requestgroup["validity_window_mjd"],
            'queue_type': 'list',
            'user': request.requester.username,
        }

        with tempfile.NamedTemporaryFile(mode='w') as f:
            tab = get_table(payload)
            tab.write(f, format='csv')
            f.seek(0)

            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=altdata['host'],
                port=altdata['port'],
                username=altdata['username'],
                password=altdata['password'],
            )
            scp = SCPClient(ssh.get_transport())
            scp.put(
                f.name,
                os.path.join(altdata['directory'], payload["queue_name"] + '.csv'),
            )
            scp.close()

            request.status = 'submitted'

            transaction = FacilityTransaction(
                request=None,
                response=None,
                observation_plan_request=request,
                initiator_id=request.last_modified_by_id,
            )

            session.add(transaction)

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "title": "Host",
            },
            "port": {
                "type": "string",
                "title": "Port",
            },
            "username": {
                "type": "string",
                "title": "Username",
            },
            "password": {
                "type": "string",
                "title": "Password",
            },
            "directory": {
                "type": "string",
                "title": "Directory",
            },
        },
    }
