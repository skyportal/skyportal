# External Services (Plugins)

SkyPortal can run **external micro-services**: standalone "plugins" that live in
their own Git repository, are cloned into your instance, and run as supervised
background services alongside the core app. This is how instances ingest from
brokers or run bespoke background jobs without forking SkyPortal. Examples
include the [Lasair plugin](https://github.com/skyportal/lasair-skyportal-plugin)
(ingests LSST objects from the [Lasair](https://lasair.lsst.ac.uk/) broker) and
the [babamul plugin](https://github.com/skyportal/babamul-skyportal-plugin).

An external service is a normal Python program (`main.py`) that connects to the
SkyPortal database using SkyPortal's own models and helpers. SkyPortal takes care
of fetching it, checking that it is compatible with your version, and keeping it
running.

**How this differs from other extension mechanisms.** An external service is
distinct from:

- **[Extensions](extensions.html)** copy custom handlers/components *into* the
  SkyPortal source tree at build time.
- **[External analysis services](analysis.html)** receive data over HTTP and
  return results via a webhook.

An *external service* is neither: it is a separate repository that SkyPortal
clones and runs as a long-lived background process with direct database access.

## How it works

External services are declared in your `config.yaml` under `services.external`.
On startup (`make run`), SkyPortal:

1. reads each entry under `services.external`;
2. **clones** the plugin's `repo` at the requested `rev` into
   `services/<name>` (a shallow clone; if the directory already exists and has
   local modifications, it is left untouched so you can hack on it in place);
3. **checks compatibility**: the plugin declares which SkyPortal version it
   supports, and the service is skipped if your installed version does not match;
4. **supervises** the plugin: it generates a supervisor program that runs the
   plugin's `main.py` with `PYTHONPATH="."` set to the SkyPortal root, so
   `baselayer` and `skyportal` are importable, and restarts it if it exits.

## Enabling a service

Add a block under `services.external` in your instance's `config.yaml` (in the
SkyPortal root, alongside `config.yaml.defaults`). Using Lasair as the example:

```yaml
services:
    external:
        lasair:                      # the service name; becomes services/lasair
            repo: https://github.com/skyportal/lasair-skyportal-plugin.git
            rev: main                # branch, tag, or commit (default: main)
            params:                  # arbitrary config handed to the plugin
                lasair:
                    token: <YOUR_LASAIR_API_TOKEN>
                ingest:
                    poll_interval: 86400
                    group_ids: [1]
                    lsst_instrument_name: LSST
                    filter_ids: []
                    queries:
                        - name: nightly
                          fields: 'objects.diaObjectId, objects.ra, objects.decl'
                          tables: objects
                          conditions: 'objects.nDiaSources > 2 AND objects.firstDiaSourceMjdTai > (mjdnow() - 40)'
```

Each entry accepts:

- **`repo`**: Git URL to clone. If omitted, SkyPortal assumes the code is
  already present in `services/<name>` and only supervises it.
- **`rev`**: Branch, tag, or commit to check out. Defaults to `main`.
- **`params`**: Free-form configuration passed through to the plugin. SkyPortal
  does not interpret it; the plugin reads it (see *Writing a plugin* below). Each
  plugin documents its own `params` in its `config.yaml.defaults` and
  `README`.

A service runs when it is present under `services.external`, clones successfully,
passes the compatibility check, and is **not** listed in `services.disabled`.

### Install the plugin's dependencies

SkyPortal **does not install a plugin's Python dependencies for you**; it only
verifies version compatibility. Install them into the SkyPortal environment
yourself before starting. For Lasair:

```bash
cd /path/to/skyportal
source .venv/bin/activate     # the environment created when you installed SkyPortal
uv pip install lasair         # the plugin's dependency (see its pyproject.toml)
```

### Start it

Start SkyPortal normally from its root directory:

```bash
make run
```

On startup the plugin is cloned into `services/lasair` and launched. Its output
goes to `log/lasair_service.log`.

## Writing a plugin

A plugin is a Git repository containing at least:

- **`main.py`**: the entry point SkyPortal runs. (You may instead ship your own
  `supervisor.conf` if you need custom process settings; otherwise SkyPortal
  generates one that runs `main.py`.)
- **`pyproject.toml`**: with a `[project]` name and a `[tool.compatibility]`
  section declaring the SkyPortal version(s) it supports. **This section is
  required**: a plugin that declares no compatibility is treated as incompatible
  and skipped.

```toml
[project]
name = "lasair"
version = "0.1.0"
dependencies = ["lasair"]

[tool.compatibility]
compatible-with = [
  { name = "skyportal", version = ">=1.4.0" },
]
```

Inside `main.py`, load the merged SkyPortal config and read your own `params`
from `services.external.<name>.params`:

```python
from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log

log = make_log("lasair")

if __name__ == "__main__":
    env, cfg = load_env()
    init_db(**cfg["database"])

    params = cfg.get("services.external.lasair.params", {})
    # ... your polling / ingestion loop, writing via skyportal models ...
```

From here you have the full `skyportal` model layer available (e.g. `Obj`,
`Photometry`, `add_external_photometry`) and can write directly to the database.
Ship a `config.yaml.defaults` in your repo documenting every `params` key so
operators know what to set.

## Disabling a service

Remove the block from `services.external`, or add the service name to
`services.disabled`:

```yaml
services:
    disabled:
        - lasair
```
