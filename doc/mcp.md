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

| Method            | Purpose                                                   |
| ----------------- | --------------------------------------------------------- |
| `server/discover` | Supported protocol versions, capabilities, server identity |
| `tools/list`      | Tool definitions with input schemas                       |
| `tools/call`      | Invoke a tool                                             |

## Tools

| Tool              | REST endpoint                          |
| ----------------- | -------------------------------------- |
| `get_sources`     | `GET /api/sources[/{obj_id}]`          |
| `post_source`     | `POST /api/sources`                    |
| `get_photometry`  | `GET /api/sources/{obj_id}/photometry` |
| `post_photometry` | `POST /api/photometry`                 |
| `get_spectra`     | `GET /api/sources/{obj_id}/spectra`    |
| `post_spectrum`   | `POST /api/spectrum`                   |

Each tool documents its most common parameters in its input schema and
accepts any other parameter of the underlying endpoint, so the
[API reference](api) applies. Arguments are validated against the input
schema before the call. These tools return the endpoint's `data` as JSON
text and as `structuredContent`; an API error returns the error message with
`isError` set.

Tools are async functions in `skyportal/handlers/mcp.py` that may call the
REST API any number of times (with the caller's token) and return their own
content, so tools that combine or analyze several API results are added the
same way.

## Direct use

As required by the transport, each POST mirrors its method (and tool name)
into headers and declares its protocol version both in a header and in
`_meta`:

```sh
curl -X POST https://<host>/mcp \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -H "MCP-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: tools/call" \
  -H "Mcp-Name: get_sources" \
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
    "params": {
      "name": "get_sources",
      "arguments": {"obj_id": "ZTF21aaaaaaa"},
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}
      }
    }
  }'
```
