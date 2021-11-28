__all__ = ['LightcurveFit']

import enum

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from baselayer.app.models import Base


class LightcurveFit(Base):
    """A record of an astronomical light curve fit and its metadata,
    such as best fit, parameter distribution, and Bayes factors."""

    object_id = sa.Column(
        sa.String, primary_key=True, nullable=False, doc="Name of object being fit"
    )

    model_name = sa.Column(
        sa.String, primary_key=True, nullable=False, doc="Model name"
    )

    bestfit_lightcurve = sa.Column(
        JSONB,
        nullable=True,
        doc="best fit light curve information.",
    )

    posterior_samples = sa.Column(
        JSONB,
        nullable=True,
        doc="posterior distributions.",
    )

    log_bayes_factor = sa.Column(
        sa.Float, nullable=True, comment="log(Bayes) factor for the run"
    )

    class Status(enum.IntEnum):
        WORKING = 0
        READY = 1

    status = sa.Column(
        sa.Enum(Status), default=Status.WORKING, nullable=False, comment="Plan status"
    )
