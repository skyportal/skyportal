import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import TNSRobot, TNSRobotSubmission
from ...base import BaseHandler

log = make_log("api/tns_robot_submission")


class TNSRobotSubmissionHandler(BaseHandler):
    @auth_or_token
    def get(self, tnsrobot_id, tnsrobot_submission_id=None):
        """
        ---
        single:
            summary: Retrieve a TNSRobotSubmission
            description: Retrieve a TNSRobotSubmission
            tags:
                - tns robot
            parameters:
                - in: path
                  name: tnsrobot_id
                  required: true
                  schema:
                    type: integer
                  description: The ID of the TNSRobot
                - in: path
                  name: tnsrobot_submission_id
                  required: false
                  schema:
                    type: integer
                  description: The ID of the TNSRobotSubmission
            responses:
                200:
                    content:
                        application/json:
                            schema: TNSRobotSubmission
                400:
                    content:
                        application/json:
                            schema: Error
        multiple:
            summary: Retrieve all TNSRobotSubmissions
            description: Retrieve all TNSRobotSubmissions
            tags:
                - tns robot
            parameters:
                - in: path
                  name: tnsrobot_id
                  required: true
                  schema:
                    type: integer
                  description: The ID of the TNSRobot
                - in: query
                  name: pageNumber
                  required: false
                  schema:
                    type: integer
                  description: The page number to retrieve, starting at 1
                - in: query
                  name: numPerPage
                  required: false
                  schema:
                    type: integer
                  description: The number of results per page, defaults to 100
                - in: query
                  name: include_payload
                  required: false
                  schema:
                    type: boolean
                  description: Whether to include the payload in the response
                - in: query
                  name: include_response
                  required: false
                  schema:
                    type: boolean
                  description: Whether to include the response in the response
            responses:
                200:
                    content:
                        application/json:
                            schema: ArrayOfTNSRobotSubmissions
                400:
                    content:
                        application/json:
                            schema: Error
        """
        include_payload = self.get_query_argument("include_payload", False)
        include_response = self.get_query_argument("include_response", False)
        if str(include_payload).lower().strip() in ["true", "t", "1"]:
            include_payload = True
        if str(include_response).lower().strip() in ["true", "t", "1"]:
            include_response = True

        page_number = self.get_query_argument("pageNumber", 1)
        page_size = self.get_query_argument("numPerPage", 100)
        obj_id = self.get_query_argument("objectID", None)
        try:
            page_number = int(page_number)
            page_size = int(page_size)
            if page_number < 1 or page_size < 1:
                raise ValueError
        except ValueError:
            return self.error(
                "pageNumber and pageSize must be integers, with pageNumber starting at 1 and pageSize > 0"
            )

        if obj_id is not None:
            try:
                obj_id = str(obj_id)
                if len(obj_id) == 0:
                    obj_id = None
            except ValueError:
                return self.error("objectID must be a string")

        # for a given TNSRobot, return all the submissions (paginated)
        with self.Session() as session:
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f"TNSRobot {tnsrobot_id} not found")

            if tnsrobot_submission_id is not None:
                # we want to return a single submission
                submission = session.scalar(
                    TNSRobotSubmission.select(session.user_or_token).where(
                        TNSRobotSubmission.tnsrobot_id == tnsrobot_id,
                        TNSRobotSubmission.id == tnsrobot_submission_id,
                    )
                )
                if submission is None:
                    return self.error(
                        f"Submission {tnsrobot_submission_id} not found for TNSRobot {tnsrobot_id}"
                    )
                submission = {
                    "tns_name": submission.obj.tns_name,
                    **submission.to_dict(),
                }
                return self.success(data=submission)
            else:
                stmt = TNSRobotSubmission.select(session.user_or_token).where(
                    TNSRobotSubmission.tnsrobot_id == tnsrobot_id
                )
                if obj_id is not None:
                    stmt = stmt.where(TNSRobotSubmission.obj_id == obj_id)

                # run a count query to get the total number of results
                total_matches = session.execute(
                    sa.select(sa.func.count()).select_from(stmt)
                ).scalar()

                # order by created_at descending
                stmt = stmt.order_by(TNSRobotSubmission.created_at.desc())

                # undefer the payload and response columns if requested
                if include_payload:
                    stmt = stmt.options(sa.orm.undefer(TNSRobotSubmission.payload))
                if include_response:
                    stmt = stmt.options(sa.orm.undefer(TNSRobotSubmission.response))

                # get the paginated results
                submissions = session.scalars(
                    stmt.limit(page_size).offset((page_number - 1) * page_size)
                ).all()

                return self.success(
                    data={
                        "tnsrobot_id": tnsrobot.id,
                        "submissions": [
                            {"tns_name": s.obj.tns_name, **s.to_dict()}
                            for s in submissions
                        ],
                        "pageNumber": page_number,
                        "numPerPage": page_size,
                        "totalMatches": total_matches,
                    }
                )
