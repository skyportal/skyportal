__all__ = [
    'GcnNotice',
    'GcnTag',
    'GcnEvent',
    'GcnProperty',
    'GcnPublication',
    'GcnSummary',
    'GcnTrigger',
    'DefaultGcnTag',
]

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.orm import deferred
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

import gcn
import lxml

from baselayer.app.models import (
    Base,
    DBSession,
    AccessibleIfUserMatches,
    CustomUserAccessControl,
    UserAccessControl,
    safe_aliased,
    join_model,
    restricted,
)
from .group import accessible_by_group_members
from .allocation import Allocation, AllocationUser

SOURCE_RADIUS_THRESHOLD = 5 / 60.0  # 5 arcmin in degrees


def gcn_update_delete_logic(cls, user_or_token):
    """This function generates the query for GCN-related tables
    that the current user can update or delete. If the querying user
    doesn't have System admin or Manage GCNs acl, then no GCN tags are
    accessible to that user under this policy .
    """

    if len({'Manage GCNs', 'System admin'} & set(user_or_token.permissions)) == 0:
        # nothing accessible
        return restricted.query_accessible_rows(cls, user_or_token)

    return DBSession().query(cls)


class DefaultGcnTag(Base):
    """A default set of criteria to apply a GcnTag."""

    __tablename__ = 'default_gcntags'

    # TODO: Make read-accessible via target groups
    update = delete = AccessibleIfUserMatches('requester')

    requester_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc="ID of the User who requested the default gcn tag.",
    )

    requester = relationship(
        "User",
        back_populates='default_gcntags',
        doc="The User who requested the default gcn tag.",
        foreign_keys=[requester_id],
    )

    filters = sa.Column(
        JSONB,
        doc="Filters to determine which of the default gcn tags get executed for which events",
    )

    default_tag_name = sa.Column(
        sa.String, unique=True, nullable=False, doc='Default tag name'
    )


class GcnPublication(Base):
    """Store GCN publication for events."""

    create = read = accessible_by_group_members

    update = delete = AccessibleIfUserMatches('sent_by') | CustomUserAccessControl(
        gcn_update_delete_logic
    )

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnPublication.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="gcnpublications",
        doc="The user that saved this GcnPublication",
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # have a relationship to a group
    group_id = sa.Column(
        sa.ForeignKey('groups.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the Group that this GcnPublication is associated with.",
    )

    group = relationship(
        "Group",
        foreign_keys=group_id,
        back_populates="gcnpublications",
        doc="The group that this GcnPublication is associated with.",
    )

    data = deferred(sa.Column(JSONB, nullable=False, doc="Publication data in JSON."))

    publication_name = sa.Column(sa.String, nullable=False)

    publish = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc='Whether GcnPublication should be published',
    )


class GcnSummary(Base):
    """Store GCN summary text for events."""

    create = read = accessible_by_group_members

    update = delete = AccessibleIfUserMatches('sent_by') | CustomUserAccessControl(
        gcn_update_delete_logic
    )

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnSummary.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="gcnsummaries",
        doc="The user that saved this GcnSummary",
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # have a relationship to a group
    group_id = sa.Column(
        sa.ForeignKey('groups.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the Group that this GcnSummary is associated with.",
    )

    group = relationship(
        "Group",
        foreign_keys=group_id,
        back_populates="gcnsummaries",
        doc="The group that this GcnSummary is associated with.",
    )

    title = sa.Column(sa.String, nullable=False)

    text = deferred(sa.Column(sa.Unicode, nullable=False))


class GcnNotice(Base):
    """Records of ingested GCN notices"""

    update = delete = AccessibleIfUserMatches('sent_by') | CustomUserAccessControl(
        gcn_update_delete_logic
    )

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

    has_localization = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='true',
        doc='Whether event notice has localization',
    )

    localization_ingested = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc='Whether localization has been ingested',
    )


class GcnProperty(Base):
    """Store properties for events."""

    update = delete = AccessibleIfUserMatches('sent_by') | CustomUserAccessControl(
        gcn_update_delete_logic
    )

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnProperty.",
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

    data = sa.Column(JSONB, doc="Event properties in JSON format.", index=True)


class GcnTag(Base):
    """Store qualitative tags for events."""

    update = delete = AccessibleIfUserMatches('sent_by') | CustomUserAccessControl(
        gcn_update_delete_logic
    )

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

    text = sa.Column(sa.Unicode, nullable=False, index=True)


class GcnEvent(Base):
    """Event information, including an event ID, mission, and time of the event."""

    update = delete = AccessibleIfUserMatches('sent_by') | CustomUserAccessControl(
        gcn_update_delete_logic
    )

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

    publications = relationship(
        'GcnPublication',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="GcnPublication.created_at",
        doc="Publications associated with this GCN event.",
    )

    summaries = relationship(
        'GcnSummary',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="GcnSummary.created_at",
        doc="Summaries associated with this GCN event.",
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

    aliases = sa.Column(
        sa.ARRAY(sa.String),
        nullable=False,
        server_default='{}',
        doc="List of different names for this event, parsed from different GCN notices.",
    )

    tach_id = sa.Column(
        sa.String,
        nullable=True,
        doc="TACH id associated with a GCN event",
    )

    circulars = deferred(
        sa.Column(
            JSONB,
            nullable=False,
            server_default='{}',
            doc="List of circulars associated with a GCN event. Keys are circulars ids, values are circular titles.",
        )
    )

    gracedb_log = deferred(
        sa.Column(
            JSONB,
            nullable=False,
            server_default='{}',
            doc="List of GraceDB logs associated with a GW event.",
        )
    )

    gracedb_labels = deferred(
        sa.Column(
            JSONB,
            nullable=False,
            server_default='{}',
            doc="List of GraceDB labels associated with a GW event.",
        )
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

    gcn_triggers = relationship(
        "GcnTrigger",
        back_populates="gcnevent",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="GCN triggers that contributed this event.",
    )

    @hybrid_property
    def tags(self):
        """List of tags."""
        return [tag.text for tag in set(self._tags)]

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


def gcntrigger_allocationuser_access_logic(cls, user_or_token):
    aliased = safe_aliased(cls)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    user_allocation_admin = (
        DBSession()
        .query(Allocation)
        .join(AllocationUser, AllocationUser.allocation_id == Allocation.id)
        .filter(sa.and_(AllocationUser.user_id == user_id))
    )
    query = (
        DBSession().query(cls).join(aliased, cls.allocation_id == aliased.allocation_id)
    )
    if not user_or_token.is_system_admin:
        query = query.filter(
            aliased.allocation_id.in_(
                [allocation.id for allocation in user_allocation_admin.all()]
            )
        )
    return query


GcnTrigger = join_model(
    'gcntriggers',
    GcnEvent,
    Allocation,
    "dateobs",
    "allocation_id",
    "dateobs",
    "id",
    new_name='GcnTrigger',
)

GcnTrigger.triggered = sa.Column(
    sa.Boolean,
    nullable=False,
    default=False,
    doc="Whether this GCN event triggered the allocation.",
)

GcnTrigger.create = GcnTrigger.update = GcnTrigger.delete = CustomUserAccessControl(
    gcntrigger_allocationuser_access_logic
)
