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
import { photometryTag } from "./photometryTags";
import { brokersApi } from "./brokers";
import type { RouteData } from "../types/routeSchemaMap";

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
      PhotometryPoint[],
      { id: number | string; params?: { [key: string]: any } }
    >({
      async queryFn({ id, params = {} }, api, _extraOptions, baseQuery) {
        // The broker flagged `default_photometry`, if any, serves this fetch:
        // saved points merged with on-demand broker photometry, same response
        // shape. Its list is awaited, not read from the store, which is still
        // empty when a page first renders.
        const { data: brokers } = await api.dispatch(
          brokersApi.endpoints.getBrokers.initiate(undefined, {
            subscribe: false,
          }),
        );
        const broker = (brokers || []).find(
          (b) =>
            b.active &&
            b.capabilities?.["get_photometry"] &&
            b.default_photometry,
        );
        return baseQuery({
          url: broker
            ? `/api/brokers/photometry/${encodeURIComponent(String(id))}`
            : `/api/sources/${id}/photometry`,
          params: {
            includeOwnerInfo: true,
            includeStreamInfo: true,
            includeValidationInfo: true,
            ...params,
          },
        }) as Promise<{ data: PhotometryPoint[] }>;
      },
      providesTags: (_result, _error, arg) => photometryTag(arg.id),
    }),
    deletePhotometry: build.mutation<
      RouteData<"DELETE /api/photometry/{photometry_id}">,
      number | string
    >({
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
      RouteData<"PATCH /api/photometry/{photometry_id}">,
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

// Scoped to the pushed object, so a push about one source does not refetch the
// photometry another page is showing.
invalidateOnMessage(REFRESH_SOURCE_PHOTOMETRY, (payload) =>
  payload?.obj_id != null ? photometryTag(payload.obj_id) : null,
);

export const {
  useFetchSourcePhotometryQuery,
  useLazyFetchSourcePhotometryQuery,
  useDeletePhotometryMutation,
  useSubmitPhotometryMutation,
  useUpdatePhotometryMutation,
} = photometryApi;
