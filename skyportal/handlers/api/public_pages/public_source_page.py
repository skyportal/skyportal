import operator  # noqa: F401
import json

import joblib
import numpy as np
from sqlalchemy import or_

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log
from ..source import get_source
from ...base import BaseHandler
from ....enum_types import THUMBNAIL_TYPES

from ....models import PublicSourcePage, Group, Stream, Classification, Photometry
from ....utils.thumbnail import get_thumbnail_alt_link, get_thumbnail_header

log = make_log('api/public_source_page')


def calculate_hash(data):
    return joblib.hash(json.dumps(data, sort_keys=True))


def process_thumbnails(thumbnails, ra, dec):
    thumbnails = sorted(
        thumbnails,
        key=lambda x: THUMBNAIL_TYPES.index(x["type"]),
    )
    for index, thumbnail in enumerate(thumbnails):
        alt, link = get_thumbnail_alt_link(thumbnail["type"], ra, dec)
        header = get_thumbnail_header(thumbnail["type"])
        thumbnails[index] = {
            "type": thumbnail["type"],
            "public_url": thumbnail["public_url"],
            "alt": alt,
            "link": link,
            "header": header,
        }
    return thumbnails


def get_redshift_to_display(source):
    redshift_display = "..."
    if source.get('redshift') and source.get('redshift_error'):
        z_round = int(np.ceil(abs(np.log10(source['redshift_error']))))
        redshift_display = f"{round(source['redshift'], z_round)} ± {round(source['redshift_error'], z_round)}"
    elif source.get('redshift'):
        redshift_display = round(source['redshift'], 4)
    return redshift_display


class PublicSourcePageHandler(BaseHandler):
    @permissions(['Manage sources'])
    async def post(self, source_id):
        """
        ---
          description:
            Create a public page for a source, with given options,
            only if this page does not already exist
          tags:
            - public_source_page
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

        with self.Session() as session:
            group_ids = options.get("groups")
            stream_ids = options.get("streams")

            # get source
            source = await get_source(
                source_id,
                self.associated_user_object.id,
                session=session,
                include_thumbnails=True,
            )
            if source is None:
                return self.error("Source not found", status=404)
            data_to_publish = {
                "ra": round(source["ra"], 6) if source["ra"] else None,
                "dec": round(source["dec"], 6) if source["dec"] else None,
                "redshift_display": get_redshift_to_display(source),
                "gal_lon": round(source["gal_lon"], 6) if source["gal_lon"] else None,
                "gal_lat": round(source["gal_lat"], 6) if source["gal_lat"] else None,
                "ebv": round(source["ebv"], 2) if source["ebv"] else None,
                "dm": round(source["dm"], 3) if source["dm"] else None,
                "dl": round(source["luminosity_distance"], 2)
                if source["luminosity_distance"]
                else None,
                "thumbnails": process_thumbnails(
                    source["thumbnails"], source["ra"], source["dec"]
                ),
                "options": options,
            }

            # get photometry
            if options.get("include_photometry"):
                query = Photometry.select(session.user_or_token, mode="read").where(
                    Photometry.obj_id == source_id
                )
                if len(group_ids) and len(stream_ids):
                    query = query.where(
                        or_(
                            Photometry.groups.any(Group.id.in_(group_ids)),
                            Photometry.streams.any(Stream.id.in_(stream_ids)),
                        )
                    )
                data_to_publish["photometry"] = [
                    photo.to_dict_public() for photo in session.scalars(query).all()
                ]

            # get classifications
            if options.get("include_classifications"):
                query = Classification.select(session.user_or_token, mode="read").where(
                    Classification.obj_id == source_id
                )
                if len(group_ids):
                    query = query.where(
                        Classification.groups.any(Group.id.in_(group_ids))
                    )
                data_to_publish["classifications"] = [
                    c.to_dict_public() for c in session.scalars(query).all()
                ]

            new_page_hash = calculate_hash(data_to_publish)
            if (
                session.scalars(
                    PublicSourcePage.select(session.user_or_token, mode="read").where(
                        PublicSourcePage.source_id == source_id,
                        PublicSourcePage.hash == new_page_hash,
                    )
                ).first()
                is not None
            ):
                return self.error(
                    "A public page with the same data and same options already exists for this source"
                )

            public_source_page = PublicSourcePage(
                source_id=source_id,
                hash=new_page_hash,
                data=data_to_publish,
                is_visible=True,
            )
            session.add(public_source_page)
            session.commit()
            try:
                public_source_page.generate_page()
            except Exception as e:
                session.rollback()
                if public_source_page in session:
                    session.delete(public_source_page)
                    session.commit()
                return self.error(f"Error generating public page: {e}")
            return self.success(data={"PublicSourcePage": public_source_page})

    @auth_or_token
    def get(self, source_id, nb_results=None):
        """
        ---
          description:
            Retrieve a certain number of public pages, or all pages,
             for a given source from the most recent to the oldest
          tags:
            - public_source_page
          parameters:
            - in: path
              name: source_id
              schema:
                type: string
                required: true
                description: The ID of the source for which to retrieve the public page
            - in: query
              name: nb_results
              schema:
                type: integer
                required: false
                description: The number of public pages to return
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
            stmt = (
                PublicSourcePage.select(session.user_or_token, mode="read")
                .where(
                    PublicSourcePage.source_id == source_id, PublicSourcePage.is_visible
                )
                .order_by(PublicSourcePage.created_at.desc())
            )
            if nb_results is not None:
                stmt = stmt.limit(nb_results)
            public_source_pages = session.execute(stmt).all()
            return self.success(data=public_source_pages)

    @auth_or_token
    def delete(self, page_id):
        """
        ---
        description: Delete a public source page
        tags:
          - public_source_page
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
            public_source_page = session.scalars(
                PublicSourcePage.select(session.user_or_token, mode="delete").where(
                    PublicSourcePage.id == page_id
                )
            ).first()

            if public_source_page is None:
                return self.error("Public source page not found", status=404)
            public_source_page.remove_from_cache()

            session.delete(public_source_page)
            session.commit()
            return self.success()
