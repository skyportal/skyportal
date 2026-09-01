# MCP server

SkyPortal exposes a [Model Context Protocol](https://modelcontextprotocol.io)
endpoint at `/mcp` so AI assistants can read and write data through the same
API and permission checks as any other client.

The endpoint implements protocol revision
[2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28) over the
Streamable HTTP transport, and only that revision: there is no `initialize`
handshake, no session, and no server-initiated stream. Every request is a
self-contained JSON-RPC POST that carries its protocol version and client
capabilities in `_meta`, so requests can be served by any app process behind
the load balancer. Clients that still use the pre-2026 `initialize` handshake
are rejected with an `UnsupportedProtocolVersion` error naming the supported
revision.

## Authentication

Send a SkyPortal API token in the `Authorization` header, either as
`Bearer <token>` (MCP convention) or `token <token>` (SkyPortal convention).
Tools run with that token's permissions.

## Methods

| Method            | Purpose                                                    |
| ----------------- | ---------------------------------------------------------- |
| `server/discover` | Supported protocol versions, capabilities, server identity |
| `tools/list`      | Tool definitions with input schemas                        |
| `tools/call`      | Invoke a tool                                              |

## GCN events

Five tools cover multi-messenger events, so an assistant can answer questions
about a trigger and reply in the discussion on it.

| Tool                        | Purpose                                            |
| --------------------------- | -------------------------------------------------- |
| `get_gcn_events`            | List or search events; `partialdateobs` matches a dateobs prefix or an alias |
| `get_gcn_event`             | One event in full, including its GCN circulars      |
| `get_gcn_event_extractions` | Structured data a pipeline extracted from the circulars |
| `get_gcn_event_comments`    | The discussion on the event                         |
| `post_gcn_event_comment`    | Reply in that discussion                            |

`get_gcn_event_extractions` reads the `gcneventextractions` table, where any
producer may store machine-readable values parsed out of an event's prose.
`origin` names the producer and the payload is that producer's own shape, so
filter by `origin` when you care which pipeline it came from.

## Tools

Sources, photometry and spectra are read and written with `get_sources` /
`post_source`, `get_photometry` / `post_photometry` and `get_spectra` /
`post_spectrum`. `analyze_light_curve` summarises how a source evolves per band.

Broker filters have their own set, covering the whole life of a filter:

| Tool                             | Purpose                                     |
| -------------------------------- | ------------------------------------------- |
| `post_filter`                    | Create a filter on a stream and group       |
| `get_broker_filter`              | Its versions, which is active, its settings |
| `run_broker_filter`              | Preview which alerts a pipeline passes      |
| `post_broker_filter_version`     | Add a version from a compiled pipeline      |
| `activate_broker_filter_version` | Make a version the one the broker runs      |
| `diff_broker_filter_versions`    | Unified diff between two versions           |

Posting a version does not activate it, so a version can be previewed and
compared before it goes live. `diff_broker_filter_versions` defaults to the two
most recent versions, which is what answers "this filter stopped passing alerts
after I edited it -- what changed?".

`run_broker_filter` writes nothing. A pipeline that returns no alerts there will
pass none in production, so it is worth running before activating a version.
