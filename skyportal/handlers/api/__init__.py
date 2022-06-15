from .acls import ACLHandler, UserACLHandler
from .allocation import AllocationHandler
from .analysis import AnalysisServiceHandler
from .candidate import CandidateHandler
from .classification import ClassificationHandler, ObjClassificationHandler
from .comment import CommentHandler, CommentAttachmentHandler
from .annotation import AnnotationHandler
from .annotation_services import (
    GaiaQueryHandler,
    IRSAQueryWISEHandler,
    VizierQueryHandler,
    DatalabQueryHandler,
)
from .db_stats import StatsHandler
from .enum_types import EnumTypesHandler
from .filter import FilterHandler
from .followup_request import (
    FollowupRequestHandler,
    FollowupRequestPrioritizationHandler,
    FollowupRequestSchedulerHandler,
    AssignmentHandler,
)
from .facility_listener import FacilityMessageHandler
from .galaxy import GalaxyCatalogHandler
from .gcn import (
    GcnEventHandler,
    LocalizationHandler,
)
from .group import (
    GroupHandler,
    GroupUserHandler,
    GroupStreamHandler,
    GroupUsersFromOtherGroupsHandler,
    ObjGroupsHandler,
)

from .user_obj_list import UserObjListHandler
from .group_admission_request import GroupAdmissionRequestHandler
from .instrument import InstrumentHandler
from .invalid import InvalidEndpointHandler
from .invitations import InvitationHandler
from .news_feed import NewsFeedHandler
from .observation import (
    ObservationASCIIFileHandler,
    ObservationHandler,
    ObservationGCNHandler,
    ObservationTreasureMapHandler,
    ObservationExternalAPIHandler,
    ObservationSimSurveyHandler,
)
from .observingrun import ObservingRunHandler
from .observation_plan import (
    ObservationPlanRequestHandler,
    ObservationPlanTreasureMapHandler,
    ObservationPlanGCNHandler,
    ObservationPlanSubmitHandler,
    ObservationPlanMovieHandler,
    ObservationPlanSimSurveyHandler,
    ObservationPlanGeoJSONHandler,
    ObservationPlanAirmassChartHandler,
    ObservationPlanCreateObservingRunHandler,
    ObservationPlanFieldsHandler,
)
from .photometry import (
    PhotometryHandler,
    ObjPhotometryHandler,
    BulkDeletePhotometryHandler,
    PhotometryRangeHandler,
    PhotometryOriginHandler,
)
from .color_mag import ObjColorMagHandler
from .photometry_request import PhotometryRequestHandler
from .public_group import PublicGroupHandler
from .roles import RoleHandler, UserRoleHandler
from .obj import ObjHandler
from .sharing import SharingHandler
from .shift import ShiftHandler, ShiftUserHandler, ShiftSummary
from .source import (
    SourceHandler,
    SourceOffsetsHandler,
    SourceFinderHandler,
    SourceNotificationHandler,
    PS1ThumbnailHandler,
)
from .source_exists import SourceExistsHandler
from .source_groups import SourceGroupsHandler
from .spectrum import (
    SpectrumHandler,
    ObjSpectraHandler,
    SpectrumASCIIFileParser,
    SpectrumASCIIFileHandler,
    SpectrumRangeHandler,
    SyntheticPhotometryHandler,
)
from .stream import StreamHandler, StreamUserHandler
from .sysinfo import SysInfoHandler
from .config_handler import ConfigHandler
from .taxonomy import TaxonomyHandler
from .telescope import TelescopeHandler
from .tns import ObjTNSHandler, SpectrumTNSHandler, TNSRobotHandler
from .thumbnail import ThumbnailHandler
from .user import (
    UserHandler,
    set_default_acls,
    set_default_group,
    set_default_role,
)
from .unsourced_finder import UnsourcedFinderHandler
from .weather import WeatherHandler
