import json
import operator  # noqa: F401

import joblib
import numpy as np
import sqlalchemy as sa
from sqlalchemy import not_, or_

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.flow import Flow
from baselayer.app.models import DBSession
from baselayer.log import make_log

from ....enum_types import THUMBNAIL_TYPES
from ....models import (
    Classification,
    Group,
    Instrument,
    Photometry,
    PhotStat,
    PublicRelease,
    PublicSourcePage,
    Spectrum,
    Stream,
    User,
)
from ....utils.safe_round import safe_round
from ....utils.thumbnail import get_thumbnail_alt_link, get_thumbnail_header
from ...base import BaseHandler
from ..source import get_source

log = make_log("api/public_source_page")


def calculate_hash(data):
    return joblib.hash(json.dumps(data, sort_keys=True))


def process_thumbnails(thumbnails, ra, dec):
    if thumbnails is None or ra is None or dec is None:
        return []
    # Sort thumbnails by type, and remove 'DR8' thumbnail if 'LS' (that corresponds to DR10) thumbnail are present
    has_ls = any("ls" in thumbnail["type"] for thumbnail in thumbnails)
    thumbnails = sorted(
        [thumb for thumb in thumbnails if not (thumb["type"] == "dr8" and has_ls)],
        key=lambda x: THUMBNAIL_TYPES.index(x["type"]),
    )

    for index, thumbnail in enumerate(thumbnails):
        alt, link = get_thumbnail_alt_link(thumbnail["type"], ra, dec)
        thumbnails[index] = {
            "type": thumbnail["type"],
            "public_url": thumbnail["public_url"],
            "alt": alt,
            "link": link,
            "header": get_thumbnail_header(thumbnail["type"]),
        }
    return thumbnails


def get_redshift_to_display(source):
    redshift_display = "..."
    if source.get("redshift") and source.get("redshift_error"):
        z_round = int(np.ceil(abs(np.log10(source["redshift_error"]))))
        redshift_display = f"{round(source['redshift'], z_round)} ± {round(source['redshift_error'], z_round)}"
    elif source.get("redshift"):
        redshift_display = round(source["redshift"], 4)
    return redshift_display


def get_photometry(source_id, group_ids, stream_ids, session):
    stmt = Photometry.select(session.user_or_token, mode="read").where(
        Photometry.obj_id == source_id
    )
    if len(group_ids) > 0 and len(stream_ids) > 0:
        stmt = stmt.where(
            or_(
                Photometry.groups.any(Group.id.in_(group_ids)),
                Photometry.streams.any(Stream.id.in_(stream_ids)),
            )
        )
    return [photo.to_dict_public() for photo in session.scalars(stmt).unique().all()]


def get_phot_stats(source_id, phot_stats, session):
    if phot_stats is not None:
        return phot_stats[0]

    fetched_phot_stats = session.scalar(
        PhotStat.select(session.user_or_token, mode="read").where(
            PhotStat.obj_id == source_id
        )
    )
    return fetched_phot_stats.to_dict() if fetched_phot_stats else None


def get_spectroscopy(source_id, group_ids, session):
    stmt = (
        Spectrum.select(session.user_or_token, mode="read")
        .where(Spectrum.obj_id == source_id)
        .join(Spectrum.instrument)
        .order_by(Instrument.name, Spectrum.observed_at.desc())
    )
    if len(group_ids) > 0:
        stmt = stmt.where(Spectrum.groups.any(Group.id.in_(group_ids)))
    return [spec.to_dict_public() for spec in session.scalars(stmt).unique().all()]


def get_classifications(source_id, group_ids, session):
    stmt = Classification.select(session.user_or_token, mode="read").where(
        Classification.obj_id == source_id
    )
    if len(group_ids) > 0:
        stmt = stmt.where(Classification.groups.any(Group.id.in_(group_ids)))
    return [c.to_dict_public() for c in session.scalars(stmt).unique().all()]


def async_post_public_source_page(options, source, release, user_id):
    """Asynchronously create a public page for a source
    options: The options for managing data to display publicly.
    source: The source data to publish.
    release: The release where the public source page belongs.
    """
    with DBSession() as session:
        session.user_or_token = session.scalar(
            sa.select(User).where(User.id == user_id)
        )
        post_public_source_page(options, source, release, True, session)


def post_public_source_page(options, source, release, is_auto_published, session):
    """Create a public page for a source.
    options: The options for managing data to display publicly.
    source: The source data to publish.
    release: The release where the public source page belongs.
    is_auto_published: Whether the page has been auto-published.
    session: The session used to interact with the database.
    """
    group_ids = options.get("groups")
    stream_ids = options.get("streams")
    source_id = source["id"]

    data_to_publish = {
        "ra": safe_round(source.get("ra"), 6),
        "dec": safe_round(source.get("dec"), 6),
        "peak_mag_per_filter": None,
        "first_detected_mjd": None,
        "redshift_display": get_redshift_to_display(source),
        "gal_lon": safe_round(source.get("gal_lon"), 6),
        "gal_lat": safe_round(source.get("gal_lat"), 6),
        "ebv": safe_round(source.get("ebv"), 2),
        "dm": safe_round(source.get("dm"), 3),
        "dl": safe_round(source.get("luminosity_distance"), 2),
        "t0": safe_round(source.get("t0"), 6),
        "thumbnails": process_thumbnails(
            source.get("thumbnails"), source.get("ra"), source.get("dec")
        ),
        "options": options,
        "release_link_name": release.link_name if release is not None else None,
    }
    if options.get("include_summary"):
        data_to_publish["summary"] = source.get("summary")
    if options.get("include_photometry"):
        data_to_publish["photometry"] = get_photometry(
            source_id, group_ids, stream_ids, session
        )
        phot_stats = get_phot_stats(source_id, source.get("photstats"), session)
        if phot_stats:
            data_to_publish["peak_mag_per_filter"] = phot_stats.get(
                "peak_mag_per_filter"
            )
            data_to_publish["first_detected_mjd"] = safe_round(
                phot_stats.get("first_detected_mjd"), 4
            )
    if options.get("include_spectroscopy"):
        data_to_publish["spectroscopy"] = get_spectroscopy(
            source_id, group_ids, session
        )
    if options.get("include_classifications"):
        data_to_publish["classifications"] = get_classifications(
            source_id, group_ids, session
        )

    new_page_hash = calculate_hash(data_to_publish)
    same_page = session.scalar(
        sa.select(PublicSourcePage).where(
            PublicSourcePage.source_id == source_id,
            PublicSourcePage.hash == new_page_hash,
        )
    )
    if same_page is not None:
        raise AttributeError(
            "A public page with the same data, options and release already exists for this source"
        )

    public_source_page = PublicSourcePage(
        source_id=source_id,
        hash=new_page_hash,
        data=data_to_publish,
        is_auto_published=is_auto_published,
        is_visible=True,
        release_id=release.id if release is not None else None,
    )
    session.add(public_source_page)
    session.commit()

    if release is None or release.is_visible:
        try:
            public_source_page.generate_page()
        except Exception as e:
            session.rollback()
            if public_source_page in session:
                session.delete(public_source_page)
                session.commit()
            raise AttributeError(f"Error generating public page: {e}")

    flow = Flow()
    flow.push(
        "*", "skyportal/REFRESH_PUBLIC_SOURCE_PAGES", payload={"source_id": source_id}
    )
    return public_source_page.id


def delete_auto_published_page(source_id, remaining_group_ids):
    """
    Delete auto-published public pages for a source.
    But only if the release, link to the page, share no groups with the remaining source groups.
    source_id: The ID of the source for which to delete auto-published pages.
    remaining_group_ids: The IDs of the groups that the source is still associated with.
    """
    # only called with `run_async`, so we open the session here with DBSession()
    with DBSession() as session:
        public_source_pages = session.scalars(
            sa.select(PublicSourcePage)
            .join(PublicRelease)
            .where(
                not_(PublicRelease.groups.any(Group.id.in_(remaining_group_ids))),
                PublicSourcePage.source_id == source_id,
                PublicSourcePage.is_auto_published,
            )
        ).all()

        flow = Flow()
        for public_source_page in public_source_pages:
            public_source_page.remove_from_cache()
            session.delete(public_source_page)
            flow.push(
                "*",
                "skyportal/REFRESH_PUBLIC_SOURCE_PAGES",
                payload={"source_id": public_source_page.source_id},
            )

        session.commit()


class PublicSourcePageHandler(BaseHandler):
    @permissions(["Manage sources"])
    async def post(self, source_id):
        """
        ---
          summary: Create a public page for a source
          description:
            Create a public page for a source, with given options,
            only if this page does not already exist
          tags:
            - sources
          parameters:
            - in: path
              name: source_id
              schema:
                type: string
                required: true
                description: The ID of the source from which to create a public page
          requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            options:
                                type: object
                                required: true
                                description: Options to manage data to display publicly
                            release_id:
                                type: integer
                                required: false
                                description: The ID of the public release where the public source page belongs
          responses:
            200:
              content:
                application/json:
                  schema: Success
            400:
              content:
                application/json:
                  schema: Error
        """
        data = self.get_json()
        if data is None or data == {}:
            return self.error("No data provided")
        if source_id is None:
            return self.error("Source ID is required")
        options = data.get("options")
        if options is None:
            return self.error("Options are required")
        release_id = data.get("release_id")
        if release_id is not None and not isinstance(release_id, int):
            return self.error("Invalid release ID")

        with self.Session() as session:
            try:
                source = await get_source(
                    obj_id=source_id,
                    user_id=self.associated_user_object.id,
                    session=session,
                    include_thumbnails=True,
                    include_detection_stats=options.get("include_photometry") is True,
                )
            except ValueError:
                return self.error("Source not found", status=404)
            if source is None:
                return self.error("Source not found", status=404)

            release = None
            if release_id is not None:
                release = session.scalar(
                    PublicRelease.select(session.user_or_token, mode="read").where(
                        PublicRelease.id == release_id
                    )
                )
                if release is None:
                    return self.error("Release not found", status=404)

            try:
                public_source_page_id = post_public_source_page(
                    options=options,
                    source=source,
                    release=release,
                    is_auto_published=False,
                    session=session,
                )
                return self.success(data={"id": public_source_page_id})
            except Exception as e:
                return self.error(str(e))

    @auth_or_token
    def get(self, source_id):
        """
        ---
          summary: Retrieve all public pages for a source
          description:
            Retrieve all public pages for a given source from the most recent to the oldest
          tags:
            - sources
          parameters:
            - in: path
              name: source_id
              schema:
                type: string
                required: true
                description: The ID of the source for which to retrieve the public page
          responses:
            200:
              content:
                application/json:
                    schema: Success
            400:
              content:
                application/json:
                  schema: Error
            404:
              content:
                application/json:
                  schema: Error
        """
        if source_id is None:
            return self.error("Source ID is required")
        with self.Session() as session:
            public_source_pages = session.scalars(
                PublicSourcePage.select(session.user_or_token, mode="read")
                .where(
                    PublicSourcePage.source_id == source_id, PublicSourcePage.is_visible
                )
                .order_by(PublicSourcePage.created_at.desc())
            ).all()
            return self.success(data=public_source_pages)

    @permissions(["Manage sources"])
    def delete(self, page_id):
        """
        ---
        summary: Delete a public source page
        description: Delete a public source page
        tags:
          - sources
        parameters:
          - in: path
            name: page_id
            schema:
              type: string
              required: true
              description: The ID of the public source page to delete
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        if page_id is None:
            return self.error("Page ID is required")

        with self.Session() as session:
            public_source_page = session.scalar(
                PublicSourcePage.select(session.user_or_token, mode="delete").where(
                    PublicSourcePage.id == page_id
                )
            )

            if public_source_page is None:
                return self.error("Public source page not found", status=404)
            public_source_page.remove_from_cache()

            session.delete(public_source_page)
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_PUBLIC_SOURCE_PAGES",
                payload={"source_id": public_source_page.source_id},
            )
            return self.success()
