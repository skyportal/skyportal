from .acls import ACLHandler, UserACLHandler
from .allocation import (
    AllocationHandler,
    AllocationReportHandler,
    AllocationObservationPlanHandler,
)
from .analysis import (
    AnalysisUploadOnlyHandler,
    AnalysisServiceHandler,
    AnalysisHandler,
    AnalysisProductsHandler,
    DefaultAnalysisHandler,
)
from .candidate import CandidateHandler, CandidateFilterHandler
from .classification import (
    ClassificationHandler,
    ClassificationVotesHandler,
    ObjClassificationHandler,
    ObjClassificationQueryHandler,
)
from .comment import CommentHandler, CommentAttachmentHandler
from .comment_attachment import CommentAttachmentUpdateHandler
from .annotation import AnnotationHandler
from .annotation_services import (
    GaiaQueryHandler,
    IRSAQueryWISEHandler,
    VizierQueryHandler,
    DatalabQueryHandler,
    PS1QueryHandler,
)
from .catalog_services import (
    CatalogQueryHandler,
    SwiftLSXPSQueryHandler,
    GaiaPhotometricAlertsQueryHandler,
)
from .db_stats import StatsHandler
from .earthquake import (
    EarthquakeHandler,
    EarthquakeMeasurementHandler,
    EarthquakePredictionHandler,
    EarthquakeStatusHandler,
)
from .enum_types import EnumTypesHandler
from .filter import FilterHandler
from .followup_request import (
    DefaultFollowupRequestHandler,
    FollowupRequestHandler,
    FollowupRequestCommentHandler,
    FollowupRequestWatcherHandler,
    FollowupRequestPrioritizationHandler,
    FollowupRequestSchedulerHandler,
    AssignmentHandler,
)
from .facility_listener import FacilityMessageHandler
from .galaxy import (
    GalaxyCatalogHandler,
    GalaxyASCIIFileHandler,
    GalaxyGladeHandler,
    ObjHostHandler,
)
from .gcn import (
    DefaultGcnTagHandler,
    GcnEventHandler,
    GcnEventAliasesHandler,
    GcnEventObservationPlanRequestsHandler,
    GcnEventPropertiesHandler,
    GcnEventSurveyEfficiencyHandler,
    GcnEventCatalogQueryHandler,
    GcnEventInstrumentFieldHandler,
    GcnEventTagsHandler,
    GcnReportHandler,
    GcnSummaryHandler,
    GcnEventTriggerHandler,
    LocalizationHandler,
    LocalizationNoticeHandler,
    LocalizationDownloadHandler,
    LocalizationCrossmatchHandler,
    LocalizationPropertiesHandler,
    LocalizationTagsHandler,
    ObjGcnEventHandler,
)
from .gcn_tach import GcnTachHandler
from .gcn_gracedb import GcnGraceDBHandler
from .group import (
    GroupHandler,
    GroupUserHandler,
    GroupStreamHandler,
    GroupUsersFromOtherGroupsHandler,
    ObjGroupsHandler,
)
from .healpix import HealpixUpdateHandler
from .user_obj_list import UserObjListHandler
from .group_admission_request import GroupAdmissionRequestHandler
from .instrument import InstrumentHandler, InstrumentFieldHandler
from .instrument_log import (
    InstrumentLogHandler,
    InstrumentLogExternalAPIHandler,
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
from .observation import (
    ObservationASCIIFileHandler,
    ObservationHandler,
    ObservationTreasureMapHandler,
    ObservationExternalAPIHandler,
    ObservationSimSurveyHandler,
    ObservationSimSurveyPlotHandler,
)
from .obj import ObjHandler, ObjPositionHandler
from .observingrun import ObservingRunHandler
from .observation_plan import (
    DefaultObservationPlanRequestHandler,
    ObservationPlanRequestHandler,
    ObservationPlanTreasureMapHandler,
    ObservationPlanGCNHandler,
    ObservationPlanSubmitHandler,
    ObservationPlanMovieHandler,
    ObservationPlanNameHandler,
    ObservationPlanObservabilityPlotHandler,
    ObservationPlanWorldmapPlotHandler,
    ObservationPlanSimSurveyHandler,
    ObservationPlanSimSurveyPlotHandler,
    ObservationPlanSurveyEfficiencyHandler,
    ObservationPlanGeoJSONHandler,
    ObservationPlanAirmassChartHandler,
    ObservationPlanCreateObservingRunHandler,
    ObservationPlanFieldsHandler,
    ObservationPlanManualRequestHandler,
)
from .photometry import (
    PhotometryHandler,
    ObjPhotometryHandler,
    BulkDeletePhotometryHandler,
    PhotometryRangeHandler,
    PhotometryOriginHandler,
)
from .photometry_validation import PhotometryValidationHandler
from .photometric_series import PhotometricSeriesHandler
from .phot_stat import PhotStatHandler, PhotStatUpdateHandler
from .color_mag import ObjColorMagHandler
from .photometry_request import PhotometryRequestHandler
from .public_group import PublicGroupHandler
from .summary_query import SummaryQueryHandler
from .roles import RoleHandler, UserRoleHandler
from .recurring_api import RecurringAPIHandler
from .reminder import ReminderHandler
from .sharing import SharingHandler
from .shift import ShiftHandler, ShiftUserHandler, ShiftSummary
from .skymap_trigger import SkymapTriggerAPIHandler
from .source import (
    SourceHandler,
    SourceCopyPhotometryHandler,
    SourceOffsetsHandler,
    SourceFinderHandler,
    SourceNotificationHandler,
    SourceObservabilityPlotHandler,
    SurveyThumbnailHandler,
)
from .source_exists import SourceExistsHandler
from .source_groups import SourceGroupsHandler
from .spatial_catalog import SpatialCatalogHandler, SpatialCatalogASCIIFileHandler
from .spectrum import (
    SpectrumHandler,
    ObjSpectraHandler,
    SpectrumASCIIFileParser,
    SpectrumASCIIFileHandler,
    SpectrumRangeHandler,
    SyntheticPhotometryHandler,
)
from .source_labels import SourceLabelsHandler
from .survey_efficiency import (
    DefaultSurveyEfficiencyRequestHandler,
    SurveyEfficiencyForObservationPlanHandler,
    SurveyEfficiencyForObservationsHandler,
)
from .stream import StreamHandler, StreamUserHandler
from .sysinfo import SysInfoHandler
from .config_handler import ConfigHandler
from .taxonomy import TaxonomyHandler
from .telescope import TelescopeHandler
from .tns import (
    ObjTNSHandler,
    BulkTNSHandler,
    SpectrumTNSHandler,
    TNSRobotHandler,
    TNSRobotCoauthorHandler,
    TNSRobotGroupHandler,
    TNSRobotGroupAutoreporterHandler,
    TNSRobotSubmissionHandler,
)
from .thumbnail import ThumbnailHandler, ThumbnailPathHandler
from .user import (
    UserHandler,
    set_default_acls,
    set_default_group,
    set_default_role,
)
from .unsourced_finder import UnsourcedFinderHandler
from .weather import WeatherHandler
from .webhook import AnalysisWebhookHandler
from .sources_confirmed_in_gcn import (
    SourcesConfirmedInGCNHandler,
    SourcesConfirmedInGCNTNSHandler,
    GCNsAssociatedWithSourceHandler,
)
from .public_pages.public_source_page import PublicSourcePageHandler
