import asyncio
import json
import time
from copy import deepcopy
from threading import Thread

import arrow
import requests
import tornado.escape
import tornado.ioloop
import tornado.web

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.observation_plan import (
    post_observation_plan,
    post_observation_plans,
    post_survey_efficiency_analysis,
)
from skyportal.models import DBSession, Allocation

env, cfg = load_env()
log = make_log('observation_plan_queue')

init_db(**cfg['database'])

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)

queue = []


def prioritize_queue(queue, session):
    try:
        if (
            len(queue) == 1
        ):  # if there is only one plan in the queue, no need to prioritize
            return 0

        telescopeAllocationLookup = {}
        allocationByPlanLookup = {}

        # we create 2 lookups to avoid repeating some operations like getting the morning and evening for a telescope
        for ii, (
            plans,
            survey_efficiencies,
            combine_plans,
            default_plan,
            user_id,
        ) in enumerate(queue):
            for plan in plans:
                allocation_id = plan.get("allocation_id", None)
                if ii not in allocationByPlanLookup.keys():
                    allocationByPlanLookup[ii] = [
                        {
                            "allocation_id": allocation_id,
                            "start_date": plan.get("payload", {}).get(
                                "start_date", None
                            ),
                        }
                    ]
                else:
                    allocationByPlanLookup[ii].append(
                        {
                            "allocation_id": allocation_id,
                            "start_date": plan.get("payload", {}).get(
                                "start_date", None
                            ),
                        }
                    )
                if allocation_id not in telescopeAllocationLookup:
                    allocation = session.query(Allocation).get(allocation_id)
                    telescope = allocation.instrument.telescope

                    telescopeAllocationLookup[allocation_id] = telescope.current_time

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
                    earliest = allocation
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
        log(f"Error occured prioritizing the observation plan queue: {e}")
        return 0


def service(queue):
    while True:
        if len(queue) == 0:
            time.sleep(2)
            continue

        with DBSession() as session:
            queue_copy = deepcopy(queue)
            index = prioritize_queue(queue_copy, session)

            plans, survey_efficiencies, combine_plans, default_plan, user_id = queue[
                index
            ]
            plan_ids = []
            try:
                if len(plans) == 1:
                    plan_id = post_observation_plan(
                        plans[0],
                        user_id,
                        session,
                        default_plan=default_plan,
                        asynchronous=False,
                    )
                    plan_ids.append(plan_id)
                else:
                    if combine_plans:
                        plan_ids = post_observation_plans(
                            plans,
                            user_id,
                            session,
                            default_plan=default_plan,
                            asynchronous=False,
                        )
                    else:
                        for plan in plans:
                            plan_id = post_observation_plan(
                                plan,
                                user_id,
                                session,
                                default_plan=default_plan,
                                asynchronous=False,
                            )
                            plan_ids.append(plan_id)
            except Exception as e:
                log(f"Observation plan failed: {str(e)}")

            for plan_id in plan_ids:
                for survey_efficiency in survey_efficiencies:
                    try:
                        post_survey_efficiency_analysis(
                            survey_efficiency,
                            plan_id,
                            user_id,
                            session,
                            asynchronous=False,
                        )
                    except Exception as e:
                        log(f"Survey efficiency analysis failed: {str(e)}")

            queue.pop(index)


def api(queue):
    class QueueHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            self.write({"status": "success", "data": {"queue_length": len(queue)}})

        def post(self):
            try:
                data = tornado.escape.json_decode(self.request.body)
            except json.JSONDecodeError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Malformed JSON data"})

            user_id = data.get('user_id', None)
            plans = data.get('plans', None)
            plan = data.get('plan', None)
            survey_efficiencies = data.get('survey_efficiencies', [])
            combine_plans = data.get('combine_plans', False)
            default_plan = data.get('default_plan', False)

            if user_id is None:
                self.set_status(400)
                return self.write({"status": "error", "message": "Missing user_id"})
            if plan is None and plans is None:
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Missing plan or plans"}
                )

            if plan is not None:
                plans = [plan]

            try:
                user_id = int(user_id)
            except ValueError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Invalid user_id"})

            if not isinstance(combine_plans, bool):
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Invalid combine_plans"}
                )

            if not isinstance(plans, list):
                self.set_status(400)
                return self.write({"status": "error", "message": "Invalid plans"})

            if not isinstance(survey_efficiencies, list):
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Invalid survey_efficiencies"}
                )

            for plan in plans:
                if not isinstance(plan, dict):
                    self.set_status(400)
                    return self.write({"status": "error", "message": "Invalid plan"})

            for survey_efficiency in survey_efficiencies:
                if not isinstance(survey_efficiency, dict):
                    self.set_status(400)
                    return self.write(
                        {
                            "status": "error",
                            "message": "Invalid survey_efficiencies, not all elements are dicts",
                        }
                    )

            queue_copy = deepcopy(queue)
            # check that no plan in the queue has the same queue_name as any plan in the request
            for plan in plans:
                for plans_in_queue in queue_copy:
                    if any(
                        plan.get("payload", {}).get("queue_name", None)
                        == plan_in_queue.get("payload", {}).get("queue_name", None)
                        for plan_in_queue in plans_in_queue[0]
                    ):
                        self.set_status(400)
                        return self.write(
                            {
                                "status": "error",
                                "message": f"An observation plan called {plan['queue_name']} is already being processed.",
                            }
                        )

                    # if there is a plan that has the same values for all the keys in the payload, then it is a duplicate
                    if any(
                        plan.get("payload", {}) == plan_in_queue.get("payload", {})
                        for plan_in_queue in plans_in_queue[0]
                    ):
                        self.set_status(400)
                        return self.write(
                            {
                                "status": "error",
                                "message": "An observation plan with the same parameters is already being processed.",
                            }
                        )

            # if there is more than one plan and combine plan is false, then we add the plans to the queue one by one
            if len(plans) > 1 and combine_plans is False:
                for plan in plans:
                    try:
                        queue.append(
                            [[plan], survey_efficiencies, False, default_plan, user_id]
                        )
                    except Exception as e:
                        log(f"Error submitting observation plan: {str(e)}")
                        self.set_status(400)
                        return self.write(
                            {
                                "status": "error",
                                "message": "Error processing observation plan",
                            }
                        )

                self.set_status(200)
                return self.write(
                    {
                        "status": "success",
                        "message": "Observation plan(s) accepted into queue",
                        "data": {"queue_length": len(queue)},
                    }
                )
            else:
                try:
                    queue.append(
                        [
                            plans,
                            survey_efficiencies,
                            combine_plans,
                            default_plan,
                            user_id,
                        ]
                    )

                    self.set_status(200)
                    return self.write(
                        {
                            "status": "success",
                            "message": "Observation plan(s) accepted into queue",
                            "data": {"queue_length": len(queue)},
                        }
                    )
                except Exception as e:
                    log(f"Error submitting observation plan(s): {str(e)}")
                    self.set_status(400)
                    return self.write(
                        {
                            "status": "error",
                            "message": "Error processing observation plan(s)",
                        }
                    )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.observation_plan_queue"])
    loop.run_forever()


if __name__ == "__main__":
    try:
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t.start()
        t2.start()

        while True:
            log(f"Current obsplan queue length: {len(queue)}")
            time.sleep(120)
    except Exception as e:
        log(f"Error starting observation plan queue: {str(e)}")
        raise e
