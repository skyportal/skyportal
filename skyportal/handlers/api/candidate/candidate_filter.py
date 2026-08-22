from typing import Literal

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.sql.expression import func

from baselayer.app.access import auth_or_token

from ....models import Candidate, Obj, Source
from ....utils.data_access import accessible_group_and_filter_ids
from ....utils.parse import get_page_and_n_per_page, parse_optional_date
from ...base import BaseHandler

SAVED_STATUSES = (
    "all",
    "savedToAllSelected",
    "savedToAnySelected",
    "savedToAnyAccessible",
    "notSavedToAnyAccessible",
    "notSavedToAnySelected",
    "notSavedToAllSelected",
)


def get_subquery_for_saved_status(stmt, saved_status, group_ids, user):
    if saved_status == "all":
        return stmt

    accessible_group_ids = [g.id for g in user.accessible_groups]
    group_ids = [g for g in group_ids if g in accessible_group_ids]
    # sources data access is group_id based and the accessible group ids are
    # already filtered above, so sa.select is safe here instead of Source.select
    active_sources = sa.select(Source.obj_id).where(Source.active.is_(True))
    polarity, scope = saved_status.split("To", 1)

    if scope == "AnyAccessible":
        subquery = active_sources.where(Source.group_id.in_(accessible_group_ids))
    elif scope == "AnySelected":
        subquery = active_sources.where(Source.group_id.in_(group_ids))
    else:
        # as many active saved groups in group_ids as there are items in group_ids
        subquery = (
            active_sources.where(Source.group_id.in_(group_ids))
            .group_by(Source.obj_id)
            .having(func.count(Source.group_id) == len(group_ids))
        )

    return stmt.where(
        Obj.id.notin_(subquery) if polarity == "notSaved" else Obj.id.in_(subquery)
    )


class CandidateFilterGetQuery(BaseModel):
    """Query parameters for listing candidates with their alert ids."""

    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "Candidate.passed_at >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "Candidate.passed_at <= endDate"
        ),
    )
    groupIDs: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of group IDs (e.g. "1,2"). Defaults to all of '
            "user's groups if filterIDs is not provided."
        ),
    )
    filterIDs: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of filter IDs (e.g. "1,2"). Defaults to all of '
            "user's groups' filters if groupIDs is not provided."
        ),
    )
    savedStatus: Literal[*SAVED_STATUSES] = Field(
        default="all",
        description=(
            "String indicating the saved status to filter candidate results for. "
            "Must be one of the enumerated values."
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )
    numPerPage: int = Field(
        default=25,
        description=(
            "Number of candidates to return per paginated request. Defaults to 25. "
            "Capped at 500."
        ),
    )


class CandidateFilterHandler(BaseHandler):
    @auth_or_token
    async def get(self, *, query: CandidateFilterGetQuery = None):
        """
        ---
        summary: Get candidates with their alert ids
        description: >-
          A lighter CandidateHandler that returns the Candidates themselves,
          including the alert id (candid) they passed on, rather than the Objs.
          Lets the upstream system that sends the alerts map them back to
          candidates.
        tags:
          - candidates
        """
        query = self.parse_query(CandidateFilterGetQuery)

        async with self.AsyncSession() as session:
            group_ids, filter_ids = await accessible_group_and_filter_ids(
                session, session.user_or_token, query.groupIDs, query.filterIDs
            )

            try:
                page_number, n_per_page = get_page_and_n_per_page(
                    query.pageNumber, query.numPerPage
                )
            except ValueError as e:
                return self.error(str(e))

            try:
                start_date = parse_optional_date(query.startDate)
            except Exception as e:
                return self.error(f"Invalid startDate value: {e}")
            try:
                end_date = parse_optional_date(query.endDate)
            except Exception as e:
                return self.error(f"Invalid endDate value: {e}")

            stmt = Candidate.select(session.user_or_token).where(
                Candidate.filter_id.in_(filter_ids)
            )
            if start_date:
                stmt = stmt.where(Candidate.passed_at >= start_date)
            if end_date:
                stmt = stmt.where(Candidate.passed_at <= end_date)
            stmt = get_subquery_for_saved_status(
                stmt, query.savedStatus, group_ids, session.user_or_token
            )

            # ascending so candidates added mid-pagination land at the end:
            # totalMatches is only computed on page 1 and the client keeps it
            result = await session.scalars(
                stmt.order_by(Candidate.passed_at.asc())
                .limit(n_per_page)
                .offset((page_number - 1) * n_per_page)
            )
            data = {"candidates": [c.to_dict() for c in result.all()]}
            if page_number == 1:
                data["totalMatches"] = await session.scalar(
                    sa.select(func.count()).select_from(stmt.alias())
                )
            return self.success(data=data)
