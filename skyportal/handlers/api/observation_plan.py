import astropy
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
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import tempfile
from ligo.skymap import plot  # noqa: F401
import random

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    Allocation,
    DBSession,
    EventObservationPlan,
    GcnEvent,
    Group,
    Localization,
    ObservationPlanRequest,
    PlannedObservation,
    InstrumentField,
)

from ...models.schema import ObservationPlanPost

env, cfg = load_env()
TREASUREMAP_URL = cfg['app.treasuremap_endpoint']


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
        data = self.get_json()

        try:
            data = ObservationPlanPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(data['allocation_id'])
        data['localization_id'] = int(data['localization_id'])

        allocation = Allocation.get_if_accessible_by(
            data['allocation_id'],
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument
        if instrument.api_classname_obsplan is None:
            return self.error('Instrument has no remote API.')

        if not instrument.api_class_obsplan.implements()['submit']:
            return self.error(
                'Cannot submit observation plan requests for this Instrument.'
            )

        target_groups = []
        for group_id in data.pop('target_group_ids', []):
            g = Group.get_if_accessible_by(
                group_id, self.current_user, raise_if_none=True
            )
            target_groups.append(g)

        # validate the payload
        jsonschema.validate(
            data['payload'], instrument.api_class_obsplan.form_json_schema
        )

        observation_plan_request = ObservationPlanRequest.__schema__().load(data)
        observation_plan_request.target_groups = target_groups
        DBSession().add(observation_plan_request)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        try:
            instrument.api_class_obsplan.submit(observation_plan_request)
        except Exception as e:
            observation_plan_request.status = 'failed to submit'
            return self.error(f'Error submitting observation plan: {e.args[0]}')
        finally:
            self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        return self.success(data={"id": observation_plan_request.id})

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
                joinedload(ObservationPlanRequest.observation_plans).joinedload(
                    EventObservationPlan.planned_observations
                )
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
    localization : skyportal.models.localizstion.Localization
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
        "Gaia_EDR3": "#FF7F0E",
        "PS1_DR1": "#3BBED5",
        "GALEX": "#6607C2",
        "TNS": "#ED6CF6",
    }

    filters = list(set(obs.filt for obs in observations))
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

        return self.success()