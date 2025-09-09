import operator  # noqa: F401

import arrow
import sqlalchemy as sa
from sqlalchemy.sql.expression import func

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import (
    Candidate,
    Filter,
    Obj,
    Source,
)
from ....utils.parse import get_list_typed, get_page_and_n_per_page
from ...base import BaseHandler

log = make_log("api/candidate_filter")


def get_user_accessible_group_and_filter_ids(session, user, group_ids, filter_ids):
    user_accessible_group_ids = [g.id for g in user.accessible_groups]
    user_accessible_filter_ids = [
        filtr.id for g in user.accessible_groups for filtr in g.filters if g.filters
    ]

    if isinstance(group_ids, str):
        group_ids = get_list_typed(
            group_ids,
            int,
            error_msg="Invalid groupIDs value -- select at least one group",
        )
        filters = session.scalars(
            Filter.select(user).where(Filter.group_id.in_(group_ids))
        ).all()
        filter_ids = [f.id for f in filters]
    elif isinstance(filter_ids, str):
        filter_ids = get_list_typed(
            filter_ids,
            int,
            error_msg="Invalid filterIDs value -- select at least one filter",
        )
        filters = session.scalars(
            Filter.select(user).where(Filter.id.in_(filter_ids))
        ).all()
        group_ids = [f.group_id for f in filters]
    else:
        # If 'groupIDs' & 'filterIDs' params not present in request, use all user groups
        group_ids = user_accessible_group_ids
        filter_ids = user_accessible_filter_ids
    return group_ids, filter_ids


def get_subquery_for_saved_status(session, stmt, saved_status, group_ids, user):
    user_accessible_group_ids = [g.id for g in user.accessible_groups]
    group_ids = [g for g in group_ids if g in user_accessible_group_ids]
    if saved_status == "all":
        return stmt

    if saved_status in [
        "savedToAllSelected",
        "savedToAnySelected",
        "savedToAnyAccessible",
        "notSavedToAnyAccessible",
        "notSavedToAnySelected",
        "notSavedToAllSelected",
    ]:
        # we can safely use sa.select(Source.obj_id) rather than
        # Source.select(user) here because sources data access is group_id based
        # and the accessible group ids have already been filtered out above
        active_sources = sa.select(Source.obj_id).where(Source.active.is_(True))
        not_in = False
        if saved_status == "savedToAllSelected":
            # Retrieve objects that have as many active saved groups that are
            # in 'group_ids' as there are items in 'group_ids'
            subquery = (
                active_sources.where(Source.group_id.in_(group_ids))
                .group_by(Source.obj_id)
                .having(func.count(Source.group_id) == len(group_ids))
            )
        elif saved_status == "savedToAnySelected":
            subquery = active_sources.where(Source.group_id.in_(group_ids))
        elif saved_status == "savedToAnyAccessible":
            subquery = active_sources.where(
                Source.group_id.in_(user_accessible_group_ids)
            )
        elif saved_status == "notSavedToAnyAccessible":
            subquery = active_sources.where(
                Source.group_id.in_(user_accessible_group_ids)
            )
            not_in = True
        elif saved_status == "notSavedToAnySelected":
            subquery = active_sources.where(Source.group_id.in_(group_ids))
            not_in = True
        else:  # notSavedToAllSelected
            # Retrieve objects that have as many active saved groups that are
            # in 'group_ids' as there are items in 'group_ids', and select
            # the objects not in that set
            subquery = (
                active_sources.where(Source.group_id.in_(group_ids))
                .group_by(Source.obj_id)
                .having(func.count(Source.group_id) == len(group_ids))
            )
            not_in = True

        return (
            stmt.where(Obj.id.notin_(subquery))
            if not_in
            else stmt.where(Obj.id.in_(subquery))
        )
    else:
        return None


class CandidateFilterHandler(BaseHandler):
    @auth_or_token
    def get(self):
        # here we want a lighter version of the CandidateHandler, that applies
        # only the startDate, endDate, groupIDs, filterIDs, and savedStatus
        # and returns the Candidates themselves including the candidate's alert id (candid)
        # and not the Objs instead, like the CandidateHandler does
        # this is useful to map the candidates to the alerts they belong to
        # in the upstream system that sends the alerts to SkyPortal

        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        group_ids = self.get_query_argument("groupIDs", None)
        filter_ids = self.get_query_argument("filterIDs", None)
        saved_status = self.get_query_argument("savedStatus", "all")

        page_number = self.get_query_argument("pageNumber", None) or 1
        n_per_page = self.get_query_argument("numPerPage", None) or 25

        with self.Session() as session:
            group_ids, filter_ids = get_user_accessible_group_and_filter_ids(
                session,
                session.user_or_token,
                group_ids,
                filter_ids,
            )

        page_number, n_per_page = get_page_and_n_per_page(page_number, n_per_page)

        with self.Session() as session:
            stmt = Candidate.select(session.user_or_token).where(
                Candidate.filter_id.in_(filter_ids)
            )
            if start_date and start_date.strip().lower() not in {
                "",
                "null",
                "undefined",
            }:
                try:
                    start_date = arrow.get(start_date).datetime
                except Exception as e:
                    return self.error(f"Invalid startDate value: {e}")
                stmt = stmt.where(Candidate.passed_at >= start_date)
            if end_date and end_date.strip().lower() not in {"", "null", "undefined"}:
                try:
                    end_date = arrow.get(end_date).datetime
                except Exception as e:
                    return self.error(f"Invalid endDate value: {e}")
                stmt = stmt.where(Candidate.passed_at <= end_date)

            stmt = get_subquery_for_saved_status(
                session, stmt, saved_status, group_ids, session.user_or_token
            )

            if stmt is None:
                return self.error(
                    f"Invalid savedStatus: {saved_status}. Must be one of the enumerated options."
                )

            candidates = session.scalars(
                stmt.order_by(Candidate.passed_at.asc())
                .limit(n_per_page)
                .offset((page_number - 1) * n_per_page)
            ).all()

            # in this handler we take a different approach. We don't require the user to pass the totalMatches
            # parameter. But, we only calculate and return the totalMatches when getting the first page.
            # it's the client's responsibility to keep it when paginating.
            # that is also why we order the candidates by passed_at asc
            # so that even if more candidates are added while the user is paginating, they will be added at the end
            # and it shouldn't break the pagination and keep the results consistent
            if page_number == 1:
                total_matches = session.scalar(
                    sa.select(func.count()).select_from(stmt.alias())
                )
            else:
                total_matches = None

            candidates = [c.to_dict() for c in candidates]
            response = {
                "candidates": candidates,
            }
            if total_matches is not None:
                response["totalMatches"] = total_matches
            return self.success(data=response)
