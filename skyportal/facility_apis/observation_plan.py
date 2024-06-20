import json
import os
import tempfile
from datetime import datetime, timedelta

import paramiko
import requests
import sqlalchemy as sa
from astropy.time import Time
from paramiko import SSHClient
from requests import Request, Session
from scp import SCPClient
from sqlalchemy.orm import joinedload

from baselayer.log import make_log
from baselayer.app.flow import Flow
from baselayer.app.env import load_env

from ..email_utils import send_email
from ..utils import http
from . import FollowUpAPI

log = make_log('api/observation_plan')

env, cfg = load_env()

SLACK_URL = f"{cfg['slack.expected_url_preamble']}/services"

default_filters = cfg['app.observation_plan.default_filters']

use_skyportal_fields = cfg['app.observation_plan.use_skyportal_fields']

email = False
if cfg.get("email_service") == "sendgrid" or cfg.get("email_service") == "smtp":
    email = True


class GenericRequest:

    """A dictionary structure for ToO requests."""

    def _build_observation_plan_payload(self, request):
        """Payload json for observation plan queue requests.

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
            target = {
                'request_id': cnt,
                'field_id': obs.field.field_id,
                'ra': obs.field.ra,
                'dec': obs.field.dec,
                'filter': obs.filt,
                'exposure_time': obs.exposure_time,
                'program_pi': request.requester.username,
            }
            targets.append(target)
            cnt = cnt + 1

        json_data['targets'] = targets

        return json_data


class MMAAPI(FollowUpAPI):
    """An interface to MMA operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit_multiple(requests, asynchronous=True):
        """Generate multiple observation plans.

        Parameters
        ----------
        requests: skyportal.models.ObservationPlanRequest
            The list of requests to generate the observation plan.
        asynchronous : bool
            Create asynchronous request. Defaults to True.
        """

        from tornado.ioloop import IOLoop
        from ..models import DBSession, EventObservationPlan
        from ..utils.observation_plan import generate_plan

        plan_ids, request_ids = [], []
        for request in requests:
            plan = EventObservationPlan.query.filter_by(
                plan_name=request.payload["queue_name"]
            ).first()
            if plan is None:
                # check payload
                required_parameters = {
                    'start_date',
                    'end_date',
                    'schedule_type',
                    'schedule_strategy',
                    'filter_strategy',
                    'exposure_time',
                    'filters',
                    'maximum_airmass',
                    'integrated_probability',
                    'galactic_latitude',
                }

                if not required_parameters.issubset(set(request.payload.keys())):
                    raise ValueError('Missing required planning parameter')

                if (
                    request.payload["filter_strategy"] == "integrated"
                    and "minimum_time_difference" not in request.payload
                ):
                    raise ValueError(
                        'minimum_time_difference must be defined for integrated scheduling'
                    )

                if request.payload["schedule_type"] not in [
                    "greedy",
                    "greedy_slew",
                    "sear",
                    "airmass_weighted",
                ]:
                    raise ValueError(
                        'schedule_type must be one of greedy, greedy_slew, sear, or airmass_weighted'
                    )

                if (
                    request.payload["integrated_probability"] < 0
                    or request.payload["integrated_probability"] > 100
                ):
                    raise ValueError('integrated_probability must be between 0 and 100')

                if request.payload["filter_strategy"] not in ["block", "integrated"]:
                    raise ValueError(
                        'filter_strategy must be either block or integrated'
                    )

                start_time = Time(
                    request.payload["start_date"], format='iso', scale='utc'
                )
                end_time = Time(request.payload["end_date"], format='iso', scale='utc')

                plan = EventObservationPlan(
                    observation_plan_request_id=request.id,
                    dateobs=request.gcnevent.dateobs,
                    plan_name=request.payload['queue_name'],
                    instrument_id=request.instrument.id,
                    validity_window_start=start_time.datetime,
                    validity_window_end=end_time.datetime,
                )

                DBSession().add(plan)
                DBSession().commit()

                request.status = 'running'
                DBSession().merge(request)
                DBSession().commit()

                log(
                    f"Created observation plan request for ID {plan.id} in session {plan._sa_instance_state.session_id}"
                )

                flow = Flow()
                flow.push(
                    '*',
                    "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
                    payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
                )

                plan_ids.append(plan.id)
                request_ids.append(request.id)
            else:
                raise ValueError(
                    f'plan_name {request.payload["queue_name"]} already exists.'
                )

        log(f"Generating schedule for observation plan {plan.id}")
        requester_id = request.requester.id

        if asynchronous:
            IOLoop.current().run_in_executor(
                None,
                lambda: generate_plan(
                    observation_plan_ids=plan_ids,
                    request_ids=request_ids,
                    user_id=requester_id,
                ),
            )
        else:
            generate_plan(
                observation_plan_ids=plan_ids,
                request_ids=request_ids,
                user_id=requester_id,
            )

        return plan_ids

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request_id, asynchronous=True):
        """Generate an observation plan.

        Parameters
        ----------
        request_id : int
            The ID of the ObservationPlanRequest to generate the observation plan.
        asynchronous : bool
            Create asynchronous request. Defaults to True.
        """

        from tornado.ioloop import IOLoop
        from ..models import DBSession, EventObservationPlan, ObservationPlanRequest
        from ..utils.observation_plan import generate_plan

        log(f"request_id: {request_id}")
        with DBSession() as session:
            request = session.scalar(
                sa.select(ObservationPlanRequest).where(
                    ObservationPlanRequest.id == request_id
                )
            )
            plan = session.scalars(
                sa.select(EventObservationPlan).where(
                    EventObservationPlan.plan_name == request.payload["queue_name"]
                )
            ).first()

            # if the request is marked as running but there is a plan that is complete,
            # then mark the request as complete as well
            if (
                plan is not None
                and plan.status == 'complete'
                and request.status == 'running'
            ):
                request.status = 'complete'
                session.merge(request)
                session.commit()
                log(
                    f"Plan {plan.id} is already complete. Marking request {request.id} as complete."
                )
                return plan.id

            # if the request is marked as running and there is already a plan that is pending submissions,
            # then it is likely that processing the plan failed before
            # so we delete the plan and create a new one
            if (
                plan is not None
                and plan.status == 'pending submission'
                and request.status == 'running'
            ):
                log(
                    f"Plan {plan.id} has been pending submission for more than 24 hours. Deleting and creating a new plan."
                )
                session.delete(plan)
                session.commit()
                plan = None

            if plan is None:
                # check payload
                required_parameters = {
                    'start_date',
                    'end_date',
                    'schedule_type',
                    'schedule_strategy',
                    'filter_strategy',
                    'exposure_time',
                    'filters',
                    'maximum_airmass',
                    'integrated_probability',
                }

                if not required_parameters.issubset(set(request.payload.keys())):
                    raise ValueError('Missing required planning parameter')

                if (
                    request.payload["filter_strategy"] == "integrated"
                    and "minimum_time_difference" not in request.payload
                ):
                    raise ValueError(
                        'minimum_time_difference must be defined for integrated scheduling'
                    )

                if request.payload["schedule_type"] not in [
                    "greedy",
                    "greedy_slew",
                    "sear",
                    "airmass_weighted",
                ]:
                    raise ValueError(
                        'schedule_type must be one of greedy, greedy_slew, sear, or airmass_weighted'
                    )

                if (
                    request.payload["integrated_probability"] < 0
                    or request.payload["integrated_probability"] > 100
                ):
                    raise ValueError('integrated_probability must be between 0 and 100')

                if request.payload["filter_strategy"] not in ["block", "integrated"]:
                    raise ValueError(
                        'filter_strategy must be either block or integrated'
                    )

                start_time = Time(
                    request.payload["start_date"], format='iso', scale='utc'
                )
                end_time = Time(request.payload["end_date"], format='iso', scale='utc')

                plan = EventObservationPlan(
                    observation_plan_request_id=request.id,
                    dateobs=request.gcnevent.dateobs,
                    plan_name=request.payload['queue_name'],
                    instrument_id=request.instrument.id,
                    validity_window_start=start_time.datetime,
                    validity_window_end=end_time.datetime,
                )

                session.add(plan)
                session.commit()

                plan_id = plan.id

                request.status = 'running'
                session.merge(request)
                session.commit()

                log(
                    f"Created observation plan request for ID {plan.id} in session {plan._sa_instance_state.session_id}"
                )

                flow = Flow()
                flow.push(
                    '*',
                    "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
                    payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
                )

                flow.push(
                    '*',
                    "skyportal/REFRESH_OBSERVATION_PLAN_NAMES",
                )

                log(f"Generating schedule for observation plan {plan.id}")
                requester_id = request.requester.id

                if asynchronous:
                    IOLoop.current().run_in_executor(
                        # TODO: add stats_method and stats_logging to the arguments
                        None,
                        lambda: generate_plan(
                            observation_plan_ids=[plan.id],
                            request_ids=[request.id],
                            user_id=requester_id,
                        ),
                    )
                else:
                    generate_plan(
                        observation_plan_ids=[plan.id],
                        request_ids=[request.id],
                        user_id=requester_id,
                    )

                return plan_id

            else:
                raise ValueError(
                    f'plan_name {request.payload["queue_name"]} already exists.'
                )

    @staticmethod
    def delete(request_id):
        """Delete an observation plan from list.

        Parameters
        ----------
        request_id: integer
            The id of the skyportal.models.ObservationPlanRequest to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, ObservationPlanRequest

        req = (
            DBSession.execute(
                sa.select(ObservationPlanRequest)
                .filter(ObservationPlanRequest.id == request_id)
                .options(joinedload(ObservationPlanRequest.observation_plans))
            )
            .unique()
            .one()
        )
        req = req[0]

        if len(req.observation_plans) > 1:
            raise ValueError(
                'Should only be one observation plan associated to this request'
            )

        if len(req.observation_plans) > 0:
            observation_plan = req.observation_plans[0]
            DBSession().delete(observation_plan)

        DBSession().delete(req)
        DBSession().commit()

    def custom_json_schema(instrument, user, **kwargs):
        from ..models import DBSession, GalaxyCatalog, InstrumentField

        galaxy_catalogs = kwargs.get("galaxy_catalog_names", [])
        if not isinstance(galaxy_catalogs, list) or len(galaxy_catalogs) == 0:
            galaxy_catalogs = [
                g for g, in DBSession().query(GalaxyCatalog.name).distinct().all()
            ]
        end_date = instrument.telescope.next_sunrise()
        if end_date is None:
            end_date = str(datetime.utcnow() + timedelta(days=1))
        else:
            end_date = Time(end_date, format='jd').iso

        # we add a use_references boolean to the schema if any of the instrument's fields has reference filters
        has_references = (
            DBSession()
            .query(InstrumentField)
            .filter(
                InstrumentField.instrument_id == instrument.id,
                InstrumentField.reference_filters != '{}',
            )
            .count()
            > 0
        )

        form_json_schema = {
            "type": "object",
            "properties": {
                "queue_name": {
                    "type": "string",
                    "default": f"ToO_{str(datetime.utcnow()).replace(' ', 'T')}",
                },
                "start_date": {
                    "type": "string",
                    "default": str(datetime.utcnow()),
                    "title": "Start Date (UT)",
                },
                "end_date": {
                    "type": "string",
                    "title": "End Date (UT)",
                    "default": end_date,
                },
                "filter_strategy": {
                    "type": "string",
                    "enum": ["block", "integrated"],
                    "default": "block",
                },
                "schedule_type": {
                    "type": "string",
                    "enum": ["greedy", "greedy_slew", "sear", "airmass_weighted"],
                    "default": "greedy",
                },
                "schedule_strategy": {
                    "type": "string",
                    "enum": ["tiling", "galaxy"],
                    "default": "tiling",
                },
                "exposure_time": {
                    "title": "Exposure Time [s]",
                    "type": "number",
                    "default": 300,
                    "minimum": 1,
                },
                "filters": {"type": "string", "default": ",".join(default_filters)},
                "maximum_airmass": {
                    "title": "Maximum Airmass (1-3)",
                    "type": "number",
                    "default": 2.0,
                    "minimum": 1,
                    "maximum": 3,
                },
                "integrated_probability": {
                    "title": "Integrated Probability (0-100)",
                    "type": "number",
                    "default": 90.0,
                    "minimum": 0,
                    "maximum": 100,
                },
                "galactic_plane": {
                    "title": "Avoid the Galactic Plane?",
                    "type": "boolean",
                    "default": False,
                },
                "max_tiles": {
                    "title": "Threshold on number of fields?",
                    "type": "boolean",
                    "default": False,
                },
                "balance_exposure": {
                    "title": "Balance exposures across fields",
                    "type": "boolean",
                    "default": True,
                },
                "ra_slice": {
                    "title": "RA Slicing",
                    "type": "boolean",
                    "default": False,
                },
            },
            "required": [
                "start_date",
                "end_date",
                "filters",
                "queue_name",
                "filter_strategy",
                "schedule_type",
                "schedule_strategy",
                "exposure_time",
                "maximum_airmass",
                "integrated_probability",
            ],
            "dependencies": {
                "galactic_plane": {
                    "oneOf": [
                        {
                            "properties": {
                                "galactic_plane": {
                                    "enum": [True],
                                },
                                "galactic_latitude": {
                                    "title": "Galactic latitude to exclude",
                                    "type": "number",
                                    "default": 10.0,
                                    "minimum": 0,
                                    "maximum": 90,
                                },
                            },
                            "required": ["galactic_latitude"],
                        },
                        {
                            "properties": {
                                "galactic_plane": {
                                    "enum": [False],
                                },
                            },
                        },
                    ],
                },
                "max_tiles": {
                    "oneOf": [
                        {
                            "properties": {
                                "max_tiles": {
                                    "enum": [True],
                                },
                                "max_nb_tiles": {
                                    "title": "Maximum number of fields",
                                    "type": "number",
                                    "default": 100.0,
                                    "minimum": 0,
                                    "maximum": 1000,
                                },
                            },
                            "required": ["max_nb_tiles"],
                        },
                        {
                            "properties": {
                                "max_tiles": {
                                    "enum": [False],
                                },
                            },
                        },
                    ],
                },
                "ra_slice": {
                    "oneOf": [
                        {
                            "properties": {
                                "ra_slice": {
                                    "enum": [True],
                                },
                                "ra_slice_min": {
                                    "title": "Minimum RA",
                                    "type": "number",
                                    "default": 0.0,
                                    "minimum": 0,
                                    "maximum": 360,
                                },
                                "ra_slice_max": {
                                    "title": "Maximum RA",
                                    "type": "number",
                                    "default": 360.0,
                                    "minimum": 0.0,
                                    "maximum": 360,
                                },
                            },
                            "required": ["ra_slice_min", "ra_slice_max"],
                        },
                        {
                            "properties": {
                                "ra_slice": {
                                    "enum": [False],
                                },
                            },
                        },
                    ],
                },
                "filter_strategy": {
                    # we want to show min_time_difference only if filter_strategy is integrated
                    "oneOf": [
                        {
                            "properties": {
                                "filter_strategy": {
                                    "enum": ["integrated"],
                                },
                                "minimum_time_difference": {
                                    "title": "Minimum time difference [min] (0-180)",
                                    "type": "number",
                                    "default": 30.0,
                                    "minimum": 0,
                                    "maximum": 180,
                                },
                            },
                            "required": ["minimum_time_difference"],
                        },
                        {
                            "properties": {
                                "filter_strategy": {
                                    "enum": ["block"],
                                },
                            },
                        },
                    ],
                },
                # we want to show galaxy_catalog and galaxy_sorting only if schedule_strategy is galaxy
                "schedule_strategy": {
                    "oneOf": [
                        {
                            "properties": {
                                "schedule_strategy": {
                                    "enum": ["galaxy"],
                                },
                                "galaxy_catalog": {
                                    "type": "string",
                                    "enum": galaxy_catalogs,
                                    "default": galaxy_catalogs[0]
                                    if len(galaxy_catalogs) > 0
                                    else "",
                                },
                                "galaxy_sorting": {
                                    "type": "string",
                                    "enum": [
                                        "mstar_prob_weighted",
                                        "equal",
                                        "sfr_fuv",
                                        "mstar",
                                        "magb",
                                        "magk",
                                    ],
                                    "default": "mstar_prob_weighted",
                                },
                            },
                            "required": ["galaxy_catalog", "galaxy_sorting"],
                        },
                        {
                            "properties": {
                                "schedule_strategy": {
                                    "enum": ["tiling"],
                                },
                            },
                        },
                    ],
                },
            },
        }

        if has_references:
            form_json_schema["properties"]["use_references"] = {
                "title": "Use fields with references only?",
                "type": "boolean",
                "default": True,
            }
        return form_json_schema

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

        if 'type' in altdata and altdata['type'] == 'scp':
            with tempfile.NamedTemporaryFile(mode='w') as f:
                json.dump(payload, f, indent=4, sort_keys=True)
                f.flush()

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
                    os.path.join(altdata['directory'], payload["queue_name"] + '.json'),
                )
                scp.close()

                request.status = 'submitted'

                transaction = FacilityTransaction(
                    request=None,
                    response=None,
                    observation_plan_request=request,
                    initiator_id=request.last_modified_by_id,
                )
        elif 'type' in altdata and altdata['type'] == 'slack':
            slack_microservice_url = (
                f'http://127.0.0.1:{cfg["slack.microservice_port"]}'
            )

            data = json.dumps(
                {
                    "url": f"{SLACK_URL}/{altdata['slack_workspace']}/{altdata['slack_channel']}/{altdata['slack_token']}",
                    "text": str(payload),
                }
            )

            r = requests.post(
                slack_microservice_url,
                data=data,
                headers={'Content-Type': 'application/json'},
            )
            r.raise_for_status()

            request.status = 'submitted'

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=http.serialize_requests_response(r),
                observation_plan_request=request,
                initiator_id=request.last_modified_by_id,
            )

        elif 'type' in altdata and altdata['type'] == 'email':
            subject = f"{cfg['app.title']} - New observation plans"

            send_email(
                recipients=[altdata['email']],
                subject=subject,
                body=str(payload),
            )

            request.status = 'submitted'

            transaction = FacilityTransaction(
                request=None,
                response=None,
                observation_plan_request=request,
                initiator_id=request.last_modified_by_id,
            )

        else:
            headers = {"Authorization": f"token {altdata['access_token']}"}

            # default to API
            url = (
                altdata['protocol']
                + '://'
                + ('127.0.0.1' if 'localhost' in altdata['host'] else altdata['host'])
                + ':'
                + altdata['port']
                + '/api/obsplans'
            )
            s = Session()
            genericreq = Request('PUT', url, json=payload, headers=headers)
            prepped = genericreq.prepare()
            r = s.send(prepped)

            if r.status_code == 200:
                request.status = 'submitted to telescope queue'
            else:
                request.status = f'rejected from telescope queue: {r.content}'

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=None,
                observation_plan_request=request,
                initiator_id=request.last_modified_by_id,
            )

        session.add(transaction)

    ui_json_schema = {}
