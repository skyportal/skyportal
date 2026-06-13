/**
 * A single allocation (with its follow-up requests).
 *
 * RTK Query conversion of the old `FETCH_ALLOCATION` duck. The endpoint is
 * injected into the central `skyportalApi`. `getAllocation` is keyed by the
 * allocation id plus the pagination/sort params; the backend returns
 * `{ allocation, totalMatches }`, which is preserved as the query result shape.
 *
 * Mutations (`submitAllocation`, `modifyAllocation`, `deleteAllocation`,
 * `editFollowupRequestComment`) invalidate the `Allocation` tag so any active
 * `getAllocation` query refetches.
 *
 * The websocket `REFRESH_ALLOCATION` / `REFRESH_ALLOCATION_REQUEST_COMMENT`
 * messages are bridged to cache invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

interface GetAllocationArg {
  id: number | string;
  params?: Record<string, any> | undefined;
}

export const allocationApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAllocation: build.query<
      RouteData<"GET /api/allocation/{allocation_id}">,
      GetAllocationArg
    >({
      query: ({ id, params }) => ({
        url: `api/allocation/${id}`,
        params: params ?? {},
      }),
      providesTags: ["Allocation"],
    }),
    submitAllocation: build.mutation<unknown, Record<string, any>>({
      query: (payload) => ({
        url: "api/allocation",
        method: "POST",
        body: payload,
      }),
      invalidatesTags: ["Allocation"],
    }),
    modifyAllocation: build.mutation<
      unknown,
      { id: number | string; payload: Record<string, any> }
    >({
      query: ({ id, payload }) => ({
        url: `api/allocation/${id}`,
        method: "PUT",
        body: payload,
      }),
      invalidatesTags: ["Allocation"],
    }),
    deleteAllocation: build.mutation<unknown, number | string>({
      query: (allocationID) => ({
        url: `api/allocation/${allocationID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Allocation"],
    }),
    editFollowupRequestComment: build.mutation<
      RouteData<"PUT /api/followup_request/{followup_request_id}/comment">,
      { id: number | string; params: Record<string, any> }
    >({
      query: ({ id, params }) => ({
        url: `api/followup_request/${id}/comment`,
        method: "PUT",
        body: params,
      }),
      invalidatesTags: ["Allocation"],
    }),
  }),
});

// Websocket-driven invalidation: refresh the active allocation query on
// REFRESH_ALLOCATION or REFRESH_ALLOCATION_REQUEST_COMMENT.
invalidateOnMessage("skyportal/REFRESH_ALLOCATION", () => ["Allocation"]);
invalidateOnMessage(
  "skyportal/REFRESH_ALLOCATION_REQUEST_COMMENT",
  (payload) => (payload?.followup_request_id ? ["Allocation"] : null),
);

export const {
  useGetAllocationQuery,
  useSubmitAllocationMutation,
  useModifyAllocationMutation,
  useDeleteAllocationMutation,
  useEditFollowupRequestCommentMutation,
} = allocationApi;
