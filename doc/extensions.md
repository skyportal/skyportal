# SkyPortal Extensions

It is common for specific instances of SkyPortal to employ "extensions", which use added components and APIs not available in the baseline app, usually because of particular forms of data access and distribution. Some examples include [Fritz](https://github.com/fritz-marshal/fritz) or [SkyPortal-GRANDMA](https://github.com/grandma-collaboration/icare).

For the APIs, they will have a folder: extensions/skyportal/skyportal/handlers/api
For the ducks, they will have a folder: extensions/skyportal/static/js/ducks
For the components, they will have a folder: extensions/skyportal/static/js/components

When deploying, each of these folders are copied into skyportal in their corresponding folder.

For the APIs in particular, a dedicated app_server.py needs to be created. To deploy, it will take a form similar to [this](https://github.com/fritz-marshal/fritz/blob/main/extensions/skyportal/skyportal/app_server_fritz.py), where in addition to the baseline application loaded with

```from skyportal.app_server import make_app```

specific handlers are added like (taking Fritz as an example):

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

For the components, we also have specific ``Plug Ins,'' where specific components can be added to extend individual pages. These are currently available on the Source Page (SourcePlugins.jsx), Candidates Page (CandidatePlugins.jsx), Filters Page (FilterPlugins.jsx) and About Page (AboutPlugins.jsx).

Finally, extra entries can be added directly in the config.yaml as needed for these extensions. Taking fritz as an example again, access information for kowalski and gloria is added to the config:

```
  kowalski:
    protocol: https
    host: kowalski.caltech.edu
    port: 443
    token: YOUR_TOKEN_HERE

  gloria:
    protocol: https
    host: gloria.caltech.edu
    port: 443
    token: YOUR_TOKEN_HERE
```
