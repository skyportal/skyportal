# Services

SkyPortal runs as a set of supervised background processes. On `make run`, every
directory under `services.paths` (`baselayer/services/` and `services/`, plus any
[external service](external_services) you cloned) becomes a supervisor program.

## Disabling services

Everything runs by default. Name what you do not want in your `config.yaml`:

```yaml
services:
  disabled:
    - dask
    - slack
```

Or invert the choice, turning everything off and naming what to run:

```yaml
services:
  disabled: "*"
  enabled:
    - app
    - nginx
```

A name matching no service is ignored silently, so check the spelling below when
a service you meant to disable keeps starting.

Most services already sleep when the feature they serve is unconfigured, so
disabling them saves a process and its database connections, not CPU. The ones
worth listing are those that poll for something you do not use.

## baselayer services

| Service             | Role                                                                          | Disable                                    |
| ------------------- | ----------------------------------------------------------------------------- | ------------------------------------------ |
| `app`               | Tornado backends serving the API and the frontend, `server.processes` of them | Required                                   |
| `nginx`             | Reverse proxy in front of the app processes                                   | Required                                   |
| `migration_manager` | Applies alembic migrations at startup, then answers readiness checks          | Required                                   |
| `message_proxy`     | ZeroMQ proxy carrying internal messages to `websocket_server`                 | Required                                   |
| `websocket_server`  | Pushes live updates to open browsers                                          | Required                                   |
| `status_server`     | Serves the "being provisioned" page until the app answers                     | Never, it only serves the boot page        |
| `cron`              | Runs the jobs declared under `cron` in the config                             | No jobs declared                           |
| `external_logging`  | Tails the logs and forwards them to a remote syslog                           | Not shipping logs                          |
| `fake_oauth2`       | Stub Google OAuth provider for `server.auth.debug_login`                      | Real OAuth                                 |
| `rspack`            | Watches the frontend sources and rebuilds the bundle                          | Production, where the bundle is built once |
| `dask`              | Scheduler and four workers that nothing in SkyPortal connects to              | Always, disabled by default                |

## SkyPortal services

| Service                            | Role                                                                                    | Disable                                           |
| ---------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `health_monitor`                   | Polls each app process and restarts the ones that stop answering                        | Supervising the processes yourself                |
| `pgbouncer`                        | Bundled connection pooler                                                               | Already inert without `database.pooler.enabled`   |
| `notification_queue`               | Delivers user notifications (email, SMS, Slack, push)                                   | Never, notifications stop being delivered         |
| `facility_queue`                   | Submits and polls follow-up requests to observing facilities                            | No follow-up                                      |
| `observation_plan_queue`           | Builds and submits the observation plans of the [MMA](mma) workflow                     | No MMA                                            |
| `recurring_apis`                   | Calls the `RecurringAPI` records users created                                          | Feature unused                                    |
| `reminders`                        | Delivers the reminders users set on sources, GCN events and shifts                      | Feature unused                                    |
| `thumbnail_queue`                  | Fetches SDSS/LS/PS1 cutouts for new objects                                             | No outbound network                               |
| `tns_retrieval_queue`              | Matches your objects against TNS reports                                                | Idles without `app.tns.*`                         |
| `sharing_service_submission_queue` | Submits sources to TNS and Hermes for the sharing services                              | No sharing service                                |
| `jpl_sbident_queue`                | Answers "is this a known minor planet?" through JPL SBIdent                             | Feature unused                                    |
| `gcn_service`                      | Consumes GCN Kafka notices                                                              | Idles without `gcn.client_id`/`gcn.client_secret` |
| `gcn_crossmatch`                   | Crossmatches GCN alerts against sources, see [GCN crossmatch](gcn_crossmatch)           | Idles without `gcn_crossmatch.enabled`            |
| `ep_service`                       | Ingests candidates from the proprietary Einstein Probe feed                             | Idles without `einstein_probe.enabled`            |
| `scout_service`                    | Consumes the JPL Scout NEO ToO Kafka stream                                             | Idles without `scout.*`                           |
| `neofixer_service`                 | Polls NEOFixer target lists and annotates solar system objects                          | Idles without `neofixer.enabled`                  |
| `tess_sector`                      | Loads TESS sector footprints and annotates coverage                                     | Idles without `tess.enabled`                      |
| `broker_ingest`                    | Runs the ingestion loop of each active broker, see [broker ingestion](broker_ingestion) | Idles without `brokers.ingest_enabled`            |
| `hermes_skyportal_sync`            | Consumes the Hermes Kafka topic into sources and photometry                             | Idles without `app.hermes.sync.*`                 |
| `pdl_service`                      | Watches a PDL receiver directory and ingests earthquake QuakeML                         | No PDL client feeding it                          |
| `slack`                            | Proxies Slack notifications so the token stays server-side                              | No Slack integration                              |
| `assistant`                        | Answers posted assistant messages through the MCP endpoint                              | No `app.assistant` configured                     |
| `openai_analysis_service`          | [Analysis](analysis) backend: LLM summaries and embeddings                              | No `AnalysisService` record points at it          |
| `sn_analysis_service`              | [Analysis](analysis) backend: supernova light curve fitting                             | No `AnalysisService` record points at it          |
| `ngsf_analysis_service`            | [Analysis](analysis) backend: NGSF spectral fitting                                     | No `AnalysisService` record points at it          |
| `spectral_cube_analysis_service`   | [Analysis](analysis) backend: spectral cube extraction                                  | No `AnalysisService` record points at it          |
