import json
import operator  # noqa: F401

import joblib
import numpy as np
from sqlalchemy import or_

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ....enum_types import THUMBNAIL_TYPES
from ....models import (
    Classification,
    Group,
    Instrument,
    Photometry,
    PublicRelease,
    PublicSourcePage,
    Spectrum,
    Stream,
)
from ....utils.thumbnail import get_thumbnail_alt_link, get_thumbnail_header
from ...base import BaseHandler
from ..source import get_source

log = make_log("api/public_source_page")


def calculate_hash(data):
    return joblib.hash(json.dumps(data, sort_keys=True))


def process_thumbnails(thumbnails, ra, dec):
    # Sort thumbnails by type, and remove 'DR8' thumbnail if 'LS' (that corresponds to DR9) thumbnail are present
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


def safe_round(number, precision):
    return round(number, precision) if isinstance(number, int | float) else None


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
            group_ids = options.get("groups")
            stream_ids = options.get("streams")

            try:
                source = await get_source(
                    source_id,
                    self.associated_user_object.id,
                    session=session,
                    include_thumbnails=True,
                )
            except ValueError:
                return self.error("Source not found", status=404)

            if source is None:
                return self.error("Source not found", status=404)

            if release_id is not None:
                release = session.scalar(
                    PublicRelease.select(session.user_or_token, mode="read").where(
                        PublicRelease.id == release_id
                    )
                )
                if release is None:
                    return self.error("Release not found", status=404)

            data_to_publish = {
                "ra": safe_round(source.get("ra"), 6),
                "dec": safe_round(source.get("dec"), 6),
                "redshift_display": get_redshift_to_display(source),
                "gal_lon": safe_round(source.get("gal_lon"), 6),
                "gal_lat": safe_round(source.get("gal_lat"), 6),
                "ebv": safe_round(source.get("ebv"), 2),
                "dm": safe_round(source.get("dm"), 3),
                "dl": safe_round(source.get("luminosity_distance"), 2),
                "thumbnails": process_thumbnails(
                    source["thumbnails"], source["ra"], source["dec"]
                ),
                "options": options,
                "release_link_name": release.link_name if release_id else None,
            }
            if options.get("include_summary"):
                data_to_publish["summary"] = source.get("summary")
            if options.get("include_photometry"):
                data_to_publish["photometry"] = get_photometry(
                    source_id, group_ids, stream_ids, session
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
            if (
                session.scalar(
                    PublicSourcePage.select(session.user_or_token, mode="read").where(
                        PublicSourcePage.source_id == source_id,
                        PublicSourcePage.hash == new_page_hash,
                    )
                )
                is not None
            ):
                return self.error(
                    "A public page with the same data, options and release already exists for this source"
                )

            public_source_page = PublicSourcePage(
                source_id=source_id,
                hash=new_page_hash,
                data=data_to_publish,
                is_visible=True,
                release_id=release_id,
            )
            session.add(public_source_page)
            session.commit()

            if release_id is None or release.is_visible:
                try:
                    public_source_page.generate_page()
                except Exception as e:
                    session.rollback()
                    if public_source_page in session:
                        session.delete(public_source_page)
                        session.commit()
                    return self.error(f"Error generating public page: {e}")

            self.push_all(
                action="skyportal/REFRESH_PUBLIC_SOURCE_PAGES",
                payload={"source_id": source_id},
            )
            return self.success()

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
