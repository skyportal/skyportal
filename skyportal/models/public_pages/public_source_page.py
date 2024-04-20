__all__ = [
    'PublicSourcePage',
]

import json
import jinja2
from ligo.skymap import plot  # noqa: F401 F811
import numpy as np
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred

from baselayer.app.env import load_env
from baselayer.app.json_util import to_json
from baselayer.app.models import (
    Base,
)

from ...utils.cache import Cache, dict_to_bytes

env, cfg = load_env()

cache_dir = "cache/public_pages/sources"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_public_source_pages_cache"] * 60,
)

public = True
private = False


class PublicSourcePage(Base):
    """Public page of a source on a given date."""

    id = sa.Column(sa.Integer, primary_key=True)

    date_created = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
        doc="UTC timestamp representing when this page was created.",
    )

    source_id = sa.Column(sa.String, nullable=False, doc="ID of the source")

    data = deferred(
        sa.Column(JSONB, nullable=False, doc="Source data accessible on the page")
    )

    is_public = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc='Whether the page is accessible to the public.',
    )

    def publish(self):
        """Set the page to public and create the public source page."""
        self.is_public = public
        self.generate_public_source_page(self.data)

    def unpublish(self):
        """Set the page to private and remove it from the cache."""
        self.is_public = private
        cache_key = f"source_{self.source_id}"
        cached = cache[cache_key]
        if cached is not None:
            data = np.load(cached, allow_pickle=True)
            data = data.item()
            cache[cache_key] = dict_to_bytes({"public": False, "html": data["html"]})
        else:
            cache[cache_key] = dict_to_bytes({"public": False, "html": None})

    def generate_public_source_page(self, public_data):
        """Generate a public page of the source and cache it."""
        data = self.data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {"status": "error", "message": "Invalid JSON data."}
        if data.get("status") == "error":
            raise ValueError(data.get("message", "Invalid JSON data."))
        elif data.get("status") == "pending":
            raise ValueError("Public source page is still being generated.")
        # Set the data status to pending to indicate that the page is being generated
        self.data.update({"status": "pending"})

        cache_key = f"source_{self.source_id}"
        public_source_page = self.generate_html(public_data)
        cache[cache_key] = dict_to_bytes({"public": True, "html": public_source_page})
        self.data.update({"status": "success"})

    def generate_html(self, public_data):
        """Generate HTML for the public page of the source."""
        if isinstance(public_data, str):
            public_data = json.loads(public_data)

        environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader("./static/public_pages/sources")
        )
        environment.policies['json.dumps_function'] = to_json
        template = environment.get_template("source_template.html")
        html = template.render(
            source_id=self.source_id,
            data=public_data,
        )
        return html
