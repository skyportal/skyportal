import operator  # noqa: F401
import string

import arrow
import sqlalchemy as sa
from sqlalchemy.sql.expression import func

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import (
    Candidate,
    Filter,
    Source,
)
from ...base import BaseHandler

log = make_log("api/candidate_filter")


def get_subquery_for_saved_status(
    session, stmt, saved_status, group_ids, user_accessible_group_ids
):
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
        source_subquery = Source.select(
            session.user_or_token, columns=[Source.obj_id]
        ).where(Source.active.is_(True))
        not_in = False
        if saved_status == "savedToAllSelected":
            # Retrieve objects that have as many active saved groups that are
            # in 'group_ids' as there are items in 'group_ids'
            source_subquery = (
                source_subquery.where(Source.group_id.in_(group_ids))
                .group_by(Source.obj_id)
                .having(func.count(Source.group_id) == len(group_ids))
            )
        elif saved_status == "savedToAnySelected":
            source_subquery = source_subquery.where(Source.group_id.in_(group_ids))
        elif saved_status == "savedToAnyAccessible":
            source_subquery = source_subquery.where(
                Source.group_id.in_(user_accessible_group_ids)
            )
        elif saved_status == "notSavedToAnyAccessible":
            source_subquery = source_subquery.where(
                Source.group_id.in_(user_accessible_group_ids)
            )
            not_in = True
        elif saved_status == "notSavedToAnySelected":
            source_subquery = source_subquery.where(Source.group_id.in_(group_ids))
            not_in = True
        elif saved_status == "notSavedToAllSelected":
            source_subquery = (
                source_subquery.where(Source.group_id.in_(group_ids))
                .group_by(Source.obj_id)
                .having(func.count(Source.group_id) == len(group_ids))
            )
            not_in = True

        return (
            stmt.where(Candidate.obj_id.notin_(source_subquery))
            if not_in
            else stmt.where(Candidate.obj_id.in_(source_subquery))
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
            user_accessible_group_ids = [
                g.id for g in self.current_user.accessible_groups
            ]
            user_accessible_filter_ids = [
                filtr.id
                for g in self.current_user.accessible_groups
                for filtr in g.filters
                if g.filters is not None
            ]
            if group_ids is not None:
                if (
                    isinstance(group_ids, str)
                    and "," in group_ids
                    and set(group_ids).issubset(string.digits + ",")
                ):
                    group_ids = [int(g_id) for g_id in group_ids.split(",")]
                elif isinstance(group_ids, str) and group_ids.isdigit():
                    group_ids = [int(group_ids)]
                elif isinstance(group_ids, list):
                    try:
                        group_ids = [int(g_id) for g_id in group_ids]
                    except ValueError:
                        return self.error(
                            "Invalid groupIDs value -- select at least one group"
                        )
                else:
                    return self.error(
                        "Invalid groupIDs value -- select at least one group"
                    )
                filters = session.scalars(
                    Filter.select(self.current_user).where(
                        Filter.group_id.in_(group_ids)
                    )
                ).all()
                filter_ids = [f.id for f in filters]
            elif filter_ids is not None:
                if (
                    isinstance(filter_ids, str)
                    and "," in filter_ids
                    and set(filter_ids) in set(string.digits + ",")
                ):
                    filter_ids = [int(f_id) for f_id in filter_ids.split(",")]
                elif isinstance(filter_ids, str) and filter_ids.isdigit():
                    filter_ids = [int(filter_ids)]
                elif isinstance(filter_ids, list):
                    try:
                        filter_ids = [int(f_id) for f_id in filter_ids]
                    except ValueError:
                        return self.error("Invalid filterIDs parameter value.")
                else:
                    return self.error("Invalid filterIDs parameter value.")
                filters = session.scalars(
                    Filter.select(self.current_user).where(Filter.id.in_(filter_ids))
                ).all()
                group_ids = [f.group_id for f in filters]
            else:
                # If 'groupIDs' & 'filterIDs' params not present in request, use all user groups
                group_ids = user_accessible_group_ids
                filter_ids = user_accessible_filter_ids

        try:
            page = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            n_per_page = int(n_per_page)
        except ValueError:
            return self.error("Invalid numPerPage value.")
        n_per_page = min(n_per_page, 500)

        with self.Session() as session:
            stmt = Candidate.select(session.user_or_token).where(
                Candidate.filter_id.in_(filter_ids)
            )
            if start_date is not None and str(start_date).strip() not in [
                "",
                "null",
                "undefined",
            ]:
                start_date = arrow.get(start_date).datetime
                stmt = stmt.where(Candidate.passed_at >= start_date)
            if end_date is not None and str(end_date).strip() not in [
                "",
                "null",
                "undefined",
            ]:
                end_date = arrow.get(end_date).datetime
                stmt = stmt.where(Candidate.passed_at <= end_date)

            stmt = get_subquery_for_saved_status(
                session,
                stmt,
                saved_status,
                group_ids,
                user_accessible_group_ids,
            )

            if stmt is None:
                return self.error(
                    f"Invalid savedStatus: {saved_status}. Must be one of the enumerated options."
                )

            candidates = session.scalars(
                stmt.order_by(Candidate.passed_at.asc())
                .limit(n_per_page)
                .offset((page - 1) * n_per_page)
            ).all()

            # in this handler we take a different approach. We don't require the user to pass the totalMatches
            # parameter. But, we only calculate and return the totalMatches when getting the first page.
            # it's the client's responsibility to keep it when paginating.
            # that is also why we order the candidates by passed_at asc
            # so that even if more candidates are added while the user is paginating, they will be added at the end
            # and it shouldn't break the pagination and keep the results consistent
            if page == 1:
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
