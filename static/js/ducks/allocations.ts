/**
 * Allocations.
 *
 * RTK Query conversion of the old `FETCH_ALLOCATIONS` duck. Three GET variants
 * hit the same `/api/allocation` endpoint with different `apiType` filters:
 *   - getAllocations: the full list (optionally paginated/sorted/filtered).
 *   - getAllocationsApiObsplan: allocations with an observation-plan API class.
 *   - getAllocationsApiClassname: allocations with a follow-up API class.
 *
 * The old websocket `REFRESH_ALLOCATIONS` handler refetched all three lists;
 * here we invalidate the "Allocation" tag so any active variant refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type Allocation = Record<string, any>;

export type AllocationQueryParams = Record<string, unknown>;

const buildAllocationUrl = (params?: AllocationQueryParams): string => {
  if (!params || Object.keys(params).length === 0) {
    return "api/allocation";
  }
  const filtered: Record<string, string> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    if (Array.isArray(value) && value.length === 0) {
      return;
    }
    filtered[key] = String(value);
  });
  const queryString = new URLSearchParams(filtered).toString();
  return queryString ? `api/allocation?${queryString}` : "api/allocation";
};

export const allocationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAllocations: build.query<Allocation[], AllocationQueryParams | void>({
      query: (params) => buildAllocationUrl(params || undefined),
      providesTags: ["Allocation"],
    }),
    getAllocationsApiObsplan: build.query<
      Allocation[],
      AllocationQueryParams | void
    >({
      query: (params) =>
        buildAllocationUrl({
          apiType: "api_classname_obsplan",
          ...(params || {}),
        }),
      providesTags: ["Allocation"],
    }),
    getAllocationsApiClassname: build.query<
      Allocation[],
      AllocationQueryParams | void
    >({
      query: (params) =>
        buildAllocationUrl({
          apiType: "api_classname",
          ...(params || {}),
        }),
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
