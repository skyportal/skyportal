/**
 * Allocations.
 *
 * RTK Query conversion of the old `FETCH_ALLOCATIONS` duck, calling the typed
 * `skyportal-js` client. Three GET variants hit the same `/api/allocation`
 * endpoint with different `apiType` filters:
 *   - getAllocations: the full list (optionally filtered by instrument).
 *   - getAllocationsApiObsplan: allocations with an observation-plan API class.
 *   - getAllocationsApiClassname: allocations with a follow-up API class.
 *
 * The old websocket `REFRESH_ALLOCATIONS` handler refetched all three lists;
 * here we invalidate the "Allocation" tag so any active variant refetches.
 */
import type {
  Allocation,
  FetchAllocationsOptions,
} from "skyportal-js/Allocations";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type AllocationQueryParams = FetchAllocationsOptions;

export const allocationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAllocations: build.query<Allocation[], AllocationQueryParams | void>({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.fetchAllocations(params ?? {})),
      providesTags: ["Allocation"],
    }),
    getAllocationsApiObsplan: build.query<
      Allocation[],
      AllocationQueryParams | void
    >({
      queryFn: (params, api) =>
        clientQuery(api, (client) =>
          client.fetchAllocations({
            apiType: "api_classname_obsplan",
            ...(params ?? {}),
          }),
        ),
      providesTags: ["Allocation"],
    }),
    getAllocationsApiClassname: build.query<
      Allocation[],
      AllocationQueryParams | void
    >({
      queryFn: (params, api) =>
        clientQuery(api, (client) =>
          client.fetchAllocations({
            apiType: "api_classname",
            ...(params ?? {}),
          }),
        ),
      providesTags: ["Allocation"],
    }),
  }),
});

// Websocket: old handler refetched all allocation lists on REFRESH_ALLOCATIONS.
invalidateOnMessage("skyportal/REFRESH_ALLOCATIONS", () => ["Allocation"]);

export const {
  useGetAllocationsQuery,
  useGetAllocationsApiObsplanQuery,
  useGetAllocationsApiClassnameQuery,
} = allocationsApi;
