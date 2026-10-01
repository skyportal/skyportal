"""Classify Zooniverse subjects from SkyPortal.

SkyPortal is the Incubator Front End here, so it does what a Zooniverse
front end does: pick a subject off the workflow's queue, show it, and post the
volunteer's answer back to Panoptes as a classification.

Panoptes is reached from the server, never the browser: the client secret would
be public in a hosted front end, which the Zooniverse IFE guidance rules out.
"""

import datetime
import secrets
import urllib.parse

import requests
import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...models import Group, ZooniverseToken
from ..base import BaseHandler
from .classification import post_classification
from .source import post_source_async

env, cfg = load_env()
log = make_log("api/zooniverse")

PANOPTES_ENDPOINT = "https://www.zooniverse.org"
ACCEPT_TYPE = "application/vnd.api+json; version=1"
TIMEOUT = 30

# Cached across requests: a bearer token is good for two hours and the token
# endpoint is rate limited.
_token = {"value": None}


def zooniverse_config():
    return cfg.get("zooniverse") or {}


def panoptes_token(force=False):
    conf = zooniverse_config()
    if _token["value"] and not force:
        return _token["value"]

    response = requests.post(
        f"{conf.get('endpoint', PANOPTES_ENDPOINT).rstrip('/')}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": conf.get("client_id"),
            "client_secret": conf.get("client_secret"),
            "url": conf.get("endpoint", PANOPTES_ENDPOINT),
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    _token["value"] = response.json().get("access_token")
    return _token["value"]


def panoptes_request(method, path, payload=None, retry=True, token=None):
    """Call Panoptes as `token` (a volunteer) or as the instance itself."""
    conf = zooniverse_config()
    endpoint = conf.get("endpoint", PANOPTES_ENDPOINT).rstrip("/")
    response = requests.request(
        method,
        f"{endpoint}/api{path}",
        json=payload,
        headers={
            "Authorization": f"Bearer {token or panoptes_token()}",
            "Accept": ACCEPT_TYPE,
            # Panoptes answers in vnd.api+json but only parses application/json.
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT,
    )
    if response.status_code == 401 and retry and token is None:
        panoptes_token(force=True)
        return panoptes_request(method, path, payload, retry=False)
    response.raise_for_status()
    return response.json() if response.content else {}


def redirect_uri(handler):
    """Where Zooniverse sends the volunteer back to.

    Must match a callback registered on the OAuth application, so it is taken
    from config when set rather than guessed from the request.
    """
    conf = zooniverse_config()
    if conf.get("redirect_uri"):
        return conf["redirect_uri"]
    base = (
        cfg.get("server.url") or f"{handler.request.protocol}://{handler.request.host}"
    )
    return f"{base.rstrip('/')}/api/zooniverse/auth/callback"


def volunteer_token(handler, session):
    """The signed-in volunteer's Panoptes token, refreshed if it has expired.

    Returns None when this user has not linked a Zooniverse account; callers
    decide whether to fall back to the instance's own credentials.
    """
    user_id = handler.associated_user_object.id
    record = session.scalar(
        sa.select(ZooniverseToken).where(ZooniverseToken.user_id == user_id)
    )
    if record is None:
        return None

    expires_at = record.expires_at
    if expires_at is not None and expires_at > datetime.datetime.utcnow():
        return record.access_token
    if not record.refresh_token:
        return record.access_token

    conf = zooniverse_config()
    endpoint = conf.get("endpoint", PANOPTES_ENDPOINT).rstrip("/")
    response = requests.post(
        f"{endpoint}/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": record.refresh_token,
            "client_id": conf.get("client_id"),
            "client_secret": conf.get("client_secret"),
        },
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        log(f"Could not refresh the Zooniverse token for user {user_id}")
        return record.access_token
    store_token(session, user_id, response.json(), endpoint)
    return record.access_token


def store_token(session, user_id, payload, endpoint):
    """Persist a token response, and record who it belongs to on Panoptes."""
    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    expires_at = (
        datetime.datetime.utcnow() + datetime.timedelta(seconds=int(expires_in))
        if expires_in
        else None
    )

    login = user_id_on_panoptes = None
    try:
        me = requests.get(
            f"{endpoint}/api/me",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": ACCEPT_TYPE,
            },
            timeout=TIMEOUT,
        ).json()
        panoptes_user = (me.get("users") or [{}])[0]
        login = panoptes_user.get("login")
        user_id_on_panoptes = panoptes_user.get("id")
    except requests.RequestException:
        # Attribution detail only; the token is still usable without it.
        pass

    record = session.scalar(
        sa.select(ZooniverseToken).where(ZooniverseToken.user_id == user_id)
    )
    if record is None:
        record = ZooniverseToken(user_id=user_id)
        session.add(record)
    record.access_token = access_token
    record.refresh_token = payload.get("refresh_token") or record.refresh_token
    record.expires_at = expires_at
    record.zooniverse_login = login or record.zooniverse_login
    record.zooniverse_user_id = user_id_on_panoptes or record.zooniverse_user_id
    session.commit()
    return record


async def record_in_skyportal(session, user_id, conf, data, value):
    """Record the volunteer's answer in SkyPortal as well as in Panoptes, so a
    scan done through Zooniverse leaves the same trace as one done on the
    scanning page.

    Panoptes has already accepted the answer by the time this runs, so failures
    here are returned, not raised: the volunteer is never asked to classify the
    same subject twice.
    """
    outcome = {}
    obj_id = data.get("obj_id")
    save_group_ids = data.get("save_group_ids")
    if save_group_ids is None:
        save_group_ids = conf.get("save_group_ids")
    # Who decides the class. Under "consensus" (the default) one volunteer's
    # answer only saves the object; the class is written later by Caesar's
    # aggregated verdict, so the crowd is counted once rather than a row per
    # volunteer. "volunteer" records each answer directly, for instances not
    # running Caesar.
    if conf.get("classification_source", "consensus") == "volunteer":
        # The Zooniverse task speaks in answer indices; SkyPortal speaks in
        # taxonomy classes. class_map is the translation between the two.
        class_map = conf.get("class_map") or {}
        skyportal_class = data.get("skyportal_classification") or class_map.get(
            str(value)
        )
    else:
        skyportal_class = None

    if not obj_id or not (save_group_ids or skyportal_class):
        return outcome

    if save_group_ids:
        try:
            await post_source_async(
                {"id": obj_id, "group_ids": list(save_group_ids)}, user_id, session
            )
            outcome["saved_to_groups"] = list(save_group_ids)
        except Exception as e:
            log(f"Could not save {obj_id} in SkyPortal: {e}")
            outcome["save_error"] = str(e)

    if skyportal_class:
        taxonomy_id = data.get("taxonomy_id") or conf.get("taxonomy_id")
        if taxonomy_id is None:
            outcome["classification_error"] = (
                "No taxonomy configured for Zooniverse classifications"
            )
            return outcome
        try:
            outcome["skyportal_classification_id"] = await post_classification(
                {
                    "obj_id": obj_id,
                    "classification": skyportal_class,
                    "taxonomy_id": taxonomy_id,
                    "probability": data.get("probability"),
                    "origin": "zooniverse",
                    "ml": False,
                    # Only groups the save actually reached: a bad group id
                    # must not take the classification down with it.
                    "group_ids": outcome.get("saved_to_groups", []),
                },
                user_id,
                session,
            )
        except Exception as e:
            log(f"Could not classify {obj_id} in SkyPortal: {e}")
            outcome["classification_error"] = str(e)

    return outcome


class ZooniverseAuthHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        summary: Start or inspect Zooniverse sign-in
        description: Report whether this user has linked a Zooniverse account,
          and return the URL that starts the authorization flow.
        tags:
          - zooniverse
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        conf = zooniverse_config()
        if not conf.get("client_id"):
            return self.error("Zooniverse is not configured on this instance")

        with self.Session() as session:
            record = session.scalar(
                sa.select(ZooniverseToken).where(
                    ZooniverseToken.user_id == self.associated_user_object.id
                )
            )
            # The state is checked on the way back, so a callback cannot be
            # replayed against a user who never started a sign-in.
            state = secrets.token_urlsafe(24)
            self.set_secure_cookie("zooniverse_state", state, expires_days=1)
            params = {
                "client_id": conf["client_id"],
                "redirect_uri": redirect_uri(self),
                "response_type": "code",
                "scope": conf.get("scope", "public classification"),
                "state": state,
            }
            endpoint = conf.get("endpoint", PANOPTES_ENDPOINT).rstrip("/")
            return self.success(
                data={
                    "linked": record is not None,
                    "login": record.zooniverse_login if record else None,
                    "authorize_url": (
                        f"{endpoint}/oauth/authorize?{urllib.parse.urlencode(params)}"
                    ),
                }
            )

    @auth_or_token
    def delete(self):
        """
        ---
        summary: Unlink a Zooniverse account
        description: Forget this user's Zooniverse credentials.
        tags:
          - zooniverse
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        with self.Session() as session:
            record = session.scalar(
                sa.select(ZooniverseToken).where(
                    ZooniverseToken.user_id == self.associated_user_object.id
                )
            )
            if record is not None:
                session.delete(record)
                session.commit()
            return self.success()


class ZooniverseAuthCallbackHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        summary: Complete Zooniverse sign-in
        description: Exchange the authorization code for a token and store it
          against the signed-in SkyPortal user.
        tags:
          - zooniverse
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        conf = zooniverse_config()
        code = self.get_query_argument("code", None)
        state = self.get_query_argument("state", None)
        if code is None:
            return self.error("No authorization code was returned")

        expected = self.get_secure_cookie("zooniverse_state")
        expected = expected.decode() if expected else None
        if not expected or state != expected:
            return self.error("Sign-in state did not match; start again")
        self.clear_cookie("zooniverse_state")

        endpoint = conf.get("endpoint", PANOPTES_ENDPOINT).rstrip("/")
        response = requests.post(
            f"{endpoint}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri(self),
                "client_id": conf.get("client_id"),
                "client_secret": conf.get("client_secret"),
            },
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            return self.error(f"Zooniverse rejected the sign-in: {response.text[:200]}")

        with self.Session() as session:
            record = store_token(
                session, self.associated_user_object.id, response.json(), endpoint
            )
            return self.success(data={"login": record.zooniverse_login})


class ZooniverseSubjectHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        summary: Get a Zooniverse subject to classify
        description: Fetch the next queued subject for the configured workflow,
          with the task definition it should be classified against.
        tags:
          - zooniverse
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
        conf = zooniverse_config()
        workflow_id = conf.get("workflow_id")
        if not (workflow_id and conf.get("client_id") and conf.get("client_secret")):
            return self.error("Zooniverse is not configured on this instance")

        try:
            queued = panoptes_request(
                "GET", f"/subjects/queued?workflow_id={workflow_id}"
            )
            workflow = panoptes_request("GET", f"/workflows/{workflow_id}")
        except requests.RequestException as e:
            log(f"Panoptes request failed: {e}")
            return self.error(f"Could not reach Zooniverse: {e}")

        subjects = queued.get("subjects") or []
        if not subjects:
            return self.success(data={"subject": None})

        subject = subjects[0]
        workflow_data = (workflow.get("workflows") or [{}])[0]
        tasks = workflow_data.get("tasks") or {}
        task_key = conf.get("task_key") or workflow_data.get("first_task")

        # What answering will write into SkyPortal, so the page can say so
        # before the volunteer commits to it.
        save_group_ids = conf.get("save_group_ids") or []
        groups = []
        if save_group_ids:
            with self.Session() as session:
                groups = [
                    {"id": group.id, "name": group.name}
                    for group in session.scalars(
                        Group.select(self.current_user).where(
                            Group.id.in_(save_group_ids)
                        )
                    ).all()
                ]

        return self.success(
            data={
                "subject": {
                    "id": subject["id"],
                    "metadata": subject.get("metadata") or {},
                    "locations": subject.get("locations") or [],
                },
                "workflow_id": str(workflow_id),
                "task_key": task_key,
                "task": tasks.get(task_key),
                "skyportal": {
                    "save_groups": groups,
                    "class_map": conf.get("class_map") or {},
                    "taxonomy_id": conf.get("taxonomy_id"),
                },
            }
        )


class ZooniverseClassificationHandler(BaseHandler):
    @auth_or_token
    async def post(self):
        """
        ---
        summary: Submit a Zooniverse classification
        description: Post the volunteer's answer to Panoptes as a classification
          against the configured workflow.
        tags:
          - zooniverse
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  subject_id:
                    type: string
                  task:
                    type: string
                  value:
                    description: The answer, as the task defines it
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
        conf = zooniverse_config()
        workflow_id = conf.get("workflow_id")
        project_id = conf.get("project_id")
        if not (workflow_id and project_id):
            return self.error("Zooniverse is not configured on this instance")

        data = self.get_json() or {}
        subject_id = data.get("subject_id")
        task = data.get("task")
        value = data.get("value")
        if subject_id is None:
            return self.error("subject_id is required")
        if task is None or value is None:
            return self.error("task and value are required")

        # Panoptes rejects a classification whose metadata has no
        # workflow_version, so look it up when the caller has not supplied one.
        workflow_version = data.get("workflow_version")
        if not workflow_version:
            try:
                workflow = panoptes_request("GET", f"/workflows/{workflow_id}")
                workflow_version = (workflow.get("workflows") or [{}])[0].get("version")
            except requests.RequestException as e:
                return self.error(f"Could not read the workflow: {e}")

        # Panoptes validates metadata against a fixed set: workflow_version,
        # started_at, finished_at, user_language, utc_offset, subject_dimensions
        # and user_agent are all required, and it 422s naming one at a time.
        now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        started_at = data.get("started_at") or now
        payload = {
            "classifications": {
                "annotations": [{"task": task, "value": value}],
                "metadata": {
                    # Kept verbatim by Panoptes: recording the front end makes
                    # IFE classifications separable in a data export.
                    "source": "skyportal",
                    "workflow_version": workflow_version,
                    "started_at": f"{started_at}Z",
                    "finished_at": f"{now}Z",
                    "user_language": data.get("user_language") or "en",
                    "utc_offset": "0",
                    "subject_dimensions": data.get("subject_dimensions") or [None],
                    "user_agent": "skyportal",
                },
                "links": {
                    "project": str(project_id),
                    "workflow": str(workflow_id),
                    "subjects": [str(subject_id)],
                },
            }
        }

        with self.Session() as session:
            token = volunteer_token(self, session)
        if token is None and not zooniverse_config().get("allow_unattributed", True):
            return self.error("Sign in to Zooniverse before classifying", status=403)

        try:
            result = panoptes_request("POST", "/classifications", payload, token=token)
        except requests.RequestException as e:
            log(f"Classification for subject {subject_id} failed: {e}")
            return self.error(f"Could not submit the classification: {e}")

        classification = (result.get("classifications") or [{}])[0]
        outcome = {"zooniverse_classification_id": classification.get("id")}

        async with self.AsyncSession() as session:
            outcome.update(
                await record_in_skyportal(
                    session, self.associated_user_object.id, conf, data, value
                )
            )

        return self.success(data=outcome)
