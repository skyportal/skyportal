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
