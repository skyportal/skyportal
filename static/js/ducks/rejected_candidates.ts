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
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const rejectedCandidatesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getRejectedCandidates: build.query<string[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, async (client) =>
          (await client.fetchListings({ listName: "rejected_candidates" }))
            .map((rej) => rej.obj_id)
            // obj_id is NOT NULL server-side; the null check goes away once
            // skyportal-js models it as required (skyportal-js#6).
            .filter((objId): objId is string => objId != null),
        ),
      providesTags: ["RejectedCandidates"],
    }),
    addToRejected: build.mutation<{ id: number }, string>({
      queryFn: (obj_id, api) =>
        clientQuery(api, (client) =>
          client.postListing({ obj_id, list_name: "rejected_candidates" }),
        ),
      invalidatesTags: ["RejectedCandidates"],
    }),
    removeFromRejected: build.mutation<void, string>({
      queryFn: (obj_id, api) =>
        clientQuery(api, (client) =>
          client.deleteListingByName(obj_id, "rejected_candidates"),
        ),
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
