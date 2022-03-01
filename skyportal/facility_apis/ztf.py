from requests import Request, Session
from datetime import datetime, timedelta
from astropy.time import Time
import functools
from tornado.ioloop import IOLoop
import pandas as pd
import pyvo
import urllib

from . import FollowUpAPI, MMAAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()


if cfg['app.ztf.port'] is None:
    ZTF_URL = f"{cfg['app.ztf.protocol']}://{cfg['app.ztf.host']}"
else:
    ZTF_URL = f"{cfg['app.ztf.protocol']}://{cfg['app.ztf.host']}:{cfg['app.ztf.port']}"

bands = {'g': 1, 'r': 2, 'i': 3}
inv_bands = {v: k for k, v in bands.items()}


class ZTFRequest:

    """A dictionary structure for ZTF ToO requests."""

    def _build_object_payload(self, request):
        """Payload json for ZTF object queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
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


class ZTFAPI(FollowUpAPI):

    """An interface to ZTF operations."""

    @staticmethod
    def delete(request):

        """Delete a follow-up request from ZTF queue.

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
        r.raise_for_status()

        request.status = "deleted"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to ZTF.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        req = ZTFRequest()
        requestgroup = req._build_object_payload(request)

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
        req = Request('PUT', url, json=payload, headers=headers)
        prepped = req.prepare()
        r = s.send(prepped)
        r.raise_for_status()

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
        },
        "required": [
            "start_date",
            "end_date",
            "program_id",
            "filters",
            "field_ids",
            "queue_name",
            "subprogram_name",
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
        request: skyportal.models.ObservationPlanRequest
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
        r.raise_for_status()

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
        request: skyportal.models.ObservationPlanRequest
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
        r.raise_for_status()

        request.status = "deleted from telescope queue"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            observation_plan_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    @staticmethod
    def retrieve(allocation, start_date, end_date):

        """Retrieve executed observations by ZTF.

        Parameters
        ----------
        allocation: skyportal.models.Allocation
            The allocation with queue information.
        """

        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        jd_start = Time(start_date, format='datetime').jd
        jd_end = Time(end_date, format='datetime').jd

        if not jd_start < jd_end:
            raise ValueError('start_date must be before end_date.')

        s = Session()
        s.auth = (altdata['tap_username'], altdata['tap_password'])
        client = pyvo.dal.TAPService(altdata['tap_service'], session=s)

        request_str = """
            SELECT field,rcid,fid,expid,obsjd,exptime,maglimit,ipac_gid,seeing
            FROM ztf.ztf_current_meta_sci WHERE (obsjd BETWEEN {0} AND {1})
        """.format(
            jd_start, jd_end
        )

        fetch_obs = functools.partial(
            fetch_observations,
            allocation.instrument.id,
            client,
            request_str,
        )

        IOLoop.current().run_in_executor(None, fetch_obs)

    form_json_schema = MMAAPI.form_json_schema

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


def fetch_observations(instrument_id, client, request_str):
    """Fetch executed observations from a TAP client.
    instrument_id: int
        ID of the instrument
    client: pyvo.dal.TAPService
        An authenticated pyvo.dal.TAPService instance.
    request_str: str
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
        df_group_median['filter'] = 'ztf' + inv_bands[int(df_group_median["fid"])]
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
