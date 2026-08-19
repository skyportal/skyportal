/**
 * A single allocation (with its follow-up requests).
 *
 * RTK Query conversion of the old `FETCH_ALLOCATION` duck, calling the typed
 * `skyportal-js` client. `getAllocation` is keyed by the allocation id plus the
 * pagination/sort params; the backend returns `{ allocation, totalMatches }`,
 * which is preserved as the query result shape.
 *
 * Mutations (`submitAllocation`, `modifyAllocation`, `deleteAllocation`,
 * `editFollowupRequestComment`) invalidate the `Allocation` tag so any active
 * `getAllocation` query refetches.
 *
 * The websocket `REFRESH_ALLOCATION` / `REFRESH_ALLOCATION_REQUEST_COMMENT`
 * messages are bridged to cache invalidation via `invalidateOnMessage`.
 */
import type {
  AllocationPost,
  AllocationUpdate,
  FetchAllocationOptions,
} from "skyportal-js/Allocations";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

interface GetAllocationArg {
  id: number | string;
  params?: FetchAllocationOptions | undefined;
}

export const allocationApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // raw: the client's fetchAllocation drops the envelope's `totalMatches`
    // sibling, which this page needs to paginate the follow-up requests.
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
    submitAllocation: build.mutation<{ id: number }, AllocationPost>({
      queryFn: (payload, api) =>
        clientQuery(api, (client) => client.postAllocation(payload)),
      invalidatesTags: ["Allocation"],
    }),
    modifyAllocation: build.mutation<
      void,
      { id: number | string; payload: AllocationUpdate }
    >({
      queryFn: ({ id, payload }, api) =>
        clientQuery(api, (client) =>
          client.updateAllocation(Number(id), payload),
        ),
      invalidatesTags: ["Allocation"],
    }),
    deleteAllocation: build.mutation<void, number | string>({
      queryFn: (allocationID, api) =>
        clientQuery(api, (client) =>
          client.deleteAllocation(Number(allocationID)),
        ),
      invalidatesTags: ["Allocation"],
    }),
    editFollowupRequestComment: build.mutation<
      void,
      { id: number | string; params: { comment: string | null } }
    >({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.postFollowupRequestComment(Number(id), params.comment),
        ),
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
