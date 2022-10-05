# SkyPortal Extensions

It is common for specific instances of SkyPortal to employ "extensions", which use added components and APIs not available in the baseline app, usually because of particular forms of data access and distribution. Some examples include [Fritz](https://github.com/fritz-marshal/fritz) or [SkyPortal-GRANDMA](https://github.com/grandma-collaboration/icare).

For the APIs, they will have a folder: extensions/skyportal/skyportal/handlers/api
For redux, they will have a folder: extensions/skyportal/static/js/ducks
For the components, they will have a folder: extensions/skyportal/static/js/components

When deploying, files are copied into each of these SkyPortal folders from your repository.

For APIs in particular, a dedicated `app_server.py` needs to be created. To deploy, it will take a form similar to [this](https://github.com/fritz-marshal/fritz/blob/main/extensions/skyportal/skyportal/app_server_fritz.py), where in addition to the baseline application loaded with

```from skyportal.app_server import make_app```

Custom handlers are added as follows (taking Fritz as an example):

```
from skyportal.handlers.api.alert import (
    AlertHandler,
    AlertAuxHandler,
    AlertCutoutHandler,
    AlertTripletsHandler,
)
from skyportal.handlers.api.archive import (
    ArchiveCatalogsHandler,
    ArchiveHandler,
    CrossMatchHandler,
)
from skyportal.handlers.api.kowalski_filter import KowalskiFilterHandler
from skyportal.handlers.api.tns_info import TNSInfoHandler


fritz_handlers = [
    # Fritz-specific API endpoints
    # Alerts
    (r"/api/alerts(/.+)?", AlertHandler),
    (r"/api/alerts_aux(/.+)?", AlertAuxHandler),
    (r"/api/alerts_cutouts(/.+)?", AlertCutoutHandler),
    (r"/api/alerts_triplets(/.+)?", AlertTripletsHandler),
    # Archive
    (r"/api/archive", ArchiveHandler),
    (r"/api/archive/catalogs", ArchiveCatalogsHandler),
    (r"/api/archive/cross_match", CrossMatchHandler),
    # Alert Stream filter versioning via K:
    (r"/api/filters/([0-9]+)?/v", KowalskiFilterHandler),
    (r"/api/tns_info/(.*)", TNSInfoHandler),
]
```

and then those handlers are added to the baseline app:

```
    app = make_app(cfg, baselayer_handlers, baselayer_settings, process, env)
    app.add_handlers(r".*", fritz_handlers)  # match any host
```

This is known as the "app factory", which is a function used to create the Tornado application. This is often needed to add additional routes, or do certain setup procedures before the application is run.

To add accessible routes to the web interface, one configures the config.yaml as follows.

```
    routes:
      - path: "/alerts"
        component: Alerts
      - path: "/alerts/ztf/:id"
        component: ZTFAlert
      - path: "/archive"
        component: Archive
```

where each path in the browser is tied to a specific React.js component as rendered.

For certain Javascript components we also have "Plugins", through which functionality can be added to extend those pages. These are currently available on the Source (`SourcePlugins.jsx`), Candidates (`CandidatePlugins.jsx`), Filters (`FilterPlugins.jsx`), and About (`AboutPlugins.jsx`) pages.

Settings for extensions can be specified in the `config.yaml`. Taking fritz as an example again, here is a segment that configures `kowalski`:

```
  kowalski:
    protocol: https
    host: kowalski.caltech.edu
    port: 443
    token: YOUR_TOKEN_HERE
```

Your extension can read the configuration as follows:


```
  from baselayer.app.env import load_env
  env, cfg = load_env()
```

and then access specific entries with calls like:

```
  protocol = cfg["app.kowalski.protocol"]
