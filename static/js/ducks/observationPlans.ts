/**
 * Observation plans tied to an allocation, plus a plan-name existence check.
 *
 * RTK Query conversion of the old `FETCH_ALLOCATION_OBSERVATION_PLANS` duck.
 * `getAllocationObservationPlans` returns the allocation's observation plan
 * requests (the old `observation_plan_requests`/`totalMatches` slice), and
 * `getPlanWithSameNameExists` checks whether a plan name is already taken.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

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
      queryFn: ({ id, params = {} }, api) =>
        clientQuery(api, (client) =>
          client.fetchAllocationObservationPlans(Number(id), params),
        ),
      providesTags: ["ObservationPlan"],
    }),
    getPlanWithSameNameExists: build.query<PlanNameExists, string>({
      queryFn: (name, api) =>
        clientQuery(api, async (client) => ({
          exists: await client.fetchObservationPlanNameExists(name),
        })),
      providesTags: ["ObservationPlan"],
    }),
  }),
});

export const {
  useGetAllocationObservationPlansQuery,
  useLazyGetPlanWithSameNameExistsQuery,
} = observationPlansApi;
