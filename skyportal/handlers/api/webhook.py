import datetime

from baselayer.log import make_log
from baselayer.app.env import load_env

from ..base import BaseHandler

from ...models import (
    ObjAnalysis,
)

log = make_log('app/webhook')

_, cfg = load_env()


class AnalysisWebhookHandler(BaseHandler):
    def post(self, analysis_resource_type, token):
        """
        ---
        description: Return the results of an analysis
        tags:
          - webhook
        parameters:
          - in: path
            name: analysis_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the analysis was performed on:
               must be "obj" (more to be added in the future)
          - in: path
            name: token
            required: true
            schema:
              type: string
            description: |
               The unique token for this analysis.
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: object
                    description: Results data of this analysis
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
        log(
            f"Received webhook request for Analysis type={analysis_resource_type} token={token}"
        )

        # allowable resources now are [obj]. Can be extended in the future.
        if analysis_resource_type.lower() not in ['obj']:
            return self.error("Invalid analysis resource type", status=403)

        # Authenticate the token, then lock this analysis, before going on.

        with self.Session() as session:
            try:
                analysis = (
                    session.query(ObjAnalysis)
                    .filter(ObjAnalysis.token == token)
                    .first()
                )
                if not analysis:
                    return self.error("Invalid token", status=403)
                last_active = analysis.last_activity
                if analysis.status not in ['pending', 'queued']:
                    return self.error(
                        f"Analysis already updated with status='{analysis.status}'"
                        f" and message={analysis.status_message}",
                        status=403,
                    )
                if (
                    analysis.invalid_after
                    and datetime.datetime.utcnow() > analysis.invalid_after
                ):
                    analysis.status = 'timed_out'
                    analysis.status_message = f'Analysis timed out before webhook call at {str(datetime.datetime.utcnow())}'
                    analysis.last_activity = datetime.datetime.utcnow()
                    analysis.duration = (
                        analysis.last_activity - last_active
                    ).total_seconds()
                    session.commit()
                    session.close()
                    return self.error("Token has expired", status=400)

                # lock the analysis associated with this token and commit immediately to avoid race conditions,
                # so that the results are not written more than once
                analysis.status = 'completed'
                analysis.last_activity = datetime.datetime.utcnow()
                analysis.duration = (
                    analysis.last_activity - last_active
                ).total_seconds()
                session.commit()
            except Exception as e:
                log(f'Trouble posting Analysis results. Token: {token}. Error: {e}')
                return self.error(
                    f'Trouble posting Analysis results. Token: {token}. Error: {e}',
                    status=403,
                )

            data = self.get_json()

            if data.get("status", "error") != "success":
                analysis.status = 'failure'
            analysis.status_message = data.get("message", "")

            results = data.get("analysis", {})
            if len(results.keys()) > 0:
                analysis._data = results
                analysis.save_data()
                log(
                    f"Saved webhook data at {analysis.filename}. Message: {analysis.status_message}"
                )
            else:
                log(
                    f"Note: empty analysis results for this webhook. Message: {analysis.status_message}"
                )

            session.commit()

        return self.success(data={"status": "success"})
