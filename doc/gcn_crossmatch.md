# Scanning GCN events for optical counterparts

SkyPortal can crossmatch broker alerts against the localization of a GCN event
and raise whatever falls inside it as candidates to scan. This works for any
event with a localization, e.g. Einstein Probe and Swift XRT
error circles, Fermi and GW skymaps, against any broker implementing
`query_alerts` (BOOM, Babamul, ALeRCE, Fink, Lasair, …).

## How it works

The `gcn_crossmatch` service walks every event still inside its active window.
For each one, and for each active broker:

1. The localization is reduced to a **search cone**. Cone localizations (EP,
   Swift XRT) give this directly; skymaps are bounded using the stored 90%
   credible contour. A localization that cannot be bounded, or whose bound
   exceeds `max_radius_deg`, is skipped and logged — never guessed at.
2. The broker is queried inside that cone, restricted to an alert-JD window
   around the event, with **quality cuts applied broker-side** (see below).
3. Returned alerts are checked for **real containment** against the
   localization's HEALPix tiles. As the cone over-selects, this decides
   candidate membership.
4. Survivors become an `Obj` plus a `Candidate` against the configured filter,
   so they appear on the scanning page.
5. Each match is annotated with how it relates to the event (below).

Events are re-queried while they stay active, because alerts keep arriving after
the trigger. Each pass resumes from the newest alert already seen rather than
from wall-clock time, so late-arriving alerts are not skipped.

A one-shot **archival** pass also searches the window *before* the event. Those
alerts cannot have been caused by it, so they rule a candidate out: a position
already flaring last month is a variable, not a counterpart. Such matches carry
`prior_activity: true` on the annotation.

## Configuring the quality-cut filter

Without cuts, every artifact, asteroid and variable star inside the error region
is reported. The cuts are expressed as a **broker filter**, so they are
versioned and editable in the filter builder rather than frozen in code.

1. Create a filter on the broker (for BOOM, an aggregation pipeline) holding the
   cuts you want. A reasonable ZTF starting point is in `ZTF_QUALITY_CUTS` in
   `skyportal/utils/gcn_crossmatch.py`: real/bogus thresholds (`rb`, `drb`),
   positive subtractions only, solar-system rejection, stellar rejection by
   `sgscore`/`distpsnr`, and a PS1 red-star colour cut.
2. Create the corresponding SkyPortal `Filter`, whose `altdata` carries
   `{"boom": {"filter_id": "<broker filter uuid>"}}`.
3. Point the service at it:

```yaml
gcn_crossmatch:
  enabled: True
  filter_id: 42        # the SkyPortal Filter id
```

The service reads that filter's **active version** and prepends the cone to it,
so cuts run on the broker and only survivors cross the wire. With `filter_id`
unset it falls back to the built-in cuts, which works but is frozen — and
without a filter no `Candidate` can be created, so nothing reaches the scanning
page.

> **Choose the filter's group deliberately.** A candidate is visible to the
> filter's group. Annotations inherit the *event's* groups, so the link between
> an object and a restricted event stays restricted, but the candidate itself
> does not. For a proprietary stream, point `filter_id` at a filter whose group
> matches that stream's audience.

## Configuration reference

All settings live under `gcn_crossmatch` in `config.yaml`:

| Setting | Default | Meaning |
|---|---|---|
| `enabled` | `False` | Run the service at all |
| `poll_interval` | `300` | Seconds between passes |
| `filter_id` | unset | SkyPortal Filter holding the quality cuts |
| `survey` | `ZTF` | Survey whose alerts are searched |
| `max_event_age` | `31.0` | Days; older events are no longer crossmatched |
| `recheck_interval_minutes` | `10.0` | Minimum gap before re-querying an event |
| `delta_t_before` / `delta_t_after` | `1.0` / `31.0` | Query window around the event, in days |
| `archival` / `archival_days` | `True` / `31.0` | One-shot pre-event search |
| `max_radius_deg` | `5.0` | Skip localizations bounding wider than this |
| `credible_level` | `90` | Contour used to bound non-cone localizations |
| `cumprob` | `0.95` | Cumulative probability defining "inside" |
| `max_alerts` | `500` | Cap per event, per broker, per pass |

## Scanning the results

Matches appear on the **candidates** page under the configured filter, like any
other candidates. Each carries an annotation with origin `GCN-crossmatch`, keyed
by event, holding the fields the reviewer needs:

| Field | Meaning |
|---|---|
| `delta_t` | Days between the event and the alert |
| `distance_arcmin` | Separation from the localization centre |
| `distance_ratio` | That separation as a fraction of the error radius |
| `age` | Days since the object's first detection |
| `drb` | Deep-learning real/bogus score |
| `sgscore`, `distpsnr` | Star/galaxy score and distance to the nearest PS1 source |
| `ssdistnr`, `ssmagnr` | Proximity to a known solar-system object |
| `ndethist` | Number of prior detections |
| `event_mjd` | Event time, MJD |
| `prior_activity` | Set when the position was already active before the event |

Because these are annotations, they can be sorted and filtered on the scanning
page — `delta_t` and `distance_arcmin` are the usual first cut, and
`prior_activity` is the quickest way to discard variables.

Once a candidate is saved to a group, it appears as a source on that event's
page in the usual way.

## Per-event progress and requeuing

```
GET  /api/gcn_event/{dateobs}/crossmatch
POST /api/gcn_event/{dateobs}/crossmatch     # requires Manage GCNs
```

`GET` returns per-broker progress: when the event was last queried, how far
through the alert stream it has got, how many matches it has produced, and any
error. `POST` resets that state so the next pass re-queries from the start of
the window, archival pass included; you can use it after changing the filter or the
search parameters.

## Finding the events

The **gcn_events** page filters by group, so a proprietary stream can be
separated from public alerts. Group filtering narrows within what you can
already read; it never widens access.
