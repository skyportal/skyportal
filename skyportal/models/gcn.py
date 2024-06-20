__all__ = [
    'GcnNotice',
    'GcnTag',
    'GcnEvent',
    'GcnProperty',
    'GcnReport',
    'GcnSummary',
    'GcnTrigger',
    'DefaultGcnTag',
]
import io
import json
import random

import astropy.units as u
import jinja2
from ligo.skymap import plot  # noqa: F401 F811
from ligo.skymap import postprocess
import lxml
import matplotlib
import matplotlib.pyplot as plt
from mocpy import MOC
import numpy as np
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import deferred, relationship

from baselayer.app.env import load_env
from baselayer.app.json_util import to_json
from baselayer.app.models import (
    AccessibleIfUserMatches,
    Base,
    CustomUserAccessControl,
    DBSession,
    UserAccessControl,
    join_model,
    restricted,
    safe_aliased,
)

from ..utils.cache import Cache, dict_to_bytes
from .allocation import Allocation, AllocationUser
from .group import accessible_by_group_members
from .localization import Localization

env, cfg = load_env()

host = f'{cfg["server.protocol"]}://{cfg["server.host"]}' + (
    f':{cfg["server.port"]}' if cfg['server.port'] not in [80, 443] else ''
)

cache_dir = "cache/public_pages/reports"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_reports_cache"] * 60,
)

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


class GcnReport(Base):
    """Store GCN report for events."""

    create = read = accessible_by_group_members

    update = delete = AccessibleIfUserMatches('sent_by') | CustomUserAccessControl(
        gcn_update_delete_logic
    )

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnReport.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="gcnreports",
        doc="The user that saved this GcnReport",
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
        doc="The ID of the Group that this GcnReport is associated with.",
    )

    group = relationship(
        "Group",
        foreign_keys=group_id,
        back_populates="gcnreports",
        doc="The group that this GcnReport is associated with.",
    )

    data = deferred(sa.Column(JSONB, nullable=False, doc="Report data in JSON."))

    report_name = sa.Column(sa.String, nullable=False)

    published = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc='Whether GcnReport should be published',
    )

    def get_plot(self, figsize=(10, 5), output_format='png'):
        """GcnReport plot.
        Parameters
        ----------
        figsize : tuple, optional
            Matplotlib figsize of the plot created
        output_format : str
            Figure extension, either png or pdf.
        """

        # cache_key = f"gcn_{self.id}"
        data = self.data
        if isinstance(data, str):
            data = json.loads(data)

        localization_name = None
        if "event" in data:
            localization_name = data["event"].get("localization_name", None)

        if localization_name is None:
            localization = (
                DBSession()
                .query(Localization)
                .where(Localization.dateobs == self.dateobs)
                .first()
            )
        else:
            localization = (
                DBSession()
                .query(Localization)
                .where(Localization.dateobs == self.dateobs)
                .where(Localization.localization_name == localization_name)
                .first()
            )

        center = postprocess.posterior_max(localization.flat_2d)

        matplotlib.use("Agg")
        fig = plt.figure(figsize=figsize, constrained_layout=False)
        ax = plt.axes(projection='astro globe', center=center)
        ax.grid()
        ax.imshow_hpx(localization.flat_2d, cmap='cylon')

        if "observations" in data and len(data["observations"]) > 0:
            surveyColors = {
                "ztfg": "#28A745",
                "ztfr": "#DC3545",
                "ztfi": "#F3DC11",
                "AllWISE": "#2F5492",
                "Gaia_DR3": "#FF7F0E",
                "PS1_DR1": "#3BBED5",
                "GALEX": "#6607C2",
                "TNS": "#ED6CF6",
            }

            observations = data["observations"]
            filters = list({obs["filt"] for obs in observations})
            for filt in filters:
                if filt in surveyColors:
                    continue
                surveyColors[filt] = "#" + ''.join(
                    [random.choice('0123456789ABCDEF') for i in range(6)]
                )

            for i, obs in enumerate(observations):
                field_coordinates = np.array(obs["field_coordinates"])
                coords = np.squeeze(field_coordinates)
                ra, dec = coords[:, 0], coords[:, 1]
                moc = MOC.from_polygon(ra * u.deg, dec * u.deg, max_depth=10)

                moc.fill(
                    ax=ax,
                    wcs=ax.wcs,
                    alpha=0.1,
                    fill=True,
                    color=surveyColors.get(filt, "black"),
                    linewidth=1,
                )
                moc.border(ax=ax, wcs=ax.wcs, alpha=1, color="black")

        if "sources" in data and len(data["sources"]) > 0:
            for source in data["sources"]:
                ax.scatter(
                    source['ra'],
                    source['dec'],
                    transform=ax.get_transform('world'),
                    color='w',
                    zorder=2,
                    s=30,
                )
                ax.text(
                    source['ra'] + 5.5,
                    source['dec'] + 5.5,
                    source['id'],
                    transform=ax.get_transform('world'),
                    color='k',
                    fontsize=8,
                    zorder=3,
                )

        buf = io.BytesIO()
        fig.savefig(buf, format=output_format)
        plt.close(fig)
        buf.seek(0)

        return buf.read()

    def get_html(self):
        """Get the HTML content of the GCN report."""
        data = self.data
        if isinstance(data, str):
            data = json.loads(data)

        # Create the filters mapper
        if data.get("sources"):
            from skyportal.handlers.api.photometry import get_bandpasses_to_colors

            for source in data["sources"]:
                filters = {
                    photometry["filter"] for photometry in source.get("photometry", [])
                }
                source["filters_mapper"] = get_bandpasses_to_colors(filters)

        env = jinja2.Environment(
            autoescape=True,
            loader=jinja2.FileSystemLoader("./static/public_pages/reports/report"),
        )
        env.policies['json.dumps_function'] = to_json

        template = env.get_template("gcn_report_template.html")
        html = template.render(
            host=host,
            dateobs=str(self.dateobs).replace(" ", "T"),
            report_id=self.id,
            report_name=self.report_name,
            program=self.group.name,
            data=data,
        )
        return html

    def generate_report(self):
        """Generate the GCN report and cache it."""
        data = self.data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {"status": "error", "message": "Invalid JSON data."}
        if data.get("status") == "error":
            raise ValueError(data.get("message", "Invalid JSON data."))
        elif data.get("status") == "pending":
            raise ValueError("Report is still being generated.")
        cache_key = f"gcn_{self.id}"
        pub_html = self.get_html()
        pub_plot = self.get_plot()
        cache[cache_key] = dict_to_bytes(
            {"published": True, "html": pub_html, "plot": pub_plot}
        )

    def publish(self):
        """Publish GcnReport."""
        self.generate_report()
        self.published = True

    def unpublish(self):
        """Unpublish GcnReport."""
        self.published = False
        # TODO: delete the html from cache
        cache_key = f"gcn_{self.id}"
        cached = cache[cache_key]
        if cached is not None:
            data = np.load(cached, allow_pickle=True)
            data = data.item()
            cache[cache_key] = dict_to_bytes(
                {"published": False, "html": data["html"], "plot": data["plot"]}
            )
        else:
            cache[cache_key] = dict_to_bytes(
                {"published": False, "html": None, "plot": None}
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
        sa.String,
        nullable=True,
        doc='GCN Notice type',
    )

    notice_format = sa.Column(
        sa.String,
        nullable=True,
        doc="Notice format (voevent, json, dictionary)",
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
        sa.String, unique=True, doc='Trigger ID supplied by instrument'
    )

    gcn_notices = relationship("GcnNotice", order_by=GcnNotice.date)

    properties = relationship(
        'GcnProperty',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="GcnProperty.created_at",
        doc="Properties associated with this GCN event.",
    )

    reports = relationship(
        'GcnReport',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="GcnReport.created_at",
        doc="Reports associated with this GCN event.",
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
        if notice.notice_format == 'json':
            return None
        try:
            root = lxml.etree.fromstring(notice.content)
            elem = root.find(".//Param[@name='LightCurve_URL']")
        except lxml.etree.XMLSyntaxError:
            return None

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
        if notice.notice_format == 'json':
            return None
        try:
            root = lxml.etree.fromstring(notice.content)
            elem = root.find(".//Param[@name='EventPage']")
        except lxml.etree.XMLSyntaxError:
            return None

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
        if notice.notice_format == 'json':
            return None
        try:
            root = lxml.etree.fromstring(notice.content)
            elem = root.find(".//Param[@name='GraceID']")
        except lxml.etree.XMLSyntaxError:
            return None

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
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        if notice.notice_format == 'json':
            return None
        try:
            root = lxml.etree.fromstring(notice.content)
            elem = root.find(".//Param[@name='HasNS']")
        except lxml.etree.XMLSyntaxError:
            return None

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
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        if notice.notice_format == 'json':
            return None
        try:
            root = lxml.etree.fromstring(notice.content)
            elem = root.find(".//Param[@name='HasRemnant']")
        except lxml.etree.XMLSyntaxError:
            return None

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
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        if notice.notice_format == 'json':
            return None
        try:
            root = lxml.etree.fromstring(notice.content)
            elem = root.find(".//Param[@name='FAR']")
        except lxml.etree.XMLSyntaxError:
            return None

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
