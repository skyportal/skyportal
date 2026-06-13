/**
 * Observation plans tied to an allocation, plus a plan-name existence check.
 *
 * RTK Query conversion of the old `FETCH_ALLOCATION_OBSERVATION_PLANS` duck.
 * `getAllocationObservationPlans` returns the allocation's observation plan
 * requests (the old `observation_plan_requests`/`totalMatches` slice), and
 * `getPlanWithSameNameExists` checks whether a plan name is already taken.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface AllocationObservationPlans {
  observation_plan_requests: any[];
  totalMatches?: number | undefined;
  [key: string]: unknown;
}

export interface PlanNameExists {
  exists: boolean;
  [key: string]: unknown;
}

export interface GetAllocationObservationPlansArg {
  id: number | string;
  params?: Record<string, any> | undefined;
}

export const observationPlansApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAllocationObservationPlans: build.query<
      AllocationObservationPlans,
      GetAllocationObservationPlansArg
    >({
      query: ({ id, params = {} }) => ({
        url: `api/allocation/observation_plans/${id}`,
        params,
      }),
      providesTags: ["ObservationPlan"],
    }),
    getPlanWithSameNameExists: build.query<PlanNameExists, string>({
      query: (name) => `api/observation_plan/plan_names?name=${name}`,
      providesTags: ["ObservationPlan"],
    }),
  }),
});

export const {
  useGetAllocationObservationPlansQuery,
  useLazyGetPlanWithSameNameExistsQuery,
} = observationPlansApi;
