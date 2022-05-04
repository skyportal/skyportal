import tornado.web

from baselayer.app.app_server import MainPageHandler
from baselayer.app.model_util import create_tables
from baselayer.log import make_log

from skyportal.handlers import BecomeUserHandler, LogoutHandler
from skyportal.handlers.api import (
    ACLHandler,
    UserACLHandler,
    AllocationHandler,
    AssignmentHandler,
    CandidateHandler,
    ClassificationHandler,
    CommentHandler,
    CommentAttachmentHandler,
    EnumTypesHandler,
    AnnotationHandler,
    DatalabQueryHandler,
    IRSAQueryWISEHandler,
    FilterHandler,
    FollowupRequestHandler,
    FollowupRequestSchedulerHandler,
    FollowupRequestPrioritizationHandler,
    FacilityMessageHandler,
    GalaxyCatalogHandler,
    GcnEventHandler,
    LocalizationHandler,
    GroupHandler,
    GroupUserHandler,
    GroupUsersFromOtherGroupsHandler,
    GroupAdmissionRequestHandler,
    PublicGroupHandler,
    GroupStreamHandler,
    InstrumentHandler,
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
    ObservationPlanGeoJSONHandler,
    ObservationPlanAirmassChartHandler,
    PhotometryHandler,
    BulkDeletePhotometryHandler,
    ObjHandler,
    ObjPhotometryHandler,
    ObjClassificationHandler,
    ObjTNSHandler,
    ObservationHandler,
    ObservationGCNHandler,
    ObservationTreasureMapHandler,
    ObservationASCIIFileHandler,
    ObservationExternalAPIHandler,
    PhotometryRangeHandler,
    PhotometryRequestHandler,
    RoleHandler,
    UserRoleHandler,
    SharingHandler,
    SourceHandler,
    SourceExistsHandler,
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
    SpectrumTNSHandler,
    ShiftHandler,
    ShiftUserHandler,
    StatsHandler,
    StreamHandler,
    StreamUserHandler,
    SysInfoHandler,
    ConfigHandler,
    TaxonomyHandler,
    TelescopeHandler,
    ThumbnailHandler,
    TNSRobotHandler,
    UserHandler,
    UnsourcedFinderHandler,
    WeatherHandler,
    VizierQueryHandler,
    PS1ThumbnailHandler,
)
from skyportal.handlers.api.internal import (
    PlotPhotometryHandler,
    PlotSpectroscopyHandler,
    SourceViewsHandler,
    SourceCountHandler,
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
    RecentGcnEventsHandler,
    FilterWavelengthHandler,
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
    (r'/api/allocation(/.*)?', AllocationHandler),
    (r'/api/assignment(/.*)?', AssignmentHandler),
    (r'/api/candidates(/[0-9A-Za-z-_]+)/([0-9]+)', CandidateHandler),
    (r'/api/candidates(/.*)?', CandidateHandler),
    (r'/api/classification(/[0-9]+)?', ClassificationHandler),
    (r'/api/enum_types(/.*)?', EnumTypesHandler),
    (r'/api/facility', FacilityMessageHandler),
    (r'/api/filters(/.*)?', FilterHandler),
    (r'/api/followup_request/schedule(/[0-9]+)', FollowupRequestSchedulerHandler),
    (
        r'/api/followup_request/prioritization(/.*)?',
        FollowupRequestPrioritizationHandler,
    ),
    (r'/api/followup_request(/.*)?', FollowupRequestHandler),
    (r'/api/photometry_request(/.*)', PhotometryRequestHandler),
    (r'/api/galaxy_catalog(/[0-9]+)?', GalaxyCatalogHandler),
    (r'/api/(sources|spectra|gcn_event)/([0-9A-Za-z-_\.\+]+)/comments', CommentHandler),
    (
        r'/api/(sources|spectra|gcn_event)/([0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)?',
        CommentHandler,
    ),
    (
        r'/api/(sources|spectra|gcn_event)(/[0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)/attachment',
        CommentAttachmentHandler,
    ),
    # Allow the '.pdf' suffix for the attachment route, as the
    # react-file-previewer package expects URLs ending with '.pdf' to
    # load PDF files.
    (
        r'/api/(sources|spectra|gcn_event)/([0-9A-Za-z-_\.\+]+)/comments(/[0-9]+)/attachment.pdf',
        CommentAttachmentHandler,
    ),
    (r'/api/gcn_event(/.*)?', GcnEventHandler),
    (
        r'/api/localization(/[0-9]+)/airmass(/[0-9]+)?',
        ObservationPlanAirmassChartHandler,
    ),
    (r'/api/localization(/.*)/name(/.*)?', LocalizationHandler),
    (r'/api/groups/public', PublicGroupHandler),
    (r'/api/groups(/[0-9]+)/streams(/[0-9]+)?', GroupStreamHandler),
    (r'/api/groups(/[0-9]+)/users(/.*)?', GroupUserHandler),
    (
        r'/api/groups(/[0-9]+)/usersFromGroups(/.*)?',
        GroupUsersFromOtherGroupsHandler,
    ),
    (r'/api/groups(/[0-9]+)?', GroupHandler),
    (r'/api/listing(/[0-9]+)?', UserObjListHandler),
    (r'/api/group_admission_requests(/[0-9]+)?', GroupAdmissionRequestHandler),
    (r'/api/instrument(/[0-9]+)?', InstrumentHandler),
    (r'/api/invitations(/.*)?', InvitationHandler),
    (r'/api/newsfeed', NewsFeedHandler),
    (r'/api/observation(/[0-9]+)?', ObservationHandler),
    (r'/api/observation/ascii(/[0-9]+)?', ObservationASCIIFileHandler),
    (r'/api/observation/gcn(/[0-9]+)', ObservationGCNHandler),
    (r'/api/observation/treasuremap(/[0-9]+)', ObservationTreasureMapHandler),
    (r'/api/observation/external_api(/[0-9]+)?', ObservationExternalAPIHandler),
    (r'/api/observing_run(/[0-9]+)?', ObservingRunHandler),
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
        r'/api/observation_plan(/[0-9A-Za-z-_\.\+]+)/geojson',
        ObservationPlanGeoJSONHandler,
    ),
    (r'/api/objs(/[0-9A-Za-z-_\.\+]+)', ObjHandler),
    (r'/api/photometry(/[0-9]+)?', PhotometryHandler),
    (r'/api/sharing', SharingHandler),
    (r'/api/shifts(/[0-9]+)?', ShiftHandler),
    (r'/api/shifts(/[0-9]+)/users(/[0-9]+)?', ShiftUserHandler),
    (r'/api/photometry/bulk_delete/(.*)', BulkDeletePhotometryHandler),
    (r'/api/photometry/range(/.*)?', PhotometryRangeHandler),
    (r'/api/roles', RoleHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/photometry', ObjPhotometryHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/spectra', ObjSpectraHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/offsets', SourceOffsetsHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/finder', SourceFinderHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/classifications', ObjClassificationHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/groups', ObjGroupsHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/color_mag', ObjColorMagHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/tns', ObjTNSHandler),
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
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/datalab', DatalabQueryHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/irsa', IRSAQueryWISEHandler),
    (r'/api/sources(/[0-9A-Za-z-_\.\+]+)/annotations/vizier', VizierQueryHandler),
    (
        r'/api/(sources|spectra)(/[0-9A-Za-z-_\.\+]+)/annotations',
        AnnotationHandler,
    ),
    (
        r'/api/(sources|spectra)(/[0-9A-Za-z-_\.\+]+)/annotations(/[0-9]+)?',
        AnnotationHandler,
    ),
    (r'/api/sources(/.*)?', SourceHandler),
    (r'/api/source_exists(/.*)?', SourceExistsHandler),
    (r'/api/source_notifications', SourceNotificationHandler),
    (r'/api/source_groups(/.*)?', SourceGroupsHandler),
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
    (r'/api/db_stats', StatsHandler),
    (r'/api/sysinfo', SysInfoHandler),
    (r'/api/config', ConfigHandler),
    (r'/api/taxonomy(/.*)?', TaxonomyHandler),
    (r'/api/telescope(/[0-9]+)?', TelescopeHandler),
    (r'/api/thumbnail(/[0-9]+)?', ThumbnailHandler),
    (r'/api/tns_robot(/.*)?', TNSRobotHandler),
    (r'/api/unsourced_finder', UnsourcedFinderHandler),
    (r'/api/user(/[0-9]+)/acls(/.*)?', UserACLHandler),
    (r'/api/user(/[0-9]+)/roles(/.*)?', UserRoleHandler),
    (r'/api/user(/.*)?', UserHandler),
    (r'/api/weather(/.*)?', WeatherHandler),
    (r'/api/internal/tokens(/.*)?', TokenHandler),
    (r'/api/internal/profile', ProfileHandler),
    (r'/api/internal/dbinfo', DBInfoHandler),
    (r'/api/internal/source_views(/.*)?', SourceViewsHandler),
    (r'/api/internal/source_counts(/.*)?', SourceCountHandler),
    (r'/api/internal/plot/photometry/(.*)', PlotPhotometryHandler),
    (r'/api/internal/plot/spectroscopy/(.*)', PlotSpectroscopyHandler),
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
    (r'/api/internal/ephemeris/([0-9]+)', EphemerisHandler),
    (r'/api/internal/log', LogHandler),
    (r'/api/internal/recent_sources(/.*)?', RecentSourcesHandler),
    (r'/api/internal/annotations_info', AnnotationsInfoHandler),
    (r'/api/internal/notifications(/[0-9]+)?', NotificationHandler),
    (r'/api/internal/notifications/all', BulkNotificationHandler),
    (r'/api/internal/ps1_thumbnail', PS1ThumbnailHandler),
    (r'/api/internal/recent_gcn_events', RecentGcnEventsHandler),
    (r'/api/.*', InvalidEndpointHandler),
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
    if cfg['cookie_secret'] == 'abc01234':
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
        }
    )

    app = CustomApplication(handlers, **settings)
    init_db(
        **cfg['database'],
        autoflush=False,
        engine_args={'pool_size': 10, 'max_overflow': 15, 'pool_recycle': 3600},
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
