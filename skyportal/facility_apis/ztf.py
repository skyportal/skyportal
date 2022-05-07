import astropy
from astropy.io import ascii
import json
import requests
from requests import Request, Session
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from astropy.time import Time
import functools
import numpy as np
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop
import pandas as pd
import pyvo
import urllib

from . import FollowUpAPI, MMAAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http

env, cfg = load_env()


if cfg['app.ztf.port'] is None:
    ZTF_URL = f"{cfg['app.ztf.protocol']}://{cfg['app.ztf.host']}"
else:
    ZTF_URL = f"{cfg['app.ztf.protocol']}://{cfg['app.ztf.host']}:{cfg['app.ztf.port']}"

ZTF_FORCED_URL = cfg['app.ztf_forced_endpoint']

bands = {'g': 1, 'ztfg': 1, 'r': 1, 'ztfr': 2, 'i': 3, 'ztfi': 3}
inv_bands = {1: 'ztfg', 2: 'ztfr', 3: 'ztfi'}

log = make_log('facility_apis/ztf')


class ZTFRequest:

    """A dictionary structure for ZTF ToO requests."""

    def _build_triggered_payload(self, request):
        """Payload json for ZTF object queue requests.

        Parameters
        ----------

        request : skyportal.models.FollowupRequest
            The request to add to the observation queue and the SkyPortal database.

        Returns
        ----------
        payload : json
            payload for requests.
        """

        start_mjd = Time(request.payload["start_date"], format='iso').mjd
        end_mjd = Time(request.payload["end_date"], format='iso').mjd

        json_data = {
            'queue_name': "ToO_" + request.payload["queue_name"],
            'validity_window_mjd': [start_mjd, end_mjd],
        }

        if request.payload["program_id"] == "Partnership":
            program_id = 2
        elif request.payload["program_id"] == "Caltech":
            program_id = 3
        else:
            raise ValueError('Unknown program.')

        targets = []
        cnt = 1
        for filt in request.payload["filters"].split(","):
            filter_id = bands[filt]
            for field_id in request.payload["field_ids"].split(","):
                field_id = int(field_id)

                target = {
                    'request_id': cnt,
                    'program_id': program_id,
                    'field_id': field_id,
                    'ra': request.obj.ra,
                    'dec': request.obj.dec,
                    'filter_id': filter_id,
                    'exposure_time': float(request.payload["exposure_time"]),
                    'program_pi': 'Kulkarni' + '/' + request.requester.username,
                    'subprogram_name': "ToO_" + request.payload["subprogram_name"],
                }
                targets.append(target)
                cnt = cnt + 1

        json_data['targets'] = targets

        return json_data

    def _build_forced_payload(self, request):
        """Payload json for ZTF object queue requests.

        Parameters
        ----------

        request : skyportal.models.FollowupRequest
            The request to add to the IPAC forced photometry queue and the SkyPortal database.

        Returns
        ----------
        payload : json
            payload for requests.
        """

        start_jd = Time(request.payload["start_date"], format='iso').jd
        end_jd = Time(request.payload["end_date"], format='iso').jd

        target = {
            'jdstart': start_jd,
            'jdend': end_jd,
            'ra': request.obj.ra,
            'dec': request.obj.dec,
        }

        return target

    def _build_observation_plan_payload(self, request):
        """Payload json for ZTF observation plan queue requests.

        Parameters
        ----------

        request: skyportal.models.ObservationPlanRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        start_mjd = Time(request.payload["start_date"], format='iso').mjd
        end_mjd = Time(request.payload["end_date"], format='iso').mjd

        json_data = {
            'queue_name': "ToO_" + request.payload["queue_name"],
            'validity_window_mjd': [start_mjd, end_mjd],
        }

        if request.payload["program_id"] == "Partnership":
            program_id = 2
        elif request.payload["program_id"] == "Caltech":
            program_id = 3
        else:
            raise ValueError('Unknown program.')

        # One observation plan per request
        if not len(request.observation_plans) == 1:
            raise ValueError('Should be one observation plan for this request.')

        observation_plan = request.observation_plans[0]
        planned_observations = observation_plan.planned_observations

        if len(planned_observations) == 0:
            raise ValueError('Cannot submit observing plan with no observations.')

        targets = []
        cnt = 1
        for obs in planned_observations:
            filter_id = bands[obs.filt]
            target = {
                'request_id': cnt,
                'program_id': program_id,
                'field_id': obs.field.field_id,
                'ra': obs.field.ra,
                'dec': obs.field.dec,
                'filter_id': filter_id,
                'exposure_time': obs.exposure_time,
                'program_pi': 'Kulkarni' + '/' + request.requester.username,
                'subprogram_name': "ToO_" + request.payload["subprogram_name"],
            }
            targets.append(target)
            cnt = cnt + 1

        json_data['targets'] = targets

        return json_data


def commit_photometry(url, altdata, df_request, request_id, instrument_id, user_id):
    """
    Commits ZTF forced photometry to the database

    Parameters
    ----------
    url : str
        ZTF forced photometry service data file location.
    altdata: dict
        Contains ZTF photometry api_token for the user
    df_request: pandas.DataFrame
        DataFrame containing request parameters (ra, dec, start jd, end jd)
    request_id : int
        FollowupRequest SkyPortal ID
    instrument_id : int
        Instrument SkyPortal ID
    user_id : int
        User SkyPortal ID
    """

    from ..models import (
        DBSession,
        FollowupRequest,
        Instrument,
        User,
    )

    Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))
    session = Session()

    try:
        request = session.query(FollowupRequest).get(request_id)
        instrument = session.query(Instrument).get(instrument_id)
        user = session.query(User).get(user_id)

        r = requests.get(
            url,
            auth=HTTPBasicAuth(
                altdata['ipac_http_user'], altdata['ipac_http_password']
            ),
        )
        df = ascii.read(
            r.content.decode(), header_start=0, data_start=1, comment='#'
        ).to_pandas()

        df.columns = df.columns.str.replace(',', '')
        desired_columns = {
            'jd',
            'forcediffimflux',
            'forcediffimfluxunc',
            'diffmaglim',
            'zpdiff',
            'filter',
        }
        if not desired_columns.issubset(set(df.columns)):
            raise ValueError('Missing expected column')
        df['ra'] = df_request['ra']
        df['dec'] = df_request['dec']
        df.rename(
            columns={'diffmaglim': 'limiting_mag'},
            inplace=True,
        )
        df = df.replace({"null": np.nan})
        df['mjd'] = astropy.time.Time(df['jd'], format='jd').mjd
        df['filter'] = df['filter'].str.replace('_', '')
        df['filter'] = df['filter'].str.lower()
        df = df.astype({'forcediffimflux': 'float64', 'forcediffimfluxunc': 'float64'})

        df['mag'] = df['zpdiff'] - 2.5 * np.log10(df['forcediffimflux'])
        df['magerr'] = 1.0857 * df['forcediffimfluxunc'] / df['forcediffimflux']

        snr = df['forcediffimflux'] / df['forcediffimfluxunc'] < 5
        df['mag'].loc[snr] = None
        df['magerr'].loc[snr] = None

        iszero = df['forcediffimfluxunc'] == 0.0
        df['mag'].loc[iszero] = None
        df['magerr'].loc[iszero] = None

        isnan = np.isnan(df['forcediffimflux'])
        df['mag'].loc[isnan] = None
        df['magerr'].loc[isnan] = None

        df = df.replace({np.nan: None})

        drop_columns = list(
            set(df.columns.values)
            - {'mjd', 'ra', 'dec', 'mag', 'magerr', 'limiting_mag', 'filter'}
        )

        df.drop(
            columns=drop_columns,
            inplace=True,
        )
        df['magsys'] = 'ab'

        data_out = {
            'obj_id': request.obj_id,
            'instrument_id': instrument.id,
            'group_ids': [g.id for g in user.accessible_groups],
            **df.to_dict(orient='list'),
        }

        from skyportal.handlers.api.photometry import add_external_photometry

        if len(df.index) > 0:
            add_external_photometry(data_out, request.requester)
            request.status = "Photometry committed to database"
        else:
            request.status = "No photometry to commit to database"

        session.add(request)
        session.commit()

        flow = Flow()
        flow.push(
            '*',
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": request.obj.internal_key},
        )
    except Exception as e:
        return log(f"Unable to commit photometry for {request_id}: {e}")
    finally:
        Session.remove()


class ZTFAPI(FollowUpAPI):

    """An interface to ZTF operations."""

    @staticmethod
    def delete(request):

        """Delete a follow-up request from ZTF queue.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
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

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        queue_name = "ToO_" + request.payload["queue_name"]
        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        payload = {'queue_name': queue_name, 'user': request.requester.username}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        s = Session()
        req = Request('DELETE', url, json=payload, headers=headers)
        prepped = req.prepare()
        r = s.send(prepped)
        if r.status_code == 200:
            request.status = "deleted"
        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    @staticmethod
    def get(request):

        """Get a forced photometry request result from ZTF.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to retrieve ZTF forced photometry.
        """

        from ..models import (
            DBSession,
            FollowupRequest,
            FacilityTransaction,
            Allocation,
            Instrument,
        )

        Session = scoped_session(
            sessionmaker(bind=DBSession.session_factory.kw["bind"])
        )
        session = Session()

        req = (
            session.query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )

        instrument = (
            Instrument.query_records_accessible_by(req.requester)
            .join(Allocation)
            .join(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .first()
        )

        altdata = request.allocation.altdata

        if not altdata:
            raise ValueError('Missing allocation information.')

        keys = ['ra', 'dec', 'jdstart', 'jdend']

        content = req.transactions[-1].response["content"]
        df_request = pd.read_html(content)[0]
        if df_request.shape[0] == 0:
            raise ValueError('Missing response from forced photometry service.')
        df_request.columns = df_request.columns.str.lower()
        if not set(keys).issubset(df_request.columns):
            raise ValueError("RA, Dec, jdstart, and jdend required in response.")
        df_request = df_request.iloc[0]
        df_request = df_request.replace({np.nan: None})

        requestgroup = {
            "email": altdata["ipac_email"],
            "userpass": altdata["ipac_userpass"],
            "option": "All recent jobs",
            "action": "Query Database",
        }
        params = urllib.parse.urlencode(requestgroup)
        url = f"{ZTF_FORCED_URL}/cgi-bin/getForcedPhotometryRequests.cgi?{params}"

        r = requests.get(
            url,
            auth=HTTPBasicAuth(
                altdata['ipac_http_user'], altdata['ipac_http_password']
            ),
        )
        if r.status_code == 200:
            df_result = pd.read_html(r.text)[0]
            df_result.rename(
                inplace=True, columns={'startJD': 'jdstart', 'endJD': 'jdend'}
            )
            df_result = df_result.replace({np.nan: None})
            if not set(keys).issubset(df_result.columns):
                raise ValueError("RA, Dec, jdstart, and jdend required in response.")
            index_match = None
            for index, row in df_result.iterrows():
                if not all([np.isclose(row[key], df_request[key]) for key in keys]):
                    continue
                index_match = index
            if index_match is None:
                raise ValueError(
                    'No matching response from forced photometry service. Please try again later.'
                )
            else:
                row = df_result.loc[index_match]
                if row['lightcurve'] is None:
                    raise ValueError(
                        'Light curve not yet available. Please try again later.'
                    )
                else:
                    lightcurve = row['lightcurve']
                    dataurl = f"{ZTF_FORCED_URL}/{lightcurve}"
                    IOLoop.current().run_in_executor(
                        None,
                        lambda: commit_photometry(
                            dataurl,
                            altdata,
                            df_request,
                            req.id,
                            instrument.id,
                            request.requester.id,
                        ),
                    )
        else:
            req.status = f'error: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=req,
            initiator_id=req.last_modified_by_id,
        )

        session.add(transaction)
        session.commit()

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to ZTF.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        req = ZTFRequest()

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        if request.payload["request_type"] == "triggered":
            requestgroup = req._build_triggered_payload(request)
            url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        elif request.payload["request_type"] == "forced_photometry":
            requestgroup = req._build_forced_payload(request)
            requestgroup["email"] = altdata["ipac_email"]
            requestgroup["userpass"] = altdata["ipac_userpass"]
            params = urllib.parse.urlencode(requestgroup)
            url = f"{ZTF_FORCED_URL}/cgi-bin/requestForcedPhotometry.cgi?{params}"

        if request.payload["request_type"] == "triggered":
            headers = {"Authorization": f"Bearer {altdata['access_token']}"}

            payload = {
                'targets': requestgroup["targets"],
                'queue_name': requestgroup["queue_name"],
                'validity_window_mjd': requestgroup["validity_window_mjd"],
                'queue_type': 'list',
                'user': request.requester.username,
            }

            url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
            s = Session()
            req = Request('PUT', url, json=payload, headers=headers)
            prepped = req.prepare()
            r = s.send(prepped)
        elif request.payload["request_type"] == "forced_photometry":
            r = requests.get(
                url,
                auth=HTTPBasicAuth(
                    altdata['ipac_http_user'], altdata['ipac_http_password']
                ),
            )

        if r.status_code == 200:
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

    form_json_schema = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "default": str(datetime.utcnow()).replace("T", ""),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": str(datetime.utcnow() + timedelta(days=1)).replace("T", ""),
            },
            "program_id": {
                "type": "string",
                "enum": ["Partnership", "Caltech"],
                "default": "Partnership",
            },
            "subprogram_name": {
                "type": "string",
                "enum": ["GW", "GRB", "Neutrino", "SolarSystem", "Other"],
                "default": "GRB",
            },
            "exposure_time": {"type": "string", "default": "300"},
            "filters": {"type": "string", "default": "g,r,i"},
            "field_ids": {"type": "string", "default": "699,700"},
            "queue_name": {"type": "string", "default": datetime.utcnow()},
            "request_type": {
                "type": "string",
                "enum": ["triggered", "forced_photometry"],
                "default": "triggered",
                "title": "Request Type",
            },
        },
        "required": [
            "start_date",
            "end_date",
            "program_id",
            "filters",
            "field_ids",
            "queue_name",
            "subprogram_name",
            "request_type",
        ],
    }

    ui_json_schema = {}


class ZTFMMAAPI(MMAAPI):

    """An interface to ZTF MMA operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def send(request):

        """Submit an EventObservationPlan to ZTF.

        Parameters
        ----------
        request : skyportal.models.ObservationPlanRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        req = ZTFRequest()
        requestgroup = req._build_observation_plan_payload(request)

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        payload = {
            'targets': requestgroup["targets"],
            'queue_name': requestgroup["queue_name"],
            'validity_window_mjd': requestgroup["validity_window_mjd"],
            'queue_type': 'list',
            'user': request.requester.username,
        }

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        s = Session()
        ztfreq = Request('PUT', url, json=payload, headers=headers)
        prepped = ztfreq.prepare()
        r = s.send(prepped)

        if r.status_code == 200:
            request.status = 'submitted to telescope queue'
        else:
            request.status = f'rejected from telescope queue: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            observation_plan_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    @staticmethod
    def remove(request):

        """Delete an EventObservationPlan from ZTF queue.

        Parameters
        ----------
        request : skyportal.models.ObservationPlanRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, ObservationPlanRequest, FacilityTransaction

        req = (
            DBSession()
            .query(ObservationPlanRequest)
            .filter(ObservationPlanRequest.id == request.id)
            .one()
        )

        # this happens for failed submissions
        # just go ahead and delete
        if len(req.transactions) == 0:
            DBSession().query(ObservationPlanRequest).filter(
                ObservationPlanRequest.id == request.id
            ).delete()
            DBSession().commit()
            return

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        queue_name = "ToO_" + request.payload["queue_name"]
        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        payload = {'queue_name': queue_name, 'user': request.requester.username}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        s = Session()
        ztfreq = Request('DELETE', url, json=payload, headers=headers)
        prepped = ztfreq.prepare()
        r = s.send(prepped)
        if r.status_code == 200:
            request.status = "deleted from telescope queue"
        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            observation_plan_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    @staticmethod
    def queued(allocation, start_date, end_date):

        """Retrieve queued observations by ZTF.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation with queue information.
        start_date : datetime.datetime
            Minimum time for observation request
        end_date : datetime.datetime
            Maximum time for observation request
        """

        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        s = Session()
        ztfreq = Request('GET', url, headers=headers)
        prepped = ztfreq.prepare()
        r = s.send(prepped)

        if r.status_code == 200:
            df = pd.DataFrame(r.json()['data'])
            queue_names = set(df['queue_name'])
            fetch_obs = functools.partial(
                fetch_queued_observations,
                allocation.instrument.id,
                df,
                start_date,
                end_date,
            )
            IOLoop.current().run_in_executor(None, fetch_obs)
            return queue_names
        else:
            return ValueError(f'Error querying for queued observations: {r.text}')

    @staticmethod
    def retrieve(allocation, start_date, end_date):

        """Retrieve executed observations by ZTF.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation with queue information.
        start_date : datetime.datetime
            Minimum time for observation request
        end_date : datetime.datetime
            Maximum time for observation request
        """

        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        jd_start = Time(start_date, format='datetime').jd
        jd_end = Time(end_date, format='datetime').jd

        if jd_start > jd_end:
            raise ValueError('start_date must be before end_date.')

        s = Session()
        s.auth = (altdata['tap_username'], altdata['tap_password'])
        client = pyvo.dal.TAPService(altdata['tap_service'], session=s)

        request_str = f"""
            SELECT field,rcid,fid,expid,obsjd,exptime,maglimit,ipac_gid,seeing
            FROM ztf.ztf_current_meta_sci WHERE (obsjd BETWEEN {jd_start} AND {jd_end})
        """

        fetch_obs = functools.partial(
            fetch_observations,
            allocation.instrument.id,
            client,
            request_str,
        )

        IOLoop.current().run_in_executor(None, fetch_obs)

    def custom_json_schema(instrument, user):
        form_json_schema = MMAAPI.custom_json_schema(instrument, user)

        form_json_schema["properties"] = {
            **form_json_schema["properties"],
            "program_id": {
                "type": "string",
                "enum": ["Partnership", "Caltech"],
                "default": "Partnership",
            },
            "subprogram_name": {
                "type": "string",
                "enum": ["GW", "GRB", "Neutrino", "SolarSystem", "Other"],
                "default": "GRB",
            },
        }
        form_json_schema["required"] = form_json_schema["required"] + [
            "subprogram_name",
            "program_id",
        ]

        return form_json_schema


def fetch_observations(instrument_id, client, request_str):
    """Fetch executed observations from a TAP client.
    instrument_id : int
        ID of the instrument
    client : pyvo.dal.TAPService
        An authenticated pyvo.dal.TAPService instance.
    request_str : str
        TAP request of the form:
        SELECT field,rcid,fid,expid,obsjd,exptime,maglimit,ipac_gid,seeing
        FROM ztf.ztf_current_meta_sci WHERE (obsjd BETWEEN 2459637.2474652776 AND 2459640.2474652776)
    """

    job = client.submit_job(request_str)
    job = job.run().wait()
    job.raise_if_error()
    obstable = job.fetch_result().to_table()
    obstable = obstable.filled().to_pandas()

    obs_grouped_by_exp = obstable.groupby('expid')
    dfs = []
    for expid, df_group in obs_grouped_by_exp:
        df_group_median = df_group.median()
        df_group_median['observation_id'] = int(expid)
        df_group_median['processed_fraction'] = len(df_group["field"]) / 64.0
        df_group_median['filter'] = inv_bands[int(df_group_median["fid"])]
        dfs.append(df_group_median)
    obstable = pd.concat(dfs, axis=1).T
    obstable.rename(
        columns={
            'obsjd': 'obstime',
            'field': 'field_id',
            'maglimit': 'limmag',
            'exptime': 'exposure_time',
        },
        inplace=True,
    )

    from skyportal.handlers.api.observation import add_observations

    add_observations(instrument_id, obstable)


def fetch_queued_observations(instrument_id, obstable, start_date, end_date):
    """Fetch queued (i.e. yet to be completed) observations from ZTF scheduler.
    instrument_id : int
        ID of the instrument
    obstable : pandas.DataFrame
        A dataframe returned from the ZTF scheduler queue
    start_date : datetime.datetime
        Minimum time for observation request
    end_date : datetime.datetime
        Maximum time for observation request
    """

    observations = []
    for _, queue in obstable.iterrows():
        validity_window_mjd = queue['validity_window_mjd']
        if validity_window_mjd is not None:
            validity_window_start = Time(
                validity_window_mjd[0], format='mjd', scale='utc'
            ).datetime
            validity_window_end = Time(
                validity_window_mjd[1], format='mjd', scale='utc'
            ).datetime
        else:
            continue

        res = json.loads(queue['queue'])
        for row in res:
            field_id = int(row["field_id"])
            if "slot_start_time" in row:
                slot_start_time = Time(row["slot_start_time"], format='iso').datetime
            else:
                slot_start_time = validity_window_start

            if (slot_start_time < Time(start_date, format='datetime').datetime) or (
                slot_start_time > Time(end_date, format='datetime').datetime
            ):
                continue

            if not row['filter_id'] is None:
                filt = inv_bands[row['filter_id']]
            elif row['subprogram_name'] == 'i_band':
                filt = 'ztfi'
            else:
                filt = None
            observations.append(
                {
                    'queue_name': queue['queue_name'],
                    'instrument_id': instrument_id,
                    'field_id': field_id,
                    'obstime': slot_start_time,
                    'validity_window_start': validity_window_start,
                    'validity_window_end': validity_window_end,
                    'exposure_time': row["exposure_time"],
                    'filter': filt,
                }
            )

    from skyportal.handlers.api.observation import add_queued_observations

    obstable = pd.DataFrame(observations)

    add_queued_observations(instrument_id, obstable)
