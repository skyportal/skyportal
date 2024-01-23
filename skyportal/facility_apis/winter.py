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

from . import FollowUpAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http

env, cfg = load_env()


WINTER_URL = f"{cfg['app.winter.protocol']}://{cfg['app.winter.host']}"
if cfg['app.winter.port'] is not None and int(cfg['app.winter.port']) not in [80, 443]:
    WINTER_URL += f":{cfg['app.winter.port']}"

log = make_log('facility_apis/winter')


class WINTERRequest:

    """A dictionary structure for WINTER ToO requests."""

    def _build_payload(self, request):
        """Payload json for WINTER object queue requests.

        Parameters
        ----------

        request : skyportal.models.FollowupRequest
            The request to add to the WINTER TOO queue and the SkyPortal database.

        Returns
        ----------
        payload : json
            payload for requests.
        """

        # here an example of what a WINTER payload should look like
        filters = [request.payload["filter"]]
        target_priority = int(request.payload["priority"])
        t_exp = int(request.payload["exposure_time"])
        n_exp = int(request.payload["exposure_counts"])
        n_dither = int(request.payload["n_dither"])
        dither_distance = float(request.payload["dither_distance"])
        start_time_mjd = Time(request.payload["start_date"], format='iso').mjd
        end_time_mjd = Time(request.payload["end_date"], format='iso').mjd
        max_airmass = float(request.payload["max_airmass"])

        target = {
                "ra_deg": request.obj.ra,
                "dec_deg": request.obj.dec,
                "use_field_grid": False,
                "filters": filters,
                "target_priority": target_priority,
                "t_exp": t_exp,
                "n_exp": n_exp,
                "n_dither": n_dither,
                "dither_distance": dither_distance,
                "start_time_mjd": start_time_mjd,
                "end_time_mjd": end_time_mjd,
                "max_airmass": max_airmass,
            }

        return target

class WINTERAPI(FollowUpAPI):

    """An interface to WINTER operations."""

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a follow-up request from WINTER queue.

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
        else:
            raise NotImplementedError("WINTER API submit not implemented yet.")

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
        """Submit a follow-up request to WINTER.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FacilityTransactionRequest

        req = WINTERRequest()

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        payload = req._build_payload(request, session)
        url = urllib.parse.urljoin(WINTER_URL, 'too/winter')
        # from the system config, grab the api_key
        # from the allocation altdata, get the program_api_key and program_name
        # and set submit_trigger to True ALWAYS

        # the WINTER API is using fast api, so check what the auth looks like
        raise NotImplementedError("WINTER API submit not implemented yet.")

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
            "filter": {
                "type": "string",
                "title": "Filter",
                "default": "Y",
                "enum": ["Y", "J", "Hs", "dark"],
            },
            "priority": {
                "type": "integer",
                "title": "Priority",
                "default": 50,
                "minimum": 0,
                "maximum": 1000,
            },
            "exposure_time": {
                "type": "integer",
                "title": "Exposure Time (s)",
                "default": 30,
                "minimum": 1,
                "maximum": 300,
            },
            "exposure_counts": {
                "type": "integer",
                "title": "Number of Exposures",
                "default": 1,
                "minimum": 1,
                "maximum": 100,
            },
            "n_dither": {
                "type": "integer",
                "title": "Number of Dithers",
                "minimum": 1,
                "maximum": 100,
            },
            "dither_distance": {
                "type": "number",
                "title": "Dither Distance (arcsec)",
                "default": 600,
                "minimum": 0,
                "maximum": 1000,
            },
            "advanced": {
                "type": "boolean",
                "title": "Show Advanced Options",
                "default": False,
            },
        },
        "dependencies": {
            "advanced": {
                "oneOf": [
                    {
                        "properties": {
                            "advanced": {"enum": [True]},
                            "maximum_airmass": {
                                "type": "number",
                                "title": "Maximum Airmass",
                                "default": 2.0,
                                "minimum": 1.0,
                                "maximum": 10.0,
                            },
                        }
                    }
                ]
            },
            # we want to change the default n_dither value depending on the filter chosen
            # for Y: 8, J: TOFIGURE OUT USE 4 FOR NOW, Hs: 15, dark: 5
            "filter": {
                "oneOf": [
                    {
                        "properties": {
                            "filter": {"enum": ["Y"]},
                            "n_dither": {"default": 1},
                        }
                    },
                    {
                        "properties": {
                            "filter": {"enum": ["J"]},
                            "n_dither": {"default": 4},
                        }
                    },
                    {
                        "properties": {
                            "filter": {"enum": ["Hs"]},
                            "n_dither": {"default": 15},
                        }
                    },
                    {
                        "properties": {
                            "filter": {"enum": ["dark"]},
                            "n_dither": {"default": 5},
                        }
                    },
                ]
            },

        },
        "required": [
            "start_date",
            "end_date",
            "filter",
            "priority",
            "exposure_time",
            "exposure_counts",
            "n_dither",
            "dither_distance",
        ],
    }

    ui_json_schema = {}

