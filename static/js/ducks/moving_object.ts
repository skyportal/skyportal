/**
 * Moving object follow-up observation plan.
 *
 * RTK Query conversion of the old `POST_MOVING_OBJECT_OBSPLAN` duck. The single
 * POST mutation submits the observation-plan request for a named moving object
 * and returns the generated plan rows. There is no associated query/reducer or
 * websocket message, so nothing is provided/invalidated.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface MovingObjectObsPlanRow {
  id: number | string;
  start_time: string;
  field_id: number | string;
  band: string;
  airmass: number;
  moon_distance: number;
  sun_altitude: number;
  [key: string]: unknown;
}

interface PostMovingObjectObsPlanArg {
  name: string;
  data: Record<string, unknown>;
}

export const movingObjectApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    postMovingObjectObsPlan: build.mutation<
      MovingObjectObsPlanRow[],
      PostMovingObjectObsPlanArg
    >({
      query: ({ name, data }) => ({
        url: `api/moving_object/${name}/followup`,
        method: "POST",
        body: data,
      }),
    }),
  }),
});

export const { usePostMovingObjectObsPlanMutation } = movingObjectApi;
