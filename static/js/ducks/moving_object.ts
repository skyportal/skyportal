/**
 * Moving object follow-up observation plan.
 *
 * RTK Query conversion of the old `POST_MOVING_OBJECT_OBSPLAN` duck. The single
 * POST mutation submits the observation-plan request for a named moving object
 * and returns the generated plan rows. There is no associated query/reducer or
 * websocket message, so nothing is provided/invalidated.
 */
import type {
  MovingObjectFollowupPost,
  MovingObjectObservation,
} from "skyportal-js/MovingObjects";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export type { MovingObjectObservation as MovingObjectObsPlanRow } from "skyportal-js/MovingObjects";

interface PostMovingObjectObsPlanArg {
  name: string;
  data: MovingObjectFollowupPost;
}

export const movingObjectApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    postMovingObjectObsPlan: build.mutation<
      MovingObjectObservation[],
      PostMovingObjectObsPlanArg
    >({
      queryFn: ({ name, data }, api) =>
        clientQuery(api, (client) =>
          client.postMovingObjectFollowup(name, data),
        ),
    }),
  }),
});

export const { usePostMovingObjectObsPlanMutation } = movingObjectApi;
