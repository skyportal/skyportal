# Broker ingestion

Ingestion runs in `services/broker_ingest`, one asyncio task per active broker
whose provider implements `run_ingestion`. It is off unless the config says
otherwise:

```
brokers:
  ingest_enabled: True
  ingest_processes: 1
```

`ingest_processes` sets how many OS processes supervisor starts. Process 0 runs
every broker. Higher-index processes run only providers that are safe to
replicate, which means Kafka consumers, since Kafka rebalances a consumer group
across them. REST pollers are not duplicated.

## What a survey needs

An alert becomes a candidate only if all of these are true:

1. **The broker subscribes to its topic.** Topics come from the broker's
   `altdata['kafka']['topics']`.
2. **The survey has a zeropoint.** `ZP_PER_SURVEY` in
   `skyportal/broker_apis/_save.py` maps the survey name to an AB zeropoint. A
   survey missing from it raises on every alert, which shows up in the ingest
   log. The value follows the units the points arrive in: flux in nJy is scaled
   to Jy and takes 8.9, magnitudes are converted against 23.9.
3. **Its bands map to filters.** Filters are named `<survey><band>` by default.
   A survey that names its filters otherwise needs an entry in
   `BAND_TO_FILTER_PER_SURVEY`, alongside the zeropoints.
4. **A stream carries it.** The stream's `altdata` names the collection and the
   program ids it admits.
5. **Filters are paired with the broker's own.** A `Filter` row carries the
   broker's filter id in `altdata['boom']['filter_id']`, and ingestion maps that
   back to the SkyPortal filter.

## Names do not have to match

Three names are involved and they are set independently.

- The **survey** name is what the alert carries, and it is the key into
  `ZP_PER_SURVEY`.
- The **stream** name is a SkyPortal label for the same data.
- The **topic** is the broker's, usually `<survey>_alerts_results`.

## Where the configuration lives

Broker data, including the topic list and the credentials, lives in
`Broker.altdata`, set through the API or the `/brokers/{id}` page.

## Adding a survey to a broker

1. Add `<SURVEY>` to `ZP_PER_SURVEY` if it is not already there. Use the
   zeropoint the survey's photometry is already on, so light curves stay
   continuous across a change of broker.
2. Check how its filters are named. If they are not `<survey><band>`, add the
   band mapping.
3. Add the topic to the broker's `altdata['kafka']['topics']`.
4. Check that the stream exists, and that each filter carries its partner's id
   in `altdata`.
5. Restart `broker_ingest`. Topics are read once, when the consumer starts.

## Replaying a backlog

A consumer group that has already read a topic will not read it again, and a
broker configured with `auto_offset_reset: latest` starts at the end. To take in
messages a broker has missed, add a second broker row that reads only that
topic, with its own `group_id` and `auto_offset_reset: earliest`, then
deactivate it once it has caught up.

Re-consuming an alert is safe. The save path looks for an existing candidate
with the same `passing_alert_id` before adding one, so a replay that overlaps
normal ingestion does not double up.

Retention is the limit. A backlog older than the topic's retention is gone,
whatever the offsets say.
