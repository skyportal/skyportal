import astropy
import numpy as np
import requests
from sqlalchemy.orm import scoped_session, sessionmaker
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from ..utils.calculations import great_circle_distance
from . import FollowUpAPI

env, cfg = load_env()

PS1_URL = cfg["app.ps1_endpoint"]

log = make_log("facility_apis/ps1")


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
    user_id : int
        User SkyPortal ID
    """

    from ..models import DBSession, FollowupRequest, Instrument

    Session = scoped_session(sessionmaker())
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        request = session.query(FollowupRequest).get(request_id)
        instrument = session.query(Instrument).get(instrument_id)
        allocation = request.allocation
        if not allocation:
            raise ValueError("Missing request's allocation information.")

        tab = astropy.io.ascii.read(text_response)
        # good data only
        tab = tab[tab["psfQfPerfect"] > 0.9]
        id2filter = np.array(["ps1::g", "ps1::r", "ps1::i", "ps1::z", "ps1::y"])
        tab["filter"] = id2filter[(tab["filterID"] - 1).data.astype(int)]
        df = tab.to_pandas()

        df.rename(
            columns={
                "obsTime": "mjd",
                "psfFlux": "flux",
                "psfFluxerr": "fluxerr",
            },
            inplace=True,
        )
        df = df.replace({np.nan: None})

        df.drop(
            columns=[
                "detectID",
                "filterID",
                "psfQfPerfect",
            ],
            inplace=True,
        )
        df["magsys"] = "ab"
        df["zp"] = 8.90

        # data is visible to the group attached to the allocation
        # as well as to any of the allocation's default share groups
        data_out = {
            "obj_id": request.obj_id,
            "instrument_id": instrument.id,
            "group_ids": list(
                set(
                    [allocation.group_id]
                    + (
                        allocation.default_share_group_ids
                        if allocation.default_share_group_ids
                        else []
                    )
                )
            ),
            **df.to_dict(orient="list"),
        }

        from skyportal.handlers.api.photometry import add_external_photometry

        if len(df.index) > 0:
            ids, _ = add_external_photometry(
                data_out, request.requester, duplicates="update", refresh=True
            )
            if ids is None:
                raise ValueError("Failed to commit photometry")
            request.status = "Photometry committed to database"
        else:
            request.status = "No photometry to commit to database"

        session.add(request)
        session.commit()

        flow = Flow()
        flow.push(
            "*",
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": request.obj.internal_key},
        )

    except Exception as e:
        session.rollback()
        log(f"Unable to commit photometry for {request_id}: {e}")
    finally:
        session.close()
        Session.remove()


class PS1API(FollowUpAPI):
    """An interface to PS1 forced photometry."""

    @staticmethod
    def get(request, session, **kwargs):
        """Get a forced photometry request result from PS1.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session : baselayer.DBSession
            Database session to use for photometry
        """

        from ..models import (
            Allocation,
            FacilityTransaction,
            FollowupRequest,
            Instrument,
        )

        if request.status == "Photometry committed to database":
            raise ValueError("Photometry already in database")

        instrument = (
            Instrument.query_records_accessible_by(request.requester)
            .join(Allocation)
            .join(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .first()
        )

        content = request.transactions[0].response["content"]
        tab = astropy.io.ascii.read(content)

        ra, dec = request.obj.ra, request.obj.dec
        closest_row_index, closest_row_distance = 0, 1e10
        for i in range(len(tab)):
            row = tab[i]
            dist = great_circle_distance(ra, dec, row["raMean"], row["decMean"])
            if dist < closest_row_distance:
                closest_row_index, closest_row_distance = i, dist

        objid = tab["objID"][closest_row_index]

        params = {
            "objID": objid,
            "columns": [
                "detectID",
                "filterID",
                "obsTime",
                "ra",
                "dec",
                "psfFlux",
                "psfFluxerr",
                "psfQfPerfect",
            ],
        }

        url = f"{PS1_URL}/api/v0.1/panstarrs/dr2/detection.csv"
        try:
            r = requests.get(url, params=params, timeout=5.0)  # timeout in seconds
        except TimeoutError:
            request.status = "error: timeout"

        if r.status_code == 200:
            try:
                text_response = r.text
            except Exception:
                raise ValueError("No text data returned in request")

            IOLoop.current().run_in_executor(
                None,
                lambda: commit_photometry(
                    text_response, request.id, instrument.id, request.requester.id
                ),
            )
            request.status = "Committing photometry to database"
        else:
            request.status = f"error: {r.content}"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)
        session.commit()

        if kwargs.get("refresh_source", False):
            flow = Flow()
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": request.obj.internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a photometry request to PS1 DR2 API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        params = {
            "ra": request.obj.ra,
            "dec": request.obj.dec,
            "radius": request.payload["radius"] / 3600.0,
            "nDetections.gt": request.payload["min_detections"],
            "columns": [
                "objID",
                "raMean",
                "decMean",
                "nDetections",
                "gMeanPSFMag",
                "rMeanPSFMag",
                "iMeanPSFMag",
                "zMeanPSFMag",
                "yMeanPSFMag",
            ],
        }

        url = f"{PS1_URL}/api/v0.1/panstarrs/dr2/mean.csv"
        r = requests.get(url, params=params)
        if r.status_code == 200:
            try:
                if len(r.text) == 0:
                    raise ValueError("No data returned in request")
                tab = astropy.io.ascii.read(r.text)
                if len(tab) == 0:
                    raise ValueError("No data returned in request")
                request.status = "submitted"
            except Exception as e:
                log(str(e))
                request.status = "No DR2 source"
        else:
            request.status = f"rejected: {r.content}"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)

        if kwargs.get("refresh_source", False):
            flow = Flow()
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": request.obj.internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a photometry request from PS1 DR2 API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        if request.status.lower() != "photometry committed to database":
            if len(request.transactions) == 0:
                session.query(FollowupRequest).filter(
                    FollowupRequest.id == request.id
                ).delete()
                session.commit()
            else:
                request.status = "deleted"
                session.add(request)
        else:
            raise ValueError(
                "Can't delete PS1 requests which photometry has been committed to the database."
            )

        if kwargs.get("refresh_source", False):
            flow = Flow()
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

    form_json_schema_forced_photometry = {
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
