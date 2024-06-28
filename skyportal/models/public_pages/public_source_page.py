__all__ = ['PublicSourcePage']

import json
import jinja2
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred
from baselayer.app.env import load_env
from baselayer.app.json_util import to_json
from baselayer.app.models import (
    Base,
    UserAccessControl,
    CustomUserAccessControl,
)
from ..source import Source
from ..group import GroupUser

from ...utils.cache import Cache, dict_to_bytes

env, cfg = load_env()

cache_dir = "cache/public_pages/sources"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_public_source_pages_cache"] * 60,
)


def published_source_access_logic(cls, user_or_token):
    """Return a query that filters PublicSourcePage instances based on user access."""
    # if the user is a system admin, he can update and delete all published sources
    # otherwise, he can only delete and update the published sources associate with his group
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.join(Source, cls.source_id == Source.obj_id)
        query = query.join(GroupUser, Source.group_id == GroupUser.group_id)
        query = query.filter(GroupUser.user_id == user_id)
    return query


class PublicSourcePage(Base):
    """Public page of a source on a given date."""

    update = delete = CustomUserAccessControl(published_source_access_logic)

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
        cache_key = f"source_{self.source_id}_version_{self.hash}"
        public_source_page_html = self.get_html(data)
        cache[cache_key] = dict_to_bytes(
            {"public": True, "html": public_source_page_html}
        )

    def get_html(self, public_data):
        """Get the HTML content of the public source page."""
        # Create the filters mapper
        if "photometry" in public_data and public_data["photometry"] is not None:
            from skyportal.handlers.api.photometry import get_bandpasses_to_colors

            filters = {
                photometry["filter"] for photometry in public_data.get("photometry", [])
            }
            public_data["filters_mapper"] = get_bandpasses_to_colors(filters)

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
