# Broker plugins

SkyPortal integrates with external alert **brokers** (e.g. BOOM, Kowalski, Fink,
Lasair) through a pluggable provider interface, modeled on the follow-up
facility APIs (`skyportal/facility_apis/`). A broker provider is a registered
class; a configured connection to a broker is a `Broker` database record that
supplies the per-instance endpoints/credentials the provider operates on.

This lets a new broker be added as a provider class (and shared helpers) instead
of forking SkyPortal or re-deriving the same integration in every deployment.

## Concepts

- **`BrokerAPI`** (`skyportal/broker_apis/interface.py`) — the base class. Every
  operation is a stub that raises `NotImplementedError`; a provider overrides
  only what it supports.
- **Registry** — providers are listed in the `BROKERS` tuple in
  `skyportal/broker_apis/__init__.py`. The `broker_classnames` Postgres enum
  (`skyportal/enum_types.py`) is derived from it, so provider names are
  validated at the database level (mirrors `api_classnames`). Append new
  providers to the end of the tuple to keep the enum stable.
- **Capabilities** — `BrokerAPI.implements()` reports which operations a
  provider overrode. Handlers gate on it, and the frontend can show/hide
  features accordingly.
- **`Broker` model** (`skyportal/models/broker.py`) — one configured broker:
  `name`, `broker_classname` (which provider), `active`, and encrypted
  `altdata` (endpoints/credentials, mirroring `Allocation.altdata`). Only system
  admins may create/update/delete brokers, and `altdata` is redacted from
  non-admins.

## Operations

Interactive (SkyPortal → broker): `query_alerts`, `get_alert`, `get_cutouts`,
`cone_search`, `save_as_source`, and filter management (`get_filters`,
`create_filter`, `update_filter`, `delete_filter`, `test_filter`,
`filter_modules`).

Ingestion (broker → SkyPortal): `run_ingestion` — a long-lived consumer/poller,
implemented on top of shared ETL helpers in a later stage.

## Endpoints

- `GET/POST/PATCH/DELETE /api/brokers[/{id}]` — manage `Broker` records.
- `GET /api/brokers/{id}/alerts[/{alert_id}]` — query alerts (dispatched to the
  broker's provider).
- `GET /api/internal/broker_apis` — capabilities + config schema of every
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
