import tornado.web

from baselayer.app.app_server import (handlers as baselayer_handlers,
                                      settings as baselayer_settings,
                                      MainPageHandler)

from skyportal.handlers import (SourceHandler, CommentHandler, GroupHandler,
                                GroupUserHandler, PlotPhotometryHandler,
                                PlotSpectroscopyHandler, ProfileHandler,
                                BecomeUserHandler, LogoutHandler,
                                PhotometryHandler, TokenHandler)
from skyportal import models, model_util


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
        (r'/api/sources(/.*)?', SourceHandler),
        (r'/api/groups/(.*)/users/(.*)?', GroupUserHandler),
        (r'/api/groups(/.*)?', GroupHandler),
        (r'/api/plot/photometry/(.*)', PlotPhotometryHandler),
        (r'/api/plot/spectroscopy/(.*)', PlotSpectroscopyHandler),
        (r'/api/comment(/.*)?', CommentHandler),
        (r'/api/profile', ProfileHandler),
        (r'/api/photometry(/.*)?', PhotometryHandler),
        (r'/api/tokens(/.*)?', TokenHandler),
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
    model_util.create_tables()
    model_util.setup_permissions()
    app.cfg = cfg

    return app
