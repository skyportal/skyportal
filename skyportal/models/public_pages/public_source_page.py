__all__ = ['PublicSourcePage']

import json
import jinja2
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred, relationship
from baselayer.app.env import load_env
from baselayer.app.json_util import to_json
from baselayer.app.models import Base
from ..group import accessible_by_groups_members

from ...utils.cache import Cache, dict_to_bytes

env, cfg = load_env()

cache_dir = "cache/public_pages/sources"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_public_source_pages_cache"] * 60,
)


class PublicSourcePage(Base):
    """Public page of a source on a given date."""

    update = delete = accessible_by_groups_members

    id = sa.Column(sa.Integer, primary_key=True)

    source_id = sa.Column(sa.String, nullable=False, doc="ID of the source")

    data = deferred(
        sa.Column(JSONB, nullable=False, doc="Source data accessible on the page")
    )

    hash = sa.Column(
        sa.String,
        nullable=False,
        doc="Hash of the source data used to identify the page version",
    )

    is_visible = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc='Whether the page is visible to the public',
    )

    release_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('publicreleases.id'),
        nullable=True,
        doc='ID of the public release associated with this source page',
    )

    release = relationship(
        "PublicRelease",
        back_populates="source_pages",
        doc="The release associated with this source page",
    )

    def to_dict(self):
        """Convert the page to a dictionary with
        the options to be displayed and the creation date in ISO format."""
        return {
            'id': self.id,
            'source_id': self.source_id,
            'is_visible': self.is_visible,
            'created_at': self.created_at,
            'hash': self.hash,
            'options': self.get_options(),
        }

    def get_options(self):
        """Get the options check to be displayed on the public page."""
        photometry = self.data.get("photometry")
        classifications = self.data.get("classifications")
        return {
            "photometry": "no data"
            if photometry == []
            else "public"
            if photometry
            else "private",
            "classifications": "no data"
            if classifications == []
            else "public"
            if classifications
            else "private",
        }

    def generate_page(self):
        """Generate the public page for the source and cache it."""
        data = self.data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                raise ValueError("Invalid data provided")
        if self.release:
            cache_key = f"release_{self.release.link_name}_source_{self.source_id}_version_{self.hash}"
        else:
            cache_key = f"source_{self.source_id}_version_{self.hash}"
        public_source_page_html = self.get_html(data)
        cache[cache_key] = dict_to_bytes(
            {"public": True, "html": public_source_page_html}
        )

    def get_html(self, public_data):
        """Get the HTML content of the public source page."""
        # Create the filters mapper
        if "photometry" in public_data and public_data["photometry"] is not None:
            from skyportal.handlers.api.photometry import get_filters_mapper

            public_data["filters_mapper"] = get_filters_mapper(
                public_data["photometry"]
            )

        if self.release:
            public_data["release"] = {
                "name": self.release.name,
                "link_name": self.release.link_name,
            }
        environment = jinja2.Environment(
            autoescape=True,
            loader=jinja2.FileSystemLoader("./static/public_pages/sources/source"),
        )
        environment.policies['json.dumps_function'] = to_json
        template = environment.get_template("source_template.html")
        html = template.render(
            source_id=self.source_id,
            data=public_data,
            created_at=self.created_at,
        )
        return html

    def remove_from_cache(self):
        """Remove the page from the cache."""
        cache_key = f"source_{self.source_id}_version_{self.hash}"
        del cache[cache_key]
