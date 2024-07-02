import astropy
from astropy.io import ascii
import json
import requests
from requests import Request, Session
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from astropy.time import Time
import functools
from marshmallow.exceptions import ValidationError
import numpy as np
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop
import pandas as pd
import sqlalchemy as sa
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

bands = {'g': 1, 'ztfg': 1, 'r': 2, 'ztfr': 2, 'i': 3, 'ztfi': 3}
inv_bands = {1: 'ztfg', 2: 'ztfr', 3: 'ztfi'}

log = make_log('facility_apis/ztf')


class ZTFRequest:

    """A dictionary structure for ZTF ToO requests."""

    def _build_triggered_payload(self, request, session):
        """Payload json for ZTF object queue requests.

        Parameters
        ----------

        request : skyportal.models.FollowupRequest
            The request to add to the observation queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction

        Returns
        ----------
        payload : json
            payload for requests.
        """

        from ..models import Allocation, InstrumentField

        allocation = (
            session.scalars(
                sa.select(Allocation).where(Allocation.id == request.allocation_id)
            )
        ).first()
        instrument = allocation.instrument

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

                field = session.scalars(
                    sa.select(InstrumentField).where(
                        InstrumentField.instrument_id == instrument.id,
                        InstrumentField.field_id == field_id,
                    )
                ).first()

                if field is None:
                    raise ValueError(f"Could not find field {field_id} in instrument.")

                target = {
                    'request_id': cnt,
                    'program_id': program_id,
                    'field_id': field_id,
                    'ra': field.ra,
                    'dec': field.dec,
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
        error : str
            error message if the request is invalid.
        """
        from ..models import Instrument, Photometry, DBSession

        error = None

        start_jd = Time(request.payload["start_date"], format='iso').jd
        end_jd = Time(request.payload["end_date"], format='iso').jd

        target = {
            'jdstart': start_jd,
            'jdend': end_jd,
            'ra': None,
            'dec': None,
        }

        ra, dec = None, None
        position = request.payload.get("position", "Source (object's coordinates)")
        if "Flux weighted centroid" in position:
            # here we query the database to get the all the photometry rows for the object that:
            # 1. belong to an instrument with data stream(s)
            # 2. have a non-null flux value
            # 3. have a non-null flux error value
            # 4. have coordinates (ra and dec)
            # 5. do not have "fp" in the origin column
            # 6. have abs(snr) = abs(flux/fluxerr) > 3
            with DBSession() as session:
                photometry = (
                    session.scalars(
                        sa.select(Photometry).where(
                            sa.and_(
                                Photometry.obj_id == request.obj.id,
                                ~Photometry.origin.ilike('%fp%'),
                            )
                        )
                    )
                ).all()
                additional_constraints = []
                if "alert photometry only" in position:
                    additional_constraints.append(lambda p: p and len(p.streams) > 0)
                if "ZTF alert photometry only" in position:
                    # grab the id of the ZTF instrument (one of ZTF or CFH12k)
                    ztf_instrument_id = session.scalar(
                        sa.select(Instrument.id).where(
                            sa.or_(
                                Instrument.name == "ZTF",
                                Instrument.name == "CFH12k",
                            )
                        )
                    )
                    if ztf_instrument_id is not None:
                        additional_constraints.append(
                            lambda p: p and p.instrument_id == ztf_instrument_id
                        )
                    else:
                        error = "Could not find the ZTF instrument in the database."
                        return target, error
                photometry = [
                    (p.ra, p.dec, p.flux, p.fluxerr)
                    for p in photometry
                    if not np.isnan(p.flux)
                    and not np.isnan(p.fluxerr)
                    and not np.isnan(p.ra)
                    and not np.isnan(p.dec)
                    and len(p.streams) > 0
                    and all(constraint(p) for constraint in additional_constraints)
                ]
                if len(photometry) > 0:
                    # calculate the weighted centroid based on the object's photometry
                    ras, decs, flux, fluxerr = np.array(photometry).T
                    snr = np.abs(flux / fluxerr)

                    # only keep the ras, decs, flux, and fluxerr where the snr is above 3
                    snr_cut_indices = np.where(snr > 3)
                    if len(snr_cut_indices[0]) == 0:
                        error = "No photometry found that meets the criteria for flux weighted centroid calculation (all snr < 3)."
                        return target, error

                    ras, decs, flux, fluxerr, snr = (
                        ras[snr_cut_indices],
                        decs[snr_cut_indices],
                        flux[snr_cut_indices],
                        fluxerr[snr_cut_indices],
                        snr[snr_cut_indices],
                    )
                    ra, dec = np.sum(ras * snr) / np.sum(snr), np.sum(
                        decs * snr
                    ) / np.sum(snr)

                    if np.isnan(ra) or np.isnan(dec):
                        error = "Could not compute the flux weighted centroid for the object."
                        return target, error
                else:
                    error = "No photometry found that meets the criteria for flux weighted centroid calculation."
                    return target, error

        elif "Source (object's coordinates)" in position:
            ra, dec = request.obj.ra, request.obj.dec
        else:
            error = "Unknown position type."
            return target, error

        target['ra'] = ra
        target['dec'] = dec

        return target, error

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


def commit_photometry(
    url,
    altdata,
    request_id,
    instrument_id,
    user_id,
    parent_session=None,
    duplicates="error",
):
    """
    Commits ZTF forced photometry to the database

    Parameters
    ----------
    url : str
        ZTF forced photometry service data file location.
    altdata: dict
        Contains ZTF photometry api_token for the user
    request_id : int
        FollowupRequest SkyPortal ID
    instrument_id : int
        Instrument SkyPortal ID
    user_id : int
        User SkyPortal ID
    parent_session : sqlalchemy.orm.session.Session
        SQLAlchemy session object. If None, a new session is created.
    """

    from ..models import (
        DBSession,
        FollowupRequest,
        Instrument,
    )

    if parent_session is None:
        Session = scoped_session(sessionmaker())
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    try:
        request = session.query(FollowupRequest).get(request_id)
        instrument = session.query(Instrument).get(instrument_id)
        allocation = request.allocation
        if not allocation:
            raise ValueError("Missing request's allocation information.")

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
            'procstatus',
        }
        if not desired_columns.issubset(set(df.columns)):
            raise ValueError('Missing expected column')

        # filter on the procstatus, only keeping data where procstatus = 0
        valid_index = [
            i for i, x in enumerate(df['procstatus']) if str(x).strip() == '0'
        ]
        df = df.iloc[valid_index]
        df.drop(columns=['procstatus'], inplace=True)

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

        snr = df['forcediffimflux'] / df['forcediffimfluxunc'] < 3
        df.loc[snr, 'mag'] = None
        df.loc[snr, 'magerr'] = None

        iszero = df['forcediffimfluxunc'] == 0.0
        df.loc[iszero, 'mag'] = None
        df.loc[iszero, 'magerr'] = None

        isnan = np.isnan(df['forcediffimflux'])
        df.loc[isnan, 'mag'] = None
        df.loc[isnan, 'magerr'] = None

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
        df['origin'] = 'fp'

        # data is visible to the group attached to the allocation
        # as well as to any of the allocation's default share groups
        data_out = {
            'obj_id': request.obj_id,
            'instrument_id': instrument.id,
            'group_ids': list(
                set(
                    [allocation.group_id]
                    + (
                        allocation.default_share_group_ids
                        if allocation.default_share_group_ids
                        else []
                    )
                )
            ),
            **df.to_dict(orient='list'),
        }

        from skyportal.handlers.api.photometry import add_external_photometry

        if len(df.index) > 0:
            ids, _ = add_external_photometry(
                data_out, request.requester, duplicates=duplicates, refresh=True
            )
            if ids is None:
                raise ValueError('Failed to commit photometry')
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
        session.rollback()
        raise Exception(f"Unable to commit photometry for {request_id}: {e}")
    finally:
        if parent_session is None:
            session.close()
            Session.remove()


class ZTFAPI(FollowUpAPI):

    """An interface to ZTF operations."""

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a follow-up request from ZTF queue.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import (
            FollowupRequest,
            FacilityTransaction,
            FacilityTransactionRequest,
        )

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        # this happens for failed submissions
        # just go ahead and delete
        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        elif request.payload["request_type"] == "triggered":
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
            session.add(transaction)
        elif request.payload["request_type"] == "forced_photometry":
            transaction = (
                session.query(FacilityTransactionRequest)
                .filter(FacilityTransactionRequest.followup_request_id == request.id)
                .first()
            )
            if transaction is not None:
                if transaction.status == "complete":
                    raise ValueError('Request already complete. Cannot delete.')
                session.delete(transaction)
            session.delete(request)
            session.commit()
            log(f"Deleted request {request.id} from ZTF queue.")
        else:
            raise ValueError('Unknown request type.')

        if kwargs.get('refresh_source', False):
            flow = Flow()
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_internal_key},
            )
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to ZTF.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FacilityTransactionRequest

        req = ZTFRequest()

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        if request.payload["request_type"] == "triggered":
            requestgroup = req._build_triggered_payload(request, session)
            url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        elif request.payload["request_type"] == "forced_photometry":
            requestgroup, error = req._build_forced_payload(request)
            if error:
                raise ValueError(error)
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

            if request.payload["request_type"] == "forced_photometry":
                params = urllib.parse.urlencode(
                    {
                        "email": altdata["ipac_email"],
                        "userpass": altdata["ipac_userpass"],
                        "option": "All recent jobs",
                        "action": "Query Database",
                    }
                )
                url = (
                    f"{ZTF_FORCED_URL}/cgi-bin/getForcedPhotometryRequests.cgi?{params}"
                )

                request_body = {
                    'method': 'GET',
                    'endpoint': url,
                    'data': requestgroup,
                    'followup_request_id': request.id,
                    'initiator_id': request.last_modified_by_id,
                }
                try:
                    req = FacilityTransactionRequest(**request_body)
                except ValidationError as e:
                    raise ValidationError(
                        'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                    )

                session.add(req)
                session.commit()

                facility_microservice_url = (
                    f'http://127.0.0.1:{cfg["ports.facility_queue"]}'
                )
                requests.post(
                    facility_microservice_url,
                    json={
                        'request_id': req.id,
                        'followup_request_id': req.followup_request_id,
                    },
                )

        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)

        if kwargs.get('refresh_source', False):
            flow = Flow()
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': request.obj.internal_key},
            )
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    # split the form above (that has triggered, and forced_photometry) into two forms
    form_json_schema = {
        "type": "object",
        "properties": {
            "request_type": {
                "type": "string",
                "enum": ["triggered"],
                "default": "triggered",
            },
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
            "queue_name": {
                "type": "string",
                "default": datetime.utcnow(),
            },
        },
        "required": [
            "start_date",
            "end_date",
        ],
    }

    form_json_schema_forced_photometry = {
        "type": "object",
        "properties": {
            "request_type": {
                "type": "string",
                "enum": ["forced_photometry"],
                "default": "forced_photometry",
            },
            "position": {
                "type": "string",
                "enum": [
                    "Source (object's coordinates)",
                    "Flux weighted centroid",
                    "Flux weighted centroid (alert photometry only)",
                    "Flux weighted centroid (ZTF alert photometry only)",
                ],
                "default": "Source (object's coordinates)",
            },
            "start_date": {
                "type": "string",
                "default": str(datetime.utcnow() - timedelta(days=30)).replace("T", ""),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": str(datetime.utcnow()).replace("T", ""),
            },
        },
        "required": [
            "start_date",
            "end_date",
        ],
    }

    # use the ui schema to hide the request type
    ui_json_schema = {
        "request_type": {"ui:widget": "hidden"},
    }


class ZTFMMAAPI(MMAAPI):

    """An interface to ZTF MMA operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def send(request, session):
        """Submit an EventObservationPlan to ZTF.

        Parameters
        ----------
        request : skyportal.models.ObservationPlanRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction

        req = ZTFRequest()
        requestgroup = req._build_observation_plan_payload(request)

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        if 'access_token' not in altdata:
            raise ValueError('Missing access token in allocation information.')

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

        session.add(transaction)

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
    def queued(allocation, start_date=None, end_date=None, queues_only=False):
        """Retrieve queued observations by ZTF.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation with queue information.
        start_date : datetime.datetime
            Minimum time for observation request
        end_date : datetime.datetime
            Maximum time for observation request
        queues_only : bool
            Return only queues (do not commit observations to database)
        """

        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        s = Session()
        ztfreq = Request('GET', url, headers=headers, json={})
        prepped = ztfreq.prepare()
        r = s.send(prepped)

        if r.status_code == 200:
            df = pd.DataFrame(r.json()['data'])
            queue_names = sorted(list(set(df['queue_name'])))

            if not queues_only:
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
    def remove_queue(allocation, queue_name, username):
        """Remove a queue from ZTF.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation with queue information.
        queue_name : str
            Remove a queue from ZTF
        username: str
            Username for the removal
        """
        from ..models import DBSession, ObservationPlanRequest

        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        headers = {"Authorization": f"Bearer {altdata['access_token']}"}
        payload = {'queue_name': queue_name, 'user': username}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztf')
        s = Session()
        ztfreq = Request('DELETE', url, json=payload, headers=headers)
        prepped = ztfreq.prepare()

        r = s.send(prepped)
        if not r.status_code == 200:
            return ValueError(f'Error deleting queue: {r.text}')

        # check if there is an observation plan request associated with this queue (same queue name)
        # if so, mark it as removed from queue
        try:
            with DBSession() as session:
                observation_plan_request = session.scalar(
                    session.query(ObservationPlanRequest).filter(
                        ObservationPlanRequest.payload['queue_name'] == queue_name,
                        ObservationPlanRequest.allocation_id == allocation.id,
                    )
                )
                if (
                    observation_plan_request
                    and observation_plan_request.status
                    == 'submitted to telescope queue'
                ):
                    observation_plan_request.status = 'deleted from telescope queue'
                    session.commit()

                    flow = Flow()
                    flow.push(
                        '*',
                        "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
                        payload={
                            "gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs
                        },
                    )
        except Exception as e:
            log(
                f'Error marking observation plan request (with same queue name) status as deleted from queue: {e}'
            )

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
        s.auth = (altdata['depot_username'], altdata['depot_password'])

        fetch_obs = functools.partial(
            fetch_depot_observations,
            allocation.instrument.id,
            s,
            altdata['depot'],
            jd_start,
            jd_end,
        )

        IOLoop.current().run_in_executor(None, fetch_obs)

    @staticmethod
    def send_skymap(allocation, payload):
        """Submit skymap queue to ZTF.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation with queue information.
        payload : object
            Skymap queue information to submit to instrument
        """

        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztfmma')

        s = Session()
        ztfreq = Request('PUT', url, json=payload, headers=headers)
        prepped = ztfreq.prepare()
        r = s.send(prepped)

        if r.status_code != 200:
            raise ValueError(f'rejected from skymap queue: {r.content}')

    @staticmethod
    def queued_skymap(allocation):
        """Get all the skymap-based triggers name."""

        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztfmma')

        s = Session()
        ztfreq = Request('GET', url, headers=headers, json={})
        prepped = ztfreq.prepare()
        r = s.send(prepped)

        if r.status_code == 200:
            return [d['trigger_name'] for d in r.json()['data']]
        else:
            raise ValueError(f'Error querying for queued skymaps: {r.text}')

    @staticmethod
    def remove_skymap(allocation, trigger_name, username=None):
        """Delete a skymap trigger by trigger_name."""
        altdata = allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        if trigger_name is None:
            raise ValueError('Missing trigger name.')

        if username is None:
            raise ValueError('Missing user information.')

        headers = {"Authorization": f"Bearer {altdata['access_token']}"}

        url = urllib.parse.urljoin(ZTF_URL, 'api/triggers/ztfmma')

        payload = {'trigger_name': trigger_name, 'user': username}

        s = Session()
        ztfreq = Request('DELETE', url, json=payload, headers=headers)
        prepped = ztfreq.prepare()
        r = s.send(prepped)

        if r.status_code != 200:
            raise ValueError(f'Error deleting skymap: {r.text}')

    def custom_json_schema(instrument, user, **kwargs):
        form_json_schema = MMAAPI.custom_json_schema(instrument, user, **kwargs)

        # we make sure that all the boolean properties come last, which helps with the display
        non_boolean_properties = {
            k: v
            for k, v in form_json_schema["properties"].items()
            if v["type"] != "boolean"
        }
        boolean_properties = {
            k: v
            for k, v in form_json_schema["properties"].items()
            if v["type"] == "boolean"
        }

        form_json_schema["properties"] = {
            **non_boolean_properties,
            "program_id": {
                "type": "string",
                "enum": ["Partnership", "Caltech"],
                "default": "Partnership",
            },
            "subprogram_name": {
                "type": "string",
                "enum": ["GW", "GRB", "Neutrino", "SolarSystem", "Other"],
                "default": "GW",
            },
            "filters": {"type": "string", "default": "ztfg,ztfr,ztfg"},
            "use_primary": {
                "title": "Use primary grid only?",
                "type": "boolean",
                "default": True,
            },
            "use_secondary": {
                "title": "Use secondary grid only?",
                "type": "boolean",
                "default": False,
            },
            **boolean_properties,
        }

        form_json_schema["required"] = form_json_schema["required"] + [
            "subprogram_name",
            "program_id",
        ]

        return form_json_schema


def fetch_depot_observations(instrument_id, session, depot_url, jd_start, jd_end):
    """Fetch executed observations from a TAP client.
    instrument_id : int
        ID of the instrument
    session : request.Session()
        An authenticated request session.
    depot_url : str
        URL of the depot server
    jd_start : float
        JD of the start time of observations
    jd_end : float
        JD of the end time of observations
    """

    dfs = []

    jds = np.arange(np.floor(jd_start), np.ceil(jd_end))
    for jd in jds:
        date = Time(jd, format='jd').datetime.strftime("%Y%m%d")
        url = f'{depot_url}/{date}/ztf_recentproc_{date}.json'
        r = session.head(url)

        # file exists
        if r.status_code == 200:
            r = session.get(url)
            obstable = pd.DataFrame(r.json())

            if obstable.empty:
                log(f'No observations for instrument ID {instrument_id} for JD: {jd}')
                continue
            # only want successfully reduced images
            obstable = obstable[obstable['status'] == 0]

            obs_grouped_by_exp = obstable.groupby('exposure_id')
            for expid, df_group in obs_grouped_by_exp:
                df_group_median = df_group.median()
                df_group_median['observation_id'] = int(expid)
                df_group_median['processed_fraction'] = len(df_group["field_id"]) / 64.0
                df_group_median['filter'] = inv_bands[int(df_group_median["filter_id"])]
                dfs.append(df_group_median)

    if len(dfs) > 0:
        obstable = pd.concat(dfs, axis=1).T
        obstable.rename(
            columns={
                'obsjd': 'obstime',
                'maglim': 'limmag',
                'fwhm': 'seeing',  # equivalent as plate scale is 1"/pixel
            },
            inplace=True,
        )
        obstable['target_name'] = None

        from skyportal.handlers.api.observation import add_observations

        add_observations(instrument_id, obstable)


def fetch_tap_observations(instrument_id, client, request_str):
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
    if obstable.empty:
        log(
            f'No observations for instrument ID {instrument_id} for request: {request_str}'
        )
        return

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
    obstable['target_name'] = None

    # engineering data is ipac_gid = -1 and we do not want to save that
    obstable = obstable[obstable['ipac_gid'] >= 1.0]

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
