/**
 * Source photometry: the query is tagged `Photometry` and the mutations
 * (delete, submit, update) invalidate it so the list refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import { photometryTag } from "./photometryTags";
import type { RouteData } from "../types/routeSchemaMap";

const REFRESH_SOURCE_PHOTOMETRY = "skyportal/REFRESH_SOURCE_PHOTOMETRY";

export interface PhotometryPoint {
  id: number;
  obj_id: string;
  [key: string]: any;
}

export const photometryApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    fetchSourcePhotometry: build.query<
      PhotometryPoint[],
      { id: number | string; params?: { [key: string]: any } }
    >({
      query: ({ id, params = {} }) => ({
        url: `/api/brokers/photometry/${encodeURIComponent(String(id))}`,
        params: {
          includeOwnerInfo: true,
          includeStreamInfo: true,
          includeValidationInfo: true,
          ...params,
        },
      }),
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

// scoped to the pushed object, so one source's push cannot refetch another page's
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
