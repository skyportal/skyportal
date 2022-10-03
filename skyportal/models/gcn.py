__all__ = ['GcnNotice', 'GcnTag', 'GcnEvent', 'GcnProperty']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.orm import deferred
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

import gcn
import lxml

from baselayer.app.models import Base, DBSession, AccessibleIfUserMatches


class GcnNotice(Base):
    """Records of ingested GCN notices"""

    update = delete = AccessibleIfUserMatches('sent_by')

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnNotice.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="gcnnotices",
        doc="The user that saved this GcnNotice",
    )

    ivorn = sa.Column(
        sa.String, unique=True, index=True, doc='Unique identifier of VOEvent'
    )

    notice_type = sa.Column(
        sa.Enum(gcn.NoticeType),
        nullable=False,
        doc='GCN Notice type',
    )

    stream = sa.Column(
        sa.String, nullable=False, doc='Event stream or mission (i.e., "Fermi")'
    )

    date = sa.Column(sa.DateTime, nullable=False, doc='UTC message timestamp')

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        doc='UTC event timestamp',
    )

    content = deferred(
        sa.Column(sa.LargeBinary, nullable=False, doc='Raw VOEvent content')
    )


class GcnProperty(Base):
    """Store properties for events."""

    update = delete = AccessibleIfUserMatches('sent_by')

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnTag.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="gcnproperties",
        doc="The user that saved this GcnProperty",
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    data = sa.Column(JSONB, doc="Event properties in JSON format.")


class GcnTag(Base):
    """Store qualitative tags for events."""

    update = delete = AccessibleIfUserMatches('sent_by')

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnTag.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="gcntags",
        doc="The user that saved this GcnTag",
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    text = sa.Column(sa.Unicode, nullable=False)


class GcnEvent(Base):
    """Event information, including an event ID, mission, and time of the event."""

    update = delete = AccessibleIfUserMatches('sent_by')

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnEvent.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="gcnevents",
        doc="The user that saved this GcnEvent",
    )

    dateobs = sa.Column(sa.DateTime, doc='Event time', unique=True, nullable=False)

    trigger_id = sa.Column(
        sa.BigInteger, unique=True, doc='Trigger ID supplied by instrument'
    )

    gcn_notices = relationship("GcnNotice", order_by=GcnNotice.date)

    properties = relationship(
        'GcnProperty',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="GcnProperty.created_at",
        doc="Properties associated with this GCN event.",
    )

    _tags = relationship(
        "GcnTag",
        order_by=(
            sa.func.lower(GcnTag.text).notin_({'fermi', 'swift', 'amon', 'lvc'}),
            sa.func.lower(GcnTag.text).notin_({'long', 'short'}),
            sa.func.lower(GcnTag.text).notin_({'grb', 'gw', 'transient'}),
        ),
    )

    localizations = relationship("Localization")

    observationplan_requests = relationship(
        'ObservationPlanRequest',
        back_populates='gcnevent',
        cascade='delete',
        passive_deletes=True,
        doc="Observation plan requests of the event.",
    )

    survey_efficiency_analyses = relationship(
        'SurveyEfficiencyForObservations',
        back_populates='gcnevent',
        cascade='delete',
        passive_deletes=True,
        doc="Survey efficiency analyses of the event.",
    )

    comments = relationship(
        'CommentOnGCN',
        back_populates='gcn',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="CommentOnGCN.created_at",
        doc="Comments posted about this GCN event.",
    )

    reminders = relationship(
        'ReminderOnGCN',
        back_populates='gcn',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="ReminderOnGCN.created_at",
        doc="Reminders about this GCN event.",
    )

    detectors = relationship(
        "MMADetector",
        secondary="gcnevents_mmadetectors",
        back_populates="events",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="MMA Detectors that contributed this event.",
    )

    @hybrid_property
    def tags(self):
        """List of tags."""
        return [tag.text for tag in self._tags]

    @tags.expression
    def tags(cls):
        """List of tags."""
        return (
            DBSession()
            .query(GcnTag.text)
            .filter(GcnTag.dateobs == cls.dateobs)
            .subquery()
        )

    @hybrid_property
    def retracted(self):
        """Check if event is retracted."""
        return 'retracted' in self.tags

    @retracted.expression
    def retracted(cls):
        """Check if event is retracted."""
        return sa.literal('retracted').in_(cls.tags)

    @property
    def lightcurve(self):
        """GRB lightcurve URL."""
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='LightCurve_URL']")
        if elem is None:
            return None
        else:
            try:
                return elem.attrib.get('value', '').replace('http://', 'https://')
            except Exception:
                return None

    @property
    def gracesa(self):
        """Event page URL."""
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='EventPage']")
        if elem is None:
            return None
        else:
            try:
                return elem.attrib.get('value', '')
            except Exception:
                return None

    @property
    def graceid(self):
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='GraceID']")
        if elem is None:
            return None
        else:
            return elem.attrib.get('value', '')

    @property
    def ned_gwf(self):
        """NED URL."""
        return "https://ned.ipac.caltech.edu/gwf/events"

    @property
    def HasNS(self):
        """Checking if GW event contains NS."""
        notice = self.gcn_notices[0]
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='HasNS']")
        if elem is None:
            return None
        else:
            try:
                return 'HasNS: ' + elem.attrib.get('value', '')
            except Exception:
                return None

    @property
    def HasRemnant(self):
        """Checking if GW event has remnant matter."""
        notice = self.gcn_notices[0]
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='HasRemnant']")
        if elem is None:
            return None
        else:
            try:
                return 'HasRemnant: ' + elem.attrib.get('value', '')
            except Exception:
                return None

    @property
    def FAR(self):
        """Returning event false alarm rate."""
        notice = self.gcn_notices[0]
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='FAR']")
        if elem is None:
            return None
        else:
            try:
                return 'FAR: ' + elem.attrib.get('value', '')
            except Exception:
                return None
