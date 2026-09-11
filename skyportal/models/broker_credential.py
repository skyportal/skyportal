__all__ = ["BrokerCredential"]

import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy_utils.types import JSONType
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    AesEngine,
    StringEncryptedType,
)

from baselayer.app.env import load_env
from baselayer.app.models import AccessibleIfUserMatches, Base

_, cfg = load_env()


class BrokerCredential(Base):
    """One user's own credentials for a broker.

    A broker is shared infrastructure and only system admins configure it, but
    an upstream account is personal: a Lasair filter can be private to the
    account that owns it, visible neither to the broker's shared account nor to
    any other user. Storing those credentials here rather than in
    ``Broker.altdata`` keeps them out of a blob that admins read and edit, and
    the API redacts secrets by dotted dict path, so a list of accounts inside
    ``altdata`` could not be redacted at all.
    """

    # A credential belongs to the user who created it, and to nobody else.
    create = read = update = delete = AccessibleIfUserMatches("user")

    broker_id = sa.Column(
        sa.ForeignKey("brokers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The broker these credentials authenticate against.",
    )

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The user the credentials belong to.",
    )

    topics = sa.Column(
        JSONB,
        nullable=False,
        server_default="[]",
        doc="Stream topics this account can read, e.g. the user's private Lasair "
        "filters. Not secret, so stored alongside rather than in altdata.",
    )

    topic_filter_ids = sa.Column(
        JSONB,
        nullable=False,
        server_default="{}",
        doc="Maps a topic to the skyportal Filter ids its objects become "
        "candidates for, mirroring the broker-level routing.",
    )

    _altdata = sa.Column(
        StringEncryptedType(JSONType, cfg["app.secret_key"], AesEngine, "pkcs5"),
        doc="The credentials themselves: the upstream API token and any stream "
        "username/password. Never serialized back to a client.",
    )

    broker = relationship("Broker", doc="The broker these credentials are for.")
    user = relationship("User", doc="The owner of these credentials.")

    __table_args__ = (sa.UniqueConstraint("broker_id", "user_id"),)

    @property
    def altdata(self):
        if self._altdata is None:
            return {}
        if isinstance(self._altdata, dict):
            return self._altdata
        return json.loads(self._altdata)

    @altdata.setter
    def altdata(self, value):
        self._altdata = json.dumps(value) if value is not None else None

    def as_credential_set(self, label=None):
        """This row in the shape the ingestion loop consumes.

        The connection details stay with the broker; only identity and routing
        are personal.
        """
        altdata = self.altdata
        # Stored flat, as the provider's credential form declares them; the
        # stream fields are grouped here for the consumer config.
        kafka = {
            key: altdata[key] for key in ("username", "password") if altdata.get(key)
        }
        return {
            "label": label or f"user{self.user_id}",
            "token": altdata.get("token"),
            "kafka": kafka,
            "topics": self.topics or [],
            "topic_filter_ids": self.topic_filter_ids or {},
        }
