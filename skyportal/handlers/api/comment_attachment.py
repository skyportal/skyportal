import sqlalchemy as sa
from sqlalchemy import func

from baselayer.app.access import permissions

from ...models import (
    Comment,
)
from ..base import BaseHandler

DEFAULT_COMMENTS_PER_PAGE = 100
MAX_COMMENTS_PER_PAGE = 500


class CommentAttachmentUpdateHandler(BaseHandler):
    @permissions(["System admin"])
    async def get(self):
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

        async with self.AsyncSession() as session:
            stmt = sa.select(Comment).where(Comment.attachment_bytes.is_(None))
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_missing = await session.scalar(count_stmt)

            # get the number of Comments with Attachments
            stmt = sa.select(Comment).where(Comment.attachment_bytes.isnot(None))
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_with = await session.scalar(count_stmt)

        results = {
            "totalWithoutAttachmentBytes": total_missing,
            "totalWithAttachmentBytes": total_with,
        }
        return self.success(data=results)

    @permissions(["System admin"])
    async def post(self):
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

        page_number = self.get_query_argument("pageNumber", 1, type=int)
        num_per_page = self.get_query_argument(
            "numPerPage", DEFAULT_COMMENTS_PER_PAGE, type=int
        )
        if page_number is None or num_per_page is None:
            return self.error(
                "Cannot parse inputs pageNumber or numPerPage as integers."
            )
        num_per_page = min(num_per_page, MAX_COMMENTS_PER_PAGE)

        async with self.AsyncSession() as session:
            try:
                stmt = sa.select(Comment).where(Comment.attachment_bytes.isnot(None))
                # select only comments that have attachment_bytes
                count_stmt = sa.select(func.count()).select_from(stmt)
                total_matches = await session.scalar(count_stmt)
                stmt = stmt.offset((page_number - 1) * num_per_page)
                stmt = stmt.limit(num_per_page)
                result = await session.scalars(stmt)
                comments = result.unique().all()

                for i, comment in enumerate(comments):
                    attachment_name = comment.attachment_name
                    data_to_disk = comment.attachment_bytes
                    comment.save_data(attachment_name, data_to_disk)
                    comment.attachment_bytes = None
                await session.commit()
            except Exception as e:
                await session.rollback()
                return self.error(
                    f"Error updating comments with attachment_bytes: {str(e)}"
                )

        results = {
            "totalMatches": total_matches,
            "numPerPage": num_per_page,
            "pageNumber": page_number,
        }
        return self.success(data=results)
