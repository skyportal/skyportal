/**
 * Default observation plans.
 *
 * RTK Query conversion of the old `FETCH_DEFAULT_OBSERVATION_PLANS` duck.
 * Websocket-driven invalidation refetches the plan list; mutations submit/delete
 * a default observation plan.
 */
import type {
  DefaultObservationPlanPost,
  DefaultObservationPlanRequest,
} from "skyportal-js/ObservationPlans";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const defaultObservationPlansApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultObservationPlans: build.query<
      DefaultObservationPlanRequest[],
      void
    >({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchDefaultObservationPlans()),
      providesTags: ["DefaultObservationPlan"],
    }),
    submitDefaultObservationPlan: build.mutation<
      { id: number },
      DefaultObservationPlanPost
    >({
      queryFn: (default_plan, api) =>
        clientQuery(api, (client) =>
          client.postDefaultObservationPlan(default_plan),
        ),
      invalidatesTags: ["DefaultObservationPlan"],
    }),
    deleteDefaultObservationPlan: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.deleteDefaultObservationPlan(Number(id)),
        ),
      invalidatesTags: ["DefaultObservationPlan"],
    }),
  }),
});

// Websocket: the old handler refetched the full list on
// REFRESH_DEFAULT_OBSERVATION_PLANS.
invalidateOnMessage("skyportal/REFRESH_DEFAULT_OBSERVATION_PLANS", () => [
  "DefaultObservationPlan",
]);

export const {
  useGetDefaultObservationPlansQuery,
  useSubmitDefaultObservationPlanMutation,
  useDeleteDefaultObservationPlanMutation,
} = defaultObservationPlansApi;
