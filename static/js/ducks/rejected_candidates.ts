/**
 * Rejected candidates (user listing "rejected_candidates").
 *
 * RTK Query conversion of the old `FETCH_REJECTED_CANDIDATES` duck. The list of
 * rejected obj_ids is fetched from `/api/listing`, and add/remove are mutations
 * against the same endpoint. The old reducer mapped the listing entries down to
 * their `obj_id`, so `transformResponse` preserves that shape (a `string[]`).
 *
 * The websocket `REFRESH_REJECTED_CANDIDATES` message invalidates the
 * `RejectedCandidates` tag so any active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface ListingEntry {
  obj_id: string;
  [key: string]: unknown;
}

export const rejectedCandidatesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getRejectedCandidates: build.query<string[], void>({
      query: () => "api/listing?listName=rejected_candidates",
      transformResponse: (data: ListingEntry[]) =>
        (data ?? []).map((rej) => rej.obj_id),
      providesTags: ["RejectedCandidates"],
    }),
    addToRejected: build.mutation<unknown, string>({
      query: (obj_id) => ({
        url: "api/listing",
        method: "POST",
        body: { list_name: "rejected_candidates", obj_id },
      }),
      invalidatesTags: ["RejectedCandidates"],
    }),
    removeFromRejected: build.mutation<unknown, string>({
      query: (obj_id) => ({
        url: "api/listing",
        method: "DELETE",
        body: { list_name: "rejected_candidates", obj_id },
      }),
      invalidatesTags: ["RejectedCandidates"],
    }),
  }),
});

// Websocket message handler -> cache invalidation.
invalidateOnMessage("skyportal/REFRESH_REJECTED_CANDIDATES", () => [
  "RejectedCandidates",
]);

export const {
  useGetRejectedCandidatesQuery,
  useAddToRejectedMutation,
  useRemoveFromRejectedMutation,
} = rejectedCandidatesApi;
