# BOOM alert filters

SkyPortal can integrate with the BOOM alert broker to let group admins author,
test, and manage the alert-stream filters that decide which alerts become
candidates in SkyPortal.

## Configuration

The integration is configured through the `boom` section:

```yaml
boom:
  protocol: http
  host: localhost
  port: 4000
  username: admin
  password: adminsecret
  filter_modules:
    mongodb_uri: "mongodb://mongoadmin:mongoadminsecret@localhost:27017/?authSource=admin"
    database: "boom_filter_modules"
```

`username`/`password` are used to obtain an API token from the BOOM instance.
The `filter_modules` database holds the filter builder's reusable elements
(blocks, variables, and per-survey alert schemas).

## Concepts

- A SkyPortal `Filter` row is linked to a BOOM filter through
  `Filter.altdata["boom"]["filter_id"]`. Renaming a filter through
  `PATCH /api/filters/{id}` propagates the rename to BOOM.
- BOOM filters are MongoDB aggregation pipelines evaluated against each
  incoming alert; alerts that pass are pushed to SkyPortal as candidates of
  the filter's group.

## The filter builder

The filter page (`/filter/:id`) mounts a visual builder (via the
`FilterPlugins` extension point) in which pipeline stages are composed from
condition blocks, reusable modules (e.g. catalog cross-matches), variables,
and LaTeX-rendered expressions. Filters can be test-run against recent alerts
before being activated.

## API

- `GET/POST/PATCH/DELETE /api/boom/filters/...` — manage the BOOM-side filter
  (pipeline versions and which version is active).
- `GET/POST /api/boom/filter_modules/...` — reusable builder elements and
  per-survey alert schemas.
- `POST /api/boom/run_filter` — test-run a filter version against alerts.

The corresponding API tests require a reachable BOOM instance seeded with
reference data and skip themselves otherwise.
