/**
 * Source photometry.
 *
 * RTK Query conversion of the old `FETCH_SOURCE_PHOTOMETRY` duck. The query
 * fetches a source's photometry and is tagged `Photometry`; the mutations
 * (delete, submit, update) invalidate it so the list refetches.
 *
 * The websocket `REFRESH_SOURCE_PHOTOMETRY` message is bridged to `Photometry`
 * tag invalidation via `invalidateOnMessage`, preserving the old conditional
 * logic (only refresh when the currently-loaded source matches the pushed
 * obj_id).
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

const REFRESH_SOURCE_PHOTOMETRY = "skyportal/REFRESH_SOURCE_PHOTOMETRY";

export interface PhotometryPoint {
  id: number;
  obj_id: string;
  [key: string]: any;
}

export const photometryApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // Photometry points carry many optional, app-specific fields, so the element
    // type is `any` (the `PhotometryPoint` interface above documents the stable
    // fields).
    fetchSourcePhotometry: build.query<
      any[],
      { id: number | string; params?: { [key: string]: any } }
    >({
      query: ({ id, params = {} }) => ({
        url: `/api/sources/${id}/photometry`,
        params: {
          includeOwnerInfo: true,
          includeStreamInfo: true,
          includeValidationInfo: true,
          ...params,
        },
      }),
      providesTags: ["Photometry"],
    }),
    deletePhotometry: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `/api/photometry/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Photometry"],
    }),
    submitPhotometry: build.mutation<unknown, any>({
      query: (photometry) => ({
        url: "/api/photometry?refresh=true",
        method: "POST",
        body: photometry,
      }),
      invalidatesTags: ["Photometry"],
    }),
    updatePhotometry: build.mutation<
      unknown,
      { id: number | string; photometry: any }
    >({
      query: ({ id, photometry }) => ({
        url: `/api/photometry/${id}?refresh=true`,
        method: "PATCH",
        body: photometry,
      }),
      invalidatesTags: ["Photometry"],
    }),
  }),
});

// Websocket-driven invalidation: refresh photometry on
// REFRESH_SOURCE_PHOTOMETRY. Active queries already keyed to the pushed obj_id
// will refetch; others stay untouched.
invalidateOnMessage(REFRESH_SOURCE_PHOTOMETRY, (payload) =>
  payload?.obj_id != null ? ["Photometry"] : null,
);

export const {
  useFetchSourcePhotometryQuery,
  useLazyFetchSourcePhotometryQuery,
  useDeletePhotometryMutation,
  useSubmitPhotometryMutation,
  useUpdatePhotometryMutation,
} = photometryApi;
