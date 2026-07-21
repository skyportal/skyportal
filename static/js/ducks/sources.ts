/**
 * Sources (paginated source listings).
 *
 * RTK Query conversion of the old `FETCH_SOURCES` family of ducks. All six list
 * queries hit `/api/sources` with a different `filterParams` object; the object
 * becomes the query's cache key automatically, so each distinct page/filter is
 * cached independently.
 *
 * The websocket handlers (`REFRESH_FAVORITE_SOURCES`, `FETCH_GCNEVENT_SOURCES`,
 * `REFRESH_SOURCE`) are bridged to `Sources` tag invalidation via
 * `invalidateOnMessage`, preserving the conditional refresh logic of the old
 * `messageHandler.add(...)` callbacks.
 */
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { buildQueryString, filterOutEmptyValues } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { findCachedQueryArg, invalidateOnMessage } from "../api/wsInvalidation";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const REFRESH_SOURCE = "skyportal/REFRESH_SOURCE";
const REFRESH_FAVORITE_SOURCES = "skyportal/REFRESH_FAVORITE_SOURCES";
const FETCH_GCNEVENT_SOURCES = "skyportal/FETCH_GCNEVENT_SOURCES";

export type FilterParams = Record<string, any>;

export interface SourcesResult {
  sources: { [key: string]: any }[] | null;
  totalMatches: number;
  pageNumber: number;
  numPerPage: number;
  [key: string]: any;
}

const addFilterParamDefaults = (filterParams: FilterParams): FilterParams => {
  const params = { ...filterParams };
  if (!Object.keys(params).includes("numPerPage")) {
    params["numPerPage"] = 30;
  }
  params["includeColorMagnitude"] = true;
  params["includeThumbnails"] = true;
  params["includeDetectionStats"] = true;
  params["includeLabellers"] = true;
  params["includeHosts"] = true;
  return params;
};

/** Build a `/api/sources?...` URL from a filterParams object. */
const buildSourcesUrl = (params: FilterParams, removeFalse = true): string => {
  const filtered = filterOutEmptyValues(params, true, removeFalse);
  const queryString = buildQueryString(filtered);
  return `/api/sources?${queryString}`;
};

export const sourcesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    fetchSources: build.query<SourcesResult, FilterParams | void>({
      query: (filterParams) =>
        buildSourcesUrl(addFilterParamDefaults(filterParams ?? {})),
      providesTags: ["Sources"],
    }),
    fetchSavedGroupSources: build.query<SourcesResult, FilterParams | void>({
      query: (filterParams) =>
        buildSourcesUrl(addFilterParamDefaults(filterParams ?? {})),
      providesTags: ["Sources"],
    }),
    fetchPendingGroupSources: build.query<SourcesResult, FilterParams | void>({
      query: (filterParams) => {
        const params = addFilterParamDefaults(filterParams ?? {});
        params["pendingOnly"] = true;
        return buildSourcesUrl(params);
      },
      providesTags: ["Sources"],
    }),
    fetchFavoriteSources: build.query<SourcesResult, FilterParams | void>({
      query: (filterParams) => {
        const params = addFilterParamDefaults(filterParams ?? {});
        params["listName"] = "favorites";
        return buildSourcesUrl(params);
      },
      providesTags: ["Sources"],
    }),
    fetchGcnEventSources: build.query<
      SourcesResult,
      { dateobs: any; filterParams?: FilterParams }
    >({
      query: ({ dateobs, filterParams = {} }) => {
        const params = addFilterParamDefaults(filterParams);
        params["localizationDateobs"] = dateobs;
        if (dateobs) {
          params["startDate"] ??= dayjs(dateobs).format("YYYY-MM-DD HH:mm:ss");
          params["endDate"] ??= dayjs(dateobs)
            .add(7, "day")
            .format("YYYY-MM-DD HH:mm:ss");
          params["includeLocalizationStatus"] ??= true;
        }
        params["includeSourcesInGcn"] = true;
        params["includeGeoJSON"] = true;
        return buildSourcesUrl(params, false);
      },
      providesTags: ["Sources"],
    }),
    fetchSpatialCatalogSources: build.query<
      SourcesResult,
      { catalogName: string; entryName: string; filterParams?: FilterParams }
    >({
      query: ({ catalogName, entryName, filterParams = {} }) => {
        const params = addFilterParamDefaults(filterParams);
        params["spatialCatalogName"] = catalogName;
        params["spatialCatalogEntryName"] = entryName;
        return buildSourcesUrl(params);
      },
      providesTags: ["Sources"],
    }),
    // Distinct top-level altdata keys, for offering altdata columns on the table.
    getAltdataInfo: build.query<{ keys: Record<string, string>[] }, void>({
      query: () => "api/internal/altdata_info",
      providesTags: ["AltdataInfo"],
    }),
  }),
});

// Websocket-driven invalidation. Each handler preserves the old conditional
// refresh logic, returning the `Sources` tag to refetch active list queries or
// `null` to ignore the message.
invalidateOnMessage(REFRESH_FAVORITE_SOURCES, () =>
  window.location.pathname === "/favorites" ? ["Sources"] : null,
);

// Only refetch when the affected event's sources are actually loaded. Map the
// pushed gcnEvent id -> dateobs (the query key) via the cached event, then check
// for a loaded gcn-event-sources query. Pre-RTK this was gated on the currently-
// viewed event; unconditional invalidation refetched the heavy list every time.
invalidateOnMessage(FETCH_GCNEVENT_SOURCES, (payload, getState) => {
  const dateobs =
    payload?.gcnEvent?.dateobs ??
    (payload?.gcnEvent?.id != null
      ? findCachedQueryArg(
          getState,
          "getGcnEvent",
          (data) => data?.id === payload.gcnEvent.id,
        )
      : null);
  if (dateobs == null) return null;
  const queries = (getState() as any)?.skyportalApi?.queries ?? {};
  const onLoadedEvent = Object.values(queries).some(
    (entry: any) =>
      entry?.endpointName === "fetchGcnEventSources" &&
      entry?.originalArgs?.dateobs === dateobs,
  );
  return onLoadedEvent ? ["Sources"] : null;
});

// Only refetch when the updated source is actually on a currently-loaded page.
// Pre-RTK this handler was gated on the source being in the list (and merged a
// single source); refetching the whole heavy list on every REFRESH_SOURCE
// app-wide — these arrive at alert rates — made the sources page crawl/crash.
invalidateOnMessage(REFRESH_SOURCE, (payload, getState) => {
  const queries = (getState() as any)?.skyportalApi?.queries ?? {};
  const onLoadedPage = Object.values(queries).some((entry: any) =>
    (entry?.data?.sources as any[] | undefined)?.some(
      (s) => s.internal_key === payload?.obj_key,
    ),
  );
  return onLoadedPage ? ["Sources"] : null;
});

export const {
  useFetchSourcesQuery,
  useLazyFetchSourcesQuery,
  useFetchSavedGroupSourcesQuery,
  useLazyFetchSavedGroupSourcesQuery,
  useFetchPendingGroupSourcesQuery,
  useLazyFetchPendingGroupSourcesQuery,
  useFetchFavoriteSourcesQuery,
  useFetchGcnEventSourcesQuery,
  useFetchSpatialCatalogSourcesQuery,
  useGetAltdataInfoQuery,
} = sourcesApi;
