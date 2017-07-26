import tornado.web

from baselayer.app import  model_util
from baselayer.app.app_server import (handlers as baselayer_handlers,
                                      settings as baselayer_settings,
                                      MainPageHandler)
from baselayer.app.config import load_config

from skyportal.handlers import (SourceHandler, SourceCommentsHandler,
                                CommentHandler,
                                PlotPhotometryHandler,
                                PlotSpectroscopyHandler)
from skyportal import models


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
        (r'/sources(/.*)?', SourceHandler),
        (r'/source/(.*)/comments$', SourceCommentsHandler),
        (r'/comment(/.*)?', CommentHandler),
        # TODO combine plot handlers? one per plot seems excessive
        (r'/plot_photometry/(.*)', PlotPhotometryHandler),
        (r'/plot_spectroscopy/(.*)', PlotSpectroscopyHandler),
        (r'/.*', MainPageHandler)  # route all frontend pages, such as
                                   # /sources/g647ba through main page
    ]

    settings = baselayer_settings
    settings.update({})  # Specify any additional settings here

    app = tornado.web.Application(handlers, **settings)
    models.init_db(**cfg['database'])
    model_util.create_tables()
    app.cfg = cfg

    return app
