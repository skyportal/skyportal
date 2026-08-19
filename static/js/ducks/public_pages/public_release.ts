/**
 * Public releases (public_pages/release).
 *
 * RTK Query conversion of the old `FETCH_PUBLIC_RELEASES` duck. The list query
 * is injected into the central `skyportalApi`; submit/update/delete are
 * mutations that invalidate the `PublicRelease` tag so the list refetches.
 *
 * The websocket `REFRESH_PUBLIC_RELEASES` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import type {
  PublicRelease,
  PublicReleasePost,
  PublicReleaseUpdate,
} from "skyportal-js/PublicPages";

import { skyportalApi } from "../../api/skyportalApi";
import { clientQuery } from "../../api/skyportalClient";
import { invalidateOnMessage } from "../../api/wsInvalidation";

export type { PublicRelease };

export const publicReleaseApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getPublicReleases: build.query<PublicRelease[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchPublicReleases()),
      providesTags: ["PublicRelease"],
    }),
    submitPublicRelease: build.mutation<{ id: number }, PublicReleasePost>({
      queryFn: (payload, api) =>
        clientQuery(api, (client) => client.postPublicRelease(payload)),
      invalidatesTags: ["PublicRelease"],
    }),
    updatePublicRelease: build.mutation<
      void,
      { releaseId: number; payload: PublicReleaseUpdate }
    >({
      queryFn: ({ releaseId, payload }, api) =>
        clientQuery(api, (client) =>
          client.updatePublicRelease(releaseId, payload),
        ),
      invalidatesTags: ["PublicRelease"],
    }),
    deletePublicRelease: build.mutation<void, number>({
      queryFn: (releaseId, api) =>
        clientQuery(api, (client) => client.deletePublicRelease(releaseId)),
      invalidatesTags: ["PublicRelease"],
    }),
  }),
});

// Websocket: old handler refetched public releases on REFRESH_PUBLIC_RELEASES.
invalidateOnMessage("skyportal/REFRESH_PUBLIC_RELEASES", () => [
  "PublicRelease",
]);

export const {
  useGetPublicReleasesQuery,
  useSubmitPublicReleaseMutation,
  useUpdatePublicReleaseMutation,
  useDeletePublicReleaseMutation,
} = publicReleaseApi;
