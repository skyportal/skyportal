import operator  # noqa: F401
import json

import joblib
from sqlalchemy import or_

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log
from ...base import BaseHandler

from ....models import PublicSourcePage, Group, Stream, Classification, Photometry

log = make_log('api/public_source_page')


def calculate_hash(data):
    return joblib.hash(json.dumps(data, sort_keys=True))


class PublicSourcePageHandler(BaseHandler):
    @permissions(['Manage sources'])
    async def post(self, source_id):
        """
        ---
          description:
            Create a public page for a source with given data
            to display publicly, only if this page does not already exist
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
                            public_data:
                                type: object
                                required: true
                                description: Data to display publicly
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
        public_data = data.get("public_data")
        if public_data is None:
            return self.error("No data provided to display publicly")

        with self.Session() as session:
            group_ids = public_data.get("options").get("groups")
            stream_ids = public_data.get("options").get("streams")

            if public_data.get("options").get("include_photometry"):
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
                public_data["photometry"] = [
                    photo.to_dict_public() for photo in session.scalars(query).all()
                ]

            if public_data.get("options").get("include_classifications"):
                query = Classification.select(session.user_or_token, mode="read").where(
                    Classification.obj_id == source_id
                )
                if len(group_ids):
                    query = query.where(
                        Classification.groups.any(Group.id.in_(group_ids))
                    )
                public_data["classifications"] = [
                    c.to_dict_public() for c in session.scalars(query).all()
                ]

            new_page_hash = calculate_hash(public_data)
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
                    "A public page with the same data already exists for this source"
                )

            public_source_page = PublicSourcePage(
                source_id=source_id,
                hash=new_page_hash,
                data=public_data,
                is_visible=True,
            )
            session.add(public_source_page)
            session.commit()
            public_source_page.generate_page()
            return self.success({"public_source_page": public_source_page})

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
