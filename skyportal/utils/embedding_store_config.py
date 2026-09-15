"""Reading the embeddings store config. Kept apart from the search so services
that only need to know whether it is on do not import the model layer."""

__all__ = ["PGVECTOR", "store_location"]

PGVECTOR = "pgvector"


def store_location(config: dict) -> str | None:
    """The configured backend name, lowercased, or None when unset."""
    location = (config or {}).get("location")
    return str(location).strip().lower() if location else None
