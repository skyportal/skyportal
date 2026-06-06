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
import { skyportalApi } from "../../api/skyportalApi";
import { invalidateOnMessage } from "../../api/wsInvalidation";

export interface PublicRelease {
  id: number;
  name: string;
  link_name: string;
  description?: string | null;
  group_ids: number[];
  options?: unknown;
  [key: string]: unknown;
}

export const publicReleaseApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getPublicReleases: build.query<PublicRelease[], void>({
      query: () => "api/public_pages/release",
      providesTags: ["PublicRelease"],
    }),
    submitPublicRelease: build.mutation<unknown, PublicRelease>({
      query: (payload) => ({
        url: "api/public_pages/release",
        method: "POST",
        body: payload,
      }),
      invalidatesTags: ["PublicRelease"],
    }),
    updatePublicRelease: build.mutation<
      unknown,
      { releaseId: number; payload: PublicRelease }
    >({
      query: ({ releaseId, payload }) => ({
        url: `api/public_pages/release/${releaseId}`,
        method: "PATCH",
        body: payload,
      }),
      invalidatesTags: ["PublicRelease"],
    }),
    deletePublicRelease: build.mutation<unknown, number>({
      query: (releaseId) => ({
        url: `api/public_pages/release/${releaseId}`,
        method: "DELETE",
      }),
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
