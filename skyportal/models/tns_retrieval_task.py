__all__ = ["TNSRetrievalTask"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from baselayer.app.models import Base


class TNSRetrievalTask(Base):
    """Work item for the tns_retrieval_queue service.

    Producers (the HTTP receiver and the periodic TNS watcher) insert rows
    with status='pending'. The consumer claims one at a time via
    FOR UPDATE SKIP LOCKED so multiple replicas of the service can split work.
    Backs the queue that used to live in memory in the tns_retrieval_queue
    service; replaces a process-local Python list that lost items on crash and
    didn't survive multi-replica deploys.
    """

    obj_id = sa.Column(
        sa.String(),
        nullable=True,
        index=True,
        doc="ID of an existing Obj to look up on TNS, if applicable.",
    )

    tns_source = sa.Column(
        sa.String(),
        nullable=True,
        index=True,
        doc="TNS source ID (without prefix) to retrieve, if applicable.",
    )

    tns_prefix = sa.Column(
        sa.String(),
        nullable=True,
        doc="TNS prefix (AT, SN, etc.) when known at submission time.",
    )

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Submitter, used to send back error notifications.",
    )

    radius = sa.Column(
        sa.Float(),
        nullable=True,
        doc="Search radius in degrees for obj_id-based lookups.",
    )

    status = sa.Column(
        sa.Enum(
            "pending",
            "processing",
            "done",
            "failed",
            "skipped",
            name="tns_retrieval_task_status",
        ),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
        doc="Lifecycle state for the consumer's claim/process pipeline.",
    )

    error = sa.Column(
        sa.Text(),
        nullable=True,
        doc="Failure message captured by the consumer when status='failed'.",
    )

    payload = sa.Column(
        JSONB,
        nullable=True,
        doc="Original request body, retained for debugging / audit.",
    )
