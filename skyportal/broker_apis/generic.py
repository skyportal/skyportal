import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/generic")

DEFAULT_TIMEOUT = 30  # seconds


def _request(broker, path, params=None):
    """Issue a GET against the broker's REST endpoint using ``broker.altdata``.

    ``altdata`` must provide ``base_url`` and may provide ``token`` (sent as a
    Bearer header). Returns the parsed JSON ``data`` (or the raw body).
    """
    altdata = broker.altdata or {}
    base_url = altdata.get("base_url")
    if not base_url:
        raise ValueError("Broker altdata is missing 'base_url'.")

    headers = {}
    token = altdata.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    response = requests.get(
        url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT
    )
    response.raise_for_status()
    payload = response.json()
    # unwrap a {"data": ...} envelope if the endpoint uses one
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class GENERICBROKER(BrokerAPI):
    """A configurable REST broker.

    Talks to any broker exposing a simple REST API:
      - ``GET {base_url}/alerts``            -> list/search alerts
      - ``GET {base_url}/alerts/{alert_id}`` -> a single alert

    This is the reference provider and gives REST-style brokers (e.g. Lasair)
    an integration with no bespoke code — just a configured ``Broker`` row.
    """

    surveys = []

    form_json_schema_config = {
        "type": "object",
        "required": ["base_url"],
        "properties": {
            "base_url": {
                "type": "string",
                "title": "Base URL of the broker's REST API",
            },
            "token": {
                "type": "string",
                "title": "Bearer token (optional)",
            },
        },
    }

    ui_json_schema = {"token": {"ui:widget": "password"}}

    @staticmethod
    def validate_config(altdata):
        if not (altdata or {}).get("base_url"):
            raise ValueError("Broker altdata must include 'base_url'.")

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        return _request(broker, "alerts", params=kwargs)

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        return _request(broker, f"alerts/{alert_id}", params=kwargs)
