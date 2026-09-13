"""Close out observing-run assignments once their data arrives.

Marking an assignment observed is a manual step that is easy to forget, and on
an instrument like NGPS there are too many per night to keep up with by hand.
"""

import sqlalchemy as sa
from sqlalchemy.orm import aliased

from ..models import ClassicalAssignment, ObservingRun

# Only a pending assignment is ever touched, so an explicit "not done" stands.
PENDING = "pending"
DONE = "done"


async def mark_assignments_observed(session, spectrum, window_days=1):
    """Mark the assignments a spectrum satisfies as done.

    A spectrum that names its assignment settles the question outright. Most
    arrive without that link, so the fallback matches the run's own instrument
    and a calendar date within `window_days` of the exposure -- a run's date is
    the local night, so an exposure after midnight UTC lands on the next day.

    Returns
    -------
    list of int
        IDs of the assignments that were marked done.
    """
    if spectrum.observed_at is None:
        return []

    query = ClassicalAssignment.select(session.user_or_token, mode="update").where(
        ClassicalAssignment.status == PENDING
    )

    if spectrum.assignment_id is not None:
        query = query.where(ClassicalAssignment.id == spectrum.assignment_id)
    else:
        # Without a named assignment there is nothing to match on but the run's
        # instrument and date, which `window_days=None` declines to do.
        if window_days is None or spectrum.instrument_id is None:
            return []
        observed_on = spectrum.observed_at.date()
        # Aliased: the access-controlled select already joins ObservingRun for
        # its group-scoped read rule, and joining it again is a duplicate alias.
        run = aliased(ObservingRun)
        query = query.join(run, run.id == ClassicalAssignment.run_id).where(
            ClassicalAssignment.obj_id == spectrum.obj_id,
            run.instrument_id == spectrum.instrument_id,
            sa.func.abs(run.calendar_date - observed_on) <= window_days,
        )

    assignments = (await session.scalars(query)).unique().all()
    for assignment in assignments:
        assignment.status = DONE
    return [assignment.id for assignment in assignments]
