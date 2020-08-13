import tornado.web

from baselayer.app.app_server import MainPageHandler
from baselayer.app import model_util as baselayer_model_util

from skyportal.handlers import BecomeUserHandler, LogoutHandler
from skyportal.handlers.api import (
    AssignmentHandler,
    CandidateHandler,
    ClassificationHandler,
    CommentHandler,
    CommentAttachmentHandler,
    FilterHandler,
    FollowupRequestHandler,
    GroupHandler,
    GroupUserHandler,
    PublicGroupHandler,
    GroupStreamHandler,
    InstrumentHandler,
    InvalidEndpointHandler,
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
    ObjSpectraHandler,
    StreamHandler,
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
    TokenHandler,
    DBInfoHandler,
    ProfileHandler,
    InstrumentObservationParamsHandler,
    LogHandler,
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
        (r'/api/assignment(/.*)?', AssignmentHandler),
        (r'/api/candidates(/.*)?', CandidateHandler),
        (r'/api/classification(/[0-9]+)?', ClassificationHandler),
        (r'/api/comment(/[0-9]+)?', CommentHandler),
        (r'/api/comment(/[0-9]+)/attachment', CommentAttachmentHandler),
        (r'/api/filters(/.*)?', FilterHandler),
        (r'/api/followup_request(/.*)?', FollowupRequestHandler),
        (r'/api/groups/public', PublicGroupHandler),
        (r'/api/groups(/[0-9]+)/streams(/[0-9]+)?', GroupStreamHandler),
        (r'/api/groups(/[0-9]+)/users(/.*)?', GroupUserHandler),
        (r'/api/groups(/[0-9]+)?', GroupHandler),
        (r'/api/instrument(/[0-9]+)?', InstrumentHandler),
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
        (r'/api/internal/plot/photometry/(.*)', PlotPhotometryHandler),
        (r'/api/internal/plot/spectroscopy/(.*)', PlotSpectroscopyHandler),
        (r'/api/internal/instrument_obs_params', InstrumentObservationParamsHandler),
        (r'/api/internal/log', LogHandler),
        (r'/api/.*', InvalidEndpointHandler),
        (r'/become_user(/.*)?', BecomeUserHandler),
        (r'/logout', LogoutHandler),
        # User-facing pages
        (r'/.*', MainPageHandler)  # Route all frontend pages, such as
        # `/source/g647ba`, through the main page.
        #
        # Refer to Main.jsx for routing info.
    ]

    settings = baselayer_settings
    settings.update({})  # Specify any additional settings here

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
