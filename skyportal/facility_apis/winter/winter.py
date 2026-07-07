from baselayer.log import make_log

from .. import FollowUpAPI
from .winter_utils import (
    build_form_json_schema,
    delete_request,
    form_json_schema_altdata,
    prepare_payload,
    submit_request,
    ui_json_schema,
)

log = make_log("facility_apis/winter")

# WINTER camera defaults
FILTER_DEFAULTS = {
    "Y": {
        "n_dither": 8,
        "exposure_time": 960 / 8,  # 8 dithers for 960s total = 120s
    },
    "J": {
        "n_dither": 8,
        "exposure_time": 960 / 8,  # 8 dithers for 960s total = 120s
    },
    "Hs": {
        "n_dither": 15,
        "exposure_time": 900 / 15,  # 15 dithers for 900s total = 60s
    },
    "dark": {
        "n_dither": 5,
        "exposure_time": 600 / 5,  # 5 dithers for 600s total = 120s
    },
}

CAMERA = "winter"


class WINTERAPI(FollowUpAPI):
    """An interface to WINTER operations."""

    @staticmethod
    def prepare_payload(payload, existing_payload=None):
        """Prepare a payload for submission to WINTER.

        Parameters
        ----------
        payload : dict
            The payload to prepare for submission to WINTER.
        existing_payload : dict, optional
            The existing payload, if any, to update with the new payload.

        Returns
        -------
        dict
            The prepared payload.
        """
        payload["camera"] = CAMERA
        return prepare_payload(payload, FILTER_DEFAULTS, existing_payload)

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
        delete_request(request, session, **kwargs)

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
        submit_request(request, session, CAMERA, log, **kwargs)

    form_json_schema = build_form_json_schema(FILTER_DEFAULTS)

    form_json_schema_altdata = form_json_schema_altdata

    ui_json_schema = ui_json_schema
