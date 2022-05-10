import astropy
import requests
import numpy as np
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop

from . import FollowUpAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http

env, cfg = load_env()

PS1_URL = cfg['app.ps1_endpoint']

log = make_log('facility_apis/ps1')


def commit_photometry(text_response, request_id, instrument_id, user_id):
    """
    Commits PS1 DR2 photometry to the database

    Parameters
    ----------
    text_response : dict
        response.text from call to PS1 DR2 photometry service.
    request_id : int
        FollowupRequest SkyPortal ID
    instrument_id : int
        Instrument SkyPortal ID
    user_id: int
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

        tab = astropy.io.ascii.read(text_response)
        # good data only
        tab = tab[tab['psfQfPerfect'] > 0.9]
        id2filter = np.array(['ps1::g', 'ps1::r', 'ps1::i', 'ps1::z', 'ps1::y'])
        tab['filter'] = id2filter[(tab['filterID'] - 1).data.astype(int)]
        df = tab.to_pandas()

        df.rename(
            columns={
                'obsTime': 'mjd',
                'psfFlux': 'flux',
                'psfFluxerr': 'fluxerr',
            },
            inplace=True,
        )
        df = df.replace({np.nan: None})

        df.drop(
            columns=[
                'detectID',
                'filterID',
                'psfQfPerfect',
            ],
            inplace=True,
        )
        df['magsys'] = 'ab'
        df['zp'] = 8.90

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


class PS1API(FollowUpAPI):

    """An interface to PS1 forced photometry."""

    @staticmethod
    def get(request):

        """Get a forced photometry request result from PS1.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
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

        with Session() as session:
            req = (
                session.query(FollowupRequest)
                .filter(FollowupRequest.id == request.id)
                .one()
            )

            if req.status == "Photometry committed to database":
                raise ValueError('Photometry already in database')

            instrument = (
                Instrument.query_records_accessible_by(request.requester)
                .join(Allocation)
                .join(FollowupRequest)
                .filter(FollowupRequest.id == request.id)
                .first()
            )

            content = req.transactions[0].response["content"]
            tab = astropy.io.ascii.read(content)
            objid = tab['objID'][0]

            params = {
                'objID': objid,
                'columns': [
                    'detectID',
                    'filterID',
                    'obsTime',
                    'ra',
                    'dec',
                    'psfFlux',
                    'psfFluxerr',
                    'psfQfPerfect',
                ],
            }

            url = f"{PS1_URL}/api/v0.1/panstarrs/dr2/detections.csv"
            try:
                r = requests.get(url, params=params, timeout=5.0)  # timeout in seconds
            except TimeoutError:
                req.status = 'error: timeout'

            if r.status_code == 200:
                try:
                    text_response = r.text
                except Exception:
                    raise ValueError('No text data returned in request')

                IOLoop.current().run_in_executor(
                    None,
                    lambda: commit_photometry(
                        text_response, req.id, instrument.id, request.requester.id
                    ),
                )
                req.status = "Committing photometry to database"
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

        """Submit a photometry request to PS1 DR2 API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        params = {
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'radius': request.payload["radius"] / 3600.0,
            'nDetections.gt': request.payload["min_detections"],
            'columns': [
                'objID',
                'raMean',
                'decMean',
                'nDetections',
                'gMeanPSFMag',
                'rMeanPSFMag',
                'iMeanPSFMag',
                'zMeanPSFMag',
                'yMeanPSFMag',
            ],
        }

        url = f"{PS1_URL}/api/v0.1/panstarrs/dr2/mean.csv"
        r = requests.get(url, params=params)
        if r.status_code == 200:
            tab = astropy.io.ascii.read(r.text)

            if len(tab) == 0:
                request.status = 'No DR2 source'
            else:
                request.status = 'Source available'
        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)
        DBSession().commit()

    @staticmethod
    def delete(request):

        """Delete a photometry request from PS1 DR2 API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, FollowupRequest

        DBSession().query(FollowupRequest).filter(
            FollowupRequest.id == request.id
        ).delete()
        DBSession().commit()

    form_json_schema = {
        "type": "object",
        "properties": {
            "radius": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.0,
                "maximum": 50.0,
                "title": "Query Radius [arcsec]",
            },
            "min_detections": {
                "type": "number",
                "default": 1.0,
                "minimum": 1.0,
                "maximum": 100.0,
                "title": "Minimum Number of Detections",
            },
        },
        "required": [
            "radius",
            "min_detections",
        ],
    }

    ui_json_schema = {}
