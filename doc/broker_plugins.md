# Broker plugins

SkyPortal integrates with external alert **brokers** (e.g. BOOM, Kowalski, Fink,
Lasair) through a pluggable provider interface, modeled on the follow-up
facility APIs (`skyportal/facility_apis/`). A broker provider is a registered
class; a configured connection to a broker is a `Broker` database record that
supplies the per-instance endpoints/credentials the provider operates on.

This lets a new broker be added as a provider class (and shared helpers) instead
of forking SkyPortal or re-deriving the same integration in every deployment.

## Concepts

- **`BrokerAPI`** (`skyportal/broker_apis/interface.py`), the base class. Every
  operation is a stub that raises `NotImplementedError`; a provider overrides
  only what it supports.
- **Registry**, providers are listed in the `BROKERS` tuple in
  `skyportal/broker_apis/__init__.py`. The `broker_classnames` Postgres enum
  (`skyportal/enum_types.py`) is derived from it, so provider names are
  validated at the database level (mirrors `api_classnames`). Append new
  providers to the end of the tuple to keep the enum stable.
- **Capabilities**, `BrokerAPI.implements()` reports which operations a
  provider overrode. Handlers gate on it, and the frontend can show/hide
  features accordingly.
- **`Broker` model** (`skyportal/models/broker.py`), one configured broker:
  `name`, `broker_classname` (which provider), `active`, and encrypted
  `altdata` (endpoints/credentials, mirroring `Allocation.altdata`). Only system
  admins may create/update/delete brokers, and `altdata` is redacted from
  non-admins.
- **Site defaults**, `default_alert_search` and `default_crossmatch` name the
  broker the source page's "Search alerts" button opens and the one its
  cross-matches (cone searches) run against. At most one broker holds each; pick them on the brokers page. The
  seeded data makes ALeRCE both.

## Operations

Interactive (SkyPortal → broker): `query_alerts`, `get_alert`, `get_cutouts`,
`cone_search`, `save_as_source`, and filter management (`get_filters`,
`create_filter`, `update_filter`, `delete_filter`, `test_filter`,
`filter_modules`).

Ingestion (broker → SkyPortal): `run_ingestion`, a long-lived consumer/poller
(see "Ingestion and filters" below).

## Ingestion and filters (end to end)

Once a broker is configured (a `Broker` record with valid `altdata`), ingestion,
running its filters and pulling in matching alerts, is driven by a background
service and gated by config.

### 1. Enable the ingestion service

The `broker_ingest` service (`services/broker_ingest/`) runs one task per active
broker whose provider implements `run_ingestion`. It is **off by default**; enable
it in your config and **restart** the app:

```yaml
brokers:
  ingest_enabled: true
```

With it disabled the service idles (it does not exit), so nothing is ever polled.
Confirm it via `make monitor` (the `broker_ingest` entry should be `RUNNING`) and
`log/broker_ingest.log`, which prints either `broker ingestion disabled ...` or
`starting ingestion for broker <id> (<name>)`.

`brokers.ingest_enabled` is a **config value**, not in the database, not in a
broker's `altdata`, and not exposed via the API. A broker's `run_ingestion: true`
capability only means the provider *supports* ingestion, not that it is running.

### 2. Attach filters

A `filter_kind: "query"` broker (e.g. Lasair) runs one query per SkyPortal `Filter`
linked to it. Create a `Filter` (on a `Stream` + your `Group`), then attach the
query, for Lasair the `SELECT / FROM / WHERE` parts, from the broker page (or
`POST /api/brokers/<id>/filters/<filter_id>`). Filters are re-read every poll
cycle, so adding/editing one does **not** require a restart.

### 3. When and how often

`run_ingestion` polls **immediately** on start, then sleeps `altdata.poll_interval`
seconds (provider default; e.g. Lasair 86400 = daily, ALeRCE/ANTARES 3600), so the
first batch appears within seconds of the service starting, not after a full
interval. Changing `poll_interval` (or other broker `altdata`) is read once when a
broker's task starts, so **restart the ingestion service** to apply it.

### 4. Where results land

Matching objects are registered as **Candidates** under the passing filter and
appear on the **Candidates / Scanning page** filtered by it, not as Sources. From
there you review and save the ones worth keeping.

### 5. Auto-save

To save passing objects as **Sources** automatically (into the filter's group)
instead of only registering candidates, set the filter's **`autosave`** flag, the
"Auto-save passing objects as sources" checkbox in the Lasair filter builder, or
`POST /api/brokers/<id>/filters/<filter_id>` with `{"autosave": true}`. Objects
already saved to that group are skipped. Use it only when the filter is selective
enough to trust everything it passes; otherwise keep it off and tighten the
filter's conditions so scanning stays manageable.

## Endpoints

- `GET/POST/PATCH/DELETE /api/brokers[/{id}]`, manage `Broker` records.
- `GET /api/brokers/{id}/alerts[/{alert_id}]`, query alerts (dispatched to the
  broker's provider).
- `GET /api/internal/broker_apis`, capabilities + config schema of every
  registered provider (for the frontend).

## Writing a provider

1. Add `skyportal/broker_apis/mybroker.py` with a `MYBROKER(BrokerAPI)` class
   overriding the operations you support. Read per-instance config from
   `broker.altdata`. Provide `form_json_schema_config` (and optionally
   `ui_json_schema`, `surveys`, `validate_config`).
2. Append it to `BROKERS` in `skyportal/broker_apis/__init__.py`.
3. A database migration for the extended `broker_apis` enum is generated
   automatically.

See `skyportal/broker_apis/generic.py` (`GENERICBROKER`) for a working reference
that talks to any REST broker via a configured `base_url`/`token`.
