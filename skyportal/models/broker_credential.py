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
    """One user's own credentials for a broker: a broker is admin-owned, but an
    upstream account is personal (a Lasair filter can be private to the account
    that owns it)."""

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
        "filters. Not secret, so stored outside altdata.",
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

    def as_credential_set(self):
        """This row in the shape the ingestion loop consumes: identity and routing
        only, the connection details stay with the broker."""
        altdata = self.altdata
        kafka = {
            key: altdata[key] for key in ("username", "password") if altdata.get(key)
        }
        return {
            "label": f"user{self.user_id}",
            "token": altdata.get("token"),
            "kafka": kafka,
            "topics": self.topics or [],
            "topic_filter_ids": self.topic_filter_ids or {},
        }
