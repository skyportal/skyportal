# Import all tool modules so their @mcp.tool() decorators register on import.
from . import (  # noqa: F401
    analysis,
    api,
    astro_utils,
    bulk_analysis,
    filtering,
    observing,
    source_products,
)
