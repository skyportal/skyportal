/**
 * Source photometry: the query is tagged `Photometry` and the mutations
 * (delete, submit, update) invalidate it so the list refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage, findCachedSourceId } from "../api/wsInvalidation";
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

// Loaded lists whose rows carry their source's internal_key and plot its
// photometry: the path to the list in the cached data, and the row field that
// holds the source's id.
const KEYED_LISTS: [string[], string][] = [
  [["sources"], "id"], // sources table detail panel
  [["candidates"], "id"], // scanning page
  [["assignments"], "obj_id"], // observing run summary
  [["allocation", "requests"], "obj_id"], // allocation follow-up requests
];

// The id of a source in one of those loaded lists, given its key.
const findListedObjId = (getState: () => unknown, objKey: string) => {
  const queries = (getState() as any)?.skyportalApi?.queries ?? {};
  for (const entry of Object.values(queries) as any[]) {
    for (const [path, idField] of KEYED_LISTS) {
      const rows = path.reduce((data: any, key) => data?.[key], entry?.data);
      if (Array.isArray(rows)) {
        const match = rows.find((row: any) => row?.internal_key === objKey);
        if (match?.[idField] != null) {
          return match[idField] as string | number;
        }
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
  const objId =
    findCachedSourceId(getState, objKey) ?? findListedObjId(getState, objKey);
  return objId != null ? photometryTag(objId) : null;
});

export const {
  useFetchSourcePhotometryQuery,
  useLazyFetchSourcePhotometryQuery,
  useDeletePhotometryMutation,
  useSubmitPhotometryMutation,
  useUpdatePhotometryMutation,
} = photometryApi;
