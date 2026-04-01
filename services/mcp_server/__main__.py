"""Allow running as `python -m services.mcp_server`."""

import os

from .server import MCP_HOST, MCP_PORT, logger, mcp

transport = os.getenv("MCP_TRANSPORT", "http")
if transport == "stdio":
    logger.info("Starting MCP server in stdio mode")
    mcp.run(transport="stdio", show_banner=False)
elif transport == "http":
    logger.info("Starting MCP server in HTTP mode on %s:%s", MCP_HOST, MCP_PORT)
    mcp.run(
        transport="http",
        host=MCP_HOST,
        port=MCP_PORT,
        show_banner=True,
    )
else:
    raise ValueError(f"Unknown transport: {transport}. Use 'stdio' or 'http'.")
