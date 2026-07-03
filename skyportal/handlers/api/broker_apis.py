from baselayer.app.access import auth_or_token
from skyportal import broker_apis
from skyportal.enum_types import broker_classnames

from ..base import BaseHandler

apis = {
    broker_name: getattr(broker_apis, broker_name).frontend_render_api_info()
    for broker_name in broker_classnames.enums
}


class BrokerAPIsHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: List registered broker providers
        description: Return the capabilities and config schema of every
          registered BrokerAPI provider class.
        tags:
          - brokers
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        return self.success(data=apis)
