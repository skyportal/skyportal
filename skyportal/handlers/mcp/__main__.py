"""Run the MCP server standalone over stdio for local development:

    MCP_TRANSPORT=stdio SKYPORTAL_URL=... SKYPORTAL_TOKEN=... \
        python -m skyportal.handlers.mcp

In production the server is part of the web app (served at /mcp).
"""

import os

os.environ.setdefault("MCP_TRANSPORT", "stdio")

from .server import mcp  # noqa: E402

mcp.run(transport="stdio", show_banner=False)
