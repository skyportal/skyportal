import operator  # noqa: F401

from sqlalchemy.orm import sessionmaker, scoped_session

from baselayer.app.access import auth_or_token
from baselayer.log import make_log
from ..base import BaseHandler

from ...models import (
    SourceAccessibility,
)

log = make_log('api/source_accessibility')

Session = scoped_session(sessionmaker())


class SourceAccessibilityHandler(BaseHandler):
    @auth_or_token
    async def post(self, source_id):
        """
        ---
          description: Create accessibility information for a source
          tags:
            - source_accessibility
          parameters:
            - in: path
              name: source_id
              schema:
                type: string
                required: true
                description: The ID of the source from which to create accessibility information
          responses:
            200:
              content:
                application/json:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: object
                        properties:
                          data:
                            type: object
                            properties:
                              Source id:
                                type: string
                                description: The ID of the source from which accessibility information was created
            400:
              content:
                application/json:
                  schema: Error
        """
        payload = self.get_json()
        if source_id is None:
            return self.error("Source ID is required")
        if payload.get('publish') is None:
            return self.error("Publish field is required")
        with self.Session() as session:
            source_accessibility = SourceAccessibility(
                source_id=source_id,
                data={"status": ""},
                is_public=False,
            )
            if payload.get('publish'):
                source_accessibility.publish()
            session.add(source_accessibility)
            session.commit()

            return self.success({"Source id": source_id})

    @auth_or_token
    def get(self, source_id):
        """
        ---
        description: Retrieve accessibility information from a source
        tags:
          - source_accessibility
        parameters:
          - in: path
            name: source_id
            schema:
              type: string
              required: true
              description: The ID of the source from which to retrieve accessibility information
        responses:
          200:
            content:
              application/json:
                schema: SingleSourceAccessibility
          400:
            content:
              application/json:
                schema: Error
        """
        if source_id is None:
            return self.error("Source ID is required")
        with self.Session() as session:
            stmt = SourceAccessibility.select(mode="read").where(
                SourceAccessibility.source_id == source_id
            )
            source_accessibility = session.scalars(stmt).first()
            if source_accessibility is None:
                return self.error("Accessibility information from this source not found", status=404)
            return self.success(data=source_accessibility)

    @auth_or_token
    async def patch(self, source_id):
        """
        ---
        description: Update accessibility information from a source
        tags:
          - source_accessibility
        parameters:
          - in: path
            name: source_id
            schema:
              type: string
              required: true
              description: The ID of the source from which to update accessibility information
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: object
        responses:
          200:
            content:
              application/json:
                schema: SingleSourceAccessibility
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
        publish = data.get("publish")
        if publish is not None and isinstance(publish, bool):
            return self.error("An invalid value was provided for publish")

        with self.Session() as session:
            stmt = SourceAccessibility.select(mode="read").where(
                SourceAccessibility.source_id == source_id,
                SourceAccessibility.isSourcePublic != publish,
            )
            source_accessibility = session.scalars(stmt).first()
            if source_accessibility is None:
                return self.error("Accessibility information from this source not found", status=404)
            source_accessibility.publish() if publish else source_accessibility.unpublish()
            session.commit()

            # TODO: This should refresh the public source page with the new data
            # self.push_all(
            #     action="skyportal/REFRESH_PUBLIC_SOURCE_PAGE",
            #     payload={"source_id": source_id},
            # )

            return self.success(data=source_accessibility)

    @auth_or_token
    def delete(self, source_id):
        """
        ---
        description: Delete accessibility information from a source
        tags:
          - source_accessibility
        parameters:
          - in: path
            name: source_id
            schema:
              type: string
              required: true
              description: The ID of the source from which to delete accessibility information
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

        if source_id is None:
            return self.error("Source ID is required")

        with self.Session() as session:
            stmt = SourceAccessibility.select(mode="delete").where(
                SourceAccessibility.source_id == source_id,
            )
            source_accessibility = session.scalars(stmt).first()
            if source_accessibility is None:
                return self.error("Accessibility information from this source not found", status=404)

            source_accessibility.unpublish()
            session.delete(source_accessibility)
            session.commit()

        return self.success()
