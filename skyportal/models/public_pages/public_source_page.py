__all__ = ['PublicSourcePage']

import json
import jinja2
from ligo.skymap import plot  # noqa: F401 F811
import sqlalchemy as sa
from sqlalchemy import event
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

    created_at_iso = sa.Column(
        sa.String,
        nullable=True,
        doc="Creation date in ISO format",
    )

    data = deferred(
        sa.Column(JSONB, nullable=False, doc="Source data accessible on the page")
    )

    is_public = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc='Whether the page is accessible to the public.',
    )

    def to_dict(self):
        """Convert the page to a dictionary with
        the options to be displayed and the creation date in ISO format."""
        return {
            'id': self.id,
            'source_id': self.source_id,
            'is_public': self.is_public,
            'created_at_iso': self.created_at_iso,
            'options': self.get_options(),
        }

    def get_options(self):
        """Get the options check to be displayed on the public page."""
        photometry = self.data.get("photometry")
        classifications = self.data.get("classifications")
        return {
            "photometry": "no element"
            if photometry == []
            else "public"
            if photometry
            else "private",
            "classifications": "no element"
            if classifications == []
            else "public"
            if classifications
            else "private",
        }

    def publish(self):
        """Set the page to public and create the public source page."""
        self.is_public = True
        self.generate_public_source_page()

    def generate_public_source_page(self):
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

        cache_key = f"source_{self.source_id}_version_{self.created_at_iso}"
        public_source_page = self.generate_html(data)
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
            data=public_data,
            creation_date=self.created_at,
        )
        return html

    def remove_from_cache(self):
        """Remove the page from the cache."""
        cache_key = f"source_{self.source_id}_version_{self.created_at_iso}"
        del cache[cache_key]


@event.listens_for(PublicSourcePage, 'after_insert')
def _set_created_at_iso(mapped, connection, target):
    """Set the creation date in ISO format after the page is created."""
    connection.execute(
        sa.update(PublicSourcePage.__table__)
        .where(PublicSourcePage.id == target.id)
        .values(created_at_iso=target.created_at.isoformat(timespec='seconds'))
    )
