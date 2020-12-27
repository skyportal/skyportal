import os
import requests
from datetime import datetime, timedelta
from astropy.time import Time
import urllib

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()


secret_key = cfg["app.secret_key"]


class ZTFRequest:

    """A dictionary structure for ZTF ToO requests."""

    def _build_payload(self, request):
        """Payload json for ZTF queue requests.

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

        bands = {'g': 1, 'r': 2, 'i': 3, 'z': 4, 'J': 5}
        json_data = {
            'queue_name': "ToO_" + request.payload["queue_name"],
            'validity_window_mjd': [start_mjd, end_mjd],
        }

        if request.payload["program_id"] == "Partnership":
            program_id = 2
        elif request.payload["program_id"] == "Caltech":
            program_id = 3

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


def authenticate():
    """Authenticate user, return access token
    :return:
    """

    base_url = (
        f"{cfg['app.kowalski_protocol']}://"
        f"{cfg['app.kowalski_host']}:{cfg['app.kowalski_port']}"
    )

    session = requests.Session()

    # post username and password, get access token
    auth = session.post(
        f"{base_url}/api/auth",
        json={
            "username": cfg["app.kowalski_username"],
            "password": cfg["app.kowalski_password"],
        },
    )

    if auth.status_code == requests.codes.ok:
        print(auth.json())

        if "token" not in auth.json():
            print("Authentication failed")
            raise Exception(auth.json().get("message", "Authentication failed"))

        access_token = auth.json().get("token")

        print("Successfully authenticated")

        return access_token

    raise Exception("Authentication failed")


def query_kowalski(query: dict, api: str, method="post", timeout=7):

    base_url = (
        f"{cfg['app.kowalski_protocol']}://"
        f"{cfg['app.kowalski_host']}:{cfg['app.kowalski_port']}"
    )

    token = authenticate()
    headers = {"Authorization": token}

    session = requests.Session()

    if method == "post":
        resp = session.post(
            urllib.parse.urljoin(base_url, os.path.join('api', api)),
            json=query,
            headers=headers,
            timeout=timeout,
        )
    elif method == "delete":
        resp = session.delete(
            urllib.parse.urljoin(base_url, os.path.join('api', api)),
            json=query,
            headers=headers,
            timeout=timeout,
        )
    else:
        raise Exception("Kowalski method not implemented.")

    return resp


class ZTFAPI(FollowUpAPI):

    """An interface to ZTF operations."""

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

        queue_name = "ToO_" + request.payload["queue_name"]

        payload = {'queue_name': queue_name, 'user': request.requester.username}

        r = query_kowalski(query=payload, api='triggers/ztf.DELETE', method="delete")

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
    def submit(request):

        """Submit a follow-up request to ZTF.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        req = ZTFRequest()
        requestgroup = req._build_payload(request)

        payload = {
            'targets': requestgroup["targets"],
            'queue_name': requestgroup["queue_name"],
            'validity_window_mjd': requestgroup["validity_window_mjd"],
            'queue_type': 'list',
            'user': request.requester.username,
        }

        r = query_kowalski(query=payload, api='triggers/ztf.POST', method="post")

        print(r.text)

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
            "existing_queue": {
                "type": "string",
                "enum": ["temp1", "temp2"],
                "default": "temp1",
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
        ],
    }

    ui_json_schema = {}
