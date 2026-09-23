import dayjs from "dayjs";

import { buildQueryString, filterOutEmptyValues, pickParams } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { findCachedQueryArg, invalidateOnMessage } from "../api/wsInvalidation";

export type FilterParams = Record<string, any>;

export interface SourcesResult {
  sources: { [key: string]: any }[] | null;
  totalMatches: number;
  pageNumber: number;
  numPerPage: number;
  queryID?: string | null;
  [key: string]: any;
}

const QUERY_KEYS = [
  "TNSname",
  "alias",
  "annotationsFilter",
  "annotationsFilterAfter",
  "annotationsFilterBefore",
  "annotationsFilterOrigin",
  "classifications",
  "classifications_simul",
  "classified",
  "commentsFilter",
  "commentsFilterAfter",
  "commentsFilterAuthor",
  "commentsFilterBefore",
  "createdOrModifiedAfter",
  "currentUserLabeller",
  "dec",
  "deduplicatePhotometry",
  "detectedWindowEnd",
  "detectedWindowStart",
  "endDate",
  "excludeForcedPhotometry",
  "followupRequestStatus",
  "group_ids",
  "hasBeenLabelled",
  "hasFollowupRequest",
  "hasNoSpectrum",
  "hasNoTNSname",
  "hasNotBeenLabelled",
  "hasSpectrum",
  "hasSpectrumAfter",
  "hasSpectrumBefore",
  "hasTNSname",
  "includeAnalyses",
  "includeAssociatedObjs",
  "includeCandidates",
  "includeColorMagnitude",
  "includeCommentExists",
  "includeComments",
  "includeDetectionStats",
  "includeGCNCrossmatches",
  "includeGCNNotes",
  "includeGeoJSON",
  "includeHosts",
  "includeLabellers",
  "includePeriodExists",
  "includePhotometry",
  "includePhotometryExists",
  "includeRequested",
  "includeSourcesInGcn",
  "includeSpectrumExists",
  "includeSuperObjs",
  "includeTags",
  "includeThumbnails",
  "listName",
  "localizationCumprob",
  "localizationDateobs",
  "localizationName",
  "localizationRejectSources",
  "maxLatestMagnitude",
  "maxPeakMagnitude",
  "maxRedshift",
  "minLatestMagnitude",
  "minPeakMagnitude",
  "minRedshift",
  "nonclassifications",
  "numPerPage",
  "numberDetections",
  "origin",
  "pageNumber",
  "pendingOnly",
  "queryID",
  "ra",
  "radius",
  "rejectedSourceIDs",
  "removeNested",
  "requireDetections",
  "saveSummary",
  "savedAfter",
  "savedBefore",
  "savedByCurrentUser",
  "simbadClass",
  "sortBy",
  "sortOrder",
  "sourceID",
  "spatialCatalogEntryName",
  "spatialCatalogName",
  "startDate",
  "unclassified",
  "useCache",
] as const;

const addFilterParamDefaults = (filterParams: FilterParams): FilterParams => ({
  numPerPage: 30,
  ...filterParams,
  includeColorMagnitude: true,
  includeThumbnails: true,
  includeDetectionStats: true,
  includeLabellers: true,
  includeHosts: true,
});

// The backend rejects a queryID on page 1 and requires one past it.
const withQueryCache = (params: FilterParams): FilterParams => {
  const p = { ...params };
  if (Number(p["pageNumber"] ?? 1) > 1) {
    if (p["queryID"]) p["useCache"] = true;
    else delete p["useCache"];
  } else {
    delete p["queryID"];
    p["useCache"] = true;
  }
  return p;
};

const buildSourcesUrl = (params: FilterParams, removeFalse = true): string =>
  `/api/sources?${buildQueryString(
    filterOutEmptyValues(
      pickParams(withQueryCache(params), QUERY_KEYS),
      true,
      removeFalse,
    ),
  )}`;

export const sourcesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => {
    const listQuery = (extra: FilterParams = {}) =>
      build.query<SourcesResult, FilterParams | void>({
        query: (filterParams) =>
          buildSourcesUrl({
            ...addFilterParamDefaults(filterParams ?? {}),
            ...extra,
          }),
        providesTags: ["Sources"],
      });

    return {
      fetchSources: listQuery(),
      fetchSavedGroupSources: listQuery(),
      fetchPendingGroupSources: listQuery({ pendingOnly: true }),
      fetchFavoriteSources: listQuery({ listName: "favorites" }),
      fetchGcnEventSources: build.query<
        SourcesResult,
        { dateobs: any; filterParams?: FilterParams }
      >({
        query: ({ dateobs, filterParams = {} }) => {
          const params = addFilterParamDefaults(filterParams);
          params["localizationDateobs"] = dateobs;
          // startDate/endDate require the whole detection history inside the window.
          if (params["startDate"] != null) {
            params["detectedWindowStart"] ??= params["startDate"];
            delete params["startDate"];
          }
          if (params["endDate"] != null) {
            params["detectedWindowEnd"] ??= params["endDate"];
            delete params["endDate"];
          }
          if (dateobs) {
            params["detectedWindowStart"] ??= dayjs(dateobs).format(
              "YYYY-MM-DD HH:mm:ss",
            );
            params["detectedWindowEnd"] ??= dayjs(dateobs)
              .add(7, "day")
              .format("YYYY-MM-DD HH:mm:ss");
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
        query: ({ catalogName, entryName, filterParams = {} }) =>
          buildSourcesUrl({
            ...addFilterParamDefaults(filterParams),
            spatialCatalogName: catalogName,
            spatialCatalogEntryName: entryName,
          }),
        providesTags: ["Sources"],
      }),
      getAltdataInfo: build.query<{ keys: Record<string, string>[] }, void>({
        query: () => "api/internal/altdata_info",
        providesTags: ["AltdataInfo"],
      }),
    };
  },
});

invalidateOnMessage("skyportal/REFRESH_FAVORITE_SOURCES", () =>
  window.location.pathname === "/favorites" ? ["Sources"] : null,
);

invalidateOnMessage("skyportal/FETCH_GCNEVENT_SOURCES", (payload, getState) => {
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
