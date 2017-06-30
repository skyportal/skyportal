import tornado.web

from baselayer.app import  model_util
from baselayer.app.app_server import (handlers as baselayer_handlers,
                                      settings as baselayer_settings,
                                      MainPageHandler)
from baselayer.app.config import load_config

from skyportal.handlers import (SourceHandler, PlotPhotometryHandler,
                                PlotSpectroscopyHandler)
from skyportal import models


def make_app(config_files=None, debug=False):
    """Create and return a `tornado.web.Application` object with specified
    handlers and settings.

    Parameters
    ----------
    config_files : list of str
        Filenames of configuration files, loaded in the order specified.
        By default, read 'config.yaml.example' for default values, overridden
        by 'config.yaml'.
    debug : bool
        Whether or not to start the app in debug mode.  In debug mode,
        changed source files are immediately reloaded.

    """
    # Cesium settings
    cfg = load_config(config_files)

    if cfg['cookie_secret'] == 'abc01234':
        print('!' * 80)
        print('  Your server is insecure. Please update the secret string ')
        print('  in the configuration file!')
        print('!' * 80)

    handlers = baselayer_handlers + [
        (r'/sources(/.*)?', SourceHandler),
        # TODO combine plot handlers? one per plot seems excessive
        (r'/plot_photometry/(.*)', PlotPhotometryHandler),
        (r'/plot_spectroscopy/(.*)', PlotSpectroscopyHandler),
        (r'/.*', MainPageHandler)  # route all frontend pages, such as
                                   # /sources/g647ba through main page
    ]

    settings = baselayer_settings
    settings.update({'autoreload': debug})  # Specify any additional settings here

    app = tornado.web.Application(handlers, **settings)
    models.init_db(**cfg['database'])
    model_util.create_tables()
    app.cfg = cfg

    return app
