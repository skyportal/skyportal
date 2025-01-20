from .acls import ACLHandler, UserACLHandler
from .allocation import (
    AllocationHandler,
    AllocationObservationPlanHandler,
    AllocationReportHandler,
)
from .analysis import (
    AnalysisHandler,
    AnalysisProductsHandler,
    AnalysisServiceHandler,
    AnalysisUploadOnlyHandler,
    DefaultAnalysisHandler,
)
from .annotation import AnnotationHandler
from .annotation_services import (
    DatalabQueryHandler,
    GaiaQueryHandler,
    IRSAQueryWISEHandler,
    PS1QueryHandler,
    VizierQueryHandler,
)
from .candidate import CandidateFilterHandler, CandidateHandler
from .catalog_services import (
    CatalogQueryHandler,
    GaiaPhotometricAlertsQueryHandler,
    SwiftLSXPSQueryHandler,
)
from .classification import (
    ClassificationHandler,
    ClassificationVotesHandler,
    ObjClassificationHandler,
    ObjClassificationQueryHandler,
)
from .color_mag import ObjColorMagHandler
from .comment import CommentAttachmentHandler, CommentHandler
from .comment_attachment import CommentAttachmentUpdateHandler
from .config_handler import ConfigHandler
from .db_stats import StatsHandler
from .earthquake import (
    EarthquakeHandler,
    EarthquakeMeasurementHandler,
    EarthquakePredictionHandler,
    EarthquakeStatusHandler,
)
from .enum_types import EnumTypesHandler
from .facility_listener import FacilityMessageHandler
from .filter import FilterHandler
from .followup_request import (
    AssignmentHandler,
    DefaultFollowupRequestHandler,
    FollowupRequestCommentHandler,
    FollowupRequestHandler,
    FollowupRequestPrioritizationHandler,
    FollowupRequestSchedulerHandler,
    FollowupRequestWatcherHandler,
)
from .galaxy import (
    GalaxyASCIIFileHandler,
    GalaxyCatalogHandler,
    GalaxyGladeHandler,
    ObjHostHandler,
)
from .gcn import (
    DefaultGcnTagHandler,
    GcnEventAliasesHandler,
    GcnEventCatalogQueryHandler,
    GcnEventHandler,
    GcnEventInstrumentFieldHandler,
    GcnEventNoticeDownloadHandler,
    GcnEventObservationPlanRequestsHandler,
    GcnEventPropertiesHandler,
    GcnEventSurveyEfficiencyHandler,
    GcnEventTagsHandler,
    GcnEventTriggerHandler,
    GcnEventUserHandler,
    GcnReportHandler,
    GcnSummaryHandler,
    LocalizationCrossmatchHandler,
    LocalizationDownloadHandler,
    LocalizationHandler,
    LocalizationNoticeHandler,
    LocalizationPropertiesHandler,
    LocalizationTagsHandler,
    ObjGcnEventHandler,
)
from .gcn_gracedb import GcnGraceDBHandler
from .gcn_tach import GcnTachHandler
from .group import (
    GroupHandler,
    GroupStreamHandler,
    GroupUserHandler,
    GroupUsersFromOtherGroupsHandler,
    ObjGroupsHandler,
)
from .group_admission_request import GroupAdmissionRequestHandler
from .healpix import HealpixUpdateHandler
from .instrument import InstrumentFieldHandler, InstrumentHandler
from .instrument_log import (
    InstrumentLogExternalAPIHandler,
    InstrumentLogHandler,
    InstrumentStatusHandler,
)
from .invalid import InvalidEndpointHandler
from .invitations import InvitationHandler
from .mmadetector import (
    MMADetectorHandler,
    MMADetectorSpectrumHandler,
    MMADetectorTimeIntervalHandler,
)
from .mpc import ObjMPCHandler
from .news_feed import NewsFeedHandler
from .obj import ObjHandler, ObjPositionHandler
from .observation import (
    ObservationASCIIFileHandler,
    ObservationExternalAPIHandler,
    ObservationHandler,
    ObservationSimSurveyHandler,
    ObservationSimSurveyPlotHandler,
    ObservationTreasureMapHandler,
)
from .observation_plan import (
    DefaultObservationPlanRequestHandler,
    ObservationPlanAirmassChartHandler,
    ObservationPlanCreateObservingRunHandler,
    ObservationPlanFieldsHandler,
    ObservationPlanGCNHandler,
    ObservationPlanGeoJSONHandler,
    ObservationPlanManualRequestHandler,
    ObservationPlanMovieHandler,
    ObservationPlanNameHandler,
    ObservationPlanObservabilityPlotHandler,
    ObservationPlanRequestHandler,
    ObservationPlanSimSurveyHandler,
    ObservationPlanSimSurveyPlotHandler,
    ObservationPlanSubmitHandler,
    ObservationPlanSurveyEfficiencyHandler,
    ObservationPlanTreasureMapHandler,
    ObservationPlanWorldmapPlotHandler,
)
from .observingrun import ObservingRunBulkEditHandler, ObservingRunHandler
from .phot_stat import PhotStatHandler, PhotStatUpdateHandler
from .photometric_series import PhotometricSeriesHandler
from .photometry import (
    BulkDeletePhotometryHandler,
    ObjPhotometryHandler,
    PhotometryHandler,
    PhotometryOriginHandler,
    PhotometryRangeHandler,
)
from .photometry_request import PhotometryRequestHandler
from .photometry_validation import PhotometryValidationHandler
from .public_group import PublicGroupHandler
from .public_pages.public_release import PublicReleaseHandler

# Public pages
from .public_pages.public_source_page import PublicSourcePageHandler
from .recurring_api import RecurringAPIHandler
from .reminder import ReminderHandler
from .roles import RoleHandler, UserRoleHandler
from .sharing import SharingHandler
from .shift import ShiftHandler, ShiftSummary, ShiftUserHandler
from .skymap_trigger import SkymapTriggerAPIHandler
from .source import (
    SourceCopyPhotometryHandler,
    SourceFinderHandler,
    SourceHandler,
    SourceNotificationHandler,
    SourceObservabilityPlotHandler,
    SourceOffsetsHandler,
    SurveyThumbnailHandler,
)
from .source_exists import SourceExistsHandler
from .source_groups import SourceGroupsHandler
from .source_labels import SourceLabelsHandler
from .sources_confirmed_in_gcn import (
    GCNsAssociatedWithSourceHandler,
    SourcesConfirmedInGCNHandler,
    SourcesConfirmedInGCNTNSHandler,
)
from .spatial_catalog import SpatialCatalogASCIIFileHandler, SpatialCatalogHandler
from .spectrum import (
    ObjSpectraHandler,
    SpectrumASCIIFileHandler,
    SpectrumASCIIFileParser,
    SpectrumHandler,
    SpectrumRangeHandler,
    SyntheticPhotometryHandler,
)
from .stream import StreamHandler, StreamUserHandler
from .summary_query import SummaryQueryHandler
from .survey_efficiency import (
    DefaultSurveyEfficiencyRequestHandler,
    SurveyEfficiencyForObservationPlanHandler,
    SurveyEfficiencyForObservationsHandler,
)
from .sysinfo import SysInfoHandler
from .taxonomy import TaxonomyHandler
from .telescope import TelescopeHandler
from .thumbnail import ThumbnailHandler, ThumbnailPathHandler
from .tns import (
    BulkTNSHandler,
    ObjTNSHandler,
    SpectrumTNSHandler,
    TNSRobotCoauthorHandler,
    TNSRobotGroupAutoreporterHandler,
    TNSRobotGroupHandler,
    TNSRobotHandler,
    TNSRobotSubmissionHandler,
)
from .unsourced_finder import UnsourcedFinderHandler
from .user import (
    UserHandler,
    set_default_acls,
    set_default_group,
    set_default_role,
)
from .user_obj_list import UserObjListHandler
from .weather import WeatherHandler
from .webhook import AnalysisWebhookHandler
