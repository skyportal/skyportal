import tornado.web

from baselayer.app.app_server import MainPageHandler
from baselayer.app.model_util import create_tables
from baselayer.log import make_log

from skyportal.handlers import BecomeUserHandler, LogoutHandler
from skyportal.handlers.api import (
    ACLHandler,
    AnalysisUploadOnlyHandler,
    AnalysisServiceHandler,
    AnalysisHandler,
    AnalysisProductsHandler,
    UserACLHandler,
    AllocationHandler,
    AllocationReportHandler,
    AllocationObservationPlanHandler,
    AssignmentHandler,
    BulkTNSHandler,
    CandidateHandler,
    CandidateFilterHandler,
    CatalogQueryHandler,
    ClassificationHandler,
    ClassificationVotesHandler,
    CommentHandler,
    CommentAttachmentHandler,
    CommentAttachmentUpdateHandler,
    DefaultAnalysisHandler,
    DefaultGcnTagHandler,
    EarthquakeHandler,
    EarthquakeMeasurementHandler,
    EarthquakePredictionHandler,
    EarthquakeStatusHandler,
    EnumTypesHandler,
    AnnotationHandler,
    GaiaQueryHandler,
    IRSAQueryWISEHandler,
    VizierQueryHandler,
    DatalabQueryHandler,
    PS1QueryHandler,
    DefaultFollowupRequestHandler,
    DefaultObservationPlanRequestHandler,
    DefaultSurveyEfficiencyRequestHandler,
    FilterHandler,
    FollowupRequestHandler,
    FollowupRequestCommentHandler,
    FollowupRequestWatcherHandler,
    FollowupRequestSchedulerHandler,
    FollowupRequestPrioritizationHandler,
    FacilityMessageHandler,
    GaiaPhotometricAlertsQueryHandler,
    GalaxyCatalogHandler,
    GalaxyASCIIFileHandler,
    GalaxyGladeHandler,
    GcnEventHandler,
    GcnEventAliasesHandler,
    GcnEventPropertiesHandler,
    GcnEventTagsHandler,
    GcnEventObservationPlanRequestsHandler,
    GcnEventSurveyEfficiencyHandler,
    GcnEventCatalogQueryHandler,
    GcnEventInstrumentFieldHandler,
    GcnEventTriggerHandler,
    GcnReportHandler,
    GcnSummaryHandler,
    GcnTachHandler,
    GcnGraceDBHandler,
    MMADetectorHandler,
    MMADetectorTimeIntervalHandler,
    MMADetectorSpectrumHandler,
    HealpixUpdateHandler,
    LocalizationHandler,
    LocalizationNoticeHandler,
    LocalizationTagsHandler,
    LocalizationDownloadHandler,
    LocalizationCrossmatchHandler,
    LocalizationPropertiesHandler,
    GroupHandler,
    GroupUserHandler,
    GroupUsersFromOtherGroupsHandler,
    GroupAdmissionRequestHandler,
    PublicGroupHandler,
    GroupStreamHandler,
    InstrumentHandler,
    InstrumentFieldHandler,
    InstrumentLogHandler,
    InstrumentLogExternalAPIHandler,
    InstrumentStatusHandler,
    InvalidEndpointHandler,
    InvitationHandler,
    UserObjListHandler,
    NewsFeedHandler,
    ObservingRunHandler,
    ObservationPlanRequestHandler,
    ObservationPlanTreasureMapHandler,
    ObservationPlanGCNHandler,
    ObservationPlanSubmitHandler,
    ObservationPlanMovieHandler,
    ObservationPlanObservabilityPlotHandler,
    ObservationPlanWorldmapPlotHandler,
    ObservationPlanSimSurveyHandler,
    ObservationPlanSimSurveyPlotHandler,
    ObservationPlanGeoJSONHandler,
    ObservationPlanSurveyEfficiencyHandler,
    ObservationPlanAirmassChartHandler,
    ObservationPlanCreateObservingRunHandler,
    ObservationPlanFieldsHandler,
    ObservationPlanManualRequestHandler,
    PhotometryHandler,
    PhotometryValidationHandler,
    PhotStatHandler,
    PhotStatUpdateHandler,
    BulkDeletePhotometryHandler,
    PhotometricSeriesHandler,
    ObjHandler,
    ObjPhotometryHandler,
    ObjHostHandler,
    ObjClassificationHandler,
    ObjClassificationQueryHandler,
    ObjGcnEventHandler,
    ObjMPCHandler,
    ObjTNSHandler,
    ObjPositionHandler,
    ObservationHandler,
    ObservationTreasureMapHandler,
    ObservationASCIIFileHandler,
    ObservationExternalAPIHandler,
    ObservationPlanNameHandler,
    ObservationSimSurveyHandler,
    ObservationSimSurveyPlotHandler,
    PhotometryRangeHandler,
    PhotometryRequestHandler,
    PhotometryOriginHandler,
    SummaryQueryHandler,
    RoleHandler,
    UserRoleHandler,
    SharingHandler,
    SkymapTriggerAPIHandler,
    SourceHandler,
    SourceCopyPhotometryHandler,
    SourceExistsHandler,
    SourceObservabilityPlotHandler,
    SourceOffsetsHandler,
    SourceFinderHandler,
    SourceNotificationHandler,
    ObjGroupsHandler,
    SourceGroupsHandler,
    ObjColorMagHandler,
    SpectrumHandler,
    SpectrumASCIIFileHandler,
    SpectrumASCIIFileParser,
    SpectrumRangeHandler,
    SyntheticPhotometryHandler,
    ObjSpectraHandler,
    RecurringAPIHandler,
    ReminderHandler,
    SourceLabelsHandler,
    SpectrumTNSHandler,
    ShiftHandler,
    ShiftUserHandler,
    ShiftSummary,
    StatsHandler,
    StreamHandler,
    StreamUserHandler,
    SpatialCatalogHandler,
    SpatialCatalogASCIIFileHandler,
    SurveyEfficiencyForObservationsHandler,
    SurveyEfficiencyForObservationPlanHandler,
    SwiftLSXPSQueryHandler,
    SysInfoHandler,
    ConfigHandler,
    TaxonomyHandler,
    TelescopeHandler,
    ThumbnailHandler,
    ThumbnailPathHandler,
    TNSRobotHandler,
    TNSRobotCoauthorHandler,
    TNSRobotGroupHandler,
    TNSRobotGroupAutoreporterHandler,
    TNSRobotSubmissionHandler,
    UserHandler,
    UnsourcedFinderHandler,
    WeatherHandler,
    AnalysisWebhookHandler,
    SurveyThumbnailHandler,
    SourcesConfirmedInGCNHandler,
    SourcesConfirmedInGCNTNSHandler,
    GCNsAssociatedWithSourceHandler,
    PublicSourcePageHandler,
)
from skyportal.handlers.api.internal import (
    SourceViewsHandler,
    SourceCountHandler,
    SourceSaverHandler,
    TokenHandler,
    DBInfoHandler,
    ProfileHandler,
    RoboticInstrumentsHandler,
    LogHandler,
    RecentSourcesHandler,
    PlotAssignmentAirmassHandler,
    PlotObjTelAirmassHandler,
    PlotHoursBelowAirmassHandler,
    AnnotationsInfoHandler,
    EphemerisHandler,
    StandardsHandler,
    NotificationHandler,
    BulkNotificationHandler,
    NotificationTestHandler,
    RecentGcnEventsHandler,
    FilterWavelengthHandler,
)
from skyportal.handlers.public import (
    ReportHandler,
    SourcePageHandler,
)

from . import model_util, openapi
from .models import init_db


log = make_log('app_server')


class CustomApplication(tornado.web.Application):
    def log_request(self, handler):
        # We don't want to log expected exceptions intentionally raised
        # during auth pipeline; such exceptions will have "google-oauth2" in
        # their request route
        if "google-oauth2" in str(handler.request.uri):
            return
        return super().log_request(handler)


skyportal_handlers = [
    # API endpoints
    (r'/api/acls', ACLHandler),
    (r'/api/allocation/report(/[0-9]+)', AllocationReportHandler),
    (r'/api/allocation/observation_plans/([0-9]+)', AllocationObservationPlanHandler),
    (r'/api/allocation(/.*)?', AllocationHandler),
    (r'/api/analysis_service/([0-9]+)/default_analysis(/.*)?', DefaultAnalysisHandler),
    (r'/api/analysis_service(/.*)?', AnalysisServiceHandler),
    (
        r'/api/(obj)/([0-9A-Za-z-_]+)/analysis_upload(/[0-9]+)?',
        AnalysisUploadOnlyHandler,
    ),
    (r'/api/(obj)/([0-9A-Za-z-_]+)/analysis(/[0-9]+)?', AnalysisHandler),
    (r'/api/(obj)/analysis(/[0-9]+)?', AnalysisHandler),
    (
        r'/api/(obj)/analysis(/[0-9]+)/(corner|results|plots)(/[0-9]+)?',
        AnalysisProductsHandler,
    ),
    (r'/api/assignment(/.*)?', AssignmentHandler),
    (r'/api/candidates_filter', CandidateFilterHandler),
    (r'/api/candidates(/[0-9A-Za-z-_]+)/([0-9]+)', CandidateHandler),
    (r'/api/candidates(/.*)?', CandidateHandler),
    (r'/api/catalogs/swift_lsxps', SwiftLSXPSQueryHandler),
    (r'/api/catalogs/gaia_alerts', GaiaPhotometricAlertsQueryHandler),
    (r'/api/catalog_queries', CatalogQueryHandler),
    (r'/api/classification/votes(/.*)?', ClassificationVotesHandler),
    (r'/api/classification/sources(/.*)?', ObjClassificationQueryHandler),
    (r'/api/classification(/[0-9]+)?', ClassificationHandler),
    (r'/api/enum_types(/.*)?', EnumTypesHandler),
    (
        r'/api/default_followup_request(/[0-9A-Za-z-_\.\+]+)?',
        DefaultFollowupRequestHandler,
    ),
    (
        r'/api/default_gcn_tag(/[0-9A-Za-z-_\.\+]+)?',
        DefaultGcnTagHandler,
    ),
    (
        r'/api/default_observation_plan(/[0-9A-Za-z-_\.\+]+)?',
        DefaultObservationPlanRequestHandler,
    ),
    (
        r'/api/default_survey_efficiency(/[0-9A-Za-z-_\.\+]+)?',
        DefaultSurveyEfficiencyRequestHandler,
    ),
    (r'/api/facility', FacilityMessageHandler),
    (r'/api/filters(/.*)?', FilterHandler),
    (
        r'/api/followup_request/([0-9A-Za-z-_\.\+]+)/comment',
        FollowupRequestCommentHandler,
    ),
    (r'/api/followup_request/watch(/[0-9]+)', FollowupRequestWatcherHandler),
    (r'/api/followup_request/schedule(/[0-9]+)', FollowupRequestSchedulerHandler),
    (
        r'/api/followup_request/prioritization(/.*)?',
        FollowupRequestPrioritizationHandler,
    ),
    (r'/api/followup_request(/.*)?', FollowupRequestHandler),
    (r'/api/photometry_request(/.*)', PhotometryRequestHandler),
    (r'/api/galaxy_catalog/glade', GalaxyGladeHandler),
    (r'/api/galaxy_catalog/ascii', GalaxyASCIIFileHandler),
    (r'/api/galaxy_catalog(/[0-9A-Za-z-_\.\+]+)?', GalaxyCatalogHandler),
    (
        r'/api/earthquake/([0-9A-Za-z-_\.\+]+)/mmadetector/([0-9A-Za-z-_\.\+]+)/predictions',
        EarthquakePredictionHandler,
    ),
    (
        r'/api/earthquake/([0-9A-Za-z-_\.\+]+)/mmadetector/([0-9A-Za-z-_\.\+]+)/measurements',
        EarthquakeMeasurementHandler,
    ),
    (
        r'/api/(sources|spectra|gcn_event|shift|earthquake)/([0-9A-Za-z-_\.\+]+)/comments',
        CommentHandler,
    ),
    (
        r'/api/(sources|spectra|gcn_event|shift|earthquake)/([0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)?',
        CommentHandler,
    ),
    (
        r'/api/(sources|spectra|gcn_event|shift|earthquake)(/[0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)/attachment',
        CommentAttachmentHandler,
    ),
    # Allow the '.pdf' suffix for the attachment route, as the
    # react-file-previewer package expects URLs ending with '.pdf' to
    # load PDF files.
    (
        r'/api/(sources|spectra|gcn_event|shift|earthquake)/([0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)/attachment.pdf',
        CommentAttachmentHandler,
    ),
    (
        r'/api/gcn_event(/[0-9A-Za-z-_\.\+]+)/observation_plan_requests',
        GcnEventObservationPlanRequestsHandler,
    ),
    (
        r'/api/gcn_event(/[0-9A-Za-z-_\.\+]+)/survey_efficiency',
        GcnEventSurveyEfficiencyHandler,
    ),
    (
        r'/api/gcn_event(/[0-9A-Za-z-_\.\+]+)/catalog_query',
        GcnEventCatalogQueryHandler,
    ),
    (
        r'/api/(source|spectra|gcn_event|shift|earthquake)/([0-9A-Za-z-_\.\+]+)/reminders(/[0-9]+)?',
        ReminderHandler,
    ),
    (r'/api/earthquake/status', EarthquakeStatusHandler),
    (r'/api/earthquake(/.*)?', EarthquakeHandler),
    (r'/api/gcn_event(/.*)/alias', GcnEventAliasesHandler),
    (r'/api/gcn_event(/.*)/triggered(/.*)?', GcnEventTriggerHandler),
    (r'/api/gcn_event(/.*)/gracedb', GcnGraceDBHandler),
    (r'/api/gcn_event/(.*)/report(/.*)?', GcnReportHandler),
    (r'/api/gcn_event(/.*)/tach', GcnTachHandler),
    (r'/api/gcn_event/(.*)/summary(/.*)?', GcnSummaryHandler),
    (r'/api/gcn_event/(.*)/instrument(/.*)?', GcnEventInstrumentFieldHandler),
    (r'/api/gcn_event/tags(/.*)?', GcnEventTagsHandler),
    (r'/api/gcn_event/properties', GcnEventPropertiesHandler),
    (r'/api/gcn_event(/.*)?', GcnEventHandler),
    (r'/api/sources_in_gcn/(.*)/tns', SourcesConfirmedInGCNTNSHandler),
    (r'/api/sources_in_gcn/(.*)/(.*)', SourcesConfirmedInGCNHandler),
    (r'/api/sources_in_gcn/(.*)', SourcesConfirmedInGCNHandler),
    (r'/api/associated_gcns/(.*)', GCNsAssociatedWithSourceHandler),
    (
        r'/api/localization(/[0-9]+)/observability',
        ObservationPlanObservabilityPlotHandler,
    ),
    (
        r'/api/localization(/[0-9]+)/airmass(/[0-9]+)?',
        ObservationPlanAirmassChartHandler,
    ),
    (
        r'/api/localization(/[0-9]+)/worldmap',
        ObservationPlanWorldmapPlotHandler,
    ),
    (r'/api/healpix', HealpixUpdateHandler),
    (r'/api/comment_attachment', CommentAttachmentUpdateHandler),
    (r'/api/sources/([0-9A-Za-z-_\.\+]+)/phot_stat', PhotStatHandler),
    (r'/api/phot_stats', PhotStatUpdateHandler),
    (r'/api/localization/tags', LocalizationTagsHandler),
    (r'/api/localization/properties', LocalizationPropertiesHandler),
    (r'/api/localization(/.*)/name(/.*)/download', LocalizationDownloadHandler),
    (r'/api/localization(/.*)/name(/.*)?', LocalizationHandler),
    (r'/api/localization(/.*)/notice(/.*)?', LocalizationNoticeHandler),
    (r'/api/localizationcrossmatch', LocalizationCrossmatchHandler),
    (r'/api/groups/public', PublicGroupHandler),
    (r'/api/groups(/[0-9]+)/streams(/[0-9]+)?', GroupStreamHandler),
    (r'/api/groups(/[0-9]+)/users(/.*)?', GroupUserHandler),
    (
        r'/api/groups(/[0-9]+)/usersFromGroups(/.*)?',
        GroupUsersFromOtherGroupsHandler,
    ),
    (r'/api/groups(/[0-9]+)?', GroupHandler),
    (r'/api/mmadetector(/[0-9]+)?', MMADetectorHandler),
    (r'/api/mmadetector/spectra(/[0-9]+)?', MMADetectorSpectrumHandler),
    (r'/api/mmadetector/time_intervals(/[0-9]+)?', MMADetectorTimeIntervalHandler),
    (r'/api/listing(/[0-9]+)?', UserObjListHandler),
    (r'/api/group_admission_requests(/[0-9]+)?', GroupAdmissionRequestHandler),
    (r'/api/instrument(/[0-9]+)/fields', InstrumentFieldHandler),
    (r'/api/instrument(/[0-9]+)/log', InstrumentLogHandler),
    (r'/api/instrument(/[0-9]+)/external_api', InstrumentLogExternalAPIHandler),
    (r'/api/instrument(/[0-9]+)/status', InstrumentStatusHandler),
    (r'/api/instrument(/[0-9]+)?', InstrumentHandler),
    (r'/api/invitations(/.*)?', InvitationHandler),
    (r'/api/newsfeed', NewsFeedHandler),
    (r'/api/observation(/[0-9]+)?', ObservationHandler),
    (r'/api/observation/ascii(/[0-9]+)?', ObservationASCIIFileHandler),
    (r'/api/observation/simsurvey(/[0-9]+)?', ObservationSimSurveyHandler),
    (r'/api/observation/simsurvey(/[0-9]+)/plot', ObservationSimSurveyPlotHandler),
    (r'/api/observation/treasuremap(/[0-9]+)', ObservationTreasureMapHandler),
    (r'/api/observation/external_api(/[0-9]+)?', ObservationExternalAPIHandler),
    (r'/api/observing_run(/[0-9]+)?', ObservingRunHandler),
    (r'/api/observation_plan/manual', ObservationPlanManualRequestHandler),
    (r'/api/observation_plan/plan_names', ObservationPlanNameHandler),
    (r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)?', ObservationPlanRequestHandler),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/treasuremap',
        ObservationPlanTreasureMapHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/gcn',
        ObservationPlanGCNHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/queue',
        ObservationPlanSubmitHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/movie',
        ObservationPlanMovieHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/simsurvey/plot',
        ObservationPlanSimSurveyPlotHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/simsurvey',
        ObservationPlanSimSurveyHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/geojson',
        ObservationPlanGeoJSONHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/survey_efficiency',
        ObservationPlanSurveyEfficiencyHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/observing_run',
        ObservationPlanCreateObservingRunHandler,
    ),
    (
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/fields',
        ObservationPlanFieldsHandler,
    ),
    (r'/api/objs(/[0-9A-Za-z-_\.\+]+)', ObjHandler),
    (r'/api/photometry(/[0-9]+)?', PhotometryHandler),
    (r'/api/photometry(/[0-9]+)/validation', PhotometryValidationHandler),
    (r'/api/photometric_series(/[0-9]+)?', PhotometricSeriesHandler),
    (r'/api/summary_query', SummaryQueryHandler),
    (r'/api/sharing', SharingHandler),
    (r'/api/shifts/summary(/[0-9]+)?', ShiftSummary),
    (r'/api/shifts(/[0-9]+)?', ShiftHandler),
    (r'/api/shifts(/[0-9]+)/users(/[0-9]+)?', ShiftUserHandler),
    (r'/api/photometry/bulk_delete/(.*)', BulkDeletePhotometryHandler),
    (r'/api/photometry/range(/.*)?', PhotometryRangeHandler),
    (r'/api/photometry/origins', PhotometryOriginHandler),
    (r'/api/recurring_api(/.*)?', RecurringAPIHandler),
    (r'/api/roles', RoleHandler),
    (r'/api/skymap_trigger(/[0-9]+)?', SkymapTriggerAPIHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/copy_photometry', SourceCopyPhotometryHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/photometry', ObjPhotometryHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/spectra', ObjSpectraHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/host', ObjHostHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/offsets', SourceOffsetsHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/finder', SourceFinderHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/classifications', ObjClassificationHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/groups', ObjGroupsHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/labels', SourceLabelsHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/color_mag', ObjColorMagHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/gcn_event', ObjGcnEventHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/mpc', ObjMPCHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/tns', ObjTNSHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/position', ObjPositionHandler),
    (
        r'/api/sources(/[0-9A-Za-z-_\.\+]+)/observability',
        SourceObservabilityPlotHandler,
    ),
    (r'/api/(sources|spectra)/([0-9A-Za-z-_\.\+]+)/comments', CommentHandler),
    (r'/api/(sources|spectra)/([0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)?', CommentHandler),
    (
        r'/api/(sources|spectra)(/[0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)/attachment',
        CommentAttachmentHandler,
    ),
    # Allow the '.pdf' suffix for the attachment route, as the
    # react-file-previewer package expects URLs ending with '.pdf' to
    # load PDF files.
    (
        r'/api/(sources|spectra)/([0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)/attachment.pdf',
        CommentAttachmentHandler,
    ),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/gaia', GaiaQueryHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/irsa', IRSAQueryWISEHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/vizier', VizierQueryHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/datalab', DatalabQueryHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/ps1', PS1QueryHandler),
    (
        r'/api/(sources|spectra|photometry)(/[0-9A-Za-z-_\.\+]+)/annotations',
        AnnotationHandler,
    ),
    (
        r'/api/(sources|spectra|photometry)(/[0-9A-Za-z-_\.\+]+)/annotations(/[0-9]+)?',
        AnnotationHandler,
    ),
    (r'/api/sources(/[^/]*)?', SourceHandler),
    (r'/api/source_exists(/.*)?', SourceExistsHandler),
    (r'/api/source_notifications', SourceNotificationHandler),
    (r'/api/source_groups(/.*)?', SourceGroupsHandler),
    (r'/api/spatial_catalog/ascii', SpatialCatalogASCIIFileHandler),
    (r'/api/spatial_catalog(/[0-9A-Za-z-_\.\+]+)?', SpatialCatalogHandler),
    (r'/api/spectra(/[0-9]+)?', SpectrumHandler),
    (r'/api/spectra/parse/ascii', SpectrumASCIIFileParser),
    (r'/api/spectra/ascii(/[0-9]+)?', SpectrumASCIIFileHandler),
    (r'/api/spectra/synthphot(/[0-9]+)?', SyntheticPhotometryHandler),
    (r'/api/spectra/range(/.*)?', SpectrumRangeHandler),
    # FIXME: TODO: Deprecated, to be removed in an upcoming release
    (r'/api/spectrum(/[0-9]+)?', SpectrumHandler),
    (r'/api/spectrum/parse/ascii', SpectrumASCIIFileParser),
    (r'/api/spectrum/ascii(/[0-9]+)?', SpectrumASCIIFileHandler),
    (r'/api/spectrum/range(/.*)?', SpectrumRangeHandler),
    (r'/api/spectrum/tns(/[0-9]+)?', SpectrumTNSHandler),
    # End deprecated
    (r'/api/streams(/[0-9]+)/users(/.*)?', StreamUserHandler),
    (r'/api/streams(/[0-9]+)?', StreamHandler),
    (
        r'/api/survey_efficiency/observations(/[0-9]+)?',
        SurveyEfficiencyForObservationsHandler,
    ),
    (
        r'/api/survey_efficiency/observation_plan(/[0-9]+)?',
        SurveyEfficiencyForObservationPlanHandler,
    ),
    (r'/api/db_stats', StatsHandler),
    (r'/api/sysinfo', SysInfoHandler),
    (r'/api/config', ConfigHandler),
    (r'/api/taxonomy(/.*)?', TaxonomyHandler),
    (r'/api/telescope(/[0-9]+)?', TelescopeHandler),
    (r'/api/thumbnail(/[0-9]+)?', ThumbnailHandler),
    (r'/api/thumbnailPath', ThumbnailPathHandler),
    (r'/api/tns_bulk(/.*)?', BulkTNSHandler),
    (
        r'/api/tns_robot(/[0-9]+)/group(/[0-9]+)/autoreporter(/[0-9]+)?',
        TNSRobotGroupAutoreporterHandler,
    ),
    (r'/api/tns_robot(/[0-9]+)/group(/[0-9]+)?', TNSRobotGroupHandler),
    (r'/api/tns_robot(/[0-9]+)/submissions(/[0-9]+)?', TNSRobotSubmissionHandler),
    (r'/api/tns_robot(/[0-9]+)/coauthor(/[0-9]+)?', TNSRobotCoauthorHandler),
    (r'/api/tns_robot(/[0-9]+)?', TNSRobotHandler),
    (r'/api/unsourced_finder', UnsourcedFinderHandler),
    (r'/api/user(/[0-9]+)/acls(/.*)?', UserACLHandler),
    (r'/api/user(/[0-9]+)/roles(/.*)?', UserRoleHandler),
    (r'/api/user(/.*)?', UserHandler),
    (r'/api/weather(/.*)?', WeatherHandler),
    # strictly require uuid4 token for this unauthenticated endpoint
    (
        r'/api/webhook/(obj)_analysis/([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})?',
        AnalysisWebhookHandler,
    ),
    # Public pages managed by the API.
    (r'/api/public_pages/source(/[0-9A-Za-z-_\.\+]+)', PublicSourcePageHandler),
    # Internal API endpoints
    (r'/api/internal/tokens(/[0-9A-Za-z-]+)?', TokenHandler),
    (r"/api/internal/profile(/[0-9]+)?", ProfileHandler),
    (r'/api/internal/dbinfo', DBInfoHandler),
    (r'/api/internal/source_views(/.*)?', SourceViewsHandler),
    (r'/api/internal/source_counts(/.*)?', SourceCountHandler),
    (r'/api/internal/source_savers(/.*)?', SourceSaverHandler),
    (r'/api/internal/instrument_forms', RoboticInstrumentsHandler),
    (r'/api/internal/standards', StandardsHandler),
    (r'/api/internal/wavelengths(/.*)?', FilterWavelengthHandler),
    (r'/api/internal/plot/airmass/assignment/(.*)', PlotAssignmentAirmassHandler),
    (
        r'/api/internal/plot/airmass/objtel/(.*)/([0-9]+)',
        PlotObjTelAirmassHandler,
    ),
    (
        r'/api/internal/plot/airmass/hours_below/(.*)/([0-9]+)',
        PlotHoursBelowAirmassHandler,
    ),
    (r'/api/internal/ephemeris(/[0-9]+)?', EphemerisHandler),
    (r'/api/internal/log(/.*)?', LogHandler),
    (r'/api/internal/recent_sources(/.*)?', RecentSourcesHandler),
    (r'/api/internal/annotations_info', AnnotationsInfoHandler),
    (r'/api/internal/notifications(/[0-9]+)?', NotificationHandler),
    (r'/api/internal/notifications/all', BulkNotificationHandler),
    (r'/api/internal/notifications_test(/[0-9]+)?', NotificationTestHandler),
    (r'/api/internal/survey_thumbnail', SurveyThumbnailHandler),
    (r'/api/internal/recent_gcn_events', RecentGcnEventsHandler),
    (r'/api/.*', InvalidEndpointHandler),
    # Public pages.
    (r'/public/reports/(gcn)(/[0-9]+)?(/.*)?', ReportHandler),
    (
        r'/public/sources(?:/)?([0-9A-Za-z-_\.\+]+)?(?:/)?(?:version)?(?:/)?([0-9a-f]+)?',
        SourcePageHandler,
    ),
    (r'/public/.*', InvalidEndpointHandler),
    # Debug and logout pages.
    (r'/become_user(/.*)?', BecomeUserHandler),
    (r'/logout', LogoutHandler),
    # User-facing pages.
    # Route all frontend pages, such as
    # `/source/g647ba`, through the main page.
    (r'/.*', MainPageHandler),
    #
    # Refer to Main.jsx for routing info.
]


def make_app(cfg, baselayer_handlers, baselayer_settings, process=None, env=None):
    """Create and return a `tornado.web.Application` object with specified
    handlers and settings.

    Parameters
    ----------
    cfg : Config
        Loaded configuration.  Can be specified with '--config'
        (multiple uses allowed).
    baselayer_handlers : list
        Tornado handlers needed for baselayer to function.
    baselayer_settings : cfg
        Settings needed for baselayer to function.
    process : int
        When launching multiple app servers, which number is this?
    env : dict
        Environment in which the app was launched.  Currently only has
        one key, 'debug'---true if launched with `--debug`.

    """
    if cfg['app.secret_key'] == 'abc01234':
        print('!' * 80)
        print('  Your server is insecure. Please update the secret string ')
        print('  in the configuration file!')
        print('!' * 80)

    handlers = baselayer_handlers + skyportal_handlers

    settings = baselayer_settings
    settings.update(
        {
            'SOCIAL_AUTH_PIPELINE': (
                # Get the information we can about the user and return it in a simple
                # format to create the user instance later. In some cases the details are
                # already part of the auth response from the provider, but sometimes this
                # could hit a provider API.
                'social_core.pipeline.social_auth.social_details',
                # Get the social uid from whichever service we're authing thru. The uid is
                # the unique identifier of the given user in the provider.
                'social_core.pipeline.social_auth.social_uid',
                # Verify that the current auth process is valid within the current
                # project, this is where emails and domains whitelists are applied (if
                # defined).
                'social_core.pipeline.social_auth.auth_allowed',
                # Checks if the current social-account is already associated in the site.
                'social_core.pipeline.social_auth.social_user',
                'skyportal.onboarding.get_username',
                'skyportal.onboarding.create_user',
                # Create a user account if we haven't found one yet.
                # 'social_core.pipeline.user.create_user',
                # Create the record that associates the social account with the user.
                'social_core.pipeline.social_auth.associate_user',
                # Populate the extra_data field in the social record with the values
                # specified by settings (and the default ones like access_token, etc).
                'social_core.pipeline.social_auth.load_extra_data',
                # Update the user record with info from the auth service only if blank
                'skyportal.onboarding.user_details',
                'skyportal.onboarding.setup_invited_user_permissions',
            ),
            'SOCIAL_AUTH_NEW_USER_REDIRECT_URL': '/profile?newUser=true',
            'SOCIAL_AUTH_FIELDS_STORED_IN_SESSION': ['invite_token'],
            'debug': env.debug if env is not None else False,
        }
    )

    app = CustomApplication(handlers, **settings)

    default_engine_args = {'pool_size': 10, 'max_overflow': 15, 'pool_recycle': 3600}
    database_cfg = cfg['database']
    if database_cfg.get('engine_args', {}) in [None, '', {}]:
        database_cfg['engine_args'] = default_engine_args
    else:
        database_cfg['engine_args'] = {
            **default_engine_args,
            **database_cfg['engine_args'],
        }

    init_db(
        **database_cfg,
        autoflush=False,
    )

    # If tables are found in the database, new tables will only be added
    # in debug mode.  In production, we leave the tables alone, since
    # migrations might be used.
    create_tables(add=env.debug)
    model_util.refresh_enums()

    model_util.setup_permissions()
    app.cfg = cfg

    admin_token = model_util.provision_token()
    with open('.tokens.yaml', 'w') as f:
        f.write(f'INITIAL_ADMIN: {admin_token.id}\n')
    with open('.tokens.yaml') as f:
        print('-' * 78)
        print('Tokens in .tokens.yaml:')
        print('\n'.join(f.readlines()), end='')
        print('-' * 78)

    model_util.provision_public_group()
    app.openapi_spec = openapi.spec_from_handlers(handlers)

    return app
