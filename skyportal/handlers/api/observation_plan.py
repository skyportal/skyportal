import astropy
from astropy import units as u
import healpy as hp
import humanize
import jsonschema
import requests
from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload
import urllib
from astropy.time import Time
import numpy as np
import io
from tornado.ioloop import IOLoop
import functools
import ligo.skymap
from ligo.skymap.tool.ligo_skymap_plot_airmass import main as plot_airmass
from ligo.skymap import plot  # noqa: F401
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import pandas as pd
import simsurvey
from simsurvey.utils import model_tools
from simsurvey.models import AngularTimeSeriesSource
import tempfile
from ligo.skymap.distance import parameters_to_marginal_moments
from ligo.skymap.bayestar import rasterize
from ligo.skymap import plot  # noqa: F401 F811
import random
import sncosmo

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from ..base import BaseHandler
from ...models import (
    Allocation,
    DBSession,
    EventObservationPlan,
    GcnEvent,
    Group,
    InstrumentField,
    Localization,
    ObservationPlanRequest,
    PlannedObservation,
    Telescope,
    User,
)

from ...models.schema import ObservationPlanPost

from skyportal.handlers.api.source import post_source
from skyportal.handlers.api.followup_request import post_assignment
from skyportal.handlers.api.observingrun import post_observing_run

env, cfg = load_env()
TREASUREMAP_URL = cfg['app.treasuremap_endpoint']


def post_observation_plan(plan, user_id, session):
    """Post ObservationPlan to database.

    Parameters
    ----------
    plan: dict
        Observation plan dictionary
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.query(User).get(user_id)

    try:
        data = ObservationPlanPost.load(plan)
    except ValidationError as e:
        raise ValidationError(
            f'Invalid / missing parameters: {e.normalized_messages()}'
        )

    data["requester_id"] = user.id
    data["last_modified_by_id"] = user.id
    data['allocation_id'] = int(data['allocation_id'])
    data['localization_id'] = int(data['localization_id'])

    allocation = Allocation.get_if_accessible_by(
        data['allocation_id'],
        user,
        raise_if_none=False,
    )
    if allocation is None:
        raise AttributeError(f"Missing allocation with ID: {data['allocation_id']}")

    instrument = allocation.instrument
    if instrument.api_classname_obsplan is None:
        raise AttributeError('Instrument has no remote API.')

    if not instrument.api_class_obsplan.implements()['submit']:
        raise AttributeError(
            'Cannot submit observation plan requests for this Instrument.'
        )

    target_groups = []
    for group_id in data.pop('target_group_ids', []):
        g = Group.get_if_accessible_by(group_id, user, raise_if_none=False)
        if g is None:
            raise AttributeError(f"Missing group with ID: {group_id}")
        target_groups.append(g)

    try:
        formSchema = instrument.api_class_obsplan.custom_json_schema(instrument, user)
    except AttributeError:
        formSchema = instrument.api_class_obsplan.form_json_schema

    # validate the payload
    try:
        jsonschema.validate(data['payload'], formSchema)
    except jsonschema.exceptions.ValidationError as e:
        raise jsonschema.exceptions.ValidationError(f'Payload failed to validate: {e}')

    observation_plan_request = ObservationPlanRequest.__schema__().load(data)
    observation_plan_request.target_groups = target_groups
    session.add(observation_plan_request)
    session.commit()

    flow = Flow()

    flow.push(
        '*',
        "skyportal/REFRESH_GCNEVENT",
        payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
    )

    try:
        instrument.api_class_obsplan.submit(observation_plan_request)
    except Exception as e:
        observation_plan_request.status = 'failed to submit'
        raise AttributeError(f'Error submitting observation plan: {e.args[0]}')
    finally:
        session.commit()

    flow.push(
        '*',
        "skyportal/REFRESH_GCNEVENT",
        payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
    )

    return observation_plan_request.id


class ObservationPlanRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Submit observation plan request.
        tags:
          - observation_plan_requests
        requestBody:
          content:
            application/json:
              schema: ObservationPlanPost
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
                            id:
                              type: integer
                              description: New observation plan request ID
        """
        json_data = self.get_json()
        if 'observation_plans' in json_data:
            observation_plans = json_data['observation_plans']
        else:
            observation_plans = [json_data]

        ids = []
        with DBSession() as session:
            ids = []
            for plan in observation_plans:
                observation_plan_request_id = post_observation_plan(
                    plan, self.associated_user_object.id, session
                )
                ids = [observation_plan_request_id]

            return self.success(data={"ids": ids})

    @auth_or_token
    def get(self, observation_plan_request_id=None):
        """
        ---
        single:
          description: Get an observation plan.
          tags:
            - observation_plan_requests
          parameters:
            - in: path
              name: observation_plan_id
              required: true
              schema:
                type: string
            - in: query
              name: includePlannedObservations
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated planned observations. Defaults to false.
          responses:
            200:
              content:
                application/json:
                  schema: SingleObservationPlanRequest
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Get all observation plans.
          tags:
            - observation_plan_requests
          parameters:
            - in: query
              name: includePlannedObservations
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated planned observations. Defaults to false.
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfObservationPlanRequests
            400:
              content:
                application/json:
                  schema: Error
        """

        include_planned_observations = self.get_query_argument(
            "includePlannedObservations", False
        )
        if include_planned_observations:
            options = [
                joinedload(ObservationPlanRequest.observation_plans)
                .joinedload(EventObservationPlan.planned_observations)
                .joinedload(PlannedObservation.field)
            ]
        else:
            options = [joinedload(ObservationPlanRequest.observation_plans)]

        if observation_plan_request_id is not None:
            observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
                observation_plan_request_id,
                self.current_user,
                mode="read",
                raise_if_none=True,
                options=options,
            )
            return self.success(data=observation_plan_request)

        query = ObservationPlanRequest.query_records_accessible_by(
            self.current_user, mode="read", options=options
        )
        observation_plan_requests = query.all()
        self.verify_and_commit()
        return self.success(data=observation_plan_requests)

    @auth_or_token
    def delete(self, observation_plan_request_id):
        """
        ---
        description: Delete observation plan.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="delete",
            raise_if_none=True,
        )
        dateobs = observation_plan_request.gcnevent.dateobs

        api = observation_plan_request.instrument.api_class_obsplan
        if not api.implements()['delete']:
            return self.error('Cannot delete observation plans on this instrument.')

        observation_plan_request.last_modified_by_id = self.associated_user_object.id
        api.delete(observation_plan_request.id)

        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": dateobs},
        )

        return self.success()


class ObservationPlanSubmitHandler(BaseHandler):
    @auth_or_token
    def post(self, observation_plan_request_id):
        """
        ---
        description: Submit an observation plan.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: SingleObservationPlanRequest
        """

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )

        api = observation_plan_request.instrument.api_class_obsplan
        if not api.implements()['send']:
            return self.error('Cannot send observation plans on this instrument.')

        try:
            api.send(observation_plan_request)
        except Exception as e:
            observation_plan_request.status = 'failed to send'
            return self.error(
                f'Error sending observation plan to telescope: {e.args[0]}'
            )
        finally:
            self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        self.verify_and_commit()

        return self.success(data=observation_plan_request)

    @auth_or_token
    def delete(self, observation_plan_request_id):
        """
        ---
        description: Remove an observation plan from the queue.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
        )

        api = observation_plan_request.instrument.api_class_obsplan
        if not api.implements()['remove']:
            return self.error(
                'Cannot remove observation plans from the queue of this instrument.'
            )

        try:
            api.remove(observation_plan_request)
        except Exception as e:
            observation_plan_request.status = 'failed to remove from queue'
            return self.error(
                f'Error removing observation plan from telescope: {e.args[0]}'
            )
        finally:
            self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        self.verify_and_commit()

        return self.success(data=observation_plan_request)


class ObservationPlanGCNHandler(BaseHandler):
    @auth_or_token
    def get(self, observation_plan_request_id):
        """
        ---
        description: Get a GCN-izable summary of the observation plan.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: SingleObservationPlanRequest
        """

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        event = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(GcnEvent.gcn_notices),
                ],
            )
            .filter(GcnEvent.id == observation_plan_request.gcnevent_id)
            .first()
        )

        allocation = Allocation.get_if_accessible_by(
            observation_plan_request.allocation_id,
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument

        observation_plan = observation_plan_request.observation_plans[0]
        num_observations = observation_plan.num_observations
        if num_observations == 0:
            return self.error('Need at least one observation to produce a GCN')

        start_observation = astropy.time.Time(
            observation_plan.start_observation, format='datetime'
        )
        unique_filters = observation_plan.unique_filters
        total_time = observation_plan.total_time
        probability = observation_plan.probability
        area = observation_plan.area

        trigger_time = astropy.time.Time(event.dateobs, format='datetime')
        dt = observation_plan.start_observation - event.dateobs

        content = f"""
            SUBJECT: Follow-up of {event.gcn_notices[0].stream} trigger {trigger_time.isot} with {instrument.name}.
            We observed the localization region of {event.gcn_notices[0].stream} trigger {trigger_time.isot} UTC with {instrument.name} on the {instrument.telescope.name}. We obtained a total of {num_observations} images covering {",".join(unique_filters)} bands for a total of {total_time} seconds. The observations covered {area:.1f} square degrees beginning at {start_observation.isot} ({humanize.naturaldelta(dt)} after the burst trigger time) corresponding to ~{int(100 * probability)}% of the probability enclosed in the localization region.
            """

        return self.success(data=content)


def observation_animations(
    observations,
    localization,
    output_format='gif',
    figsize=(10, 8),
    decay=4,
    alpha_default=1,
    alpha_cutoff=0.1,
):

    """Create a movie to display observations of a given skymap
    Parameters
    ----------
    observations : skyportal.models.observation_plan.PlannedObservation
        The planned observations associated with the request
    localization : skyportal.models.localization.Localization
        The skymap that the request is made based on
    output_format : str, optional
        "gif" or "mp4" -- determines the format of the returned movie
    figsize : tuple, optional
        Matplotlib figsize of the movie created
    decay: float, optional
        The alpha of older fields follows an exponential decay to
        avoid cluttering the screen, this is how fast it falls off
        set decay = 0 to have no exponential decay
    alpha_default: float, optional
        The alpha to assign all fields observed if decay is 0,
        unused otherwise
    alpha_cutoff: float, optional
        The alpha below which you don't draw a field since it is
        too light. Used to not draw lots of invisible fields and
        waste processing time.
    Returns
    -------
    dict
        success : bool
            Whether the request was successful or not, returning
            a sensible error in 'reason'
        name : str
            suggested filename based on `source_name` and `output_format`
        data : str
            binary encoded data for the movie (to be streamed)
        reason : str
            If not successful, a reason is returned.
    """

    surveyColors = {
        "ztfg": "#28A745",
        "ztfr": "#DC3545",
        "ztfi": "#F3DC11",
        "AllWISE": "#2F5492",
        "Gaia_DR3": "#FF7F0E",
        "PS1_DR1": "#3BBED5",
        "GALEX": "#6607C2",
        "TNS": "#ED6CF6",
    }

    filters = list({obs.filt for obs in observations})
    for filt in filters:
        if filt in surveyColors:
            continue
        surveyColors[filt] = "#" + ''.join(
            [random.choice('0123456789ABCDEF') for i in range(6)]
        )

    matplotlib.use("Agg")
    fig = plt.figure(figsize=figsize, constrained_layout=False)
    ax = plt.axes(projection='astro mollweide')
    ax.imshow_hpx(localization.flat_2d, cmap='cylon')

    old_artists = []

    def plot_schedule(k):
        for artist in old_artists:
            artist.remove()
        del old_artists[:]

        for i, obs in enumerate(observations):

            if decay != 0:
                alpha = np.exp((i - k) / decay)
            else:
                alpha = alpha_default
            if alpha > 1:
                alpha = 1

            if alpha > alpha_cutoff:
                coords = obs.field.contour_summary["features"][0]["geometry"][
                    "coordinates"
                ]
                ras = np.array(coords)[:, 0]
                # cannot handle 0-crossing well
                if len(np.where(ras > 180)[0]) > 0 and len(np.where(ras < 180)) > 0:
                    continue
                poly = plt.Polygon(
                    coords,
                    alpha=alpha,
                    facecolor=surveyColors[obs.filt],
                    edgecolor='black',
                    transform=ax.get_transform('world'),
                )
                ax.add_patch(poly)
                old_artists.append(poly)

        patches = []
        for filt in filters:
            patches.append(mpatches.Patch(color=surveyColors[filt], label=filt))
        plt.legend(handles=patches)

    if output_format == "gif":
        writer = animation.PillowWriter()
    elif output_format == "mp4":
        writer = animation.FFMpegWriter()
    else:
        raise ValueError('output_format must be gif or mp4')

    with tempfile.NamedTemporaryFile(mode='w', suffix='.' + output_format) as f:
        anim = animation.FuncAnimation(fig, plot_schedule, frames=len(observations))
        anim.save(f.name, writer=writer)
        f.flush()

        with open(f.name, mode='rb') as g:
            anim_content = g.read()

    return {
        "success": True,
        "name": f"{localization.localization_name}.{output_format}",
        "data": anim_content,
        "reason": "",
    }


class ObservationPlanMovieHandler(BaseHandler):
    @auth_or_token
    async def get(self, observation_plan_request_id):
        """
        ---
        description: Get a movie summary of the observation plan.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: SingleObservationPlanRequest
        """

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
            .undefer(InstrumentField.contour_summary)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        localization = (
            Localization.query_records_accessible_by(
                self.current_user,
            )
            .filter(Localization.id == observation_plan_request.localization_id)
            .first()
        )

        observations = observation_plan_request.observation_plans[
            0
        ].planned_observations

        output_format = 'gif'
        anim = functools.partial(
            observation_animations,
            observations,
            localization,
            output_format=output_format,
            figsize=(10, 8),
            decay=4,
            alpha_default=1,
            alpha_cutoff=0.1,
        )

        self.push_notification(
            'Movie generation in progress. Download will start soon.'
        )
        rez = await IOLoop.current().run_in_executor(None, anim)

        filename = rez["name"]
        data = io.BytesIO(rez["data"])

        await self.send_file(data, filename, output_type=output_format)


class ObservationPlanTreasureMapHandler(BaseHandler):
    @auth_or_token
    def post(self, observation_plan_request_id):
        """
        ---
        description: Submit the observation plan to treasuremap.space
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
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

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        event = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(GcnEvent.gcn_notices),
                ],
            )
            .filter(GcnEvent.id == observation_plan_request.gcnevent_id)
            .first()
        )

        allocation = Allocation.get_if_accessible_by(
            observation_plan_request.allocation_id,
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument

        altdata = allocation.altdata
        if not altdata:
            raise self.error('Missing allocation information.')

        observation_plan = observation_plan_request.observation_plans[0]
        planned_observations = observation_plan.planned_observations

        if len(planned_observations) == 0:
            return self.error('Cannot submit observing plan with no observations.')

        graceid = event.graceid
        payload = {"graceid": graceid, "api_token": altdata['TREASUREMAP_API_TOKEN']}

        pointings = []
        for obs in planned_observations:
            pointing = {}
            pointing["ra"] = obs.field.ra
            pointing["dec"] = obs.field.dec
            pointing["band"] = obs.filt
            pointing["instrumentid"] = str(instrument.treasuremap_id)
            pointing["status"] = "planned"
            pointing["time"] = Time(obs.obstime, format='datetime').isot
            pointing["depth"] = 0.0
            pointing["depth_unit"] = "ab_mag"
            pointings.append(pointing)
        payload["pointings"] = pointings

        url = urllib.parse.urljoin(TREASUREMAP_URL, 'api/v0/pointings')
        r = requests.post(url=url, json=payload)
        r.raise_for_status()
        request_json = r.json()
        errors = request_json["ERRORS"]
        if len(errors) > 0:
            return self.error(f'TreasureMap upload failed: {errors}')
        self.push_notification('TreasureMap upload succeeded')
        return self.success()

    @auth_or_token
    def delete(self, observation_plan_request_id):
        """
        ---
        description: Remove observation plan from treasuremap.space.
        tags:
          - observationplan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        event = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(GcnEvent.gcn_notices),
                ],
            )
            .filter(GcnEvent.id == observation_plan_request.gcnevent_id)
            .first()
        )

        allocation = Allocation.get_if_accessible_by(
            observation_plan_request.allocation_id,
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument

        altdata = allocation.altdata
        if not altdata:
            raise self.error('Missing allocation information.')

        graceid = event.graceid
        payload = {
            "graceid": graceid,
            "api_token": altdata['TREASUREMAP_API_TOKEN'],
            "instrumentid": instrument.treasuremap_id,
        }

        baseurl = urllib.parse.urljoin(TREASUREMAP_URL, 'api/v0/cancel_all')
        url = f"{baseurl}?{urllib.parse.urlencode(payload)}"
        r = requests.post(url=url)
        r.raise_for_status()
        request_text = r.text
        if "successfully" not in request_text:
            return self.error(f'TreasureMap delete failed: {request_text}')
        self.push_notification(f'TreasureMap delete succeeded: {request_text}.')
        return self.success()


class ObservationPlanGeoJSONHandler(BaseHandler):
    @auth_or_token
    def get(self, observation_plan_request_id):
        """
        ---
        description: Get GeoJSON summary of the observation plan.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: SingleObservationPlanRequest
        """

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
            .undefer(InstrumentField.contour_summary)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            options=options,
        )
        if observation_plan_request is None:
            return self.error(
                f'No observation plan with ID: {observation_plan_request_id}'
            )
        self.verify_and_commit()

        if len(observation_plan_request.observation_plans) > 0:
            observation_plan = observation_plan_request.observation_plans[0]
            # features are JSON representations that the d3 stuff understands.
            # We use these to render the contours of the sky localization and
            # locations of the transients.

            geojson = []
            fields_in = []
            for observation in observation_plan.planned_observations:
                if observation.field_id not in fields_in:
                    fields_in.append(observation.field_id)
                    geojson.append(observation.field.contour_summary)
                else:
                    continue

            return self.success(data={'geojson': geojson})
        else:
            return self.error('Observation plan not yet available.')


class ObservationPlanFieldsHandler(BaseHandler):
    @auth_or_token
    def delete(self, observation_plan_request_id):
        """
        ---
        description: Delete selected fields from the observation plan.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                properties:
                  fieldIds:
                    type: array
                    items:
                      type: integer
                    description: List of field IDs to remove from the plan
        responses:
          200:
            content:
              application/json:
                schema: SingleObservationPlanRequest
        """

        data = self.get_json()
        field_ids_to_remove = data.pop('fieldIds', None)

        if field_ids_to_remove is None:
            return self.error('Need to specify field IDs to remove')

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
            .undefer(InstrumentField.contour_summary)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            options=options,
        )
        if observation_plan_request is None:
            return self.error(
                f'No observation plan with ID: {observation_plan_request_id}'
            )
        self.verify_and_commit()

        if len(observation_plan_request.observation_plans) > 0:
            observation_plan = observation_plan_request.observation_plans[0]
            dateobs = observation_plan_request.gcnevent.dateobs

            with DBSession() as session:
                for observation in observation_plan.planned_observations:
                    if observation.field_id in field_ids_to_remove:
                        session.delete(observation)
                    else:
                        continue
                self.verify_and_commit()

            self.push_all(
                action="skyportal/REFRESH_GCNEVENT",
                payload={"gcnEvent_dateobs": dateobs},
            )

            return self.success()
        else:
            return self.error('Observation plan not yet available.')


class ObservationPlanAirmassChartHandler(BaseHandler):
    @auth_or_token
    async def get(self, localization_id, telescope_id):
        """
        ---
        description: Get an airmass chart for the GcnEvent
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: localization_id
            required: true
            schema:
              type: string
          - in: path
            name: telescope_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        telescope = Telescope.get_if_accessible_by(
            telescope_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
        )
        self.verify_and_commit()

        localization = (
            Localization.query_records_accessible_by(
                self.current_user,
            )
            .filter(Localization.id == localization_id)
            .first()
        )

        trigger_time = astropy.time.Time(localization.dateobs, format='datetime')

        output_format = 'pdf'
        with tempfile.NamedTemporaryFile(
            suffix='.fits'
        ) as fitsfile, tempfile.NamedTemporaryFile(
            suffix=f'.{output_format}'
        ) as imgfile, matplotlib.style.context(
            'default'
        ):
            ligo.skymap.io.write_sky_map(fitsfile.name, localization.table_2d, moc=True)
            plot_airmass(
                [
                    '--site-longitude',
                    str(telescope.lon),
                    '--site-latitude',
                    str(telescope.lat),
                    '--site-height',
                    str(telescope.elevation),
                    '--time',
                    trigger_time.isot,
                    fitsfile.name,
                    '-o',
                    imgfile.name,
                ]
            )

            with open(imgfile.name, mode='rb') as g:
                content = g.read()

        data = io.BytesIO(content)
        filename = (
            f"{localization.localization_name}-{telescope.nickname}.{output_format}"
        )

        await self.send_file(data, filename, output_type=output_format)


class ObservationPlanCreateObservingRunHandler(BaseHandler):
    @auth_or_token
    def post(self, observation_plan_request_id):
        """
        ---
        description: Submit the fields in the observation plan
           to an observing run
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
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

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        allocation = Allocation.get_if_accessible_by(
            observation_plan_request.allocation_id,
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument

        observation_plan = observation_plan_request.observation_plans[0]
        planned_observations = observation_plan.planned_observations

        if len(planned_observations) == 0:
            return self.error('Cannot create observing run with no observations.')

        with DBSession() as session:

            observing_run = {
                'instrument_id': instrument.id,
                'group_id': allocation.group_id,
                'calendar_date': str(observation_plan.validity_window_end.date()),
            }
            run_id = post_observing_run(
                observing_run, self.associated_user_object.id, session
            )

            min_priority = 1
            max_priority = 5
            priorities = []
            for obs in planned_observations:
                priorities.append(obs.weight)

            for obs in planned_observations:
                source = {
                    'id': f'{obs.field.ra}-{obs.field.dec}',
                    'ra': obs.field.ra,
                    'dec': obs.field.dec,
                }
                obj_id = post_source(source, self.associated_user_object.id, session)
                if np.max(priorities) - np.min(priorities) == 0.0:
                    # assign equal weights if all the same
                    normalized_priority = 0.5
                else:
                    normalized_priority = (obs.weight - np.min(priorities)) / (
                        np.max(priorities) - np.min(priorities)
                    )

                priority = np.ceil(
                    (max_priority - min_priority) * normalized_priority + min_priority
                )
                assignment = {
                    'run_id': run_id,
                    'obj_id': obj_id,
                    'priority': str(int(priority)),
                }
                try:
                    post_assignment(assignment, self.associated_user_object.id, session)
                except ValueError:
                    # No need to assign multiple times to same run
                    pass

            self.push_notification('Observing run post succeeded')
            return self.success()


def observation_simsurvey(
    observations,
    localization,
    instrument,
    output_format='pdf',
    figsize=(10, 8),
    number_of_injections=1000,
    number_of_detections=2,
    detection_threshold=5,
    minimum_phase=0,
    maximum_phase=3,
    injection_filename='data/nsns_nph1.0e+06_mejdyn0.020_mejwind0.130_phi30.txt',
):

    """Create a plot to display the simsurvey analyis for a given skymap
        Parameters
        ----------
        observations : skyportal.models.observation_plan.PlannedObservation
            The planned observations associated with the request
        localization : skyportal.models.localization.Localization
            The skymap that the request is made based on
        instrument : skyportal.models.instrument.Instrument
            The instrument that the request is made based on
        event : skyportal.models.gcn.GcnEvent
            The instrument that the request is made based on
        output_format : str, optional
            "gif" or "mp4" -- determines the format of the returned movie
        figsize : tuple, optional
            Matplotlib figsize of the movie created
        number_of_injections: int
            Number of simulations to evaluate efficiency with. Defaults to 1000.
        number_of_detections: int
            Number of detections required for detection. Defaults to 1.
        detection_threshold: int
            Threshold (in sigmas) required for detection. Defaults to 5.
        minimum_phase: int
            Minimum phase (in days) post event time to consider detections. Defaults to 0.
        maximum_phase: int
            Maximum phase (in days) post event time to consider detections. Defaults to 3.
        injection_filename: str
            Path to file for injestion as a simsurvey.models.AngularTimeSeriesSource
    . Defaults to nsns_nph1.0e+06_mejdyn0.020_mejwind0.130_phi30.txt from https://github.com/mbulla/kilonova_models.
        Returns
        -------
        dict
            success : bool
                Whether the request was successful or not, returning
                a sensible error in 'reason'
            name : str
                suggested filename based on `source_name` and `output_format`
            data : str
                binary encoded data for the plot (to be streamed)
            reason : str
                If not successful, a reason is returned.
    """

    trigger_time = astropy.time.Time(localization.dateobs, format='datetime')

    keys = ['ra', 'dec', 'field_id', 'limMag', 'jd', 'filter', 'skynoise']
    pointings = {k: [] for k in keys}
    for obs in observations:
        nmag = -2.5 * np.log10(
            np.sqrt(
                instrument.sensitivity_data[obs["filt"]]['exposure_time']
                / obs["exposure_time"]
            )
        )

        if "limmag" in obs:
            limMag = obs["limmag"]
        else:
            limMag = (
                instrument.sensitivity_data[obs["filt"]]['limiting_magnitude'] + nmag
            )
        zp = instrument.sensitivity_data[obs["filt"]]['zeropoint'] + nmag

        pointings["ra"].append(obs["field"].ra)
        pointings["dec"].append(obs["field"].dec)
        pointings["filter"].append(obs["filt"])
        pointings["jd"].append(Time(obs["obstime"], format='datetime').jd)
        pointings["field_id"].append(obs["field"].field_id)

        pointings["limMag"].append(limMag)
        pointings["skynoise"].append(10 ** (-0.4 * (limMag - zp)) / 5.0)
        pointings["zp"] = zp

    df = pd.DataFrame.from_dict(pointings)
    plan = simsurvey.SurveyPlan(
        time=df['jd'],
        band=df['filter'],
        obs_field=df['field_id'].astype(int),
        skynoise=df['skynoise'],
        zp=df['zp'],
        fields={k: v for k, v in pointings.items() if k in ['ra', 'dec', 'field_id']},
    )

    order = hp.nside2order(localization.nside)
    t = rasterize(localization.table, order)
    result = t['PROB'], t['DISTMU'], t['DISTSIGMA'], t['DISTNORM']
    hp_data = hp.reorder(result, 'NESTED', 'RING')
    map_struct = {}
    map_struct['prob'] = hp_data[0]
    map_struct['distmu'] = hp_data[1]
    map_struct['distsigma'] = hp_data[2]

    distmean, diststd = parameters_to_marginal_moments(
        map_struct['prob'], map_struct['distmu'], map_struct['distsigma']
    )

    distance_lower = astropy.coordinates.Distance(
        np.max([1, (distmean - 5 * diststd)]) * u.Mpc
    )
    distance_upper = astropy.coordinates.Distance((distmean + 5 * diststd) * u.Mpc)
    phase, wave, cos_theta, flux = model_tools.read_possis_file(injection_filename)
    transientprop = {
        'lcmodel': sncosmo.Model(
            AngularTimeSeriesSource(
                phase=phase, wave=wave, flux=flux, cos_theta=cos_theta
            )
        )
    }
    tr = simsurvey.get_transient_generator(
        [distance_lower.z, distance_upper.z],
        transient="generic",
        template="AngularTimeSeriesSource",
        ntransient=number_of_injections,
        ratefunc=lambda z: 5e-7,
        dec_range=(-90, 90),
        ra_range=(0, 360),
        mjd_range=(trigger_time.jd, trigger_time.jd),
        transientprop=transientprop,
        skymap=map_struct,
    )

    survey = simsurvey.SimulSurvey(
        generator=tr,
        plan=plan,
        phase_range=(minimum_phase, maximum_phase),
        n_det=number_of_detections,
        threshold=detection_threshold,
    )

    lcs = survey.get_lightcurves(notebook=True)

    matplotlib.use("Agg")
    fig = plt.figure(figsize=figsize, constrained_layout=False)
    ax = plt.axes([0.05, 0.05, 0.9, 0.9], projection='geo degrees mollweide')
    ax.grid()
    if lcs.meta_notobserved is not None:
        ax.scatter(
            lcs.meta_notobserved['ra'],
            lcs.meta_notobserved['dec'],
            transform=ax.get_transform('world'),
            marker='*',
            color='grey',
            label='not_observed',
            alpha=0.7,
        )
    if lcs.meta is not None:
        ax.scatter(
            lcs.meta['ra'],
            lcs.meta['dec'],
            transform=ax.get_transform('world'),
            marker='*',
            color='red',
            label='detected',
            alpha=0.7,
        )
    ax.legend(loc=0)
    ax.set_ylabel('Declination [deg]')
    ax.set_xlabel('RA [deg]')

    all_transients = []
    if lcs.meta_notobserved is not None:
        all_transients.append(len(lcs.meta_notobserved))
    if lcs.meta_full is not None:
        all_transients.append(len(lcs.meta_full))
    ntransient = np.sum(all_transients)

    if lcs.meta_full is not None:
        n_in_covered = len(lcs.meta_full['z'])
    else:
        n_in_covered = 0

    if lcs.lcs is not None:
        n_detected = len(lcs.lcs)
    else:
        n_detected = 0

    title_string = f"""
        Number of created kNe: {ntransient}
        Number of created kNe falling in the covered area: {n_in_covered}
        Number of detected over all created: {n_detected/ntransient}"""
    ax.set_title(title_string)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format=output_format)
    plt.close(fig)
    buf.seek(0)

    return {
        "success": True,
        "name": f"simsurvey_{instrument.name}.{output_format}",
        "data": buf.read(),
        "reason": "",
    }


class ObservationPlanSimSurveyHandler(BaseHandler):
    @auth_or_token
    async def get(self, observation_plan_request_id):
        """
        ---
        description: Perform an efficiency analysis of the observation plan.
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
          - in: query
            name: numberInjections
            nullable: true
            schema:
              type: number
            description: |
              Number of simulations to evaluate efficiency with. Defaults to 1000.
          - in: query
            name: numberDetections
            nullable: true
            schema:
              type: number
            description: |
              Number of detections required for detection. Defaults to 1.
          - in: query
            name: detectionThreshold
            nullable: true
            schema:
              type: number
            description: |
              Threshold (in sigmas) required for detection. Defaults to 5.
          - in: query
            name: minimumPhase
            nullable: true
            schema:
              type: number
            description: |
              Minimum phase (in days) post event time to consider detections. Defaults to 0.
          - in: query
            name: maximumPhase
            nullable: true
            schema:
              type: number
            description: |
              Maximum phase (in days) post event time to consider detections. Defaults to 3.
          - in: query
            name: injectionFilename
            nullable: true
            schema:
              type: string
            description: |
              Path to file for injestion as a simsurvey.models.AngularTimeSeriesSource.
              Defaults to nsns_nph1.0e+06_mejdyn0.020_mejwind0.130_phi30.txt
              from https://github.com/mbulla/kilonova_models.
        responses:
          200:
            content:
              application/json:
                schema: SingleObservationPlanRequest
        """

        number_of_injections = self.get_query_argument("numberInjections", 1000)
        number_of_detections = self.get_query_argument("numberDetections", 1)
        detection_threshold = self.get_query_argument("detectionThreshold", 5)
        minimum_phase = self.get_query_argument("minimumPhase", 0)
        maximum_phase = self.get_query_argument("maximumPhase", 3)
        injection_filename = self.get_query_argument(
            "injectionFilename",
            'data/nsns_nph1.0e+06_mejdyn0.020_mejwind0.130_phi30.txt',
        )

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        allocation = Allocation.get_if_accessible_by(
            observation_plan_request.allocation_id,
            self.current_user,
            raise_if_none=True,
        )

        localization = (
            Localization.query_records_accessible_by(
                self.current_user,
            )
            .filter(Localization.id == observation_plan_request.localization_id)
            .first()
        )

        instrument = allocation.instrument

        if instrument.sensitivity_data is None:
            return self.error('Need sensitivity_data to evaluate efficiency')

        observation_plan = observation_plan_request.observation_plans[0]
        planned_observations = observation_plan.planned_observations
        num_observations = observation_plan.num_observations
        if num_observations == 0:
            self.push_notification(
                'Need at least one observation to evaluate efficiency',
                notification_type='error',
            )
            return self.error('Need at least one observation to evaluate efficiency')

        unique_filters = observation_plan.unique_filters

        if not set(unique_filters).issubset(set(instrument.sensitivity_data.keys())):
            return self.error('Need sensitivity_data for all filters present')

        for filt in unique_filters:
            if not {'exposure_time', 'limiting_magnitude', 'zeropoint'}.issubset(
                set(list(instrument.sensitivity_data[filt].keys()))
            ):
                return self.error(
                    f'Sensitivity_data dictionary missing keys for filter {filt}'
                )

        observations = [observation.to_dict() for observation in planned_observations]

        output_format = 'pdf'
        simsurvey_analysis = functools.partial(
            observation_simsurvey,
            observations,
            localization,
            instrument,
            output_format=output_format,
            number_of_injections=number_of_injections,
            number_of_detections=number_of_detections,
            detection_threshold=detection_threshold,
            minimum_phase=minimum_phase,
            maximum_phase=maximum_phase,
            injection_filename=injection_filename,
        )

        self.push_notification(
            'Simsurvey analysis in progress. Download will start soon.'
        )
        rez = await IOLoop.current().run_in_executor(None, simsurvey_analysis)

        filename = rez["name"]
        data = io.BytesIO(rez["data"])

        await self.send_file(data, filename, output_type=output_format)
