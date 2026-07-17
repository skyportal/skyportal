__all__ = ["Broker"]

import json

import sqlalchemy as sa
from sqlalchemy_utils.types import JSONType
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    AesEngine,
    StringEncryptedType,
)

from baselayer.app.env import load_env
from baselayer.app.models import Base, restricted

from .. import broker_apis
from ..enum_types import broker_classnames

_, cfg = load_env()


class Broker(Base):
    """A configured connection to an external alert broker (e.g. BOOM,
    Kowalski, Fink, Lasair).

    The provider logic lives in a registered ``skyportal.broker_apis.BrokerAPI``
    subclass named by ``broker_classname``; this row supplies the per-instance
    credentials/endpoints (encrypted in ``altdata``) it operates on.
    """

    # brokers carry credentials, so only system admins may manage them.
    create = update = delete = restricted

    name = sa.Column(
        sa.String, unique=True, nullable=False, doc="Unique name of the broker."
    )

    broker_classname = sa.Column(
        broker_classnames,
        nullable=False,
        doc="Name of the registered BrokerAPI provider class.",
    )

    active = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="true",
        doc="Whether this broker is enabled.",
    )

    _altdata = sa.Column(
        StringEncryptedType(JSONType, cfg["app.secret_key"], AesEngine, "pkcs5"),
        doc="Encrypted per-instance configuration (endpoints, credentials).",
    )

    @property
    def altdata(self):
        if self._altdata is None:
            return {}
        # the encrypted column round-trips a string; older/other writers may
        # have stored a dict directly.
        if isinstance(self._altdata, dict):
            return self._altdata
        return json.loads(self._altdata)

    @altdata.setter
    def altdata(self, value):
        # store as a JSON string so the getter can decode it (mirrors how the
        # allocation handler json.dumps() its altdata before assignment).
        self._altdata = json.dumps(value) if value is not None else None

    @property
    def broker_class(self):
        """The registered BrokerAPI provider class for this broker."""
        return getattr(broker_apis, self.broker_classname)
