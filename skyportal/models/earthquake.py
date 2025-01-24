__all__ = [
    "EarthquakeEvent",
    "EarthquakeMeasured",
    "EarthquakeNotice",
    "EarthquakePrediction",
]

import sqlalchemy as sa
from sqlalchemy.orm import deferred, relationship
from sqlalchemy_utils import URLType

from baselayer.app.env import load_env
from baselayer.app.models import (
    AccessibleIfUserMatches,
    Base,
)

_, cfg = load_env()


class EarthquakeNotice(Base):
    """Earthquake notice information"""

    update = delete = AccessibleIfUserMatches("sent_by")

    sent_by_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who created this EarthquakeEvent.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="earthquakenotices",
        doc="The user that saved this EarthquakeEvent",
    )

    content = deferred(
        sa.Column(sa.LargeBinary, nullable=True, doc="Raw QuakeML content")
    )

    event_id = sa.Column(
        sa.String,
        sa.ForeignKey("earthquakeevents.event_id", ondelete="CASCADE"),
        nullable=False,
        comment="Earthquake ID",
    )

    lat = sa.Column(sa.Float, nullable=False, comment="Latitude")

    lon = sa.Column(sa.Float, nullable=False, comment="Longitude")

    depth = sa.Column(
        sa.Float,
        nullable=False,
        comment="Depth relative to sea level (positive values as depth increases) [m]",
    )

    magnitude = sa.Column(
        sa.Float, nullable=False, comment="Earthquake (Moment) Magnitude", index=True
    )

    date = sa.Column(
        sa.DateTime, nullable=False, comment="UTC event timestamp", index=True
    )

    country = sa.Column(sa.String, nullable=True, comment="Country")


class EarthquakePrediction(Base):
    """Earthquake prediction information"""

    event_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("earthquakeevents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Earthquake ID",
    )

    detector_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("mmadetectors.id", ondelete="CASCADE"),
        nullable=False,
        comment="Multimessenger Astronomical Detector id",
    )

    d = sa.Column(sa.Float, nullable=False, comment="Distance [km]")

    p = sa.Column(sa.DateTime, nullable=False, comment="P-wave time")

    s = sa.Column(sa.DateTime, nullable=False, comment="S-wave time")

    r2p0 = sa.Column(sa.DateTime, nullable=False, comment="R-2.0 km/s-wave time")

    r3p5 = sa.Column(sa.DateTime, nullable=False, comment="R-3.5 km/s-wave time")

    r5p0 = sa.Column(sa.DateTime, nullable=False, comment="R-5.0 km/s-wave time")

    rfamp = sa.Column(
        sa.Float, nullable=False, comment="Earthquake amplitude predictions [m/s]"
    )

    lockloss = sa.Column(
        sa.Float,
        nullable=False,
        comment="Earthquake lockloss prediction, between 0 (no lockloss) and 1 (lockloss)",
    )


class EarthquakeMeasured(Base):
    """Earthquake measured information"""

    event_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("earthquakeevents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Earthquake ID",
    )

    detector_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("mmadetectors.id", ondelete="CASCADE"),
        nullable=False,
        comment="Multimessenger Astronomical Detector id",
    )

    rfamp = sa.Column(
        sa.Float, nullable=True, comment="Earthquake amplitude measured [m/s]"
    )

    lockloss = sa.Column(
        sa.INT,
        nullable=True,
        comment="Earthquake lockloss measured, should be 0 (no lockloss) or 1 (lockloss)",
    )


class EarthquakeEvent(Base):
    """Earthquake information"""

    update = delete = AccessibleIfUserMatches("sent_by")

    sent_by_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnTag.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="earthquakeevents",
        doc="The user that saved this EarthquakeEvent",
    )

    event_id = sa.Column(
        sa.String, unique=True, nullable=False, comment="Earthquake ID"
    )

    event_uri = sa.Column(URLType, nullable=True, comment="Earthquake URI")

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="initial",
        index=True,
        doc="The status of the earthquake event.",
    )

    notices = relationship(
        "EarthquakeNotice",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by=EarthquakeNotice.created_at,
        doc="Notices associated with this Earthquake event.",
    )

    predictions = relationship(
        "EarthquakePrediction",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by=EarthquakePrediction.created_at,
        doc="Notices associated with this Earthquake event.",
    )

    measurements = relationship(
        "EarthquakeMeasured",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by=EarthquakeMeasured.created_at,
        doc="Notices associated with this Earthquake event.",
    )

    comments = relationship(
        "CommentOnEarthquake",
        back_populates="earthquake",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by="CommentOnEarthquake.created_at",
        doc="Comments posted about this Earthquake event.",
    )

    reminders = relationship(
        "ReminderOnEarthquake",
        back_populates="earthquake",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by="ReminderOnEarthquake.created_at",
        doc="Reminders about this Earthquake event.",
    )
