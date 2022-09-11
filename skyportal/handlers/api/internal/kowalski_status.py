from penquins import Kowalski

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log
from ...base import BaseHandler

env, cfg = load_env()
log = make_log("kowalski_status")


class KowalskiStatusHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Determine whether kowalski and/or gloria are available
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            kowalski:
                              type: boolean
                              description: Boolean indicating whether kowalski connection is active
                            gloria:
                              type: string
                              description: Boolean indicating whether gloria connection is active
        """

        kowalski = None
        if cfg.get('app.kowalski.enabled', False):
            try:
                kowalski = Kowalski(
                    token=cfg["app.kowalski.token"],
                    protocol=cfg["app.kowalski.protocol"],
                    host=cfg["app.kowalski.host"],
                    port=int(cfg["app.kowalski.port"]),
                    timeout=10,
                )
                connection_ok = kowalski.ping()
                log(f"Kowalski connection OK: {connection_ok}")
                if not connection_ok:
                    kowalski = None
            except Exception as e:
                log(f"Kowalski connection failed: {str(e)}")
                kowalski = None

        gloria = None
        if cfg.get('app.gloria.enabled', False):
            # A (dedicated) Kowalski instance holding the ZTF light curve data referred to as Gloria
            try:
                gloria = Kowalski(
                    token=cfg["app.gloria.token"],
                    protocol=cfg["app.gloria.protocol"],
                    host=cfg["app.gloria.host"],
                    port=int(cfg["app.gloria.port"]),
                    timeout=10,
                )
                connection_ok = gloria.ping()
                log(f"Gloria connection OK: {connection_ok}")
                if not connection_ok:
                    gloria = None
            except Exception as e:
                log(f"Gloria connection failed: {str(e)}")

        status = {}
        if kowalski is None:
            status['kowalski'] = False
        else:
            status['kowalski'] = True

        if gloria is None:
            status['gloria'] = False
        else:
            status['gloria'] = True

        return self.success(data=status)
