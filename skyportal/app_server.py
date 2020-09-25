import tornado.web

from baselayer.app.app_server import MainPageHandler
from baselayer.app import model_util as baselayer_model_util

from skyportal.handlers import BecomeUserHandler, LogoutHandler
from skyportal.handlers.api import (
    AllocationHandler,
    AssignmentHandler,
    CandidateHandler,
    ClassificationHandler,
    CommentHandler,
    CommentAttachmentHandler,
    FilterHandler,
    FollowupRequestHandler,
    FacilityMessageHandler,
    GroupHandler,
    GroupUserHandler,
    PublicGroupHandler,
    GroupStreamHandler,
    InstrumentHandler,
    InvalidEndpointHandler,
    InvitationHandler,
    NewsFeedHandler,
    ObservingRunHandler,
    PhotometryHandler,
    BulkDeletePhotometryHandler,
    ObjPhotometryHandler,
    SharingHandler,
    SourceHandler,
    SourceOffsetsHandler,
    SourceFinderHandler,
    SpectrumHandler,
    SpectrumFITSFileHandler,
    SpectrumFITSFileParser,
    ObjSpectraHandler,
    StreamHandler,
    StreamUserHandler,
    SysInfoHandler,
    TaxonomyHandler,
    TelescopeHandler,
    ThumbnailHandler,
    UserHandler,
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
    PlotAirmassHandler,
)

from . import models, model_util, openapi


def make_app(cfg, baselayer_handlers, baselayer_settings):
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

    """
    if cfg['cookie_secret'] == 'abc01234':
        print('!' * 80)
        print('  Your server is insecure. Please update the secret string ')
        print('  in the configuration file!')
        print('!' * 80)

    handlers = baselayer_handlers + [
        # API endpoints
        (r'/api/allocation(/.*)?', AllocationHandler),
        (r'/api/assignment(/.*)?', AssignmentHandler),
        (r'/api/candidates(/.*)?', CandidateHandler),
        (r'/api/classification(/[0-9]+)?', ClassificationHandler),
        (r'/api/comment(/[0-9]+)?', CommentHandler),
        (r'/api/comment(/[0-9]+)/attachment', CommentAttachmentHandler),
        (r'/api/facility', FacilityMessageHandler),
        (r'/api/filters(/.*)?', FilterHandler),
        (r'/api/followup_request(/.*)?', FollowupRequestHandler),
        (r'/api/groups/public', PublicGroupHandler),
        (r'/api/groups(/[0-9]+)/streams(/[0-9]+)?', GroupStreamHandler),
        (r'/api/groups(/[0-9]+)/users(/.*)?', GroupUserHandler),
        (r'/api/groups(/[0-9]+)?', GroupHandler),
        (r'/api/instrument(/[0-9]+)?', InstrumentHandler),
        (r'/api/invitations(/.*)?', InvitationHandler),
        (r'/api/newsfeed', NewsFeedHandler),
        (r'/api/observing_run(/[0-9]+)?', ObservingRunHandler),
        (r'/api/photometry(/[0-9]+)?', PhotometryHandler),
        (r'/api/sharing', SharingHandler),
        (r'/api/photometry/bulk_delete/(.*)', BulkDeletePhotometryHandler),
        (r'/api/sources(/[0-9A-Za-z-_]+)/photometry', ObjPhotometryHandler),
        (r'/api/sources(/[0-9A-Za-z-_]+)/spectra', ObjSpectraHandler),
        (r'/api/sources(/[0-9A-Za-z-_]+)/offsets', SourceOffsetsHandler),
        (r'/api/sources(/[0-9A-Za-z-_]+)/finder', SourceFinderHandler),
        (r'/api/sources(/.*)?', SourceHandler),
        (r'/api/spectrum(/[0-9]+)?', SpectrumHandler),
        (r'/api/spectrum/parse/fits', SpectrumFITSFileParser),
        (r'/api/spectrum/fits(/[0-9]+)?', SpectrumFITSFileHandler),
        (r'/api/streams(/[0-9]+)/users(/.*)?', StreamUserHandler),
        (r'/api/streams(/[0-9]+)?', StreamHandler),
        (r'/api/sysinfo', SysInfoHandler),
        (r'/api/taxonomy(/.*)?', TaxonomyHandler),
        (r'/api/telescope(/[0-9]+)?', TelescopeHandler),
        (r'/api/thumbnail(/[0-9]+)?', ThumbnailHandler),
        (r'/api/user(/.*)?', UserHandler),
        (r'/api/internal/tokens(/.*)?', TokenHandler),
        (r'/api/internal/profile', ProfileHandler),
        (r'/api/internal/dbinfo', DBInfoHandler),
        (r'/api/internal/source_views(/.*)?', SourceViewsHandler),
        (r'/api/internal/source_counts(/.*)?', SourceCountHandler),
        (r'/api/internal/plot/photometry/(.*)', PlotPhotometryHandler),
        (r'/api/internal/plot/spectroscopy/(.*)', PlotSpectroscopyHandler),
        (r'/api/internal/instrument_forms', RoboticInstrumentsHandler),
        (r'/api/internal/plot/airmass/(.*)', PlotAirmassHandler),
        (r'/api/internal/log', LogHandler),
        (r'/api/internal/recent_sources(/.*)?', RecentSourcesHandler),
        (r'/api/.*', InvalidEndpointHandler),
        (r'/become_user(/.*)?', BecomeUserHandler),
        (r'/logout', LogoutHandler),
        # User-facing pages
        (r'/.*', MainPageHandler),  # Route all frontend pages, such as
        # `/source/g647ba`, through the main page.
        #
        # Refer to Main.jsx for routing info.
    ]

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

    app = tornado.web.Application(handlers, **settings)
    models.init_db(**cfg['database'])
    baselayer_model_util.create_tables()
    model_util.setup_permissions()
    app.cfg = cfg

    admin_token = model_util.provision_token()
    with open('.tokens.yaml', 'w') as f:
        f.write(f'INITIAL_ADMIN: {admin_token.id}\n')
    with open('.tokens.yaml', 'r') as f:
        print('-' * 78)
        print('Tokens in .tokens.yaml:')
        print('\n'.join(f.readlines()), end='')
        print('-' * 78)

    model_util.provision_public_group()

    app.openapi_spec = openapi.spec_from_handlers(handlers)

    return app
