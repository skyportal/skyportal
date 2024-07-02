import itertools
import time
import traceback

import arrow
import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import (
    DBSession,
    DefaultObservationPlanRequest,
    EventObservationPlan,
    ObservationPlanRequest,
)
from skyportal.handlers.api.observation_plan import (
    send_observation_plan,
    post_survey_efficiency_analysis,
)
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log('observation_plan_queue')

init_db(**cfg['database'])


def prioritize_requests(requests):
    try:
        if (
            len(requests) == 1
        ):  # if there is only one plan in the queue, no need to prioritize
            return 0

        telescopeAllocationLookup = {}
        allocationByPlanLookup = {}

        # we create 2 lookups to avoid repeating some operations like getting the morning and evening for a telescope
        for ii, plan_requests in enumerate(requests):
            for plan in plan_requests:
                allocation_id = plan.allocation_id
                if ii not in allocationByPlanLookup.keys():
                    allocationByPlanLookup[ii] = [
                        {
                            "allocation_id": allocation_id,
                            "start_date": plan.payload.get("start_date", None),
                        }
                    ]
                else:
                    allocationByPlanLookup[ii].append(
                        {
                            "allocation_id": allocation_id,
                            "start_date": plan.payload.get("start_date", None),
                        }
                    )
                if allocation_id not in telescopeAllocationLookup:
                    telescopeAllocationLookup[
                        allocation_id
                    ] = plan.allocation.instrument.telescope.current_time()

        # now we loop over the plans. For plans with multiple plans we pick the allocation with the earliest start date and morning time
        # at the same time, we pick the plan to prioritize
        plan_with_priority = None
        for plan_id, allocationsAndStartDate in allocationByPlanLookup.items():
            if plan_with_priority is None:
                plan_with_priority = {
                    "plan_id": plan_id,
                    "morning": telescopeAllocationLookup[
                        allocationsAndStartDate[0]["allocation_id"]
                    ]["morning"],
                    "start_date": allocationsAndStartDate[0]["start_date"],
                }
            earliest = None
            for allocationAndStartDate in allocationsAndStartDate:
                # find the plan
                if earliest is None:
                    earliest = allocationAndStartDate
                    continue
                if (
                    telescopeAllocationLookup[allocationAndStartDate["allocation_id"]][
                        "morning"
                    ]
                    is False
                ):
                    continue
                start_date = allocationAndStartDate["start_date"]
                if start_date is None:
                    continue
                start_date = arrow.get(start_date).datetime
                if (
                    start_date
                    > telescopeAllocationLookup[
                        allocationAndStartDate["allocation_id"]
                    ]["morning"].datetime
                ):
                    continue
                if (
                    telescopeAllocationLookup[earliest["allocation_id"]]["morning"]
                    is False
                ):
                    earliest = allocationAndStartDate
                    continue
                if (
                    telescopeAllocationLookup[allocationAndStartDate["allocation_id"]][
                        "morning"
                    ].datetime
                    < telescopeAllocationLookup[earliest["allocation_id"]][
                        "morning"
                    ].datetime
                ):
                    earliest = plan.allocation
                    continue
            allocationByPlanLookup[plan_id] = [earliest]

            # check if that plan is more urgent than the current plan_with_priority
            if telescopeAllocationLookup[earliest["allocation_id"]]["morning"] is None:
                continue
            if plan_with_priority["morning"] is None:
                plan_with_priority = {
                    "plan_id": plan_id,
                    "morning": telescopeAllocationLookup[earliest["allocation_id"]][
                        "morning"
                    ],
                    "start_date": earliest["start_date"],
                }
                continue
            if (
                telescopeAllocationLookup[earliest["allocation_id"]]["morning"]
                <= plan_with_priority["morning"]
                and earliest["start_date"] < plan_with_priority["start_date"]
            ):
                plan_with_priority = {
                    "plan_id": plan_id,
                    "morning": telescopeAllocationLookup[earliest["allocation_id"]][
                        "morning"
                    ],
                    "start_date": earliest["start_date"],
                }
                continue

        return plan_with_priority["plan_id"]
    except Exception as e:
        traceback.print_exc()
        log(f"Error occured prioritizing the observation plan queue: {e}")
        return 0


@check_loaded(logger=log)
def service(*args, **kwargs):
    log("Starting observation plan queue.")
    while True:
        with DBSession() as session:
            try:
                stmt = sa.select(ObservationPlanRequest).where(
                    # we only want to process plans that have been created in the last 72 hours
                    sa.or_(
                        sa.and_(
                            ObservationPlanRequest.status == "pending submission",
                            ObservationPlanRequest.created_at
                            > arrow.utcnow().shift(days=-3).datetime,
                        ),
                        # or plans that have been "running" for more than 24 hours but less than 72 hours
                        # this is a way to grab plans that have been stuck in the running state
                        # and have not been processed
                        sa.and_(
                            ObservationPlanRequest.status == "running",
                            ObservationPlanRequest.created_at
                            < arrow.utcnow().shift(days=-1).datetime,
                            ObservationPlanRequest.created_at
                            > arrow.utcnow().shift(days=-3).datetime,
                        ),
                    )
                )
                single_requests = session.scalars(stmt).unique().all()

                # reprocessing plans that were marked as running before (and probably stuck in that state)
                # is lower priority, so if we have any pending submission plans, we prioritize those
                # and remove the running plans from the list
                if any(
                    request.status == "pending submission"
                    for request in single_requests
                ):
                    single_requests = [
                        request
                        for request in single_requests
                        if request.status == "pending submission"
                    ]

                # requests is a list. We want to group that list of plans to be a list of list,
                # we group based on the plans 'combined_id' which is a unique uuid for a group of plans
                # plans that are not grouped simply don't have one
                combined_requests = [
                    request
                    for request in single_requests
                    if request.combined_id is not None
                ]
                requests = [
                    list(group)
                    for _, group in itertools.groupby(
                        combined_requests, lambda x: x.combined_id
                    )
                ] + [
                    [request]
                    for request in single_requests
                    if request.combined_id is None
                ]

                if len(requests) == 0:
                    time.sleep(5)
                    continue

                log(f"Prioritizing {len(requests)} observation plan requests...")

                index = prioritize_requests(requests)

                plan_requests = requests[index]
                plan_ids = []
                if len(plan_requests) == 1:
                    plan_request = plan_requests[0]
                    try:
                        plan_id = (
                            plan_request.allocation.instrument.api_class_obsplan.submit(
                                plan_request.id, asynchronous=False
                            )
                        )
                        plan_ids.append(plan_id)
                    except Exception as e:
                        traceback.print_exc()
                        plan_request.status = 'failed to process'
                        log(f'Error processing observation plan: {e.args[0]}')
                        session.commit()
                        time.sleep(2)
                        continue
                    plan_request = session.scalar(
                        sa.select(ObservationPlanRequest).where(
                            ObservationPlanRequest.id == plan_request.id
                        )
                    )
                    log(f"Plan {plan_id} status: {plan_request.status}")
                    if plan_request.status == "running":
                        plan_request.status = 'complete'
                        session.merge(plan_request)
                        session.commit()

                    try:
                        flow = Flow()
                        flow.push(
                            '*',
                            "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
                            payload={"gcnEvent_dateobs": plan_request.gcnevent.dateobs},
                        )
                    except Exception as e:
                        log(
                            f'Error refreshing observation plan requests on the frontend: {e.args[0]}'
                        )

                else:
                    try:
                        plan_ids = plan_requests[
                            0
                        ].allocation.instrument.api_class_obsplan.submit_multiple(
                            plan_requests, asynchronous=False
                        )
                    except Exception as e:
                        for plan_request in plan_requests:
                            plan_request.status = 'failed to process'
                        log(
                            f'Error processing combined plans: {[plan_request.id for plan_request in plan_requests]}: {str(e)}'
                        )
                        session.commit()
                        time.sleep(2)
                        continue

                    for plan_request in plan_requests:
                        plan_request = session.scalar(
                            sa.select(ObservationPlanRequest).where(
                                ObservationPlanRequest.id == plan_request.id
                            )
                        )
                        log(f"Plan {plan_request.id} status: {plan_request.status}")
                        if plan_request.status == "running":
                            plan_request.status = 'complete'
                            session.merge(plan_request)
                            session.commit()

                    try:
                        unique_dateobs = {
                            plan.gcnevent.dateobs for plan in plan_requests
                        }
                        flow = Flow()
                        for dateobs in unique_dateobs:
                            flow.push(
                                '*',
                                "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
                                payload={"gcnEvent_dateobs": dateobs},
                            )
                    except Exception as e:
                        log(
                            f"Error refreshing observation plan requests on the frontend: {e}"
                        )

                log(f"Generated plans: {plan_ids}")
                for id in plan_ids:
                    try:
                        plan = session.scalars(
                            sa.select(EventObservationPlan).where(
                                EventObservationPlan.id == int(id)
                            )
                        ).first()
                        default = plan.observation_plan_request.payload.get(
                            'default', None
                        )
                        if default is not None:
                            defaultobsplanrequest = session.scalars(
                                sa.select(DefaultObservationPlanRequest).where(
                                    DefaultObservationPlanRequest.id == int(default)
                                )
                            ).first()
                            if defaultobsplanrequest is not None:
                                if defaultobsplanrequest.auto_send:
                                    send_observation_plan(
                                        plan.observation_plan_request.id,
                                        session=session,
                                        auto_send=True,
                                    )
                                for (
                                    default_survey_efficiency
                                ) in defaultobsplanrequest.default_survey_efficiencies:
                                    post_survey_efficiency_analysis(
                                        default_survey_efficiency.to_dict(),
                                        plan.id,
                                        1,
                                        session,
                                        asynchronous=False,
                                    )
                    except Exception as e:
                        log(
                            f"Error occured processing default queue submission or survey efficiency for plan {id}: {e}"
                        )
                        session.rollback()
                        time.sleep(2)

            except Exception as e:
                log(f"Error occured processing the observation plan queue: {e}")
                session.rollback()
                time.sleep(2)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting observation plan queue: {str(e)}")
        raise e
