from .acls import ACLHandler, UserACLHandler
from .allocation import AllocationHandler, AllocationReportHandler
from .analysis import (
    AnalysisUploadOnlyHandler,
    AnalysisServiceHandler,
    AnalysisHandler,
    AnalysisProductsHandler,
)
from .candidate import CandidateHandler
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
    FollowupRequestWatcherHandler,
    FollowupRequestPrioritizationHandler,
    FollowupRequestSchedulerHandler,
    AssignmentHandler,
)
from .facility_listener import FacilityMessageHandler
from .galaxy import GalaxyCatalogHandler, GalaxyASCIIFileHandler, GalaxyGladeHandler
from .gcn import (
    GcnEventHandler,
    GcnEventObservationPlanRequestsHandler,
    GcnEventPropertiesHandler,
    GcnEventSurveyEfficiencyHandler,
    GcnEventCatalogQueryHandler,
    GcnEventTagsHandler,
    GcnSummaryHandler,
    LocalizationHandler,
    LocalizationDownloadHandler,
    LocalizationCrossmatchHandler,
    LocalizationPropertiesHandler,
    LocalizationTagsHandler,
)
from .gcn_tach import GcnTachHandler
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
from .instrument import InstrumentHandler
from .invalid import InvalidEndpointHandler
from .invitations import InvitationHandler
from .mmadetector import (
    MMADetectorHandler,
    MMADetectorSpectrumHandler,
    MMADetectorTimeIntervalHandler,
)
from .news_feed import NewsFeedHandler
from .observation import (
    ObservationASCIIFileHandler,
    ObservationHandler,
    ObservationTreasureMapHandler,
    ObservationExternalAPIHandler,
    ObservationSimSurveyHandler,
    ObservationSimSurveyPlotHandler,
)
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
from .phot_stat import PhotStatHandler, PhotStatUpdateHandler
from .color_mag import ObjColorMagHandler
from .photometry_request import PhotometryRequestHandler
from .public_group import PublicGroupHandler
from .roles import RoleHandler, UserRoleHandler
from .obj import ObjHandler
from .recurring_api import RecurringAPIHandler
from .reminder import ReminderHandler
from .sharing import SharingHandler
from .shift import ShiftHandler, ShiftUserHandler, ShiftSummary
from .source import (
    SourceHandler,
    SourceOffsetsHandler,
    SourceFinderHandler,
    SourceNotificationHandler,
    SourceObservabilityPlotHandler,
    PS1ThumbnailHandler,
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
from .tns import ObjTNSHandler, SpectrumTNSHandler, TNSRobotHandler
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
    GCNsAssociatedWithSourceHandler,
)
