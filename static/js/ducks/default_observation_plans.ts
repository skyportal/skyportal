/**
 * Default observation plans.
 *
 * RTK Query conversion of the old `FETCH_DEFAULT_OBSERVATION_PLANS` duck.
 * Websocket-driven invalidation refetches the plan list; mutations submit/delete
 * a default observation plan.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const defaultObservationPlansApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultObservationPlans: build.query<any[], void>({
      query: () => "api/default_observation_plan",
      providesTags: ["DefaultObservationPlan"],
    }),
    submitDefaultObservationPlan: build.mutation<unknown, any>({
      query: (default_plan) => ({
        url: "api/default_observation_plan",
        method: "POST",
        body: default_plan,
      }),
      invalidatesTags: ["DefaultObservationPlan"],
    }),
    deleteDefaultObservationPlan: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/default_observation_plan/${id}`,
        method: "DELETE",
      }),
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
