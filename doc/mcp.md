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
the load balancer. A client that knows this revision but opens with an `initialize`
handshake anyway gets `MethodNotFound`: its version is fine, and only the
handshake is not.

## The pre-2026 handshake (deprecated)

Assistants that do not speak 2026-07-28 yet -- Codex, Cursor and others -- open
with `initialize` and then send bare JSON-RPC, with no `Mcp-Method` header and
no `_meta`. That profile is answered too, so those clients reach the same tools.

It is deprecated, and is here only until those clients catch up. Two things keep
it from costing anything structurally:

- **No session is issued.** The old transport makes `Mcp-Session-Id` optional,
  and declining to send one leaves every request independent of the process that
  served the handshake -- the same property the modern profile has by design.
- **Nothing new is built on it.** `server/discover` does not advertise it, the
  strict header and `_meta` checks still apply to every 2026-07-28 request, and
  each handshake is logged with the client that sent it, so it is possible to
  tell when the path is safe to delete.

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

| Tool                        | Purpose                                                                      |
| --------------------------- | ---------------------------------------------------------------------------- |
| `get_gcn_events`            | List or search events; `partialdateobs` matches a dateobs prefix or an alias |
| `get_gcn_event`             | One event in full, including its GCN circulars                               |
| `get_gcn_event_extractions` | Structured data a pipeline extracted from the circulars                      |
| `get_gcn_event_comments`    | The discussion on the event                                                  |
| `post_gcn_event_comment`    | Reply in that discussion                                                     |

`get_gcn_event_extractions` reads the `gcneventextractions` table, where any
producer may store machine-readable values parsed out of an event's prose.
`origin` names the producer and the payload is that producer's own shape, so
filter by `origin` when you care which pipeline it came from.

## Broker filters

Nine tools cover a filter from nothing to running on the live alert stream, so
an assistant can build one from a description of what the user wants to catch.

| Tool                             | Purpose                                                              |
| -------------------------------- | -------------------------------------------------------------------- |
| `get_filter_targets`             | The groups, streams and filter-capable brokers the token can use     |
| `get_alert_schema`               | Fields a pipeline may reference, as dotted paths with their types    |
| `post_filter`                    | Create the filter on a group and stream                              |
| `run_broker_filter`              | Preview: a count, or the alerts themselves when `sort_by` is given   |
| `post_broker_filter_version`     | Add a compiled pipeline as a new version                             |
| `validate_broker_filter_version` | Ask the broker whether a version is fit to run                       |
| `activate_broker_filter_version` | Make a version the one the broker runs                               |
| `get_broker_filter`              | Read a filter: its versions, which is active, its auto-save settings |
| `diff_broker_filter_versions`    | Unified diff of two versions' pipelines                              |

Three things about this sequence are not visible from the schemas, so they are
also stated in the server's `instructions`:

- **The stream bounds what the filter can see.** A cut on data the stream does
  not carry passes nothing, and looks identical to a cut nothing satisfies.
- **`get_alert_schema` is not optional.** A pipeline that references a path the
  survey does not have matches no alerts and reports no error, which is the
  same outcome as a filter that is merely too tight. The tool flattens the
  broker's Avro schema to dotted paths, marking nullable fields with `?` and
  arrays with `[]`, and takes `search` or `prefix` because the full ZTF schema
  is about a thousand paths.
- **Activation is gated on validation.** Posting a version validates it and
  `post_broker_filter_version` returns that verdict; activating a version with
  no passing verdict is refused.

`get_filter_targets` passes on only the broker fields a filter needs.
`GET /api/brokers` returns each broker's `altdata`, which holds its Kafka
credentials, and none of that reaches the model.

## What the assistant may call

The assistant service runs the tool loop itself, and does not offer the model
every tool the endpoint exposes. Read-only tools are always offered. A tool that
writes is offered only on the page whose subject it writes to: the five filter
write tools in `FILTER_WRITE_TOOLS` are offered when the user asks from a
filter page, and nowhere else. `call_tool` then refuses anything that was not
offered, so the selection is enforced twice.

The reason is that most of what the assistant reads was written by someone else
-- GCN circulars, comments, annotations -- and a model can be talked into a
write by the text of what it read. Scoping the write tools to the page keeps
the reachable damage to the one filter the user is already editing, and every
call still runs under that user's own token with the usual permission checks.
Activating a version remains gated on a passing validation.

Each answer records what it ran. `AssistantMessage.tool_calls` holds the calls
in order as `[{name, arguments, ok, summary}]`, and `AssistantMessage.proposal`
holds a filter pipeline the assistant arrived at, read back out of that trace.
A pipeline it never previewed is not offered: the preview is the evidence that
it matches anything, and offering one without it invites saving a filter that
passes nothing. The filter page renders both under the answer.
