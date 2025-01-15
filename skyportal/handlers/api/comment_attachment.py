import sqlalchemy as sa
from sqlalchemy import func

from ..base import BaseHandler
from ...models import (
    Comment,
)
from baselayer.app.access import permissions

DEFAULT_COMMENTS_PER_PAGE = 100
MAX_COMMENTS_PER_PAGE = 500


class CommentAttachmentUpdateHandler(BaseHandler):
    @permissions(['System admin'])
    def get(self):
        """
        ---
        summary: Get counts of comments w/ and w/o attachment_bytes
        description: find the number of comments with and without attachment_bytes
        tags:
          - comments
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
                              totalWithoutAttachmentBytes:
                                type: integer
                              totalWithAttachmentBytes:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:
            stmt = sa.select(Comment).where(Comment.attachment_bytes.is_(None))
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_missing = session.execute(count_stmt).scalar()

            # get the number of Comments with Attachments
            stmt = sa.select(Comment).where(Comment.attachment_bytes.isnot(None))
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_with = session.execute(count_stmt).scalar()

        results = {
            'totalWithoutAttachmentBytes': total_missing,
            'totalWithAttachmentBytes': total_with,
        }
        return self.success(data=results)

    @permissions(['System admin'])
    def post(self):
        """
        ---
        summary: Create attachments for comments with attachment_bytes
        description: create attachments for a batch of comments with attachment_bytes
        tags:
          - comments
        parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of comments to check for updates. Defaults to 100. Max 500.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for iterating through all comments. Defaults to 1
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
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              numPerPage:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        try:
            page_number = int(self.get_query_argument('pageNumber', 1))
            num_per_page = min(
                int(self.get_query_argument("numPerPage", DEFAULT_COMMENTS_PER_PAGE)),
                MAX_COMMENTS_PER_PAGE,
            )
        except ValueError:
            return self.error(
                f'Cannot parse inputs pageNumber ({page_number}) '
                f'or numPerPage ({num_per_page}) as an integers.'
            )

        with self.Session() as session:
            try:
                stmt = sa.select(Comment).where(Comment.attachment_bytes.isnot(None))
                # select only comments that have attachment_bytes
                count_stmt = sa.select(func.count()).select_from(stmt)
                total_matches = session.execute(count_stmt).scalar()
                stmt = stmt.offset((page_number - 1) * num_per_page)
                stmt = stmt.limit(num_per_page)
                comments = session.execute(stmt).scalars().unique().all()

                for i, comment in enumerate(comments):
                    attachment_name = comment.attachment_name
                    data_to_disk = comment.attachment_bytes
                    comment.save_data(attachment_name, data_to_disk)
                    comment.attachment_bytes = None
                session.commit()
            except Exception as e:
                session.rollback()
                return self.error(
                    f'Error updating comments with attachment_bytes: {str(e)}'
                )

        results = {
            'totalMatches': total_matches,
            'numPerPage': num_per_page,
            'pageNumber': page_number,
        }
        return self.success(data=results)
