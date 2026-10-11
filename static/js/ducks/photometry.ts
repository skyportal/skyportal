/**
 * Source photometry: the query is tagged `Photometry` and the mutations
 * (delete, submit, update) invalidate it so the list refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage, findCachedQueryArg } from "../api/wsInvalidation";
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

// The id of a source in a loaded sources or candidates list (the source
// detail panel and the scanning page plot its photometry), given its key.
const findListedObjId = (getState: () => unknown, objKey: string) => {
  const queries = (getState() as any)?.skyportalApi?.queries ?? {};
  for (const entry of Object.values(queries) as any[]) {
    const rows = entry?.data?.sources ?? entry?.data?.candidates;
    if (Array.isArray(rows)) {
      const match = rows.find((row: any) => row?.internal_key === objKey);
      if (match?.id != null) {
        return match.id as string | number;
      }
    }
  }
  return null;
};

// Broadcast to every client, so it carries the source's internal_key rather
// than its id: translate it to the id of a source this client has loaded, on
// its own page or in a list, so only that source's photometry refetches.
invalidateOnMessage(REFRESH_SOURCE_PHOTOMETRY, (payload, getState) => {
  const objKey = payload?.obj_key as string | undefined;
  if (!objKey) {
    return null;
  }
  const sourceId = findCachedQueryArg(
    getState,
    "getSource",
    (data) => data?.internal_key === objKey,
  ) as string | number | null;
  const objId = sourceId ?? findListedObjId(getState, objKey);
  return objId != null ? photometryTag(objId) : null;
});

export const {
  useFetchSourcePhotometryQuery,
  useLazyFetchSourcePhotometryQuery,
  useDeletePhotometryMutation,
  useSubmitPhotometryMutation,
  useUpdatePhotometryMutation,
} = photometryApi;
